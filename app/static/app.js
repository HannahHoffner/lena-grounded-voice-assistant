/**
 * Browser-Client von LENA.
 *
 * Verwaltet Sprache, Navigation, kurze Sessions, Query-/Speech-Aufrufe sowie
 * die Darstellung von Backend-Karten und Leaflet-Zielen. Angebotsfakten werden
 * im Frontend weder ergänzt noch fachlich neu interpretiert.
 */
const copy = {};

const speechLanguages = {
  de: "de-DE",
  en: "en-US",
  pl: "pl-PL",
  ro: "ro-RO",
  ru: "ru-RU"
};

const state = {
  language: "de",
  category: null,
  recognition: null,
  isListening: false,
  autoListenTried: false,
  keepRecognizedStatus: false,
  sessionId: null,
  map: null,
  mapLayers: [],
  idleTimer: null,
  serverTranscriptionAvailable: false,
  mediaRecorder: null,
  mediaStream: null,
  audioChunks: [],
  listeningMode: null,
  serverSynthesisAvailable: false,
  currentSpeechAudio: null,
  currentSpeechAbort: null,
  currentSpeechCleanup: null,
  currentSpeechButton: null,
  speechRequestToken: 0,
  resultTiles: new Map(),
  lastAnswer: "",
  queryInputMode: "text",
  isSubmitting: false,
  viewToken: 0,
  queryAbort: null,
  transcriptionAbort: null
};

const SESSION_TIMEOUT_MS = 3 * 60 * 1000;

const byId = (id) => document.getElementById(id);
const recognitionConstructor = window.SpeechRecognition || window.webkitSpeechRecognition;
const dialogueUI = new window.LenaDialogueUI(
  byId("clarificationPanel"),
  byId("clarificationPrompt"),
  byId("clarificationChoices"),
  byId("clarificationSubmit"),
  (dialogId, values) => submitQuery("", { dialogId, values })
);

function text() {
  return copy[state.language] || copy.de || {};
}

async function loadApplicationCopy(language) {
  if (copy[language]) return;
  const response = await fetch(`/api/i18n/copy?language=${encodeURIComponent(language)}`);
  if (!response.ok) throw new Error("application copy unavailable");
  const payload = await response.json();
  const texts = payload.texts || {};
  const categories = {};
  Object.entries(texts).forEach(([key, value]) => {
    if (key.startsWith("category.")) categories[key.slice(9)] = value;
  });
  copy[language] = { ...texts, categories };
}

function voiceInputAvailable() {
  return Boolean(recognitionConstructor) || (
    state.serverTranscriptionAvailable
    && Boolean(navigator.mediaDevices?.getUserMedia)
    && typeof MediaRecorder !== "undefined"
  );
}

async function loadSpeechConfig() {
  try {
    const response = await fetch("/api/speech/config");
    if (!response.ok) return;
    const config = await response.json();
    state.serverTranscriptionAvailable = Boolean(config.server_transcription_available);
    state.serverSynthesisAvailable = Boolean(config.server_synthesis_available);
    updateVoiceStatusReady();
  } catch (_) {
    state.serverTranscriptionAvailable = false;
    state.serverSynthesisAvailable = false;
  }
}

function resetSessionTimeout() {
  if (state.idleTimer) window.clearTimeout(state.idleTimer);
  state.idleTimer = window.setTimeout(() => {
    resetView();
    byId("appView").hidden = true;
    byId("languageView").hidden = false;
  }, SESSION_TIMEOUT_MS);
}

function setIconButton(id, label) {
  const button = byId(id);
  button.setAttribute("aria-label", label);
  button.title = label;
  const screenReaderText = button.querySelector(".sr-only");
  if (screenReaderText) screenReaderText.textContent = label;
}

async function setLanguage(language) {
  cancelPendingInteraction();
  const viewToken = state.viewToken;
  const preserveSession = Boolean(state.sessionId);
  resetSessionTimeout();
  try {
    await loadApplicationCopy(language);
  } catch (_) {
    if (viewToken !== state.viewToken) return;
    await loadApplicationCopy("de");
    language = "de";
  }
  if (viewToken !== state.viewToken) return;
  state.language = language;
  state.category = null;
  state.autoListenTried = false;
  state.keepRecognizedStatus = false;
  document.documentElement.lang = language;
  byId("languageView").hidden = true;
  byId("appView").hidden = false;
  applyCopy();
  if (!preserveSession) resetView();
  const activeViewToken = state.viewToken;
  void (async () => {
    if (preserveSession && dialogueUI.active) {
      try {
        const response = await fetch(`/api/dialogue/copy?language=${encodeURIComponent(language)}`);
        if (response.ok) {
          const payload = await response.json();
          if (activeViewToken === state.viewToken) dialogueUI.relocalize(payload);
        }
      } catch (_) {
        // Freie Text- und Spracheingabe bleiben bei einem Copy-Fehler erhalten.
      }
    }
    await loadSpeechConfig();
    if (activeViewToken !== state.viewToken) return;
    await speakIntroThenListen();
  })();
}

