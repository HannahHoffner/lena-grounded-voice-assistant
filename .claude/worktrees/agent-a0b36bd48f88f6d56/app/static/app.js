/**
 * Browser-Client von LENA.
 *
 * Verwaltet Sprache, Navigation, kurze Sessions, Query-/Speech-Aufrufe sowie
 * die Darstellung von Backend-Karten und Leaflet-Zielen. Angebotsfakten werden
 * im Frontend weder ergänzt noch fachlich neu interpretiert.
 */
const copy = {
  de: {
    languageTitle: "Sprache wählen",
    languageIntro: "Wähle deine Sprache.",
    mainTitle: "Welche Hilfe brauchst du?",
    mainIntro: "Ich beantworte Fragen zu Hilfsangeboten in Leipzig. Stell mir eine Frage!",
    speechIntro: "Ich beantworte Fragen zu Hilfsangeboten in Leipzig. Stell mir eine Frage!",
    categories: { food: "Essen", sleep: "Schlafen", medical: "Medizin", advice: "Beratung" },
    queryLabel: "Frage schreiben",
    placeholder: "Zum Beispiel: Wo bekomme ich Essen?",
    send: "Senden",
    navStart: "Start",
    navBack: "Zurück",
    navLanguage: "Sprache ändern",
    micLabel: "Frage sprechen",
    voiceReady: "Du kannst jetzt sprechen. Du kannst auch schreiben.",
    voiceSpeaking: "LENA spricht. Danach kannst du sprechen.",
    voiceListening: "Ich höre zu.",
    voiceHeard: "Ich habe verstanden: {text}",
    voiceProcessing: "Ich verarbeite deine Sprache.",
    voiceUnavailable: "Spracheingabe ist nicht verfügbar. Du kannst schreiben.",
    voiceDenied: "Das Mikrofon ist nicht frei. Du kannst schreiben.",
    voiceTryAgain: "Ich habe nichts verstanden. Bitte noch einmal sprechen oder schreiben.",
    answer: "Antwort",
    replayAnswer: "Antwort noch einmal abspielen",
    questionEcho: "Verstandene Frage",
    historyTitle: "Chatverlauf",
    mapTitle: "Karte",
    mapHint: "Startpunkt ist Leipzig Hauptbahnhof. Markiert sind passende Orte.",
    loading: "Ich suche ...",
    error: "Die Anfrage konnte nicht verarbeitet werden.",
    description: "Beschreibung",
    services: "Angebote",
    address: "Adresse",
    phone: "Telefon",
    hours: "Öffnungszeiten",
    standTimes: "Standzeiten",
    notes: "Wichtige Hinweise"
  },
  en: {
    languageTitle: "Choose language",
    languageIntro: "Choose your language.",
    mainTitle: "What help do you need?",
    mainIntro: "I answer questions about help in Leipzig. Ask me a question!",
    speechIntro: "I answer questions about help in Leipzig. Ask me a question!",
    categories: { food: "Food", sleep: "Sleep", medical: "Medical help", advice: "Advice" },
    queryLabel: "Write a question",
    placeholder: "For example: Where can I get food?",
    send: "Send",
    navStart: "Start",
    navBack: "Back",
    navLanguage: "Change language",
    micLabel: "Speak question",
    voiceReady: "You can speak now. You can also type.",
    voiceSpeaking: "LENA is speaking. Then you can speak.",
    voiceListening: "I am listening.",
    voiceHeard: "I understood: {text}",
    voiceProcessing: "I am processing your speech.",
    voiceUnavailable: "Voice input does not work in this browser. You can type.",
    voiceDenied: "The microphone is not available. You can type.",
    voiceTryAgain: "I did not understand. Please speak again or type.",
    answer: "Answer",
    replayAnswer: "Play answer again",
    questionEcho: "Understood question",
    historyTitle: "Chat history",
    mapTitle: "Map",
    mapHint: "The starting point is Leipzig Hauptbahnhof. Matching places are marked.",
    loading: "I am searching ...",
    error: "The request could not be processed.",
    description: "Description",
    services: "Help offered",
    address: "Address",
    phone: "Phone",
    hours: "Opening hours",
    standTimes: "Times at this place",
    notes: "Important notes"
  },
  pl: {
    languageTitle: "Wybierz język",
    languageIntro: "Wybierz swój język.",
    mainTitle: "Jakiej pomocy potrzebujesz?",
    mainIntro: "Odpowiadam na pytania o pomoc w Lipsku. Zadaj mi pytanie!",
    speechIntro: "Odpowiadam na pytania o pomoc w Lipsku. Zadaj mi pytanie!",
    categories: { food: "Jedzenie", sleep: "Nocleg", medical: "Pomoc medyczna", advice: "Porada" },
    queryLabel: "Napisz pytanie",
    placeholder: "Na przykład: Gdzie dostanę jedzenie?",
    send: "Wyślij",
    navStart: "Start",
    navBack: "Wstecz",
    navLanguage: "Zmień język",
    micLabel: "Powiedz pytanie",
    voiceReady: "Możesz teraz mówić. Możesz też pisać.",
    voiceSpeaking: "LENA mówi. Potem możesz mówić.",
    voiceListening: "Słucham.",
    voiceHeard: "Zrozumiałam: {text}",
    voiceProcessing: "Przetwarzam twoją mowę.",
    voiceUnavailable: "W tej przeglądarce nie działa mówienie. Możesz pisać.",
    voiceDenied: "Mikrofon nie jest dostępny. Możesz pisać.",
    voiceTryAgain: "Nie zrozumiałam. Powiedz jeszcze raz albo napisz.",
    answer: "Odpowiedź",
    replayAnswer: "Odtwórz odpowiedź jeszcze raz",
    questionEcho: "Zrozumiane pytanie",
    historyTitle: "Historia rozmowy",
    mapTitle: "Mapa",
    mapHint: "Punkt startowy to Leipzig Hauptbahnhof. Pasujące miejsca są zaznaczone.",
    loading: "Szukam ...",
    error: "Nie udało się przetworzyć pytania.",
    description: "Opis",
    services: "Pomoc",
    address: "Adres",
    phone: "Telefon",
    hours: "Godziny otwarcia",
    standTimes: "Godziny w tym miejscu",
    notes: "Ważne informacje"
  },
  ro: {
    languageTitle: "Alege limba",
    languageIntro: "Alege limba ta.",
    mainTitle: "De ce ajutor ai nevoie?",
    mainIntro: "Răspund la întrebări despre ajutor în Leipzig. Pune-mi o întrebare!",
    speechIntro: "Răspund la întrebări despre ajutor în Leipzig. Pune-mi o întrebare!",
    categories: { food: "Mâncare", sleep: "Loc de dormit", medical: "Ajutor medical", advice: "Consiliere" },
    queryLabel: "Scrie o întrebare",
    placeholder: "De exemplu: Unde primesc mâncare?",
    send: "Trimite",
    navStart: "Start",
    navBack: "Înapoi",
    navLanguage: "Schimbă limba",
    micLabel: "Spune întrebarea",
    voiceReady: "Poți vorbi acum. Poți și scrie.",
    voiceSpeaking: "LENA vorbește. Apoi poți vorbi.",
    voiceListening: "Ascult.",
    voiceHeard: "Am înțeles: {text}",
    voiceProcessing: "Procesez vocea ta.",
    voiceUnavailable: "Intrarea vocală nu merge în acest browser. Poți scrie.",
    voiceDenied: "Microfonul nu este disponibil. Poți scrie.",
    voiceTryAgain: "Nu am înțeles. Vorbește încă o dată sau scrie.",
    answer: "Răspuns",
    replayAnswer: "Redă răspunsul încă o dată",
    questionEcho: "Întrebare înțeleasă",
    historyTitle: "Istoric chat",
    mapTitle: "Hartă",
    mapHint: "Punctul de start este Leipzig Hauptbahnhof. Locurile potrivite sunt marcate.",
    loading: "Caut ...",
    error: "Cererea nu a putut fi procesată.",
    description: "Descriere",
    services: "Ajutor oferit",
    address: "Adresă",
    phone: "Telefon",
    hours: "Program",
    standTimes: "Ore în acest loc",
    notes: "Informații importante"
  },
  ru: {
    languageTitle: "Выберите язык",
    languageIntro: "Выберите ваш язык.",
    mainTitle: "Какая помощь вам нужна?",
    mainIntro: "Я отвечаю на вопросы о помощи в Leipzig. Задайте мне вопрос!",
    speechIntro: "Я отвечаю на вопросы о помощи в Leipzig. Задайте мне вопрос!",
    categories: { food: "Еда", sleep: "Ночлег", medical: "Медицинская помощь", advice: "Консультация" },
    queryLabel: "Напишите вопрос",
    placeholder: "Например: Где получить еду?",
    send: "Отправить",
    navStart: "Старт",
    navBack: "Назад",
    navLanguage: "Сменить язык",
    micLabel: "Сказать вопрос",
    voiceReady: "Теперь можно говорить. Также можно написать.",
    voiceSpeaking: "LENA говорит. Потом можно говорить.",
    voiceListening: "Я слушаю.",
    voiceHeard: "Я поняла: {text}",
    voiceProcessing: "Я обрабатываю вашу речь.",
    voiceUnavailable: "Голосовой ввод не работает в этом браузере. Можно написать.",
    voiceDenied: "Микрофон недоступен. Можно написать.",
    voiceTryAgain: "Я не поняла. Повторите или напишите.",
    answer: "Ответ",
    replayAnswer: "Прослушать ответ еще раз",
    questionEcho: "Понятый вопрос",
    historyTitle: "История чата",
    mapTitle: "Карта",
    mapHint: "Начальная точка: Leipzig Hauptbahnhof. Подходящие места отмечены.",
    loading: "Я ищу ...",
    error: "Запрос не удалось обработать.",
    description: "Описание",
    services: "Помощь",
    address: "Адрес",
    phone: "Телефон",
    hours: "Часы работы",
    standTimes: "Время в этом месте",
    notes: "Важная информация"
  }
};

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
  lastAnswer: ""
};

