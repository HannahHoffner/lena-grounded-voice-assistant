const state = {
  language: "de",
  sessionId: null,
  lastAnswer: "",
  mediaStream: null,
  mediaRecorder: null,
  chunks: [],
  recording: false,
  ignoreNextRecordingStop: false,
  health: null,
  currentMapData: null,
  mapInstance: null,
  mapMarkers: [],
  selectedMapDestinationId: null,
  selectedOfferId: null,
  activeCategoryId: null,
  activeCategoryLabel: "",
};

const labels = {
  de: {
    languageTitle: "Wähle deine Sprache.",
    navStart: "Start",
    navBack: "Zurück",
    navLanguage: "Sprache",
    navCancel: "Abbrechen",
    navEnd: "Ende",
    navLanguageAria: "Sprache ändern",
    navCancelAria: "Anfrage abbrechen",
    navEndAria: "Sitzung beenden",
    guideEyebrow: "Kleiner lokaler Wegweiser",
    mainTitle: "Was brauchst du?",
    introText: "Ich bin LENA und helfe dir bei Fragen zum Hilfesystem in Leipzig. Klicke auf das passende Symbol oder frage mich direkt im Chat.",
    textTitle: "Oder tippe",
    textPlaceholder: "Was brauchst du?",
    talk: "Sprich mit mir",
    mic: "Mikrofon",
    textMode: "Text eingeben",
    stop: "Stoppen",
    send: "Senden",
    cancel: "Abbrechen",
    retry: "Nochmal sprechen",
    review: "Ich habe verstanden:",
    ready: "Bereit",
    processing: "Ich suche passende Hilfe.",
    listening: "Ich höre zu. Tippe nochmal zum Stoppen.",
    sttMissing: "Spracheingabe ist gerade nicht verfügbar. Du kannst schreiben.",
    mockStt: "Spracheingabe ist im Mock-Modus nicht aktiv. Bitte tippe deine Frage.",
    answerPlaceholder: "Die Antwort erscheint hier.",
    answerTitle: "Antwort",
    speak: "Anhören",
    emergency: "Notfall",
    selectedPrefix: "Du suchst:",
    mapTitle: "Karte",
    mapHint: "Orte ab Leipzig Hauptbahnhof.",
    mapFallback: "Die Karte konnte gerade nicht geladen werden. Die Orte bleiben unten sichtbar.",
    places: "Orte",
    distance: "Entfernung",
    checked: "Stand",
    sources: "Quelle(n)",
    noAddress: "Ort nicht sicher gespeichert",
    chipPlace: "Ort",
    chipTime: "Zeit",
    chipPhone: "Telefon",
    detailPhone: "Telefon",
    detailEmail: "E-Mail",
    detailWeb: "Web",
    detailImportant: "Wichtig",
    detailForWhom: "Für wen",
    detailServices: "Das gibt es dort",
    detailNote: "Hinweis",
    detailsShown: "Ich zeige dir die Details.",
  },
  en: {
    languageTitle: "Choose your language.",
    navStart: "Start",
    navBack: "Back",
    navLanguage: "Language",
    navCancel: "Cancel",
    navEnd: "End",
    navLanguageAria: "Change language",
    navCancelAria: "Cancel request",
    navEndAria: "End session",
    guideEyebrow: "Small local guide",
    mainTitle: "What do you need?",
    introText: "I am LENA and I help you with questions about support services in Leipzig. Click the right symbol or ask me directly in the chat.",
    textTitle: "Or type",
    textPlaceholder: "What do you need?",
    talk: "Talk to me",
    mic: "Microphone",
    textMode: "Type",
    stop: "Stop",
    send: "Send",
    cancel: "Cancel",
    retry: "Speak again",
    review: "I understood:",
    ready: "Ready",
    processing: "I am looking for suitable help.",
    listening: "I am listening. Tap again to stop.",
    sttMissing: "Speech input is not available right now. You can type.",
    mockStt: "Speech input is in mock mode. Please type your question.",
    answerPlaceholder: "The answer appears here.",
    answerTitle: "Answer",
    speak: "Listen",
    emergency: "Emergency",
    selectedPrefix: "You selected:",
    mapTitle: "Map",
    mapHint: "Relevant places from Leipzig main station.",
    mapFallback: "The map could not be loaded right now. The places remain visible below.",
    places: "Places",
    distance: "Distance",
    checked: "Checked",
    sources: "source(s)",
    noAddress: "Location not safely stored",
    chipPlace: "Place",
    chipTime: "Time",
    chipPhone: "Phone",
    detailPhone: "Phone",
    detailEmail: "Email",
    detailWeb: "Web",
    detailImportant: "Important",
    detailForWhom: "For whom",
    detailServices: "You can get this there",
    detailNote: "Note",
    detailsShown: "I am showing you the details.",
  },
  pl: {
    languageTitle: "Wybierz język.",
    navStart: "Początek",
    navBack: "Wstecz",
    navLanguage: "Język",
    navCancel: "Anuluj",
    navEnd: "Koniec",
    navLanguageAria: "Zmień język",
    navCancelAria: "Anuluj pytanie",
    navEndAria: "Zakończ sesję",
    guideEyebrow: "Mały lokalny przewodnik",
    mainTitle: "Czego potrzebujesz?",
    introText: "Jestem LENA i pomagam w pytaniach o pomoc w Lipsku. Kliknij pasujący symbol albo zapytaj mnie w czacie.",
    textTitle: "Albo wpisz",
    textPlaceholder: "Czego potrzebujesz?",
    talk: "Porozmawiaj ze mna",
    mic: "Mikrofon",
    textMode: "Wpisz",
    stop: "Stop",
    send: "Wyslij",
    cancel: "Anuluj",
    retry: "Powiedz jeszcze raz",
    review: "Zrozumialam:",
    ready: "Gotowe",
    processing: "Szukam pasujacej pomocy.",
    listening: "Slucham. Nacisnij jeszcze raz, aby zakonczyc.",
    sttMissing: "Mowa nie jest teraz dostepna. Mozesz pisac.",
    mockStt: "Mowa jest w trybie testowym. Wpisz pytanie.",
    answerPlaceholder: "Tutaj pojawi sie odpowiedz.",
    answerTitle: "Odpowiedź",
    speak: "Odtworz",
    emergency: "Alarm",
    selectedPrefix: "Wybrano:",
    mapTitle: "Mapa",
    mapHint: "Miejsca od dworca glownego w Lipsku.",
    mapFallback: "Mapa nie moze sie teraz zaladowac. Miejsca sa nadal widoczne.",
    places: "Miejsca",
    distance: "Odleglosc",
    checked: "Sprawdzone",
    sources: "zrodlo/zrodla",
    noAddress: "Miejsce nie jest pewnie zapisane",
    chipPlace: "Miejsce",
    chipTime: "Czas",
    chipPhone: "Telefon",
    detailPhone: "Telefon",
    detailEmail: "E-mail",
    detailWeb: "Web",
    detailImportant: "Ważne",
    detailForWhom: "Dla kogo",
    detailServices: "To jest dostępne",
    detailNote: "Uwaga",
    detailsShown: "Pokazuję szczegóły.",
  },
  ro: {
    languageTitle: "Alege limba.",
    navStart: "Acasă",
    navBack: "Înapoi",
    navLanguage: "Limba",
    navCancel: "Anulează",
    navEnd: "Sfârșit",
    navLanguageAria: "Schimbă limba",
    navCancelAria: "Anulează cererea",
    navEndAria: "Încheie sesiunea",
    guideEyebrow: "Ghid local simplu",
    mainTitle: "De ce ai nevoie?",
    introText: "Sunt LENA și te ajut cu întrebări despre servicii de sprijin în Leipzig. Apasă pe simbolul potrivit sau întreabă-mă direct în chat.",
    textTitle: "Sau scrie",
    textPlaceholder: "De ce ai nevoie?",
    talk: "Vorbeste cu mine",
    mic: "Microfon",
    textMode: "Scrie",
    stop: "Stop",
    send: "Trimite",
    cancel: "Anuleaza",
    retry: "Vorbeste din nou",
    review: "Am inteles:",
    ready: "Gata",
    processing: "Caut ajutor potrivit.",
    listening: "Ascult. Apasa din nou pentru stop.",
    sttMissing: "Vocea nu este disponibila acum. Poti scrie.",
    mockStt: "Vocea este in mod test. Scrie intrebarea.",
    answerPlaceholder: "Raspunsul apare aici.",
    answerTitle: "Răspuns",
    speak: "Asculta",
    emergency: "Urgenta",
    selectedPrefix: "Ai ales:",
    mapTitle: "Harta",
    mapHint: "Locuri relevante de la gara principala Leipzig.",
    mapFallback: "Harta nu se poate incarca acum. Locurile raman vizibile.",
    places: "Locuri",
    distance: "Distanta",
    checked: "Verificat",
    sources: "sursa/surse",
    noAddress: "Locul nu este salvat sigur",
    chipPlace: "Loc",
    chipTime: "Ora",
    chipPhone: "Telefon",
    detailPhone: "Telefon",
    detailEmail: "E-mail",
    detailWeb: "Web",
    detailImportant: "Important",
    detailForWhom: "Pentru cine",
    detailServices: "Aici găsești",
    detailNote: "Notă",
    detailsShown: "Îți arăt detaliile.",
  },
  ru: {
    languageTitle: "Vyberi yazyk.",
    navStart: "Nachalo",
    navBack: "Nazad",
    navLanguage: "Yazyk",
    navCancel: "Otmena",
    navEnd: "Konets",
    navLanguageAria: "Smenit yazyk",
    navCancelAria: "Otmenit zapros",
    navEndAria: "Zavershit sessiyu",
    guideEyebrow: "Prostoy lokalnyy pomoshchnik",
    mainTitle: "Chto tebe nuzhno?",
    introText: "Ya LENA i pomogayu s voprosami o pomoshchi v Leyptsige. Nazhmi podkhodyashchiy simvol ili sprosi menya v chate.",
    textTitle: "Ili napishi",
    textPlaceholder: "Chto tebe nuzhno?",
    talk: "Govori so mnoy",
    mic: "Mikrofon",
    textMode: "Tekst",
    stop: "Stop",
    send: "Otpravit",
    cancel: "Otmena",
    retry: "Skazat eshche raz",
    review: "Ya ponyala:",
    ready: "Gotovo",
    processing: "Ishchu podkhodyashchuyu pomoshch.",
    listening: "Ya slushayu. Nazhmi eshche raz, chtoby ostanovit.",
    sttMissing: "Golosovoy vvod seychas nedostupen. Mozhno pisat.",
    mockStt: "Golosovoy vvod v testovom rezhime. Napishi vopros.",
    answerPlaceholder: "Otvet poyavitsya zdes.",
    answerTitle: "Otvet",
    speak: "Proslushat",
    emergency: "Srochno",
    selectedPrefix: "Vybrano:",
    mapTitle: "Karta",
    mapHint: "Vazhnye mesta ot glavnogo vokzala Leyptsiga.",
    mapFallback: "Karta seychas ne zagruzilas. Mesta ostayutsya vidimy nizhe.",
    places: "Mesta",
    distance: "Rasstoyanie",
    checked: "Provereno",
    sources: "istochnik(i)",
    noAddress: "Mesto ne sohraneno nadezhno",
    chipPlace: "Mesto",
    chipTime: "Vremya",
    chipPhone: "Telefon",
    detailPhone: "Telefon",
    detailEmail: "E-mail",
    detailWeb: "Web",
    detailImportant: "Vazhno",
    detailForWhom: "Dlya kogo",
    detailServices: "Tam est",
    detailNote: "Primechanie",
    detailsShown: "Pokazyvayu podrobnosti.",
  },
};

