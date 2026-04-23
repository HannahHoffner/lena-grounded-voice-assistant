const STORAGE_KEY = "lena.selectedLanguage";
const SUPPORTED_LANGUAGES = ["de", "en", "pl", "ro", "ru"];
const SESSION_TIMEOUT_MS = 5 * 60 * 1000;

const elements = {
  brandEyebrow: document.getElementById("brandEyebrow"),
  appTitle: document.getElementById("appTitle"),
  appSubtitle: document.getElementById("appSubtitle"),
  languageLabel: document.getElementById("languageLabel"),
  languageHint: document.getElementById("languageHint"),
  languageButtons: [...document.querySelectorAll(".flag-button")],
  interactionLabel: document.getElementById("interactionLabel"),
  interactionHint: document.getElementById("interactionHint"),
  sessionState: document.getElementById("sessionState"),
  endConversationButton: document.getElementById("endConversationButton"),
  recordButton: document.getElementById("recordButton"),
  recordButtonText: document.getElementById("recordButtonText"),
  statusText: document.getElementById("status"),
  manualQuestionForm: document.getElementById("manualQuestionForm"),
  manualQuestionInput: document.getElementById("manualQuestion"),
  manualQuestionLabel: document.getElementById("manualQuestionLabel"),
  manualSubmitButton: document.getElementById("manualSubmitButton"),
  answerLabel: document.getElementById("answerLabel"),
  answerHint: document.getElementById("answerHint"),
  answerState: document.getElementById("answerState"),
  answerText: document.getElementById("answerText"),
  mapPanel: document.getElementById("mapPanel"),
  mapLabel: document.getElementById("mapLabel"),
  mapHint: document.getElementById("mapHint"),
  mapCanvasWrap: document.getElementById("mapCanvasWrap"),
  mapCanvas: document.getElementById("answerMap"),
  mapFallback: document.getElementById("mapFallback"),
  mapListLabel: document.getElementById("mapListLabel"),
  mapDestinationList: document.getElementById("mapDestinationList"),
  mapDetailCard: document.getElementById("mapDetailCard"),
};

const languageMap = {
  de: "de-DE",
  en: "en-GB",
  pl: "pl-PL",
  ro: "ro-RO",
  ru: "ru-RU",
};