const SESSION_TIMEOUT_MS = 3 * 60 * 1000;

const byId = (id) => document.getElementById(id);
const recognitionConstructor = window.SpeechRecognition || window.webkitSpeechRecognition;

function text() {
  return copy[state.language];
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
    state.sessionId = null;
  }, SESSION_TIMEOUT_MS);
}

function setIconButton(id, label) {
  const button = byId(id);
  button.setAttribute("aria-label", label);
  button.title = label;
  const screenReaderText = button.querySelector(".sr-only");
  if (screenReaderText) screenReaderText.textContent = label;
}

function setLanguage(language) {
  resetSessionTimeout();
  state.language = language;
  state.category = null;
  state.autoListenTried = false;
  state.keepRecognizedStatus = false;
  document.documentElement.lang = language;
  byId("languageView").hidden = true;
  byId("appView").hidden = false;
  applyCopy();
  resetView();
  void (async () => {
    await loadSpeechConfig();
    await speakIntroThenListen();
  })();
}

function applyCopy() {
  const value = text();
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
      stopListening();
      renderCategories();
      void submitQuery("");
    });
    grid.appendChild(button);
  }
}

function resetView() {
  resetSessionTimeout();
  state.category = null;
  state.keepRecognizedStatus = false;
  state.sessionId = null;
  byId("queryInput").value = "";
  byId("searchView").hidden = false;
  byId("resultView").hidden = true;
  byId("answerText").textContent = "";
  byId("replayAnswerButton").hidden = true;
  state.lastAnswer = "";
  byId("cardList").replaceChildren();
  byId("questionEcho").hidden = true;
  byId("historyPanel").hidden = true;
  byId("historyList").replaceChildren();
  clearMap();
  renderCategories();
  updateVoiceStatusReady();
}