function applyCopy() {
  const value = text();
  byId("languageTitle").textContent = value.languageTitle;
  byId("languageIntro").textContent = value.languageIntro;
  byId("mainTitle").textContent = value.mainTitle;
  byId("mainIntro").textContent = value.mainIntro;
  byId("queryLabel").textContent = value.queryLabel;
  byId("queryInput").placeholder = value.placeholder;
  byId("submitButton").setAttribute("aria-label", value.send);
  byId("submitButton").title = value.send;
  byId("submitButtonLabel").textContent = value.send;
  byId("answerTitle").textContent = value.answer;
  byId("replayAnswerButton").setAttribute("aria-label", value.replayAnswer);
  byId("replayAnswerButton").title = value.replayAnswer;
  byId("replayAnswerLabel").textContent = value.replayAnswer;
  byId("questionEchoLabel").textContent = value.questionEcho;
  byId("historyTitle").textContent = value.historyTitle;
  byId("mapTitle").textContent = value.mapTitle;
  byId("mapHint").textContent = value.mapHint;
  byId("micButtonLabel").textContent = value.micLabel;
  setIconButton("startButton", value.navStart);
  setIconButton("backButton", value.navBack);
  setIconButton("languageButton", value.navLanguage);
  byId("micButton").setAttribute("aria-label", value.micLabel);
  byId("micButton").title = value.micLabel;
  renderCategories();
  updateVoiceStatusReady();
}

const categoryIcons = {
  food: `
    <svg viewBox="0 0 64 64" focusable="false" class="category-food-icon">
      <path d="M14 8v18"></path>
      <path d="M8 8v10c0 5 3 8 6 8s6-3 6-8V8"></path>
      <path d="M14 26v30"></path>
      <path d="M32 8c-5 0-8 6-8 15s3 15 8 15 8-6 8-15S37 8 32 8Z"></path>
      <path d="M32 38v18"></path>
      <path d="M52 8v48"></path>
      <path d="M46 8v20c0 4 2 7 6 7"></path>
    </svg>
  `,
  sleep: `
    <svg viewBox="0 0 64 64" focusable="false" class="category-sleep-icon">
      <path d="M8 28 32 10l24 18"></path>
      <path d="M14 28v24"></path>
      <path d="M50 28v24"></path>
      <path d="M14 52h36"></path>
      <path d="M18 42h28"></path>
      <path d="M18 34h12a6 6 0 0 1 6 6v2"></path>
      <path d="M18 34v8"></path>
    </svg>
  `,
  medical: `
    <svg viewBox="0 0 64 64" focusable="false" class="category-medical-icon">
      <path d="M24 10h16v14h14v16H40v14H24V40H10V24h14Z"></path>
    </svg>
  `,
  advice: `
    <svg viewBox="0 0 64 64" focusable="false" class="category-advice-icon">
      <path d="M12 16h40v26H30L18 52V42h-6Z"></path>
      <path d="M22 26h20"></path>
      <path d="M22 34h14"></path>
    </svg>
  `,
  toilet: `
    <svg viewBox="0 0 64 64" focusable="false" aria-hidden="true">
      <path d="M14 10h36v44H14z"></path>
      <path d="M32 10v44"></path>
      <circle cx="23" cy="21" r="3"></circle>
      <path d="M18 39v-8c0-4 2-6 5-6s5 2 5 6v8M20 39v10M26 39v10"></path>
      <circle cx="41" cy="21" r="3"></circle>
      <path d="M36 38l2-11h6l2 11M38 38v11M44 38v11"></path>
    </svg>
  `
};

function renderCategories() {
  const grid = byId("categoryGrid");
  grid.replaceChildren();
  for (const [category, label] of Object.entries(text().categories)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "category-button";
    button.dataset.category = category;
    button.setAttribute("aria-pressed", String(state.category === category));
    const icon = document.createElement("span");
    icon.className = "category-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.innerHTML = categoryIcons[category] || "";
    const caption = document.createElement("span");
    caption.textContent = label;
    button.append(icon, caption);
    button.addEventListener("click", () => {
      resetSessionTimeout();
      state.category = category;
      state.queryInputMode = "text";
      renderCategories();
      void submitQuery("");
    });
    grid.appendChild(button);
  }
}

// Cancellation is also a visibility boundary: transports may complete despite
// abort, so callbacks must check the view token before touching the next user.
function cancelPendingInteraction() {
  state.viewToken += 1;
  state.queryAbort?.abort();
  state.queryAbort = null;
  state.transcriptionAbort?.abort();
  state.transcriptionAbort = null;
  state.isSubmitting = false;
  byId("statusLine").textContent = "";
  dialogueUI.restore();
  stopSpeechOutput();
  if (state.recognition) {
    const recognition = state.recognition;
    state.recognition = null;
    recognition.onstart = recognition.onresult = recognition.onerror = recognition.onend = null;
    try { recognition.abort(); } catch (_) { /* Already stopped. */ }
  }
  if (state.mediaRecorder) {
    const recorder = state.mediaRecorder;
    recorder.ondataavailable = recorder.onstop = null;
    try { if (recorder.state !== "inactive") recorder.stop(); } catch (_) { /* Release tracks below. */ }
  }
  state.mediaStream?.getTracks().forEach((track) => track.stop());
  state.mediaStream = state.mediaRecorder = null;
  state.audioChunks = [];
  state.isListening = false;
  state.listeningMode = null;
}