const translations = {
  de: {
    title: "LENA",
    brandEyebrow: "Lokaler sprachbasierter Wegweiser",
    subtitle: "Finden Sie Hilfeangebote in Leipzig per Sprache oder kurzer Texteingabe.",
    languageLabel: "Sprache",
    languageHint: "Die Auswahl steuert Oberfläche, Spracheingabe, Sprachausgabe und Backend-Anfragen.",
    interactionLabel: "Frage stellen",
    interactionHint: "Sprechen Sie zuerst, oder tippen Sie unten eine kurze Testfrage ein.",
    endConversation: "Gespräch beenden",
    recordSpeak: "Sprechen",
    recordStop: "Stopp",
    manualLabel: "Oder tippen",
    manualPlaceholder: "Frage zum Testen eingeben",
    manualSubmit: "Senden",
    answerLabel: "Antwort",
    answerHint: "Die Antwort bleibt auf die lokale Wissensbasis beschränkt.",
    answerPlaceholder: "Die Antwort erscheint hier.",
    answerState: {
      clarification_needed: { label: "Kurze Rueckfrage", tone: "neutral" },
      weak_match: { label: "Aehnlicher Treffer", tone: "warning" },
      out_of_scope: { label: "Thema ausserhalb von LENA", tone: "warning" },
      self_description: { label: "Ueber LENA", tone: "neutral" },
      crisis: { label: "Soforthilfe", tone: "critical" },
    },
    session: {
      inactive: "Kein aktives Gespräch",
      active: "Gespräch aktiv",
      started: "Neues Gespräch gestartet",
      reset: "Neues Gespräch gestartet",
      languageReset: "Neues Gespräch nach Sprachwechsel",
      expired: "Gespräch abgelaufen",
      ended: "Gespräch beendet",
    },
    status: {
      idle: "Bereit",
      browserFallback: "Browser-Spracherkennung aktiv",
      browserTtsFallback: "Browser-Sprachausgabe aktiv",
      typedFallback: "Spracheingabe ist hier nicht verfügbar. Bitte unten tippen.",
      listening: "Ich höre zu",
      processing: "Ich suche in der Wissensbasis",
      clarifying: "Ich präzisiere die Antwort",
      speaking: "Ich spreche die Antwort aus",
      error: "Fehler",
    },
    errors: {
      generic: "Es gab ein Problem. Bitte versuchen Sie es noch einmal.",
      speechUnavailable: "Spracherkennung ist gerade nicht verfügbar.",
      backendSpeechFallback: "Die Backend-Spracherkennung ist gerade nicht verfügbar. Beim nächsten Versuch nutze ich die Browser-Spracherkennung.",
      backendSpeechUnavailable: "Die Backend-Spracherkennung ist gerade nicht verfügbar.",
      backendTtsFallback: "Die Backend-Sprachausgabe ist gerade nicht verfügbar. Ich nutze die Browser-Stimme.",
    },
  },
  en: {
    title: "LENA",
    brandEyebrow: "Local grounded voice assistant",
    subtitle: "Find support services in Leipzig by voice or a short typed question.",
    languageLabel: "Language",
    languageHint: "This controls the interface, speech input, speech output, and backend queries.",
    interactionLabel: "Ask a question",
    interactionHint: "Speak first, or type a short test question below.",
    endConversation: "End conversation",
    recordSpeak: "Speak",
    recordStop: "Stop",
    manualLabel: "Or type instead",
    manualPlaceholder: "Type a question for quick testing",
    manualSubmit: "Send",
    answerLabel: "Answer",
    answerHint: "Answers stay grounded in the local knowledge base.",
    answerPlaceholder: "Your answer will appear here.",
    answerState: {
      clarification_needed: { label: "Quick follow-up", tone: "neutral" },
      weak_match: { label: "Close match", tone: "warning" },
      out_of_scope: { label: "Outside LENA's scope", tone: "warning" },
      self_description: { label: "About LENA", tone: "neutral" },
      crisis: { label: "Urgent help", tone: "critical" },
    },
    session: {
      inactive: "No active conversation",
      active: "Conversation active",
      started: "New conversation started",
      reset: "New conversation started",
      languageReset: "New conversation after language change",
      expired: "Conversation expired",
      ended: "Conversation ended",
    },
    status: {
      idle: "Ready",
      browserFallback: "Browser speech fallback active",
      browserTtsFallback: "Browser speech output active",
      typedFallback: "Speech input is unavailable here. Please type a question below.",
      listening: "Listening",
      processing: "Searching the knowledge base",
      clarifying: "Clarifying the answer",
      speaking: "Speaking the answer",
      error: "Error",
    },
    errors: {
      generic: "Something went wrong. Please try again.",
      speechUnavailable: "Speech recognition is unavailable right now.",
      backendSpeechFallback: "Backend speech recognition is unavailable right now. I will use browser speech recognition on the next try.",
      backendSpeechUnavailable: "Backend speech recognition is unavailable right now.",
      backendTtsFallback: "Backend speech output is unavailable right now. I am using the browser voice instead.",
    },
  },
  pl: {
    title: "LENA",
    brandEyebrow: "Lokalny asystent glosowy",
    subtitle: "Znajdz pomoc w Lipsku glosem albo krotkim pytaniem wpisanym recznie.",
    languageLabel: "Jezyk",
    languageHint: "Wybor steruje interfejsem, rozpoznawaniem mowy, synteza mowy i zapytaniami do backendu.",
    interactionLabel: "Zadaj pytanie",
    interactionHint: "Najpierw mow, a ponizej mozesz tez wpisac krotkie pytanie testowe.",
    endConversation: "Zakoncz rozmowe",
    recordSpeak: "Mow",
    recordStop: "Stop",
    manualLabel: "Lub wpisz",
    manualPlaceholder: "Wpisz pytanie testowe",
    manualSubmit: "Wyslij",
    answerLabel: "Odpowiedz",
    answerHint: "Odpowiedz pozostaje oparta na lokalnej bazie wiedzy.",
    answerPlaceholder: "Odpowiedz pojawi sie tutaj.",
    answerState: {
      clarification_needed: { label: "Krotkie doprecyzowanie", tone: "neutral" },
      weak_match: { label: "Podobny wynik", tone: "warning" },
      out_of_scope: { label: "Poza zakresem LENA", tone: "warning" },
      self_description: { label: "O LENIE", tone: "neutral" },
      crisis: { label: "Pilna pomoc", tone: "critical" },
    },
    session: {
      inactive: "Brak aktywnej rozmowy",
      active: "Rozmowa aktywna",
      started: "Rozpoczeto nowa rozmowe",
      reset: "Rozpoczeto nowa rozmowe",
      languageReset: "Nowa rozmowa po zmianie jezyka",
      expired: "Rozmowa wygasla",
      ended: "Rozmowa zakonczona",
    },
    status: {
      idle: "Gotowe",
      browserFallback: "Aktywne rozpoznawanie mowy w przegladarce",
      browserTtsFallback: "Aktywna synteza mowy w przegladarce",
      typedFallback: "Wprowadzanie glosowe jest tutaj niedostepne. Wpisz pytanie ponizej.",
      listening: "Slucham",
      processing: "Przeszukuje baze wiedzy",
      clarifying: "Doprecyzowuje odpowiedz",
      speaking: "Odczytuje odpowiedz",
      error: "Blad",
    },
    errors: {
      generic: "Wystapil problem. Sprobuj ponownie.",
      speechUnavailable: "Rozpoznawanie mowy jest teraz niedostepne.",
      backendSpeechFallback: "Rozpoznawanie mowy w backendzie jest teraz niedostepne. Przy kolejnej probie uzyje przegladarki.",
      backendSpeechUnavailable: "Rozpoznawanie mowy w backendzie jest teraz niedostepne.",
      backendTtsFallback: "Synteza mowy w backendzie jest teraz niedostepna. Uzywam glosu przegladarki.",
    },
  },
  ro: {
    title: "LENA",
    brandEyebrow: "Asistent vocal local",
    subtitle: "Gaseste servicii de sprijin din Leipzig prin voce sau printr-o intrebare scurta scrisa.",
    languageLabel: "Limba",
    languageHint: "Selectia controleaza interfata, recunoasterea vorbirii, redarea vocala si cererile catre backend.",
    interactionLabel: "Pune o intrebare",
    interactionHint: "Vorbeste mai intai sau scrie mai jos o intrebare scurta pentru test.",
    endConversation: "Incheie conversatia",
    recordSpeak: "Vorbeste",
    recordStop: "Stop",
    manualLabel: "Sau scrie",
    manualPlaceholder: "Scrie o intrebare pentru test",
    manualSubmit: "Trimite",
    answerLabel: "Raspuns",
    answerHint: "Raspunsul ramane limitat la baza locala de cunostinte.",
    answerPlaceholder: "Raspunsul va aparea aici.",
    answerState: {
      clarification_needed: { label: "Scurta clarificare", tone: "neutral" },
      weak_match: { label: "Rezultat apropiat", tone: "warning" },
      out_of_scope: { label: "In afara scopului LENA", tone: "warning" },
      self_description: { label: "Despre LENA", tone: "neutral" },
      crisis: { label: "Ajutor urgent", tone: "critical" },
    },
    session: {
      inactive: "Nicio conversatie activa",
      active: "Conversatie activa",
      started: "A inceput o conversatie noua",
      reset: "A inceput o conversatie noua",
      languageReset: "Conversatie noua dupa schimbarea limbii",
      expired: "Conversatie expirata",
      ended: "Conversatie incheiata",
    },
    status: {
      idle: "Pregatit",
      browserFallback: "Recunoasterea vocala din browser este activa",
      browserTtsFallback: "Redarea vocala din browser este activa",
      typedFallback: "Intrarea vocala nu este disponibila aici. Te rugam sa scrii mai jos.",
      listening: "Ascult",
      processing: "Caut in baza de cunostinte",
      clarifying: "Clarific raspunsul",
      speaking: "Redau raspunsul",
      error: "Eroare",
    },
    errors: {
      generic: "A aparut o problema. Incearca din nou.",
      speechUnavailable: "Recunoasterea vorbirii nu este disponibila acum.",
      backendSpeechFallback: "Recunoasterea vorbirii din backend nu este disponibila acum. La urmatoarea incercare voi folosi browserul.",
      backendSpeechUnavailable: "Recunoasterea vorbirii din backend nu este disponibila acum.",
      backendTtsFallback: "Redarea vocala din backend nu este disponibila acum. Folosesc vocea browserului.",
    },
  },
  ru: {
    title: "LENA",
    brandEyebrow: "Lokalnyi golosovoi pomoshchnik",
    subtitle: "Naydite pomoshch v Leiptsige golosom ili korotkim vvedennym voprosom.",
    languageLabel: "Yazyk",
    languageHint: "Vybor upravlyaet interfeisom, raspoznavaniem rechi, ozvuchivaniem i zaprosami k backendu.",
    interactionLabel: "Zadayte vopros",
    interactionHint: "Snachala skazhite vopros, ili vvedite korotkii testovyi zapros nizhe.",
    endConversation: "Zavershit razgovor",
    recordSpeak: "Govorit",
    recordStop: "Stop",
    manualLabel: "Ili vvedite tekst",
    manualPlaceholder: "Vvedite testovyi vopros",
    manualSubmit: "Otpravit",
    answerLabel: "Otvet",
    answerHint: "Otvet ogranichen lokalnoi bazoi znanii.",
    answerPlaceholder: "Otvet poyavitsya zdes.",
    answerState: {
      clarification_needed: { label: "Korotkiy vopros", tone: "neutral" },
      weak_match: { label: "Pokhozhiy rezultat", tone: "warning" },
      out_of_scope: { label: "Vne vozmozhnostey LENA", tone: "warning" },
      self_description: { label: "O LENA", tone: "neutral" },
      crisis: { label: "Srochnaya pomoshch", tone: "critical" },
    },
    session: {
      inactive: "Net aktivnogo razgovora",
      active: "Razgovor aktiven",
      started: "Nachat novyi razgovor",
      reset: "Nachat novyi razgovor",
      languageReset: "Novyi razgovor posle smeny yazyka",
      expired: "Razgovor istek",
      ended: "Razgovor zavershen",
    },
    status: {
      idle: "Gotovo",
      browserFallback: "Aktivno raspoznavanie rechi v brauzere",
      browserTtsFallback: "Aktivno ozvuchivanie v brauzere",
      typedFallback: "Golosovoi vvod zdes nedostupen. Pozhaluista, vvedite vopros nizhe.",
      listening: "Slushayu",
      processing: "Ishchu v baze znanii",
      clarifying: "Utochnyayu otvet",
      speaking: "Ozvuchivayu otvet",
      error: "Oshibka",
    },
    errors: {
      generic: "Proizoshla oshibka. Pozhaluista, povtorite popytku.",
      speechUnavailable: "Raspoznavanie rechi seichas nedostupno.",
      backendSpeechFallback: "Backend raspoznavaniya rechi seichas nedostupen. Pri sleduyushchei popytke ya ispolzuyu brauzer.",
      backendSpeechUnavailable: "Backend raspoznavaniya rechi seichas nedostupen.",
      backendTtsFallback: "Backend ozvuchivaniya seichas nedostupen. Ya ispolzuyu golos brauzera.",
    },
  },
};