const symbolIcons = {
  food: "utensils",
  sleep: "bed",
  medical: "medical",
  advice: "help",
  emergency: "alert",
};

function byId(id) {
  return document.getElementById(id);
}

function copy() {
  return labels[state.language] || labels.de;
}

function iconMarkup(icon) {
  const icons = {
    home: '<svg viewBox="0 0 24 24"><path d="M3 11.5 12 4l9 7.5"></path><path d="M5 10.5V20h14v-9.5"></path><path d="M10 20v-6h4v6"></path></svg>',
    back: '<svg viewBox="0 0 24 24"><path d="m15 18-6-6 6-6"></path></svg>',
    language: '<svg viewBox="0 0 24 24"><path d="M4 5h9"></path><path d="M9 3v2"></path><path d="M5 9c2 4 6 5 8 1"></path><path d="M12 19l4-9 4 9"></path><path d="M14 15h4"></path></svg>',
    cancel: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12"></path><path d="M18 6 6 18"></path></svg>',
    end: '<svg viewBox="0 0 24 24"><path d="M10 6H6v12h4"></path><path d="M14 8l4 4-4 4"></path><path d="M18 12H9"></path></svg>',
    mic: '<svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"></rect><path d="M5 11a7 7 0 0 0 14 0"></path><path d="M12 18v3"></path></svg>',
    utensils: '<svg viewBox="0 0 24 24"><path d="M7 3v8"></path><path d="M4 3v5a3 3 0 0 0 6 0V3"></path><path d="M7 11v10"></path><path d="M17 3v18"></path><path d="M14 7c0-2 1-4 3-4"></path></svg>',
    bed: '<svg viewBox="0 0 24 24"><path d="M4 11V5"></path><path d="M4 14h16"></path><path d="M20 14v5"></path><path d="M4 19v-8h8a4 4 0 0 1 4 4"></path><path d="M8 9h1"></path></svg>',
    medical: '<svg viewBox="0 0 24 24"><path d="M9 6V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1"></path><rect x="4" y="6" width="16" height="14" rx="3"></rect><path d="M12 10v6"></path><path d="M9 13h6"></path></svg>',
    help: '<svg viewBox="0 0 24 24"><path d="M5 6h14v9H8l-3 3V6z"></path><path d="M10 10a2 2 0 1 1 3.2 1.6c-.7.5-1.2.9-1.2 1.7"></path><path d="M12 16h.01"></path></svg>',
    alert: '<svg viewBox="0 0 24 24"><path d="M12 4 3 20h18L12 4z"></path><path d="M12 9v5"></path><path d="M12 17h.01"></path></svg>',
    map: '<svg viewBox="0 0 24 24"><path d="M12 21s6-5 6-11a6 6 0 1 0-12 0c0 6 6 11 6 11z"></path><circle cx="12" cy="10" r="2"></circle></svg>',
    clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"></circle><path d="M12 8v5l3 2"></path></svg>',
    phone: '<svg viewBox="0 0 24 24"><path d="M7 5 5 7c0 6 6 12 12 12l2-2-4-4-2 2c-2-1-3-2-4-4l2-2-4-4z"></path></svg>',
    speaker: '<svg viewBox="0 0 24 24"><path d="M4 9v6h4l5 4V5L8 9H4z"></path><path d="M16 9a4 4 0 0 1 0 6"></path></svg>',
    keyboard: '<svg viewBox="0 0 24 24"><rect x="3" y="6" width="18" height="12" rx="2"></rect><path d="M7 10h.01"></path><path d="M11 10h.01"></path><path d="M15 10h.01"></path><path d="M18 10h.01"></path><path d="M7 14h10"></path></svg>',
  };
  return icons[icon] || icons.help;
}