function resetView() {
  cancelPendingInteraction();
  resetSessionTimeout();
  state.category = null;
  state.queryInputMode = "text";
  state.keepRecognizedStatus = false;
  state.sessionId = null;
  dialogueUI.clear();
  byId("queryInput").value = "";
  byId("searchView").hidden = false;
  byId("resultView").hidden = true;
  byId("answerText").textContent = "";
  byId("statusLine").textContent = "";
  byId("questionEchoText").textContent = "";
  renderSafetyState(null);
  byId("replayAnswerButton").hidden = true;
  state.lastAnswer = "";
  byId("cardList").replaceChildren();
  state.resultTiles = new Map();
  byId("questionEcho").hidden = true;
  byId("historyPanel").hidden = true;
  byId("historyList").replaceChildren();
  clearMap();
  renderCategories();
  updateVoiceStatusReady();
}

function backToSearch() {
  cancelPendingInteraction();
  resetSessionTimeout();
  state.keepRecognizedStatus = false;
  byId("searchView").hidden = false;
  byId("resultView").hidden = true;
  byId("answerText").textContent = "";
  byId("replayAnswerButton").hidden = true;
  state.lastAnswer = "";
  byId("cardList").replaceChildren();
  state.resultTiles = new Map();
  byId("questionEcho").hidden = true;
  clearMap();
  renderCategories();
  updateVoiceStatusReady();
  byId("queryInput").focus();
}

function addField(card, label, values, options = {}) {
  const list = Array.isArray(values) ? values.filter(Boolean) : (values ? [values] : []);
  if (!list.length) return;
  const group = document.createElement("div");
  group.className = "card-field";
  const heading = document.createElement("strong");
  heading.textContent = label;
  group.appendChild(heading);
  const translated = options.keepSource ? list : list.map(localizeCardText);
  if (translated.length === 1) {
    const value = document.createElement("p");
    value.textContent = translated[0];
    group.appendChild(value);
  } else {
    const ul = document.createElement("ul");
    for (const item of translated) {
      const li = document.createElement("li");
      li.textContent = item;
      ul.appendChild(li);
    }
    group.appendChild(ul);
  }
  card.appendChild(group);
}

// `spokenText` must be exactly a string the backend already vouched for --
// either the main answer (replay button) or one card's server-built
// `spoken_text` (see app/spoken_text.py). /api/speech/synthesize rejects
// (409) anything else, so this can never be built client-side from other
// fields; see buildOfferTile().
function createListenButton(spokenText) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "icon-button replay-button card-listen-button";
  button.setAttribute("aria-label", text().listenToOffer);
  button.title = text().listenToOffer;
  button.setAttribute("aria-pressed", "false");
  button.innerHTML = `
    <span class="replay-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" focusable="false">
        <path d="M4 9v6h4l5 4V5L8 9Z"></path>
        <path d="M16 9.5a4 4 0 0 1 0 5"></path>
        <path d="M18.5 7a7 7 0 0 1 0 10"></path>
      </svg>
    </span>
  `;
  button.addEventListener("click", (event) => {
    // The button lives inside a <summary> (see buildOfferTile); without this the
    // click would also trigger <details>'s native open/close toggle.
    event.stopPropagation();
    resetSessionTimeout();
    void speakText(spokenText, button);
  });
  return button;
}

// `OfferCard` (data.cards) and `MapDestination` (data.map_data.destinations)
// describe offers with slightly different field names. Selected cards without
// verified coordinates remain useful result information and are converted here
// without inventing a marker or location.
function offerCardAsDestination(card) {
  return {
    id: card.id,
    label: card.name,
    address: card.address,
    distance_meters: null,
    description: card.short_description,
    phone_numbers: card.phone_numbers,
    opening_hours: card.opening_hours_raw,
    services: card.services,
    standzeiten_raw: card.standzeiten_raw,
    notes: card.notes,
    record_type: card.record_type,
    district: card.district,
    facilities: card.facilities,
    fee_raw: card.fee_raw,
    source_attribution: card.source_attribution,
    location_description: card.location_description,
    cost_status: card.cost_status,
    seasonal_status: card.seasonal_status,
    spoken_text: card.spoken_text
  };
}

function destinationRepresentsCard(destination, card) {
  const destinationId = String(destination.id || "");
  return destinationId === card.id || destinationId.startsWith(`${card.id}:`);
}

function resultItems(cards, mapData) {
  const destinations = mapData && Array.isArray(mapData.destinations)
    ? mapData.destinations
    : [];
  const unmappedCards = cards.filter(
    (card) => !destinations.some((destination) => destinationRepresentsCard(destination, card))
  );
  return [...destinations, ...unmappedCards.map(offerCardAsDestination)];
}