const mapTranslations = {
  de: {
    label: "Karte",
    hint: "Relevante Orte ab Leipzig Hauptbahnhof.",
    listLabel: "Orte",
    tileFallback: "Die Karte konnte gerade nicht geladen werden. Die passenden Orte bleiben unten sichtbar.",
    detailEmpty: "Waehlen Sie einen Ort aus, um mehr Details zu sehen.",
    origin: "Start",
    address: "Adresse",
    serviceType: "Angebot",
    distance: "Entfernung",
    hours: "Oeffnungszeiten",
    noHours: "Keine klaren Oeffnungszeiten in der Wissensbasis.",
    approx: "ca.",
  },
  en: {
    label: "Map",
    hint: "Relevant places from Leipzig Hauptbahnhof.",
    listLabel: "Places",
    tileFallback: "The map could not be loaded right now. The relevant places remain visible below.",
    detailEmpty: "Select a place to see more details.",
    origin: "Start",
    address: "Address",
    serviceType: "Service",
    distance: "Distance",
    hours: "Opening hours",
    noHours: "No clear opening hours in the knowledge base.",
    approx: "approx.",
  },
  pl: {
    label: "Mapa",
    hint: "Wazne miejsca od dworca glownego w Lipsku.",
    listLabel: "Miejsca",
    tileFallback: "Mapa nie mogla zostac teraz zaladowana. Pasujace miejsca pozostaja widoczne ponizej.",
    detailEmpty: "Wybierz miejsce, aby zobaczyc wiecej szczegolow.",
    origin: "Start",
    address: "Adres",
    serviceType: "Usluga",
    distance: "Odleglosc",
    hours: "Godziny otwarcia",
    noHours: "Brak jasnych godzin otwarcia w bazie wiedzy.",
    approx: "ok.",
  },
  ro: {
    label: "Harta",
    hint: "Locuri relevante de la Leipzig Hauptbahnhof.",
    listLabel: "Locuri",
    tileFallback: "Harta nu a putut fi incarcata acum. Locurile relevante raman vizibile mai jos.",
    detailEmpty: "Selecteaza un loc pentru mai multe detalii.",
    origin: "Pornire",
    address: "Adresa",
    serviceType: "Serviciu",
    distance: "Distanta",
    hours: "Program",
    noHours: "Nu exista un program clar in baza de cunostinte.",
    approx: "cca.",
  },
  ru: {
    label: "Karta",
    hint: "Podkhodyashchie mesta ot Leipzig Hauptbahnhof.",
    listLabel: "Mesta",
    tileFallback: "Kartu seychas ne udalos zagruzit. Podkhodyashchie mesta ostayutsya vidimy nizhe.",
    detailEmpty: "Vyberite mesto, chtoby uvidet bolshe detaley.",
    origin: "Start",
    address: "Adres",
    serviceType: "Usluga",
    distance: "Rasstoyanie",
    hours: "Chasy raboty",
    noHours: "V baze znaniy net ponyatnykh chasov raboty.",
    approx: "okolo",
  },
};