function backToSearch() {
  resetSessionTimeout();
  state.keepRecognizedStatus = false;
  byId("searchView").hidden = false;
  byId("resultView").hidden = true;
  byId("answerText").textContent = "";
  byId("replayAnswerButton").hidden = true;
  state.lastAnswer = "";
  byId("cardList").replaceChildren();
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

function renderCards(cards) {
  const list = byId("cardList");
  list.replaceChildren();
  for (const offer of cards) {
    const card = document.createElement("article");
    card.className = "offer-card";
    const title = document.createElement("h3");
    title.textContent = offer.name;
    card.appendChild(title);
    addField(card, text().description, offer.short_description);
    addField(card, text().services, offer.services);
    addField(card, text().address, offer.address, { keepSource: true });
    addField(card, text().phone, offer.phone_numbers);
    addField(card, text().hours, offer.opening_hours_raw);
    addField(card, text().standTimes, offer.standzeiten_raw);
    addField(card, text().notes, offer.notes);
    list.appendChild(card);
  }
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

function clearMap() {
  byId("mapPanel").hidden = true;
  byId("mapList").replaceChildren();
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

function buildMapPopup(label, address) {
  const container = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = label ?? "";
  container.appendChild(title);

  const addressText = address ?? "";
  if (addressText) {
    container.appendChild(document.createElement("br"));
    container.appendChild(document.createTextNode(addressText));
  }
  return container;
}

function renderMap(mapData) {
  // Das Backend liefert bereits transformierte und fachlich gefilterte Ziele;
  // der Browser visualisiert sie ohne eine zweite Rankinglogik.
  clearMap();
  if (!mapData || !mapData.destinations || !mapData.destinations.length) return;
  byId("mapPanel").hidden = false;
  const list = byId("mapList");
  const map = ensureMap();
  const bounds = [];

  const addListItem = (label, address, distance) => {
    const item = document.createElement("article");
    item.className = "map-list-item";
    const title = document.createElement("strong");
    title.textContent = label;
    const line = document.createElement("p");
    line.textContent = distance ? `${address} · ${Math.round(distance / 100) / 10} km` : address;
    item.append(title, line);
    list.appendChild(item);
  };

  const origin = mapData.origin;
  addListItem(origin.label, origin.address, null);
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
    addListItem(destination.label, destination.address, destination.distance_meters);
    if (!map) continue;
    const marker = L.circleMarker([destination.latitude, destination.longitude], {
      radius: 9,
      color: "#005ea8",
      fillColor: "#f28c00",
      fillOpacity: 0.92
    }).bindPopup(buildMapPopup(destination.label, destination.address)).addTo(map);
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

async function submitQuery(query) {
  // Die Session-ID verbindet kurze Folgefragen. Alle Fakten werden mit jeder
  // Antwort erneut vom Backend geliefert.
  resetSessionTimeout();
  stopListening();
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, language: state.language, category: state.category, session_id: state.sessionId })
    });
    if (!response.ok) throw new Error("request failed");
    const data = await response.json();
    state.sessionId = data.session_id || state.sessionId;
    resetSessionTimeout();
    byId("statusLine").textContent = "";
    byId("answerText").textContent = data.answer;
    state.lastAnswer = data.answer || "";
    byId("replayAnswerButton").hidden = !state.lastAnswer;
    renderQuestionEcho(data.question || displayQuestionFor(query));
    renderHistory(data.history || []);
    renderCards(data.cards || []);
    renderMap(data.map_data);
    byId("resultView").scrollIntoView({ behavior: "smooth", block: "start" });
    void speakText(data.answer);
    state.category = null;
    renderCategories();
    byId("queryInput").value = "";
    updateVoiceStatusReady();
  } catch (_) {
    byId("statusLine").textContent = "";
    byId("answerText").textContent = text().error;
    state.lastAnswer = text().error;
    byId("replayAnswerButton").hidden = false;
  }
}