function renderStaticIcons() {
  document.querySelectorAll("[data-icon]").forEach((target) => {
    target.innerHTML = iconMarkup(target.dataset.icon);
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function setStatus(message) {
  byId("statusLine").textContent = message || copy().ready;
}

function setFlowPanel(panelId) {
  for (const id of ["textPanel", "transcriptReview", "answerPanel", "mapPanel"]) {
    const node = byId(id);
    if (node) node.hidden = id !== panelId;
  }
  if (panelId !== "mapPanel") {
    clearMap();
  }
}

function showAnswerPanels(hasMap) {
  byId("answerPanel").hidden = false;
  byId("textPanel").hidden = true;
  byId("transcriptReview").hidden = true;
  byId("mapPanel").hidden = !hasMap;
}

function setSelectedCategory(categoryId, label, loading = false) {
  state.activeCategoryId = categoryId;
  state.activeCategoryLabel = label || "";
  document.querySelectorAll(".symbol-tile").forEach((button) => {
    const active = button.dataset.categoryId === categoryId;
    button.classList.toggle("is-selected", active);
    button.classList.toggle("is-loading", active && loading);
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.setAttribute("aria-busy", active && loading ? "true" : "false");
  });
  const line = byId("selectedLine");
  if (label) {
    line.textContent = `${copy().selectedPrefix} ${label}`;
    line.hidden = false;
  } else {
    line.hidden = true;
  }
}

function stopRecordingIfNeeded() {
  if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
    state.ignoreNextRecordingStop = true;
    state.mediaRecorder.stop();
  }
  for (const track of state.mediaStream?.getTracks?.() || []) {
    track.stop();
  }
  state.mediaRecorder = null;
  state.mediaStream = null;
  state.chunks = [];
  state.recording = false;
}

function resetInteractionState() {
  stopRecordingIfNeeded();
  state.lastAnswer = "";
  state.activeCategoryId = null;
  state.activeCategoryLabel = "";
  state.selectedOfferId = null;
  byId("textInput").value = "";
  byId("transcriptInput").value = "";
  byId("answerText").textContent = copy().answerPlaceholder;
  byId("cardList").replaceChildren();
  byId("followUpOptions").replaceChildren();
  byId("sourceLine").textContent = "";
  byId("speakButton").hidden = true;
  byId("answerPanel").hidden = true;
  byId("textPanel").hidden = true;
  byId("transcriptReview").hidden = true;
  setSelectedCategory(null, "");
  clearMap();
  setStatus(copy().ready);
  applyLanguage();
}

function goHome() {
  byId("languageView").hidden = true;
  byId("mainView").hidden = false;
  resetInteractionState();
  void loadSymbols();
}

function goBack() {
  if (!byId("answerPanel").hidden || !byId("textPanel").hidden || !byId("transcriptReview").hidden || state.activeCategoryId) {
    resetInteractionState();
    void loadSymbols();
    return;
  }
  goHome();
}

function showLanguage() {
  resetInteractionState();
  byId("languageView").hidden = false;
  byId("mainView").hidden = true;
  clearMap();
}

function showMain(language, options = {}) {
  state.language = language;
  document.documentElement.lang = language;
  byId("languageView").hidden = true;
  byId("mainView").hidden = false;
  resetInteractionState();
  applyLanguage();
  void loadSymbols();
  void loadHealth();
  if (options.speakIntro) speakIntroOnce();
}

function applyLanguage() {
  const text = copy();
  byId("languageTitle").textContent = text.languageTitle;
  byId("homeButton").querySelector(".button-label").textContent = text.navStart;
  byId("backButton").querySelector(".button-label").textContent = text.navBack;
  byId("languageButton").querySelector(".button-label").textContent = text.navLanguage;
  byId("cancelButton").querySelector(".button-label").textContent = text.navCancel;
  byId("endSessionButton").querySelector(".button-label").textContent = text.navEnd;
  byId("homeButton").setAttribute("aria-label", text.navStart);
  byId("backButton").setAttribute("aria-label", text.navBack);
  byId("languageButton").setAttribute("aria-label", text.navLanguageAria);
  byId("cancelButton").setAttribute("aria-label", text.navCancelAria);
  byId("endSessionButton").setAttribute("aria-label", text.navEndAria);
  document.querySelector(".hero-row .eyebrow").textContent = text.guideEyebrow;
  byId("mainTitle").textContent = text.mainTitle;
  byId("introLine").textContent = text.introText;
  byId("textTitle").textContent = text.textTitle;
  byId("textInput").placeholder = text.textPlaceholder;
  byId("textSubmitButton").textContent = text.send;
  byId("talkTitle").textContent = text.talk;
  byId("micButtonText").textContent = state.recording ? text.stop : text.mic;
  byId("textModeButtonText").textContent = text.textMode;
  byId("reviewTitle").textContent = text.review;
  byId("sendTranscriptButton").textContent = text.send;
  byId("retryTranscriptButton").textContent = text.retry;
  byId("cancelTranscriptButton").textContent = text.cancel;
  byId("emergencyButton").querySelector("span:last-child").textContent = text.emergency;
  byId("speakButton").querySelector("span:last-child").textContent = text.speak;
  byId("answerLabel").textContent = text.answerTitle;
  byId("mapLabel").textContent = text.mapTitle;
  byId("mapHint").textContent = text.mapHint;
  byId("mapListLabel").textContent = text.places;
  byId("answerText").textContent = byId("answerText").textContent || text.answerPlaceholder;
  if (state.activeCategoryLabel) {
    byId("selectedLine").textContent = `${text.selectedPrefix} ${state.activeCategoryLabel}`;
  }
  byId("micButton").classList.toggle("available", canUseBrowserRecording());
  renderStaticIcons();
}

async function loadHealth() {
  try {
    state.health = await api("/api/health");
  } catch {
    state.health = null;
  }
  byId("micButton").classList.toggle("available", canUseBrowserRecording());
}

function canUseBrowserRecording() {
  return Boolean(window.MediaRecorder && navigator.mediaDevices && state.health?.stt_provider !== "mock" && state.health?.stt_ready !== false);
}

function openTextInput(message) {
  byId("textPanel").hidden = false;
  byId("answerPanel").hidden = true;
  byId("transcriptReview").hidden = true;
  byId("mapPanel").hidden = true;
  if (message) setStatus(message);
  byId("textInput").focus();
}

async function loadSymbols() {
  const data = await api(`/api/symbol/config?language=${encodeURIComponent(state.language)}`);
  const grid = byId("symbolGrid");
  grid.innerHTML = "";
  for (const category of data.categories.filter((item) => item.id !== "emergency")) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "symbol-tile";
    button.dataset.categoryId = category.id;
    button.setAttribute("aria-label", category.label);
    button.setAttribute("aria-pressed", "false");
    button.innerHTML = `<span class="symbol-tile__icon" aria-hidden="true">${iconMarkup(symbolIcons[category.id] || category.icon)}</span><span class="symbol-tile__label"></span>`;
    button.querySelector(".symbol-tile__label").textContent = category.label;
    button.addEventListener("click", () => sendSymbol(category.id));
    grid.appendChild(button);
  }
}

async function sendSymbol(categoryId) {
  const button = document.querySelector(`.symbol-tile[data-category-id="${categoryId}"]`);
  const label = button?.textContent?.trim() || categoryId;
  setSelectedCategory(categoryId, label, true);
  byId("answerPanel").hidden = false;
  byId("answerText").textContent = "";
  clearMap();
  setStatus(copy().processing);
  const data = await api("/api/symbol/answer", {
    method: "POST",
    body: JSON.stringify({ category_id: categoryId, language: state.language, session_id: state.sessionId }),
  });
  setSelectedCategory(categoryId, label, false);
  renderAnswer(data);
}

async function sendQuery(text) {
  const transcript = text.trim();
  if (!transcript) return;
  byId("answerPanel").hidden = false;
  byId("answerText").textContent = "";
  clearMap();
  setStatus(copy().processing);
  const data = await api("/api/query/answer", {
    method: "POST",
    body: JSON.stringify({ transcript, language: state.language, session_id: state.sessionId }),
  });
  renderAnswer(data);
}

function renderAnswer(data) {
  state.sessionId = data.session_id || state.sessionId;
  state.lastAnswer = data.answer_text || "";
  state.selectedOfferId = null;
  byId("answerText").textContent = state.lastAnswer || copy().answerPlaceholder;
  byId("speakButton").hidden = !state.lastAnswer;
  setStatus(data.status || copy().ready);
  renderCards(data.cards || []);
  renderFollowUpOptions(data.follow_up_options || []);
  renderSourceLine(data);
  renderMap(data.map_data);
  showAnswerPanels(Boolean(data.map_data?.destinations?.length));
}

function renderCards(cards) {
  const cardList = byId("cardList");
  cardList.innerHTML = "";
  for (const card of cards) {
    const item = document.createElement("article");
    item.className = "offer-card";
    item.tabIndex = 0;
    item.setAttribute("role", "button");
    item.setAttribute("aria-pressed", String(state.selectedOfferId === card.page_id));
    item.classList.toggle("is-selected", state.selectedOfferId === card.page_id);
    item.dataset.pageId = card.page_id;
    const meta = [];
    if (card.address) meta.push(metaChip("map", copy().chipPlace, card.address));
    else if (card.location) meta.push(metaChip("map", copy().chipPlace, card.location));
    const primaryTime = firstUsefulTime(card.opening_hours || []);
    if (primaryTime) meta.push(metaChip("clock", copy().chipTime, primaryTime));
    if (card.phone) meta.push(metaChip("phone", copy().chipPhone, primaryPhone(card.phone)));
    const details = [];
    if (card.phone && card.phone.includes(";")) details.push(`<p><strong>${escapeHtml(copy().detailPhone)}:</strong> ${escapeHtml(card.phone)}</p>`);
    if (card.email) details.push(`<p><strong>${escapeHtml(copy().detailEmail)}:</strong> ${escapeHtml(card.email)}</p>`);
    if (card.website) details.push(`<p><strong>${escapeHtml(copy().detailWeb)}:</strong> <a href="${escapeAttribute(card.website)}" target="_blank" rel="noopener noreferrer">${escapeHtml(card.website)}</a></p>`);
    const targetGroups = card.target_groups || [];
    if (card.requirements) details.push(`<p><strong>${escapeHtml(copy().detailImportant)}:</strong> ${escapeHtml(card.requirements)}</p>`);
    const services = importantServices(card.services_provided || []);
    if (services.length) details.push(`<p><strong>${escapeHtml(copy().detailServices)}:</strong> ${escapeHtml(services.join(", "))}</p>`);
    if (card.notes) details.push(`<p><strong>${escapeHtml(copy().detailNote)}:</strong> ${escapeHtml(card.notes)}</p>`);
    const expanded = state.selectedOfferId === card.page_id;
    const targetLine = targetGroups.length ? `<p class="offer-card__target"><strong>${escapeHtml(copy().detailForWhom)}:</strong> ${escapeHtml(targetGroups.join(", "))}</p>` : "";
    item.innerHTML = `<h3>${escapeHtml(shortTitle(card.title, card.page_id))}</h3><p>${escapeHtml(shortSummary(card.description || card.card_summary || ""))}</p>${targetLine}<div class="offer-meta">${meta.join("")}</div><div class="offer-card__details" ${expanded ? "" : "hidden"}>${details.join("")}</div>`;
    item.addEventListener("click", (event) => {
      if (event.target.closest("a")) return;
      selectOffer(card.page_id, { fromCard: true });
    });
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectOffer(card.page_id, { fromCard: true });
      }
    });
    cardList.appendChild(item);
  }
}