// One collapsible "Tafel" per offer/place. Collapsed: name, address, distance.
// Expanded (click, or via expandResultTile() from a map marker click): every
// field the old full-detail card used to show unconditionally.
function buildOfferTile(item) {
  const name = item.label || item.name;

  const tile = document.createElement("details");
  tile.className = "offer-tile";
  tile.dataset.resultId = item.id;

  const summary = document.createElement("summary");
  const heading = document.createElement("div");
  heading.className = "offer-tile-heading";
  const title = document.createElement("strong");
  title.textContent = name;
  heading.appendChild(title);
  if (state.serverSynthesisAvailable && item.spoken_text) {
    heading.appendChild(createListenButton(item.spoken_text));
  }
  summary.appendChild(heading);
  const distance = Number.isFinite(item.distance_meters)
    ? `${Math.round(item.distance_meters / 100) / 10} km`
    : null;
  const meta = document.createElement("p");
  meta.className = "offer-tile-meta";
  meta.textContent = [item.address, distance].filter(Boolean).join(" · ");
  summary.appendChild(meta);
  tile.appendChild(summary);

  const body = document.createElement("div");
  body.className = "offer-tile-body";
  tile.appendChild(body);

  if (item.record_type === "public_toilet") {
    tile.classList.add("public-toilet-card");
    addField(body, text().district, item.district, { keepSource: true });
    addField(body, text().hours, item.opening_hours, { keepSource: true });
    addField(body, text().facilities, item.facilities, { keepSource: true });
    addField(body, text().fee, item.fee_raw, { keepSource: true });
    addField(body, text().source, item.source_attribution, { keepSource: true });
    return tile;
  }
  if (item.record_type === "drinking_fountain") {
    tile.classList.add("drinking-fountain-card");
    addField(body, text().drinkingFountain, item.location_description || item.description, { keepSource: true });
    addField(body, text().address, item.address, { keepSource: true });
    if (item.cost_status === "free") {
      addField(body, text().fee, text().freeWater, { keepSource: true });
    }
    if (item.seasonal_status === "april_to_october") {
      addField(body, text().hours, text().seasonalOperation, { keepSource: true });
    }
    addField(body, text().airDistance, distance, { keepSource: true });
    addField(body, text().source, item.source_attribution, { keepSource: true });
    return tile;
  }
  addField(body, text().description, item.description);
  addField(body, text().services, item.services);
  addField(body, text().address, item.address, { keepSource: true });
  addField(body, text().phone, item.phone_numbers);
  addField(body, text().hours, item.opening_hours);
  addField(body, text().standTimes, item.standzeiten_raw);
  addField(body, text().notes, item.notes);
  return tile;
}

// Renders every mapped place plus selected offers that have no verified map
// destination. A destination such as `21:hbf-west` represents its parent offer
// `21`, so a verified stand and its generic offer card are not duplicated.
function renderResultList(cards, mapData) {
  const container = byId("cardList");
  container.replaceChildren();
  state.resultTiles = new Map();
  const items = resultItems(cards, mapData);
  for (const item of items) {
    const tile = buildOfferTile(item);
    state.resultTiles.set(item.id, tile);
    container.appendChild(tile);
  }
}

// Called when a map marker is clicked (see renderMap): opens and scrolls to
// the matching tile so the marker and the list stay in sync.
function expandResultTile(id) {
  const tile = state.resultTiles && state.resultTiles.get(id);
  if (!tile) return;
  tile.open = true;
  tile.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function displayQuestionFor(query) {
  if (query) return query;
  return state.category ? text().categories[state.category] || "" : "";
}

function renderQuestionEcho(question) {
  const value = question.trim();
  byId("questionEcho").hidden = !value;
  byId("questionEchoText").textContent = value;
}

function renderHistory(history) {
  const panel = byId("historyPanel");
  const list = byId("historyList");
  list.replaceChildren();
  panel.hidden = !history || history.length <= 1;
  for (const turn of history || []) {
    const item = document.createElement("article");
    item.className = "history-turn";
    const question = document.createElement("p");
    question.className = "history-question";
    question.textContent = turn.question;
    const answer = document.createElement("p");
    answer.className = "history-answer";
    answer.textContent = turn.answer;
    item.append(question, answer);
    list.appendChild(item);
  }
}

function renderSafetyState(answerType) {
  const resultView = byId("resultView");
  const answerText = byId("answerText");
  const safety = ["acute_risk", "acute_risk_clarification", "technical_fallback"].includes(answerType);
  resultView.classList.toggle("safety-result", safety);
  byId("answerTitle").textContent = safety ? text().safetyHeading : text().answer;
  if (safety) {
    resultView.setAttribute("aria-live", "off");
    answerText.setAttribute("role", "alert");
    answerText.setAttribute("aria-live", "assertive");
    answerText.setAttribute("tabindex", "-1");
  } else {
    resultView.setAttribute("aria-live", "polite");
    answerText.removeAttribute("role");
    answerText.removeAttribute("aria-live");
    answerText.removeAttribute("tabindex");
  }
  return safety;
}

function clearMap() {
  byId("mapPanel").hidden = true;
  if (state.map) {
    for (const layer of state.mapLayers) {
      layer.remove();
    }
  }
  state.mapLayers = [];
}

function ensureMap() {
  if (!window.L) return null;
  if (state.map) return state.map;
  state.map = L.map("answerMap", { scrollWheelZoom: false });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap",
    maxZoom: 19
  }).addTo(state.map);
  return state.map;
}