const defaultMapConfig = {
  tile_url_template: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  tile_attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  tile_max_zoom: 16,
};

const state = {
  mediaRecorder: null,
  chunks: [],
  recording: false,
  runtimeHealth: null,
  browserRecognition: null,
  submitting: false,
  sessionId: null,
  sessionNotice: null,
  sessionTimerId: null,
  sessionTimeoutMs: SESSION_TIMEOUT_MS,
  currentAudio: null,
  statusKey: "idle",
  forceBrowserSttFallback: false,
  answerStatus: null,
  currentMapData: null,
  selectedMapDestinationId: null,
  mapInstance: null,
  mapMarkers: [],
  language: loadInitialLanguage(),
};

function loadInitialLanguage() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED_LANGUAGES.includes(stored)) {
      return stored;
    }
  } catch {}
  return "de";
}

function persistLanguage(language) {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {}
}

function getCopy() {
  return translations[state.language] || translations.de;
}

function getMapCopy() {
  return mapTranslations[state.language] || mapTranslations.de;
}

function getMapConfig() {
  return state.runtimeHealth?.map || defaultMapConfig;
}

function showPlaceholder() {
  elements.answerText.dataset.state = "placeholder";
  elements.answerText.textContent = getCopy().answerPlaceholder;
  hideAnswerState();
  clearMapPanel();
}

function showAnswer(text) {
  elements.answerText.dataset.state = "answer";
  elements.answerText.textContent = text;
}

function clearMapPanel() {
  state.currentMapData = null;
  state.selectedMapDestinationId = null;
  state.mapMarkers = [];
  if (state.mapInstance) {
    state.mapInstance.remove();
    state.mapInstance = null;
  }
  elements.mapPanel.hidden = true;
  elements.mapCanvas.hidden = false;
  elements.mapFallback.hidden = true;
  elements.mapFallback.textContent = "";
  elements.mapDestinationList.replaceChildren();
  elements.mapDetailCard.replaceChildren();
}

function hideAnswerState() {
  state.answerStatus = null;
  elements.answerState.hidden = true;
  elements.answerState.textContent = "";
  delete elements.answerState.dataset.tone;
}

function formatDistance(distanceMeters) {
  const mapCopy = getMapCopy();
  if (!Number.isFinite(distanceMeters)) {
    return "";
  }
  if (distanceMeters < 1000) {
    return `${mapCopy.approx} ${Math.round(distanceMeters)} m`;
  }
  const kmValue = distanceMeters < 2000 ? (distanceMeters / 1000).toFixed(1) : Math.round(distanceMeters / 1000);
  return `${mapCopy.approx} ${kmValue} km`;
}

function activeDestination() {
  if (!state.currentMapData?.destinations?.length) {
    return null;
  }
  return (
    state.currentMapData.destinations.find((item) => item.id === state.selectedMapDestinationId) ||
    state.currentMapData.destinations[0] ||
    null
  );
}

function renderMapDetail(destination) {
  elements.mapDetailCard.replaceChildren();
  const mapCopy = getMapCopy();
  if (!destination) {
    const empty = document.createElement("p");
    empty.className = "map-detail-card__empty";
    empty.textContent = mapCopy.detailEmpty;
    elements.mapDetailCard.append(empty);
    return;
  }

  const title = document.createElement("h3");
  title.className = "map-detail-card__title";
  title.textContent = destination.label;
  elements.mapDetailCard.append(title);

  if (destination.organization_label) {
    const org = document.createElement("p");
    org.className = "map-detail-card__org";
    org.textContent = destination.organization_label;
    elements.mapDetailCard.append(org);
  }

  const info = document.createElement("div");
  info.className = "map-detail-card__info";

  const address = document.createElement("p");
  address.className = "map-detail-card__line";
  address.textContent = `${mapCopy.address}: ${destination.address}`;
  info.append(address);

  const serviceType = document.createElement("p");
  serviceType.className = "map-detail-card__line";
  serviceType.textContent = `${mapCopy.serviceType}: ${destination.service_type}`;
  info.append(serviceType);

  if (Number.isFinite(destination.distance_meters)) {
    const distance = document.createElement("p");
    distance.className = "map-detail-card__line";
    distance.textContent = `${mapCopy.distance}: ${formatDistance(destination.distance_meters)}`;
    info.append(distance);
  }

  if (destination.description) {
    const description = document.createElement("p");
    description.className = "map-detail-card__line";
    description.textContent = destination.description;
    info.append(description);
  }

  const hoursLabel = document.createElement("p");
  hoursLabel.className = "map-detail-card__line";
  hoursLabel.textContent = `${mapCopy.hours}:`;
  info.append(hoursLabel);

  if (destination.opening_hours?.length) {
    const list = document.createElement("ul");
    list.className = "map-detail-card__hours";
    for (const hours of destination.opening_hours) {
      const item = document.createElement("li");
      item.textContent = hours;
      list.append(item);
    }
    info.append(list);
  } else {
    const noHours = document.createElement("p");
    noHours.className = "map-detail-card__line";
    noHours.textContent = mapCopy.noHours;
    info.append(noHours);
  }

  elements.mapDetailCard.append(info);
}

function popupMarkup(destination) {
  const distance = formatDistance(destination.distance_meters);
  const lines = [
    `<div class="map-popup__title">${destination.label}</div>`,
    `<div class="map-popup__meta">${destination.address}</div>`,
  ];
  if (distance) {
    lines.push(`<div class="map-popup__meta">${distance}</div>`);
  }
  return lines.join("");
}