function renderFollowUpOptions(options) {
  const panel = byId("followUpOptions");
  panel.replaceChildren();
  if (!options.length) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  for (const option of options) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "follow-up-option";
    button.textContent = option.label || option.value;
    button.addEventListener("click", () => {
      setStatus(copy().processing);
      void sendQuery(option.value || option.label || "");
    });
    panel.appendChild(button);
  }
}

function metaChip(icon, label, text) {
  return `<span class="meta-chip meta-chip--${escapeAttribute(icon)}"><span class="meta-chip__icon" aria-hidden="true">${iconMarkup(icon)}</span><span class="meta-chip__label">${escapeHtml(label)}</span><span class="meta-chip__value">${escapeHtml(text)}</span></span>`;
}

function shortTitle(title, pageId = "") {
  const raw = String(title || "");
  if (pageId === "safe-team-wohnen" && raw.includes("Schwanenteich")) return "SAFE: Schwanenteich";
  if (pageId === "safe-team-wohnen" && raw.includes("Hauptbahnhof")) return "SAFE: Hauptbahnhof";
  if (pageId === "diakonie-streetwork" && raw.includes("Schwanenteich")) return "Diakonie: Schwanenteich";
  if (pageId === "hilfebus" && raw.includes("Hauptbahnhof")) return "Hilfebus: Hbf Westseite";
  const known = {
    "hilfebus": "Hilfebus",
    "safe-team-wohnen": "SAFE Team Wohnen",
    "safe-team-konsum": "SAFE Team Konsum",
    "diakonie-streetwork": "Diakonie Streetwork",
    "bahnhofsmission": "Bahnhofsmission",
    "timmi-care-bags": "Care Bags",
    "leipziger-oase": "Leipziger Oase",
    "tagestreff-insel": "Tagestreff Insel",
    "kontaktcafe-alternative-i": "Kontaktcafé Alternative I",
    "alternative-i-notschlafstelle": "Notschlafstelle Alternative I",
    "alternative-iii-notschlafstelle": "Notschlafstelle Alternative III",
    "cabl-clearingstelle": "CABL Clearingstelle",
    "uvo-medical-outreach": "UVO Medibus",
  };
  if (known[pageId]) return known[pageId];
  return raw
    .replace(/^Caritasverband Leipzig e\.?V\.?\s+/i, "")
    .replace(/^Diakonisches Werk Innere Mission Leipzig e\.?\s*V\.?\s+/i, "")
    .replace(/^Safe-Straßensozialarbeit für Erwachsene -\s*/i, "SAFE ")
    .replace(/\s*-\s*SZL Suchtzentrum gGmbH$/i, "")
    .replace(/\s+Leipzig e\.?\s*V\.?$/i, "")
    .trim();
}