function buildMapPopup(label, address, details = []) {
  const container = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = label ?? "";
  container.appendChild(title);

  const addressText = address ?? "";
  if (addressText) {
    container.appendChild(document.createElement("br"));
    container.appendChild(document.createTextNode(addressText));
  }
  for (const detail of details.filter(Boolean)) {
    container.appendChild(document.createElement("br"));
    container.appendChild(document.createTextNode(detail));
  }
  return container;
}

function renderMap(mapData) {
  // Das Backend liefert bereits transformierte und fachlich gefilterte Ziele;
  // der Browser visualisiert sie ohne eine zweite Rankinglogik.
  // The tile list itself comes from renderResultList(), called separately
  // with the same map_data -- this only draws markers and, on marker click,
  // expands the matching tile (see expandResultTile()).
  clearMap();
  if (!mapData || !mapData.destinations || !mapData.destinations.length) return;
  byId("mapPanel").hidden = false;
  const map = ensureMap();
  const bounds = [];

  const origin = mapData.origin;
  if (map) {
    const originMarker = L.circleMarker([origin.latitude, origin.longitude], {
      radius: 8,
      color: "#073b6d",
      fillColor: "#073b6d",
      fillOpacity: 1
    }).bindPopup(buildMapPopup(origin.label, origin.address)).addTo(map);
    state.mapLayers.push(originMarker);
    bounds.push([origin.latitude, origin.longitude]);
  }

  for (const destination of mapData.destinations) {
    if (!map) continue;
    const isToilet = destination.record_type === "public_toilet";
    const isFountain = destination.record_type === "drinking_fountain";
    const fountainDetails = isFountain ? [
      text().drinkingFountain,
      destination.cost_status === "free" ? text().freeWater : null,
      destination.seasonal_status === "april_to_october" ? text().seasonalOperation : null,
      text().operationUnknown,
      destination.source_attribution
    ] : [];
    let marker;
    if (isFountain) {
      const iconElement = document.createElement("span");
      iconElement.className = "drinking-fountain-symbol";
      iconElement.setAttribute("aria-hidden", "true");
      const iconGlyph = document.createElement("span");
      iconGlyph.className = "drinking-fountain-glyph";
      iconGlyph.textContent = "💧";
      iconElement.appendChild(iconGlyph);
      marker = L.marker([destination.latitude, destination.longitude], {
        icon: L.divIcon({
          className: "drinking-fountain-marker",
          html: iconElement,
          iconSize: [34, 40],
          iconAnchor: [17, 36]
        })
      });
    } else {
      marker = L.circleMarker([destination.latitude, destination.longitude], {
        radius: isToilet ? 11 : 9,
        color: isToilet ? "#005b4f" : "#005ea8",
        fillColor: isToilet ? "#27a889" : "#f28c00",
        fillOpacity: 0.92,
        dashArray: isToilet ? "4 2" : null
      });
    }
    marker.bindPopup(buildMapPopup(
      destination.label,
      destination.address,
      isToilet ? [destination.fee_raw, ...(destination.opening_hours || [])] : fountainDetails
    )).addTo(map);
    marker.on("click", () => expandResultTile(destination.id));
    const markerElement = marker.getElement();
    if (markerElement) {
      markerElement.setAttribute("role", "img");
      markerElement.setAttribute(
        "aria-label",
        isToilet
          ? `${text().categories.toilet}: ${destination.label}`
          : isFountain
          ? `${text().drinkingFountain}: ${destination.label}`
          : destination.label
      );
    }
    state.mapLayers.push(marker);
    bounds.push([destination.latitude, destination.longitude]);
  }
  if (map && bounds.length) {
    setTimeout(() => {
      map.invalidateSize();
      map.fitBounds(bounds, { padding: [24, 24], maxZoom: 15 });
    }, 40);
  }
}