function selectMapDestination(destinationId, options = {}) {
  if (!state.currentMapData?.destinations?.length) {
    return;
  }
  state.selectedMapDestinationId = destinationId;
  const destination = activeDestination();

  for (const button of elements.mapDestinationList.querySelectorAll(".map-destination-button")) {
    button.classList.toggle("is-selected", button.dataset.destinationId === destinationId);
    button.setAttribute("aria-pressed", String(button.dataset.destinationId === destinationId));
  }

  renderMapDetail(destination);

  if (state.mapInstance && options.panTo !== false && destination) {
    const targetMarker = state.mapMarkers.find((item) => item.id === destination.id)?.marker;
    if (targetMarker) {
      state.mapInstance.panTo(targetMarker.getLatLng(), { animate: true });
      targetMarker.openPopup();
    }
  }
}

function renderMapDestinationList(mapData) {
  elements.mapDestinationList.replaceChildren();
  for (const destination of mapData.destinations) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "map-destination-button";
    button.dataset.destinationId = destination.id;
    button.setAttribute("aria-pressed", String(destination.id === state.selectedMapDestinationId));

    const title = document.createElement("span");
    title.className = "map-destination-button__title";
    title.textContent = destination.label;
    button.append(title);

    const meta = document.createElement("span");
    meta.className = "map-destination-button__meta";
    meta.textContent = [formatDistance(destination.distance_meters), destination.address].filter(Boolean).join(" · ");
    button.append(meta);

    button.addEventListener("click", () => selectMapDestination(destination.id));
    elements.mapDestinationList.append(button);
  }
}

function renderLeafletMap(mapData) {
  if (!window.L) {
    elements.mapCanvas.hidden = true;
    elements.mapFallback.hidden = false;
    elements.mapFallback.textContent = getMapCopy().tileFallback;
    return;
  }

  if (state.mapInstance) {
    state.mapInstance.remove();
    state.mapInstance = null;
  }
  state.mapMarkers = [];
  elements.mapCanvas.hidden = false;
  elements.mapFallback.hidden = true;
  elements.mapFallback.textContent = "";

  const mapConfig = getMapConfig();
  const map = window.L.map(elements.mapCanvas, { zoomControl: true });
  state.mapInstance = map;

  let tileLoadSucceeded = false;
  let tileFallbackShown = false;
  let tileFallbackTimer = null;

  const showTileFallback = () => {
    if (tileFallbackShown || state.mapInstance !== map) {
      return;
    }
    tileFallbackShown = true;
    elements.mapFallback.hidden = false;
    elements.mapFallback.textContent = getMapCopy().tileFallback;
  };

  const hideTileFallback = () => {
    if (state.mapInstance !== map) {
      return;
    }
    tileFallbackShown = false;
    elements.mapFallback.hidden = true;
    elements.mapFallback.textContent = "";
  };

  const tiles = window.L.tileLayer(mapConfig.tile_url_template, {
    attribution: mapConfig.tile_attribution,
    maxZoom: mapConfig.tile_max_zoom || defaultMapConfig.tile_max_zoom,
    subdomains: "abc",
  });
  tiles.on("tileload", () => {
    tileLoadSucceeded = true;
    if (tileFallbackTimer) {
      window.clearTimeout(tileFallbackTimer);
      tileFallbackTimer = null;
    }
    hideTileFallback();
  });
  tiles.on("tileerror", () => {
    if (!tileLoadSucceeded) {
      showTileFallback();
    }
  });
  tiles.addTo(map);

  tileFallbackTimer = window.setTimeout(() => {
    if (!tileLoadSucceeded) {
      showTileFallback();
    }
  }, 2500);

  const bounds = [];
  const originMarker = window.L.circleMarker([mapData.origin.latitude, mapData.origin.longitude], {
    radius: 7,
    color: "#111111",
    weight: 2,
    fillColor: "#ffffff",
    fillOpacity: 1,
  }).addTo(map);
  originMarker.bindPopup(
    `<div class="map-popup__title">${mapData.origin.label}</div><div class="map-popup__meta">${mapData.origin.address}</div>`
  );
  bounds.push([mapData.origin.latitude, mapData.origin.longitude]);

  for (const destination of mapData.destinations) {
    const marker = window.L.marker([destination.latitude, destination.longitude]).addTo(map);
    marker.bindPopup(popupMarkup(destination));
    marker.on("click", () => selectMapDestination(destination.id, { panTo: false }));
    state.mapMarkers.push({ id: destination.id, marker });
    bounds.push([destination.latitude, destination.longitude]);
  }

  if (bounds.length === 1) {
    map.setView(bounds[0], Math.min(mapConfig.tile_max_zoom || defaultMapConfig.tile_max_zoom, 15));
  } else {
    map.fitBounds(bounds, { padding: [36, 36], maxZoom: mapConfig.tile_max_zoom || defaultMapConfig.tile_max_zoom });
  }
  window.setTimeout(() => {
    if (state.mapInstance === map) {
      map.invalidateSize();
    }
  }, 0);
}

function renderMap(answer) {
  const mapData = answer?.map_data;
  if (!mapData?.destinations?.length) {
    clearMapPanel();
    return;
  }

  state.currentMapData = mapData;
  state.selectedMapDestinationId = mapData.selected_destination_id || mapData.destinations[0].id;
  elements.mapPanel.hidden = false;
  renderMapDestinationList(mapData);
  renderMapDetail(activeDestination());
  renderLeafletMap(mapData);
  selectMapDestination(state.selectedMapDestinationId, { panTo: false });
}

function showAnswerState(answer) {
  const status = answer?.status;
  const config = getCopy().answerState?.[status];
  if (!config) {
    hideAnswerState();
    return;
  }
  state.answerStatus = status;
  elements.answerState.hidden = false;
  elements.answerState.textContent = config.label;
  elements.answerState.dataset.tone = config.tone;
}

function setStatus(statusKey) {
  state.statusKey = statusKey;
  renderStatus();
}

function clearSessionTimer() {
  if (state.sessionTimerId) {
    window.clearTimeout(state.sessionTimerId);
    state.sessionTimerId = null;
  }
}

function renderSessionState() {
  const copy = getCopy();
  const fallbackText = state.sessionId ? copy.session.active : copy.session.inactive;
  elements.sessionState.textContent = state.sessionNotice || fallbackText;
  elements.endConversationButton.disabled = state.submitting || state.recording || !state.sessionId;
}