function updateVoiceStatusReady() {
  const micButton = byId("micButton");
  micButton.classList.toggle("is-listening", state.isListening);
  micButton.classList.toggle("is-ready", voiceInputAvailable() && !state.isListening);
  if (state.keepRecognizedStatus) return;
  byId("voiceStatus").textContent = voiceInputAvailable() ? text().voiceReady : text().voiceUnavailable;
}

function textForSpeech(message) {
  if (state.language === "de") return normalizeGermanSpeech(message);
  if (state.language === "en") return normalizeEnglishSpeech(message);
  return message;
}

function normalizeGermanSpeech(message) {
  return message
    .replace(/\b(\d{1,2}):(\d{2})\s*(?:-|–|—|bis)\s*(\d{1,2}):(\d{2})\s*(?:Uhr)?\b/gi, (_, h1, m1, h2, m2) => (
      `${germanTime(Number(h1), Number(m1))} bis ${germanTime(Number(h2), Number(m2))}`
    ))
    .replace(/\b(\d{1,2}):(\d{2})\s*(?:Uhr)?\b/gi, (_, h, m) => germanTime(Number(h), Number(m)));
}

function normalizeEnglishSpeech(message) {
  return message
    .replace(/\b(\d{1,2}):(\d{2})\s*(?:-|–|—|to)\s*(\d{1,2}):(\d{2})\b/gi, (_, h1, m1, h2, m2) => (
      `${englishTime(Number(h1), Number(m1))} to ${englishTime(Number(h2), Number(m2))}`
    ))
    .replace(/\b(\d{1,2}):(\d{2})\b/g, (_, h, m) => englishTime(Number(h), Number(m)));
}