function shortSummary(text) {
  const value = String(text || "").replace(/\s+/g, " ").trim();
  if (!value) return "";
  const firstSentence = value.match(/^.{40,220}?[.!?](?:\s|$)/);
  if (firstSentence) return firstSentence[0].trim();
  if (value.length <= 190) return value;
  const slice = value.slice(0, 190);
  return `${slice.slice(0, Math.max(slice.lastIndexOf(" "), 120)).trim()} …`;
}

function importantServices(services) {
  const cleaned = services
    .map((item) => String(item || "").trim())
    .filter((item) => {
      if (!item || item.endsWith(":")) return false;
      const normalized = item.toLocaleLowerCase("de-DE");
      if (/^[a-z_]+$/.test(normalized)) return false;
      if (["sleep", "food", "advice", "medical", "hygiene", "emergency_accommodation"].includes(normalized)) return false;
      return true;
    });
  return cleaned.slice(0, 5);
}

function primaryPhone(phone) {
  return String(phone || "").split(";")[0].trim();
}

function renderSourceLine(data) {
  const parts = [];
  if (data.last_checked) parts.push(`${copy().checked}: ${data.last_checked}`);
  if (data.sources?.length) parts.push(`${data.sources.length} ${copy().sources}`);
  byId("sourceLine").textContent = parts.join(" | ");
}