function scheduleSessionExpiry() {
  clearSessionTimer();
  if (!state.sessionId) {
    return;
  }
  state.sessionTimerId = window.setTimeout(() => {
    state.sessionId = null;
    state.sessionNotice = getCopy().session.expired;
    renderSessionState();
  }, state.sessionTimeoutMs);
}

function sessionNoticeForEvent(sessionEvent) {
  const sessionCopy = getCopy().session;
  switch (sessionEvent) {
    case "started":
      return sessionCopy.started;
    case "expired_reset":
      return sessionCopy.expired;
    case "ended_reset":
      return sessionCopy.ended;
    case "context_reset":
      return sessionCopy.reset;
    case "language_reset":
      return sessionCopy.languageReset;
    default:
      return null;
  }
}

function applySessionResponse(answer) {
  state.sessionId = answer.session_id || null;
  const localizedNotice = sessionNoticeForEvent(answer.session_event);
  if (localizedNotice) {
    state.sessionNotice = localizedNotice;
  } else if (answer.session_message) {
    state.sessionNotice = answer.session_message;
  } else {
    state.sessionNotice = state.sessionId ? getCopy().session.active : getCopy().session.inactive;
  }
  if (state.sessionId) {
    scheduleSessionExpiry();
  } else {
    clearSessionTimer();
  }
  renderSessionState();
}

function clearSessionState(message) {
  state.sessionId = null;
  state.sessionNotice = message || getCopy().session.inactive;
  clearSessionTimer();
  renderSessionState();
}

function renderStatus() {
  elements.statusText.textContent = getCopy().status[state.statusKey] || "";
}

function canUseBrowserSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  return Boolean(SpeechRecognition);
}

function getRecorderSupport() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return { supported: false, detail: "getUserMedia_unavailable", mimeType: null };
  }
  if (!window.MediaRecorder) {
    return { supported: false, detail: "mediaRecorder_unavailable", mimeType: null };
  }
  const candidateTypes = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  if (typeof MediaRecorder.isTypeSupported !== "function") {
    return { supported: true, detail: null, mimeType: "audio/webm" };
  }
  for (const mimeType of candidateTypes) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return { supported: true, detail: null, mimeType };
    }
  }
  return { supported: false, detail: "no_supported_recorder_mime_type", mimeType: null };
}

function canUseBackendStt() {
  const stt = state.runtimeHealth?.speech?.stt;
  if (!stt) {
    return true;
  }
  return stt.active_provider !== "mock" && stt.ready === true && !state.forceBrowserSttFallback;
}

function shouldUseBrowserSpeechFallback() {
  if (!canUseBrowserSpeechRecognition()) {
    return false;
  }
  if (state.forceBrowserSttFallback) {
    return true;
  }
  return Boolean(state.runtimeHealth) && !canUseBackendStt();
}

function shouldUseTypedFallback() {
  const recorderSupport = getRecorderSupport();
  if (!recorderSupport.supported && !canUseBrowserSpeechRecognition()) {
    return true;
  }
  return Boolean(state.runtimeHealth) && !canUseBackendStt() && !canUseBrowserSpeechRecognition();
}

function setReadyStatus() {
  if (shouldUseTypedFallback()) {
    setStatus("typedFallback");
    return;
  }
  if (shouldUseBrowserSpeechFallback()) {
    setStatus("browserFallback");
    return;
  }
  setStatus("idle");
}

function focusManualQuestion() {
  elements.manualQuestionInput.focus();
  elements.manualQuestionInput.select();
}

function updateLanguageButtons() {
  const disabled = state.submitting || state.recording;
  for (const button of elements.languageButtons) {
    const isSelected = button.dataset.lang === state.language;
    button.setAttribute("aria-pressed", String(isSelected));
    button.disabled = disabled;
  }
}

function updateInputModeUi() {
  const copy = getCopy();
  const speechUnavailable = shouldUseTypedFallback();
  elements.recordButtonText.textContent = state.recording ? copy.recordStop : copy.recordSpeak;
  elements.recordButton.disabled = state.submitting || speechUnavailable;
  elements.recordButton.classList.toggle("is-recording", state.recording);
  elements.manualQuestionInput.disabled = state.submitting || state.recording;
  elements.manualSubmitButton.disabled = state.submitting || state.recording;
  elements.manualSubmitButton.textContent = copy.manualSubmit;
  updateLanguageButtons();
}

function renderCopy() {
  const copy = getCopy();
  const mapCopy = getMapCopy();
  document.documentElement.lang = state.language;
  document.title = copy.title;
  elements.brandEyebrow.textContent = copy.brandEyebrow;
  elements.appTitle.textContent = copy.title;
  elements.appSubtitle.textContent = copy.subtitle;
  elements.languageLabel.textContent = copy.languageLabel;
  elements.languageHint.textContent = copy.languageHint;
  elements.interactionLabel.textContent = copy.interactionLabel;
  elements.interactionHint.textContent = copy.interactionHint;
  elements.endConversationButton.textContent = copy.endConversation;
  elements.manualQuestionLabel.textContent = copy.manualLabel;
  elements.manualQuestionInput.placeholder = copy.manualPlaceholder;
  elements.answerLabel.textContent = copy.answerLabel;
  elements.answerHint.textContent = copy.answerHint;
  elements.mapLabel.textContent = mapCopy.label;
  elements.mapHint.textContent = mapCopy.hint;
  elements.mapListLabel.textContent = mapCopy.listLabel;
  if (!elements.mapFallback.hidden) {
    elements.mapFallback.textContent = mapCopy.tileFallback;
  }
  if (elements.answerText.dataset.state !== "answer") {
    showPlaceholder();
  } else if (state.answerStatus) {
    showAnswerState({ status: state.answerStatus });
  }
  if (state.currentMapData?.destinations?.length) {
    renderMap({ map_data: state.currentMapData });
  }
  renderStatus();
  renderSessionState();
  updateInputModeUi();
}