async function submitQuery(query, dialogSubmission = null) {
  if (state.isSubmitting) return;
  cancelPendingInteraction();
  const viewToken = state.viewToken;
  const controller = new AbortController();
  state.queryAbort = controller;
  state.isSubmitting = true;
  if (dialogueUI.active) dialogueUI.disable();
  // Die Session-ID verbindet kurze Folgefragen. Alle Fakten werden mit jeder
  // Antwort erneut vom Backend geliefert.
  resetSessionTimeout();
  byId("searchView").hidden = false;
  byId("resultView").hidden = false;
  byId("statusLine").textContent = text().loading;
  byId("answerText").textContent = "";
  byId("replayAnswerButton").hidden = true;
  state.lastAnswer = "";
  byId("cardList").replaceChildren();
  clearMap();
  try {
    const response = await fetch("/api/query", {
      method: "POST",
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        language: state.language,
        category: dialogSubmission ? null : state.category,
        session_id: state.sessionId,
        input_mode: state.queryInputMode,
        dialog_id: dialogSubmission?.dialogId || null,
        choice_values: dialogSubmission?.values || []
      })
    });
    if (!response.ok) throw new Error("request failed");
    const data = await response.json();
    if (viewToken !== state.viewToken) return;
    const safety = renderSafetyState(data.answer_type);
    state.sessionId = data.session_id || state.sessionId;
    resetSessionTimeout();
    byId("statusLine").textContent = "";
    byId("answerText").textContent = data.answer;
    // Bei einer Rückfrage wird zusätzlich zum sichtbaren Prompt auch jede
    // Auswahlmöglichkeit vorgelesen (data.clarification.spoken_text) -- sonst
    // sind die Kästen für eine sprachgeführte Nutzung nicht erreichbar. Der
    // Server registriert genau diesen Text vorab als sprechbar für diese
    // Runde (siehe QueryService.query()), sonst würde /api/speech/synthesize
    // ihn ablehnen.
    state.lastAnswer = data.clarification?.spoken_text || data.answer || "";
    byId("replayAnswerButton").hidden = !state.lastAnswer;
    renderQuestionEcho(data.question || displayQuestionFor(query));
    renderHistory(data.history || []);
    dialogueUI.render(data.clarification || null);
    renderResultList(data.cards || [], data.map_data);
    renderMap(data.map_data);
    if (safety && !data.clarification) {
      byId("answerText").focus();
    } else {
      byId("resultView").scrollIntoView({ behavior: "smooth", block: "start" });
    }
    void speakText(state.lastAnswer, byId("replayAnswerButton"));
    state.category = null;
    renderCategories();
    byId("queryInput").value = "";
    state.queryInputMode = "text";
    updateVoiceStatusReady();
  } catch (_) {
    if (viewToken !== state.viewToken) return;
    renderSafetyState(null);
    byId("statusLine").textContent = "";
    byId("answerText").textContent = text().error;
    state.lastAnswer = "";
    byId("replayAnswerButton").hidden = true;
    dialogueUI.restore();
  } finally {
    if (viewToken === state.viewToken) {
      state.isSubmitting = false;
      state.queryAbort = null;
    }
  }
}

function updateVoiceStatusReady() {
  const micButton = byId("micButton");
  micButton.classList.toggle("is-listening", state.isListening);
  micButton.classList.toggle("is-ready", voiceInputAvailable() && !state.isListening);
  if (state.keepRecognizedStatus) return;
  if (state.isListening) {
    byId("voiceStatus").textContent = state.listeningMode === "server" ? text().voiceRecording : text().voiceListening;
  } else {
    byId("voiceStatus").textContent = voiceInputAvailable()
      ? (recognitionConstructor ? text().voiceReady : text().voiceStartRecording)
      : text().voiceUnavailable;
  }
}

function setSpeechButtonActive(button) {
  if (state.currentSpeechButton && state.currentSpeechButton !== button) {
    state.currentSpeechButton.classList.remove("is-speaking");
    state.currentSpeechButton.setAttribute("aria-pressed", "false");
  }
  state.currentSpeechButton = button;
  if (button) {
    button.classList.add("is-speaking");
    button.setAttribute("aria-pressed", "true");
  }
}

function clearSpeechButtonActive(button) {
  if (button) {
    button.classList.remove("is-speaking");
    button.setAttribute("aria-pressed", "false");
  }
  if (state.currentSpeechButton === button) state.currentSpeechButton = null;
}

// Tears down whatever is currently playing/loading so a new call always
// starts from a clean slate: pauses any playing audio and aborts any
// in-flight synthesize request (a click while the fetch/blob is still
// loading has no audio object yet for the pause-branch below to catch).
function interruptCurrentSpeech() {
  if (state.currentSpeechAbort) {
    state.currentSpeechAbort.abort();
    state.currentSpeechAbort = null;
  }
  if (state.currentSpeechAudio) {
    state.currentSpeechAudio.pause();
    state.currentSpeechAudio.removeAttribute("src");
    state.currentSpeechAudio.load();
    state.currentSpeechAudio = null;
  }
  if (state.currentSpeechCleanup) state.currentSpeechCleanup();
}