function clearMap() {
  state.currentMapData = null;
  state.selectedMapDestinationId = null;
  state.selectedOfferId = null;
  state.mapMarkers = [];
  if (state.mapInstance) {
    state.mapInstance.remove();
    state.mapInstance = null;
  }
  const panel = byId("mapPanel");
  if (panel) panel.hidden = true;
  byId("mapDestinationList").replaceChildren();
  byId("mapDetailCard").replaceChildren();
  byId("mapFallback").hidden = true;
  byId("mapFallback").textContent = "";
}

function renderMap(mapData) {
  if (!mapData?.destinations?.length) {
    clearMap();
    return;
  }
  state.currentMapData = mapData;
  state.selectedMapDestinationId = mapData.selected_destination_id || mapData.destinations[0].id;
  byId("mapPanel").hidden = false;
  renderMapDestinationList(mapData);
  renderMapDetail(activeDestination());
  renderLeafletMap(mapData);
}

function activeDestination() {
  if (!state.currentMapData?.destinations?.length) return null;
  return state.currentMapData.destinations.find((item) => item.id === state.selectedMapDestinationId) || state.currentMapData.destinations[0];
}

function renderMapDestinationList(mapData) {
  const list = byId("mapDestinationList");
  list.replaceChildren();
  for (const destination of mapData.destinations) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "map-destination-button";
    button.classList.toggle("is-selected", destination.id === state.selectedMapDestinationId);
    button.innerHTML = `<span class="map-destination-button__title">${escapeHtml(shortTitle(destination.label, destination.page_id))}</span><span class="map-destination-button__meta">${escapeHtml(destination.address || "")}</span>`;
    button.addEventListener("click", () => {
      state.selectedMapDestinationId = destination.id;
      state.selectedOfferId = destination.page_id || destination.id;
      renderMapDestinationList(mapData);
      renderMapDetail(destination);
      updateOfferSelection();
      updateMarkerSelection();
      const marker = state.mapMarkers.find((item) => item.id === destination.id)?.marker;
      if (marker && state.mapInstance) {
        state.mapInstance.panTo(marker.getLatLng(), { animate: true });
        marker.openPopup();
      }
    });
    list.appendChild(button);
  }
}