function cancelCurrentSpeech() {
  if (state.currentAudio) {
    try {
      state.currentAudio.pause();
      state.currentAudio.currentTime = 0;
    } catch {}
    state.currentAudio = null;
  }
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

function normalizeSpeechText(text, language) {
  let normalized = (text || "").replace(/\s+/g, " ").trim();
  if (!normalized) {
    return normalized;
  }

  const replacements = [
    [/\bAWW\b/g, language === "de" ? "Advent Wohlfahrtswerk" : "Advent Welfare Association"],
    [/\bDRK\b/g, language === "de" ? "Deutsches Rotes Kreuz" : "German Red Cross"],
    [/\bSZL\b/g, language === "de" ? "Suchtzentrum Leipzig" : "Leipzig addiction support center"],
    [/e\.V\./g, language === "de" ? "eingetragener Verein" : "registered association"],
    [/gGmbH/g, language === "de" ? "gemeinnuetzige Gesellschaft mit beschraenkter Haftung" : "non profit limited company"],
    [/z\.\s?B\./g, language === "de" ? "zum Beispiel" : "for example"],
    [/u\.\s?a\./g, language === "de" ? "unter anderem" : "among other things"],
    [/Mo-Fr/g, language === "de" ? "Montag bis Freitag" : "Monday to Friday"],
    [/Mo – Fr/g, language === "de" ? "Montag bis Freitag" : "Monday to Friday"],
    [/Sa, So, Feiertag(e)?/g, language === "de" ? "Samstag, Sonntag und Feiertage" : "Saturday, Sunday and public holidays"],
    [/Str\./g, language === "de" ? "Strasse" : "Street"],
    [/Nr\./g, language === "de" ? "Nummer" : "number"],
    [/;/g, "."],
  ];
  for (const [pattern, value] of replacements) {
    normalized = normalized.replace(pattern, value);
  }
  normalized = normalized.replace(/(\d{1,2}(?::\d{2})?)\s*[–-]\s*(\d{1,2}(?::\d{2})?)\s*Uhr/g, "$1 bis $2 Uhr");
  normalized = normalized.replace(/[&]/g, language === "de" ? " und " : " and ");
  normalized = normalized.replace(/[\\/]/g, language === "de" ? " oder " : " or ");
  return normalized.replace(/\s+/g, " ").trim();
}

function chooseBrowserVoice(language) {
  if (!("speechSynthesis" in window)) {
    return null;
  }
  const target = languageMap[language] || "en-GB";
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) {
    return null;
  }
  const targetPrefix = target.split("-")[0];
  const ranked = voices
    .map((voice) => {
      let score = 0;
      if (voice.lang === target) {
        score += 6;
      }
      if (voice.lang.startsWith(targetPrefix)) {
        score += 4;
      }
      if (/microsoft|google|natural|neural/i.test(voice.name)) {
        score += 2;
      }
      if (voice.default) {
        score += 1;
      }
      return { voice, score };
    })
    .sort((a, b) => b.score - a.score);
  return ranked[0]?.voice || null;
}

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      return null;
    }
    state.runtimeHealth = await response.json();
    if (state.runtimeHealth?.speech?.stt?.active_provider !== "mock" && state.runtimeHealth?.speech?.stt?.ready) {
      state.forceBrowserSttFallback = false;
    }
    if (Number.isFinite(state.runtimeHealth?.session_timeout_seconds) && state.runtimeHealth.session_timeout_seconds > 0) {
      state.sessionTimeoutMs = state.runtimeHealth.session_timeout_seconds * 1000;
    }
    updateInputModeUi();
    if (!state.recording && !state.submitting) {
      setReadyStatus();
    }
    return state.runtimeHealth;
  } catch {
    return null;
  }
}

async function transcribeAudio(blob, language, debugTranscript = null) {
  const form = new FormData();
  form.append("audio", blob, "recording.webm");
  form.append("language", language);
  if (debugTranscript) {
    form.append("debug_transcript", debugTranscript);
  }
  const response = await fetch("/api/speech/transcribe", {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error("transcription_failed");
  }
  return response.json();
}

async function answerQuery(transcript, language) {
  const response = await fetch("/api/query/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript, language, session_id: state.sessionId }),
  });
  if (!response.ok) {
    throw new Error("answer_generation_failed");
  }
  return response.json();
}

async function synthesizeAnswer(text, language) {
  const speechText = normalizeSpeechText(text, language);
  const response = await fetch("/api/speech/synthesize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: speechText, language }),
  });
  if (!response.ok) {
    return null;
  }
  return response.json();
}

function playAudio(url) {
  cancelCurrentSpeech();
  return new Promise((resolve) => {
    const audio = new Audio(url);
    state.currentAudio = audio;
    const finish = () => {
      if (state.currentAudio === audio) {
        state.currentAudio = null;
      }
      resolve();
    };
    audio.addEventListener("ended", finish, { once: true });
    audio.addEventListener("error", finish, { once: true });
    audio.play().catch(finish);
  });
}

function speakWithBrowser(text, language) {
  cancelCurrentSpeech();
  return new Promise((resolve) => {
    if (!("speechSynthesis" in window)) {
      resolve();
      return;
    }
    const utterance = new SpeechSynthesisUtterance(normalizeSpeechText(text, language));
    utterance.lang = languageMap[language] || "en-GB";
    utterance.rate = 0.98;
    utterance.pitch = 1.0;
    utterance.voice = chooseBrowserVoice(language);
    utterance.addEventListener("end", () => resolve(), { once: true });
    utterance.addEventListener("error", () => resolve(), { once: true });
    window.speechSynthesis.speak(utterance);
  });
}

async function speakAnswer(text) {
  const synthesis = await synthesizeAnswer(text, state.language);
  if (synthesis?.status === "ok" && synthesis.audio_url) {
    await playAudio(synthesis.audio_url);
    return;
  }
  if (synthesis?.status !== "ok") {
    setStatus("browserTtsFallback");
  }
  await speakWithBrowser(text, state.language);
}

function handleUiError(error) {
  console.error(error);
  hideAnswerState();
  clearMapPanel();
  showAnswer(error?.userMessage || getCopy().errors.generic);
  setStatus("error");
}