function germanTime(hour, minute) {
  const safeHour = Number.isFinite(hour) ? Math.max(0, Math.min(24, hour)) : 0;
  const safeMinute = Number.isFinite(minute) ? Math.max(0, Math.min(59, minute)) : 0;
  const hourWord = safeHour === 1 ? "ein" : germanNumber(safeHour);
  if (safeMinute === 0) return `${hourWord} Uhr`;
  return `${hourWord} Uhr ${germanNumber(safeMinute)}`;
}

function germanNumber(value) {
  const ones = ["null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun"];
  const teens = {
    10: "zehn", 11: "elf", 12: "zwölf", 13: "dreizehn", 14: "vierzehn", 15: "fünfzehn",
    16: "sechzehn", 17: "siebzehn", 18: "achtzehn", 19: "neunzehn"
  };
  const tens = { 20: "zwanzig", 30: "dreißig", 40: "vierzig", 50: "fünfzig" };
  if (value < 10) return ones[value];
  if (value < 20) return teens[value];
  if (value in tens) return tens[value];
  const ten = Math.floor(value / 10) * 10;
  const one = value % 10;
  const oneWord = one === 1 ? "ein" : ones[one];
  return `${oneWord}und${tens[ten]}`;
}

function englishTime(hour, minute) {
  const safeHour = Number.isFinite(hour) ? Math.max(0, Math.min(23, hour)) : 0;
  const safeMinute = Number.isFinite(minute) ? Math.max(0, Math.min(59, minute)) : 0;
  if (safeMinute === 0 && safeHour === 0) return "midnight";
  if (safeMinute === 0 && safeHour === 12) return "noon";
  const period = safeHour < 12 ? "A M" : "P M";
  const displayHour = safeHour % 12 || 12;
  if (safeMinute === 0) return `${englishNumber(displayHour)} ${period}`;
  return `${englishNumber(displayHour)} ${englishNumber(safeMinute)} ${period}`;
}

function englishNumber(value) {
  const small = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen"
  ];
  const tens = { 20: "twenty", 30: "thirty", 40: "forty", 50: "fifty" };
  if (value < 20) return small[value];
  if (value in tens) return tens[value];
  const ten = Math.floor(value / 10) * 10;
  return `${tens[ten]} ${small[value % 10]}`;
}