// `button` is optional: when given, its visual "is-speaking" state tracks this
// call so callers (replay button, per-card listen buttons) don't need their
// own bookkeeping. Each call gets a token; a superseding call aborts the
// previous request/audio and bumps the token, so a stale response arriving
// late (or a stale error) can recognize itself and skip playback instead of
// resolving/erroring on top of the newer call -- this is what previously let
// two clicks in quick succession (before the first request had produced an
// <audio> to pause) speak over each other.
function speakText(message, button = null) {
  if (button && state.currentSpeechButton === button) {
    stopSpeechOutput();
    return Promise.resolve();
  }
  const requestToken = ++state.speechRequestToken;
  const isCurrent = () => state.speechRequestToken === requestToken;
  return new Promise(async (resolve) => {
    interruptCurrentSpeech();
    setSpeechButtonActive(button);
    const finish = () => {
      if (isCurrent()) clearSpeechButtonActive(button);
      resolve();
    };
    if (!state.serverSynthesisAvailable || !message) {
      finish();
      return;
    }
    const controller = new AbortController();
    state.currentSpeechAbort = controller;
    let audioUrl = null;
    try {
      const response = await fetch("/api/speech/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: message,
          language: state.language,
          session_id: state.sessionId
        }),
        signal: controller.signal
      });
      if (!response.ok) throw new Error("speech synthesis failed");
      const audioBlob = await response.blob();
      if (!isCurrent()) {
        finish();
        return;
      }
      audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      state.currentSpeechAudio = audio;
      const cleanup = () => {
        if (audioUrl) URL.revokeObjectURL(audioUrl);
        audioUrl = null;
        if (state.currentSpeechAudio === audio) state.currentSpeechAudio = null;
        if (state.currentSpeechCleanup === cleanup) state.currentSpeechCleanup = null;
        finish();
      };
      state.currentSpeechCleanup = cleanup;
      audio.onended = cleanup;
      audio.onerror = cleanup;
      await audio.play();
    } catch (_) {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      if (isCurrent()) {
        state.currentSpeechAudio = null;
        state.currentSpeechCleanup = null;
      }
      finish();
    }
  });
}

function stopSpeechOutput() {
  state.speechRequestToken += 1;
  clearSpeechButtonActive(state.currentSpeechButton);
  interruptCurrentSpeech();
}

async function speakIntroThenListen() {
  stopListening();
  updateVoiceStatusReady();
  startListening({ automatic: true });
}

function ensureRecognition() {
  if (!recognitionConstructor) return null;
  if (state.recognition) return state.recognition;
  const recognition = new recognitionConstructor();
  const isCurrent = () => state.recognition === recognition;
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onstart = () => {
    if (!isCurrent()) return;
    state.isListening = true;
    state.keepRecognizedStatus = false;
    byId("voiceStatus").textContent = text().voiceListening;
    updateVoiceStatusReady();
  };
  recognition.onresult = (event) => {
    if (!isCurrent()) return;
    const transcript = Array.from(event.results)
      .map((result) => result[0]?.transcript || "")
      .join(" ")
      .trim();
    state.keepRecognizedStatus = true;
    if (transcript) {
      byId("queryInput").value = transcript;
      state.queryInputMode = "speech";
      byId("voiceStatus").textContent = text().voiceHeard.replace("{text}", transcript);
      byId("submitButton").focus();
    } else {
      byId("voiceStatus").textContent = text().voiceTryAgain;
    }
  };
  recognition.onerror = (event) => {
    if (!isCurrent()) return;
    state.isListening = false;
    // true, nicht false: updateVoiceStatusReady() unten wuerde die gerade
    // gesetzte Fehlermeldung sonst im selben Zug wieder durch den generischen
    // "bereit"-Text ueberschreiben (live gemeldet: Meldung blitzt nur kurz auf).
    state.keepRecognizedStatus = true;
    byId("voiceStatus").textContent = event.error === "not-allowed" ? text().voiceDenied : text().voiceTryAgain;
    updateVoiceStatusReady();
  };
  recognition.onend = () => {
    if (!isCurrent()) return;
    state.isListening = false;
    state.listeningMode = null;
    updateVoiceStatusReady();
  };
  state.recognition = recognition;
  return recognition;
}

function preferredAudioMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4"
  ];
  return candidates.find((value) => MediaRecorder.isTypeSupported?.(value)) || "";
}

async function transcribeRecordedAudio(blob) {
  const viewToken = state.viewToken;
  state.transcriptionAbort?.abort();
  const controller = new AbortController();
  state.transcriptionAbort = controller;
  const isCurrent = () => viewToken === state.viewToken && state.transcriptionAbort === controller;
  byId("voiceStatus").textContent = text().voiceProcessing;
  try {
    const response = await fetch(`/api/speech/transcribe?language=${encodeURIComponent(state.language)}`, {
      method: "POST",
      signal: controller.signal,
      headers: { "Content-Type": blob.type || "audio/webm" },
      body: blob
    });
    if (!isCurrent()) return;
    if (!response.ok) {
      state.keepRecognizedStatus = true;
      byId("voiceStatus").textContent = [413, 415, 422].includes(response.status)
        ? text().voiceTryAgain : text().voiceServiceError;
      return;
    }
    const data = await response.json();
    if (!isCurrent()) return;
    if (typeof data.text !== "string") throw new Error("invalid transcription response");
    const transcript = data.text.trim();
    state.keepRecognizedStatus = true;
    if (transcript) {
      byId("queryInput").value = transcript;
      state.queryInputMode = "speech";
      byId("voiceStatus").textContent = text().voiceHeard.replace("{text}", transcript);
      byId("submitButton").focus();
    } else {
      byId("voiceStatus").textContent = text().voiceTryAgain;
    }
  } catch (_) {
    if (!isCurrent()) return;
    // true, nicht false: siehe recognition.onerror weiter oben -- sonst
    // ueberschreibt updateVoiceStatusReady() die Fehlermeldung sofort wieder.
    state.keepRecognizedStatus = true;
    byId("voiceStatus").textContent = text().voiceServiceError;
    updateVoiceStatusReady();
  } finally {
    if (isCurrent()) state.transcriptionAbort = null;
  }
}