async function submitTranscript(transcript) {
  state.submitting = true;
  updateInputModeUi();
  setStatus("processing");

  try {
    const answer = await answerQuery(transcript, state.language);
    applySessionResponse(answer);
    showAnswerState(answer);
    showAnswer(answer.answer_text);
    renderMap(answer);
    setStatus(answer.status === "clarification_needed" ? "clarifying" : "speaking");
    await speakAnswer(answer.answer_text);
  } finally {
    state.submitting = false;
    state.recording = false;
    updateInputModeUi();
    if (state.statusKey !== "error") {
      setReadyStatus();
    }
  }
}

async function processAudio(blob) {
  setStatus("processing");
  const transcription = await transcribeAudio(blob, state.language);
  if (transcription.status !== "ok") {
    const detail = transcription.detail ? ` ${transcription.detail}` : "";
    if (canUseBrowserSpeechRecognition()) {
      state.forceBrowserSttFallback = true;
      clearMapPanel();
      showAnswer(`${getCopy().errors.backendSpeechFallback}${detail}`.trim());
      setStatus("browserFallback");
      return;
    }
    clearMapPanel();
    showAnswer(`${getCopy().errors.backendSpeechUnavailable}${detail}`.trim());
    setStatus("typedFallback");
    return;
  }

  const transcript = (transcription.transcript || "").trim();
  if (!transcript) {
    clearMapPanel();
    showAnswer(getCopy().errors.speechUnavailable);
    setStatus("error");
    return;
  }

  await submitTranscript(transcript);
}

async function ensureRecorder() {
  if (state.mediaRecorder) {
    return state.mediaRecorder;
  }
  const recorderSupport = getRecorderSupport();
  if (!recorderSupport.supported) {
    const error = new Error(recorderSupport.detail || "recorder_unavailable");
    error.userMessage = getCopy().errors.speechUnavailable;
    throw error;
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = recorderSupport.mimeType ? new MediaRecorder(stream, { mimeType: recorderSupport.mimeType }) : new MediaRecorder(stream);
  mediaRecorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) {
      state.chunks.push(event.data);
    }
  });
  mediaRecorder.addEventListener("stop", async () => {
    const blob = new Blob(state.chunks, { type: recorderSupport.mimeType || "audio/webm" });
    state.chunks = [];
    try {
      await processAudio(blob);
    } catch (error) {
      handleUiError(error);
      state.recording = false;
      updateInputModeUi();
    }
  });
  state.mediaRecorder = mediaRecorder;
  return mediaRecorder;
}

function createBrowserRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    return null;
  }
  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.addEventListener("result", async (event) => {
    try {
      const transcript = (event.results[0][0].transcript || "").trim();
      if (!transcript) {
        showAnswer(getCopy().errors.speechUnavailable);
        setStatus("error");
        return;
      }
      await submitTranscript(transcript);
    } catch (error) {
      handleUiError(error);
      state.recording = false;
      updateInputModeUi();
    }
  });

  recognition.addEventListener("error", () => {
    state.recording = false;
    updateInputModeUi();
    setStatus("typedFallback");
    focusManualQuestion();
  });

  recognition.addEventListener("end", () => {
    if (state.recording) {
      state.recording = false;
      updateInputModeUi();
      if (!state.submitting) {
        setReadyStatus();
      }
    }
  });

  return recognition;
}

async function handleRecordClick() {
  try {
    if (!state.runtimeHealth) {
      await loadHealth();
    }

    if (shouldUseTypedFallback()) {
      setStatus("typedFallback");
      focusManualQuestion();
      return;
    }

    if (shouldUseBrowserSpeechFallback()) {
      if (!state.browserRecognition) {
        state.browserRecognition = createBrowserRecognition();
      }
      if (!state.browserRecognition) {
        setStatus("typedFallback");
        focusManualQuestion();
        return;
      }

      if (!state.recording) {
        state.browserRecognition.lang = languageMap[state.language] || "en-GB";
        state.browserRecognition.start();
        state.recording = true;
        updateInputModeUi();
        setStatus("listening");
        return;
      }

      state.browserRecognition.stop();
      state.recording = false;
      updateInputModeUi();
      return;
    }

    const recorder = await ensureRecorder();
    if (!state.recording) {
      state.chunks = [];
      recorder.start();
      state.recording = true;
      updateInputModeUi();
      setStatus("listening");
      return;
    }

    recorder.stop();
    state.recording = false;
    updateInputModeUi();
  } catch (error) {
    state.recording = false;
    updateInputModeUi();
    handleUiError(error);
    focusManualQuestion();
  }
}

async function handleEndConversation() {
  if (!state.sessionId || state.submitting || state.recording) {
    return;
  }
  const currentSessionId = state.sessionId;
  try {
    const response = await fetch("/api/session/end", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId }),
    });
    if (!response.ok) {
      throw new Error("end_session_failed");
    }
    const body = await response.json();
    clearSessionState(sessionNoticeForEvent(body.session_event) || getCopy().session.ended);
  } catch (error) {
    handleUiError(error);
  }
}

function setLanguage(language) {
  if (!SUPPORTED_LANGUAGES.includes(language) || language === state.language) {
    return;
  }
  cancelCurrentSpeech();
  state.language = language;
  clearSessionState(getCopy().session.inactive);
  persistLanguage(language);
  showPlaceholder();
  renderCopy();
  setReadyStatus();
}

elements.recordButton.addEventListener("click", () => {
  void handleRecordClick();
});

elements.endConversationButton.addEventListener("click", () => {
  void handleEndConversation();
});

elements.manualQuestionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const transcript = elements.manualQuestionInput.value.trim();
  if (!transcript || state.submitting || state.recording) {
    return;
  }

  try {
    await submitTranscript(transcript);
    elements.manualQuestionInput.value = "";
  } catch (error) {
    handleUiError(error);
  }
});

for (const button of elements.languageButtons) {
  button.addEventListener("click", () => {
    setLanguage(button.dataset.lang);
  });
}

showPlaceholder();
renderCopy();
void loadHealth().then(() => {
  updateInputModeUi();
  if (!state.runtimeHealth) {
    setReadyStatus();
  }
});