function speakText(message) {
  return new Promise(async (resolve) => {
    if (!state.serverSynthesisAvailable || !message) {
      resolve();
      return;
    }
    if (state.currentSpeechAudio) {
      state.currentSpeechAudio.pause();
      state.currentSpeechAudio.removeAttribute("src");
      state.currentSpeechAudio.load();
      state.currentSpeechAudio = null;
    }
    let audioUrl = null;
    try {
      const response = await fetch("/api/speech/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: textForSpeech(message),
          language: state.language
        })
      });
      if (!response.ok) throw new Error("speech synthesis failed");
      const audioBlob = await response.blob();
      audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      state.currentSpeechAudio = audio;
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        if (state.currentSpeechAudio === audio) state.currentSpeechAudio = null;
        resolve();
      };
      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        if (state.currentSpeechAudio === audio) state.currentSpeechAudio = null;
        resolve();
      };
      await audio.play();
    } catch (_) {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      state.currentSpeechAudio = null;
      resolve();
    }
  });
}

function stopSpeechOutput() {
  if (!state.currentSpeechAudio) return;
  state.currentSpeechAudio.pause();
  state.currentSpeechAudio.removeAttribute("src");
  state.currentSpeechAudio.load();
  state.currentSpeechAudio = null;
}

async function speakIntroThenListen() {
  stopListening();
  byId("voiceStatus").textContent = text().voiceSpeaking;
  await speakText(text().speechIntro);
  updateVoiceStatusReady();
  startListening({ automatic: true });
}

function ensureRecognition() {
  if (!recognitionConstructor) return null;
  if (state.recognition) return state.recognition;
  const recognition = new recognitionConstructor();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onstart = () => {
    state.isListening = true;
    state.keepRecognizedStatus = false;
    byId("voiceStatus").textContent = text().voiceListening;
    updateVoiceStatusReady();
  };
  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map((result) => result[0]?.transcript || "")
      .join(" ")
      .trim();
    state.keepRecognizedStatus = true;
    if (transcript) {
      byId("queryInput").value = transcript;
      byId("voiceStatus").textContent = text().voiceHeard.replace("{text}", transcript);
      byId("submitButton").focus();
    } else {
      byId("voiceStatus").textContent = text().voiceTryAgain;
    }
  };
  recognition.onerror = (event) => {
    state.isListening = false;
    state.keepRecognizedStatus = false;
    byId("voiceStatus").textContent = event.error === "not-allowed" ? text().voiceDenied : text().voiceTryAgain;
    updateVoiceStatusReady();
  };
  recognition.onend = () => {
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
  byId("voiceStatus").textContent = text().voiceProcessing;
  try {
    const response = await fetch(`/api/speech/transcribe?language=${encodeURIComponent(state.language)}`, {
      method: "POST",
      headers: { "Content-Type": blob.type || "audio/webm" },
      body: blob
    });
    if (!response.ok) throw new Error("transcription failed");
    const data = await response.json();
    const transcript = (data.text || "").trim();
    state.keepRecognizedStatus = true;
    if (transcript) {
      byId("queryInput").value = transcript;
      byId("voiceStatus").textContent = text().voiceHeard.replace("{text}", transcript);
      byId("submitButton").focus();
    } else {
      byId("voiceStatus").textContent = text().voiceTryAgain;
    }
  } catch (_) {
    state.keepRecognizedStatus = false;
    byId("voiceStatus").textContent = text().voiceTryAgain;
    updateVoiceStatusReady();
  }
}

async function startServerRecording({ automatic = false } = {}) {
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
    const mimeType = preferredAudioMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    state.audioChunks = [];
    state.mediaStream = stream;
    state.mediaRecorder = recorder;
    state.listeningMode = "server";
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) state.audioChunks.push(event.data);
    };
    recorder.onstop = () => {
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
  } catch (_) {
    state.isListening = false;
    state.listeningMode = null;
    state.keepRecognizedStatus = false;
    byId("voiceStatus").textContent = text().voiceDenied;
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

byId("queryInput").addEventListener("input", resetSessionTimeout);

byId("replayAnswerButton").addEventListener("click", () => {
  resetSessionTimeout();
  if (state.lastAnswer) void speakText(state.lastAnswer);
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
  stopListening();
  stopSpeechOutput();
  resetView();
  byId("appView").hidden = true;
  byId("languageView").hidden = false;
});

void loadSpeechConfig();