async function startServerRecording({ automatic = false } = {}) {
  const viewToken = state.viewToken;
  if (automatic) {
    updateVoiceStatusReady();
    return;
  }
  if (!state.serverTranscriptionAvailable || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    byId("voiceStatus").textContent = text().voiceUnavailable;
    byId("micButton").classList.remove("is-ready", "is-listening");
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (viewToken !== state.viewToken) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    state.mediaStream = stream;
    const mimeType = preferredAudioMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    state.audioChunks = [];
    state.mediaRecorder = recorder;
    state.listeningMode = "server";
    recorder.ondataavailable = (event) => {
      if (viewToken !== state.viewToken) return;
      if (event.data && event.data.size > 0) state.audioChunks.push(event.data);
    };
    recorder.onstop = () => {
      if (viewToken !== state.viewToken) return;
      const type = recorder.mimeType || mimeType || "audio/webm";
      const blob = new Blob(state.audioChunks, { type });
      stream.getTracks().forEach((track) => track.stop());
      state.mediaStream = null;
      state.mediaRecorder = null;
      state.listeningMode = null;
      state.isListening = false;
      updateVoiceStatusReady();
      void transcribeRecordedAudio(blob);
    };
    recorder.start();
    state.isListening = true;
    state.keepRecognizedStatus = false;
    byId("voiceStatus").textContent = text().voiceListening;
    updateVoiceStatusReady();
  } catch (error) {
    if (viewToken !== state.viewToken) return;
    state.mediaStream?.getTracks().forEach((track) => track.stop());
    state.mediaStream = null;
    state.mediaRecorder = null;
    state.isListening = false;
    state.listeningMode = null;
    // true, nicht false: siehe recognition.onerror weiter oben -- sonst
    // ueberschreibt updateVoiceStatusReady() die Fehlermeldung sofort wieder.
    state.keepRecognizedStatus = true;
    byId("voiceStatus").textContent = error.name === "NotAllowedError" || error.name === "SecurityError"
      ? text().voiceDenied : text().voiceServiceError;
    updateVoiceStatusReady();
  }
}

function startListening({ automatic = false } = {}) {
  if (!automatic) resetSessionTimeout();
  if (automatic && state.autoListenTried) return;
  if (automatic) state.autoListenTried = true;
  if (state.isListening) return;
  const recognition = ensureRecognition();
  if (!recognition) {
    void startServerRecording({ automatic });
    return;
  }
  try {
    state.listeningMode = "browser";
    recognition.lang = speechLanguages[state.language] || state.language;
    recognition.start();
  } catch (_) {
    state.isListening = false;
    updateVoiceStatusReady();
  }
}

function stopListening() {
  if (state.listeningMode === "server" && state.mediaRecorder) {
    try {
      if (state.mediaRecorder.state !== "inactive") state.mediaRecorder.stop();
    } catch (_) {
      state.isListening = false;
      state.listeningMode = null;
      state.mediaStream?.getTracks().forEach((track) => track.stop());
      state.mediaStream = null;
    }
    return;
  }
  if (!state.recognition || !state.isListening) return;
  try {
    state.recognition.stop();
  } catch (_) {
    state.isListening = false;
  }
}

function localizeCardText(value) {
  return value.replace(/^>\s*/, "");
}

document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => {
    resetSessionTimeout();
    setLanguage(button.dataset.language);
  });
});

byId("queryForm").addEventListener("submit", (event) => {
  event.preventDefault();
  resetSessionTimeout();
  const query = byId("queryInput").value.trim();
  if (query || state.category) void submitQuery(query);
});

byId("queryInput").addEventListener("input", () => {
  state.queryInputMode = "text";
  resetSessionTimeout();
});

byId("replayAnswerButton").addEventListener("click", () => {
  resetSessionTimeout();
  if (state.lastAnswer) void speakText(state.lastAnswer, byId("replayAnswerButton"));
});

byId("micButton").addEventListener("click", () => {
  resetSessionTimeout();
  state.autoListenTried = true;
  if (state.isListening) {
    stopListening();
  } else {
    startListening();
  }
});

byId("startButton").addEventListener("click", () => {
  resetSessionTimeout();
  resetView();
});
byId("backButton").addEventListener("click", () => {
  resetSessionTimeout();
  backToSearch();
});
byId("languageButton").addEventListener("click", () => {
  resetSessionTimeout();
  cancelPendingInteraction();
  byId("appView").hidden = true;
  byId("languageView").hidden = false;
});

void (async () => {
  try {
    await loadApplicationCopy("de");
    byId("languageTitle").textContent = copy.de.languageTitle;
    byId("languageIntro").textContent = copy.de.languageIntro;
  } catch (_) {
    byId("languageTitle").textContent = "LENA";
  }
  await loadSpeechConfig();
})();