function renderMapDetail(destination) {
  const card = byId("mapDetailCard");
  card.replaceChildren();
  if (!destination) return;
  const title = document.createElement("h3");
  title.textContent = shortTitle(destination.label, destination.page_id);
  const address = document.createElement("p");
  address.textContent = destination.address || copy().noAddress;
  const distance = document.createElement("p");
  distance.textContent = destination.distance_meters ? `${copy().distance}: ${formatDistance(destination.distance_meters)}` : "";
  const time = document.createElement("p");
  const primaryTime = firstUsefulTime(destination.opening_hours || []);
  time.textContent = primaryTime ? `${copy().chipTime}: ${primaryTime}` : "";
  card.append(title, address);
  if (distance.textContent) card.append(distance);
  if (time.textContent) card.append(time);
}

function renderLeafletMap(mapData) {
  if (!window.L) {
    byId("mapFallback").hidden = false;
    byId("mapFallback").textContent = copy().mapFallback;
    return;
  }
  if (state.mapInstance) {
    state.mapInstance.remove();
    state.mapInstance = null;
  }
  state.mapMarkers = [];
  const mapConfig = state.health?.map || {};
  const map = window.L.map(byId("answerMap"), { zoomControl: true });
  state.mapInstance = map;
  window.L.tileLayer(mapConfig.tile_url_template || "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: mapConfig.tile_attribution || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: mapConfig.tile_max_zoom || 16,
  }).addTo(map);
  const bounds = [];
  const coordinateCounts = coordinateGroups(mapData.destinations);
  const coordinateSeen = new Map();
  if (mapData.origin) {
    const origin = window.L.circleMarker([mapData.origin.latitude, mapData.origin.longitude], {
      radius: 7,
      color: "#17658d",
      fillColor: "#17658d",
      fillOpacity: 0.75,
    }).addTo(map);
    origin.bindPopup(`<strong>${escapeHtml(mapData.origin.label)}</strong><br>${escapeHtml(mapData.origin.address || "")}`);
    bounds.push([mapData.origin.latitude, mapData.origin.longitude]);
  }
  for (const destination of mapData.destinations) {
    const key = coordinateKey(destination);
    const seen = coordinateSeen.get(key) || 0;
    coordinateSeen.set(key, seen + 1);
    const markerLatLng = displayedMarkerLatLng(destination, seen, coordinateCounts.get(key) || 1);
    const marker = window.L.circleMarker(markerLatLng, markerStyle(destination.id === state.selectedMapDestinationId)).addTo(map);
    marker.bindPopup(mapPopup(destination));
    marker.on("click", () => {
      state.selectedMapDestinationId = destination.id;
      state.selectedOfferId = destination.page_id || destination.id;
      renderMapDestinationList(mapData);
      renderMapDetail(destination);
      updateOfferSelection();
      updateMarkerSelection();
    });
    state.mapMarkers.push({ id: destination.id, marker });
    bounds.push(markerLatLng);
  }
  if (bounds.length === 1) {
    map.setView(bounds[0], Math.min(mapConfig.tile_max_zoom || 16, 15));
  } else {
    map.fitBounds(bounds, { padding: [28, 28], maxZoom: mapConfig.tile_max_zoom || 16 });
  }
  window.setTimeout(() => {
    if (state.mapInstance === map) map.invalidateSize();
  }, 100);
}

function selectOffer(pageId, options = {}) {
  state.selectedOfferId = pageId;
  const destination = state.currentMapData?.destinations?.find((item) => item.page_id === pageId || item.id === pageId);
  if (destination) {
    state.selectedMapDestinationId = destination.id;
    renderMapDestinationList(state.currentMapData);
    renderMapDetail(destination);
    updateMarkerSelection();
    const marker = state.mapMarkers.find((item) => item.id === destination.id)?.marker;
    if (marker && state.mapInstance) {
      state.mapInstance.panTo(marker.getLatLng(), { animate: true });
      marker.openPopup();
    }
  }
  updateOfferSelection();
  if (options.fromCard) setStatus(copy().detailsShown);
}

function updateOfferSelection() {
  for (const card of document.querySelectorAll(".offer-card")) {
    const selected = card.dataset.pageId === state.selectedOfferId;
    card.classList.toggle("is-selected", selected);
    card.setAttribute("aria-pressed", String(selected));
    const details = card.querySelector(".offer-card__details");
    if (details) details.hidden = !selected;
  }
}

function updateMarkerSelection() {
  for (const item of state.mapMarkers) {
    item.marker.setStyle(markerStyle(item.id === state.selectedMapDestinationId));
    if (item.id === state.selectedMapDestinationId) item.marker.bringToFront();
  }
}

function coordinateKey(destination) {
  return `${Number(destination.latitude).toFixed(6)},${Number(destination.longitude).toFixed(6)}`;
}

function coordinateGroups(destinations) {
  const counts = new Map();
  for (const destination of destinations) {
    const key = coordinateKey(destination);
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return counts;
}

function displayedMarkerLatLng(destination, index, total) {
  const lat = Number(destination.latitude);
  const lng = Number(destination.longitude);
  if (total <= 1) return [lat, lng];
  const angle = (2 * Math.PI * index) / total;
  const offset = 0.00012;
  return [lat + Math.sin(angle) * offset, lng + Math.cos(angle) * offset];
}

function markerStyle(selected = false) {
  return {
    radius: selected ? 13 : 10,
    color: "#ffffff",
    weight: selected ? 4 : 3,
    fillColor: selected ? "#17705f" : "#17658d",
    fillOpacity: 0.95,
    opacity: 1,
    className: selected ? "lena-map-marker lena-map-marker--selected" : "lena-map-marker",
  };
}

function formatDistance(distanceMeters) {
  if (!Number.isFinite(distanceMeters)) return "";
  if (distanceMeters < 1000) return `${Math.round(distanceMeters)} m`;
  return `${(distanceMeters / 1000).toFixed(1)} km`;
}

function mapPopup(destination) {
  const lines = [
    `<strong>${escapeHtml(shortTitle(destination.label, destination.page_id))}</strong>`,
    escapeHtml(destination.address || ""),
  ];
  const primaryTime = firstUsefulTime(destination.opening_hours || []);
  if (primaryTime) lines.push(escapeHtml(primaryTime));
  return lines.filter(Boolean).join("<br>");
}

function firstUsefulTime(openingHours) {
  return openingHours.find((item) => {
    const text = String(item || "").trim();
    if (!text) return false;
    const normalized = text.toLocaleLowerCase("de-DE");
    if (normalized.endsWith(":")) return false;
    return ![
      "offene sprechzeiten",
      "mobiles angebot",
      "standzeiten",
      "übernachtungshaus",
      "kostenlose notschlafstelle",
      "sozialdienst erreichbarkeit",
    ].some((label) => normalized.includes(label));
  }) || "";
}

async function toggleMic() {
  if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
    state.mediaRecorder.stop();
    return;
  }
  if (!state.health) {
    await loadHealth();
  }
  if (state.health?.stt_provider === "mock") {
    openTextInput(copy().mockStt);
    return;
  }
  if (!canUseBrowserRecording()) {
    openTextInput(copy().sttMissing);
    return;
  }
  try {
    state.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.chunks = [];
    state.recording = true;
    applyLanguage();
    state.mediaRecorder = new MediaRecorder(state.mediaStream);
    state.mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) state.chunks.push(event.data);
    });
    state.mediaRecorder.addEventListener("stop", submitRecordingForReview);
    state.mediaRecorder.start();
    setStatus(copy().listening);
  } catch {
    state.recording = false;
    applyLanguage();
    setStatus(copy().sttMissing);
  }
}

async function submitRecordingForReview() {
  if (state.ignoreNextRecordingStop) {
    state.ignoreNextRecordingStop = false;
    return;
  }
  state.recording = false;
  applyLanguage();
  for (const track of state.mediaStream?.getTracks() || []) {
    track.stop();
  }
  const blob = new Blob(state.chunks, { type: state.mediaRecorder?.mimeType || "audio/webm" });
  const form = new FormData();
  form.append("audio", blob, "speech.webm");
  form.append("language", state.language);
  const response = await fetch("/api/speech/transcribe", { method: "POST", body: form });
  if (!response.ok) {
    byId("textPanel").hidden = false;
    setStatus(copy().sttMissing);
    return;
  }
  const data = await response.json();
  if (data.status !== "ok" || !data.transcript) {
    byId("textPanel").hidden = false;
    setStatus(data.detail || copy().sttMissing);
    byId("textInput").focus();
    return;
  }
  byId("transcriptInput").value = data.transcript || "";
  byId("transcriptReview").hidden = false;
  byId("textPanel").hidden = true;
  byId("answerPanel").hidden = true;
  byId("transcriptInput").focus();
  byId("transcriptInput").select();
  setStatus(copy().review);
}

function cancelTranscript() {
  byId("transcriptInput").value = "";
  byId("transcriptReview").hidden = true;
  setStatus(copy().ready);
}

function cancelCurrentRequest() {
  resetInteractionState();
}

async function speakLastAnswer() {
  if (!state.lastAnswer) return;
  const data = await api("/api/speech/synthesize", {
    method: "POST",
    body: JSON.stringify({ text: state.lastAnswer, language: state.language }),
  });
  if (data.audio_url) {
    new Audio(data.audio_url).play();
  }
}

async function speakIntroOnce() {
  const text = copy().introText;
  if (!text) return;
  try {
    const data = await api("/api/speech/synthesize", {
      method: "POST",
      body: JSON.stringify({ text, language: state.language }),
    });
    if (data.audio_url) {
      void new Audio(data.audio_url).play();
    }
  } catch {
    // Intro speech is helpful, but the UI must never depend on TTS.
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}

document.addEventListener("DOMContentLoaded", () => {
  renderStaticIcons();
  document.querySelectorAll(".language-option").forEach((button) => {
    button.addEventListener("click", () => showMain(button.dataset.language || "de", { speakIntro: true }));
  });
  byId("homeButton").addEventListener("click", goHome);
  byId("backButton").addEventListener("click", goBack);
  byId("languageButton").addEventListener("click", showLanguage);
  byId("cancelButton").addEventListener("click", cancelCurrentRequest);
  byId("endSessionButton").addEventListener("click", async () => {
    if (state.sessionId) {
      await api("/api/session/end", { method: "POST", body: JSON.stringify({ session_id: state.sessionId }) });
    }
    state.sessionId = null;
    showLanguage();
  });
  byId("emergencyButton").addEventListener("click", () => sendSymbol("emergency"));
  byId("textForm").addEventListener("submit", (event) => {
    event.preventDefault();
    void sendQuery(byId("textInput").value);
  });
  byId("micButton").addEventListener("click", toggleMic);
  byId("textModeButton").addEventListener("click", () => openTextInput(copy().ready));
  byId("sendTranscriptButton").addEventListener("click", () => {
    void sendQuery(byId("transcriptInput").value);
    cancelTranscript();
  });
  byId("retryTranscriptButton").addEventListener("click", () => {
    cancelTranscript();
    void toggleMic();
  });
  byId("cancelTranscriptButton").addEventListener("click", cancelTranscript);
  byId("speakButton").addEventListener("click", speakLastAnswer);
  applyLanguage();
});
