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
  screens: [...document.querySelectorAll("[data-screen]")],
  globalNav: document.getElementById("globalNav"),
  backButton: document.getElementById("backButton"),
  homeButton: document.getElementById("homeButton"),
  changeLanguageButton: document.getElementById("changeLanguageButton"),
  cancelRequestButton: document.getElementById("cancelRequestButton"),
  helpButton: document.getElementById("helpButton"),
  emergencyNavButton: document.getElementById("emergencyNavButton"),
  homeTitle: document.getElementById("homeTitle"),
  homeHint: document.getElementById("homeHint"),
  voiceTextModeButton: document.getElementById("voiceTextModeButton"),
  voiceTextModeLabel: document.getElementById("voiceTextModeLabel"),
  textModeButton: document.getElementById("textModeButton"),
  textModeLabel: document.getElementById("textModeLabel"),
  symbolModeButton: document.getElementById("symbolModeButton"),
  symbolModeLabel: document.getElementById("symbolModeLabel"),
  emergencyModeButton: document.getElementById("emergencyModeButton"),
  emergencyModeLabel: document.getElementById("emergencyModeLabel"),
  symbolTitle: document.getElementById("symbolTitle"),
  symbolHint: document.getElementById("symbolHint"),
  primarySymbolGrid: document.getElementById("primarySymbolGrid"),
  secondarySymbolGrid: document.getElementById("secondarySymbolGrid"),
  moreHelpDetails: document.getElementById("moreHelpDetails"),
  moreHelpSummary: document.getElementById("moreHelpSummary"),
  symbolSubstepTitle: document.getElementById("symbolSubstepTitle"),
  symbolSubstepHint: document.getElementById("symbolSubstepHint"),
  symbolSubstepGrid: document.getElementById("symbolSubstepGrid"),
  symbolResultsTitle: document.getElementById("symbolResultsTitle"),
  symbolResultsHint: document.getElementById("symbolResultsHint"),
  symbolAnswerText: document.getElementById("symbolAnswerText"),
  symbolNoMapReason: document.getElementById("symbolNoMapReason"),
  symbolResultList: document.getElementById("symbolResultList"),
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
    answerHint: "LENA antwortet mit geprüften Informationen aus Leipzig.",
    answerPlaceholder: "Die Antwort erscheint hier.",
    answerState: {
      clarification_needed: { label: "Kurze Rueckfrage", tone: "neutral" },
      weak_match: { label: "Aehnlicher Treffer", tone: "warning" },
      out_of_scope: { label: "Thema ausserhalb von LENA", tone: "warning" },
      self_description: { label: "Über LENA", tone: "neutral" },
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
      processing: "Ich suche passende Informationen",
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
    answerHint: "LENA answers with checked local information from Leipzig.",
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
      processing: "Looking for matching local information",
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
    answerHint: "LENA odpowiada na podstawie sprawdzonych informacji z Lipska.",
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
      processing: "Szukam pasujacych informacji",
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
    answerHint: "LENA raspunde cu informatii verificate din Leipzig.",
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
      processing: "Caut informatii potrivite",
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
    answerHint: "LENA otvechaet proverennoi informatsiei iz Leyptsiga.",
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
      processing: "Ishchu podkhodyashchuyu informatsiyu",
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
    hours: "Öffnungszeiten",
    noHours: "Keine klaren Öffnungszeiten vorhanden.",
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
    noHours: "No clear opening hours are available.",
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
    noHours: "Brak jasnych godzin otwarcia.",
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
    noHours: "Nu exista un program clar.",
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
    noHours: "Net ponyatnykh chasov raboty.",
    approx: "okolo",
  },
};

const screenTranslations = {
  de: {
    languageSubtitle: "Bitte zuerst Sprache wählen.",
    homeTitle: "Start",
    homeHint: "Wie möchten Sie Hilfe suchen?",
    voiceTextMode: "Sprechen",
    textMode: "Tippen",
    symbolMode: "Symbole",
    emergencyMode: "Notfall",
    back: "Zurück",
    home: "Start",
    language: "Sprache",
    cancel: "Abbrechen",
    help: "Hilfe",
    endSession: "Ende",
    emergency: "Notfall",
    cancelDone: "Anfrage abgebrochen.",
    helpText: "Wählen Sie ein Symbol, sprechen Sie eine kurze Frage oder tippen Sie wenige Wörter. Bei akuter Gefahr: Notfall.",
    symbolsTitle: "Symbole",
    symbolsHint: "Wählen Sie, was Sie brauchen.",
    moreHelp: "Weitere Hilfe",
    substepTitle: "Auswahl",
    substepHint: "Bitte eine Möglichkeit wählen.",
    selectedPrefix: "Sie suchen:",
    resultsTitle: "Ergebnis",
    resultsHint: "Kurze Hinweise und passende Orte.",
    noAddress: "Keine sichere Adresse vorhanden.",
    noHours: "Keine klaren Öffnungszeiten vorhanden.",
    phone: "Telefon",
    lastUpdated: "Stand",
  },
  en: {
    languageSubtitle: "Please choose a language first.",
    homeTitle: "Start",
    homeHint: "How would you like to look for help?",
    voiceTextMode: "Speak",
    textMode: "Type",
    symbolMode: "Symbols",
    emergencyMode: "Emergency",
    back: "Back",
    home: "Start",
    language: "Language",
    cancel: "Cancel",
    help: "Help",
    endSession: "End",
    emergency: "Emergency",
    cancelDone: "Request cancelled.",
    helpText: "Choose a symbol, say a short question, or type a few words. In immediate danger: Emergency.",
    symbolsTitle: "Symbols",
    symbolsHint: "Choose what you need.",
    moreHelp: "More help",
    substepTitle: "Choice",
    substepHint: "Please choose one option.",
    selectedPrefix: "You are looking for:",
    resultsTitle: "Result",
    resultsHint: "Short notes and matching places.",
    noAddress: "No safe address is available.",
    noHours: "No clear opening hours are available.",
    phone: "Phone",
    lastUpdated: "Updated",
  },
  pl: {
    languageSubtitle: "Najpierw wybierz język.",
    homeTitle: "Start",
    homeHint: "Jak chcesz szukać pomocy?",
    voiceTextMode: "Mów",
    textMode: "Pisz",
    symbolMode: "Symbole",
    emergencyMode: "Alarm",
    back: "Wstecz",
    home: "Start",
    language: "Język",
    cancel: "Anuluj",
    help: "Pomoc",
    endSession: "Koniec",
    emergency: "Alarm",
    cancelDone: "Zapytanie anulowane.",
    helpText: "Wybierz symbol, powiedz krótkie pytanie albo wpisz kilka słów. W bezpośrednim zagrożeniu: Alarm.",
    symbolsTitle: "Symbole",
    symbolsHint: "Wybierz, czego potrzebujesz.",
    moreHelp: "Więcej pomocy",
    substepTitle: "Wybór",
    substepHint: "Wybierz jedną możliwość.",
    selectedPrefix: "Szukasz:",
    resultsTitle: "Wynik",
    resultsHint: "Krótkie wskazówki i pasujące miejsca.",
    noAddress: "Brak bezpiecznego adresu.",
    noHours: "Brak jasnych godzin otwarcia.",
    phone: "Telefon",
    lastUpdated: "Aktualizacja",
  },
  ro: {
    languageSubtitle: "Alege mai întâi limba.",
    homeTitle: "Start",
    homeHint: "Cum vrei să cauți ajutor?",
    voiceTextMode: "Vorbește",
    textMode: "Scrie",
    symbolMode: "Simboluri",
    emergencyMode: "Urgență",
    back: "Înapoi",
    home: "Start",
    language: "Limba",
    cancel: "Anulează",
    help: "Ajutor",
    endSession: "Sfârșit",
    emergency: "Urgență",
    cancelDone: "Cerere anulată.",
    helpText: "Alege un simbol, spune o întrebare scurtă sau scrie câteva cuvinte. În pericol imediat: Urgență.",
    symbolsTitle: "Simboluri",
    symbolsHint: "Alege ce ai nevoie.",
    moreHelp: "Mai mult ajutor",
    substepTitle: "Alegere",
    substepHint: "Alege o opțiune.",
    selectedPrefix: "Cauți:",
    resultsTitle: "Rezultat",
    resultsHint: "Indicații scurte și locuri potrivite.",
    noAddress: "Nu există o adresă sigură.",
    noHours: "Nu există program clar.",
    phone: "Telefon",
    lastUpdated: "Actualizat",
  },
  ru: {
    languageSubtitle: "Сначала выберите язык.",
    homeTitle: "Старт",
    homeHint: "Как вы хотите искать помощь?",
    voiceTextMode: "Говорить",
    textMode: "Писать",
    symbolMode: "Символы",
    emergencyMode: "Срочно",
    back: "Назад",
    home: "Старт",
    language: "Язык",
    cancel: "Отмена",
    help: "Помощь",
    endSession: "Конец",
    emergency: "Срочно",
    cancelDone: "Запрос отменен.",
    helpText: "Выберите символ, скажите короткий вопрос или напишите несколько слов. При прямой опасности: Срочно.",
    symbolsTitle: "Символы",
    symbolsHint: "Выберите, что вам нужно.",
    moreHelp: "Еще помощь",
    substepTitle: "Выбор",
    substepHint: "Выберите один вариант.",
    selectedPrefix: "Вы ищете:",
    resultsTitle: "Результат",
    resultsHint: "Короткие подсказки и подходящие места.",
    noAddress: "Нет надежного адреса.",
    noHours: "Нет понятных часов работы.",
    phone: "Телефон",
    lastUpdated: "Обновлено",
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
  activeRequestController: null,
  recordingCancelled: false,
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
  screen: "language",
  screenHistory: [],
  symbolConfig: null,
  symbolConfigLanguage: null,
  selectedSymbolCategory: null,
  selectedSymbolSubstep: null,
  latestSymbolAnswer: null,
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

function getScreenCopy() {
  return screenTranslations[state.language] || screenTranslations.de;
}

function getMapConfig() {
  return state.runtimeHealth?.map || defaultMapConfig;
}

function showScreen(screenName, options = {}) {
  const previous = state.screen;
  const push = options.push !== false && previous && previous !== screenName;
  if (push) {
    state.screenHistory.push(previous);
  }
  state.screen = screenName;
  for (const screen of elements.screens) {
    screen.hidden = screen.dataset.screen !== screenName;
  }
  elements.globalNav.hidden = screenName === "language";
  elements.backButton.disabled = state.screenHistory.length === 0;
  if (!["voice", "symbol-results"].includes(screenName)) {
    clearMapPanel();
  } else if (state.currentMapData?.destinations?.length) {
    elements.mapPanel.hidden = false;
  }
  renderSessionState();
}

function goBack() {
  const previous = state.screenHistory.pop();
  if (!previous) {
    showScreen("home", { push: false });
    return;
  }
  showScreen(previous, { push: false });
}

function goHome() {
  state.screenHistory = [];
  state.selectedSymbolCategory = null;
  state.selectedSymbolSubstep = null;
  showPlaceholder();
  clearSymbolResults();
  showScreen("home", { push: false });
}

function returnToLanguageSelection() {
  cancelCurrentSpeech();
  state.screenHistory = [];
  clearSessionState(getCopy().session.inactive);
  showPlaceholder();
  clearSymbolResults();
  showScreen("language", { push: false });
}

function iconMarkup(icon) {
  const icons = {
    back: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M28 12 16 24l12 12M17 24h23"/></svg>',
    home: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="m8 24 16-14 16 14M13 22v18h22V22M20 40V28h8v12"/></svg>',
    language: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M8 12h18M17 8v4M14 12c2 7 7 12 14 15M24 12c-2 6-7 11-15 15M28 36l5-14 5 14M30 31h6M6 40h20M28 8h14v14"/></svg>',
    cancel: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M14 14 34 34M34 14 14 34"/></svg>',
    help: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M15 16a9 9 0 1 1 13 8c-4 2-5 4-5 8M24 39v1"/></svg>',
    end: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M20 8h-8v32h8M28 15l9 9-9 9M36 24H20"/></svg>',
    mic: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 8a6 6 0 0 0-6 6v10a6 6 0 0 0 12 0V14a6 6 0 0 0-6-6zM12 22a12 12 0 0 0 24 0M24 34v8M17 42h14"/></svg>',
    keyboard: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M8 13h32v22H8zM14 20h1M21 20h1M28 20h1M35 20h1M14 27h1M21 27h1M28 27h1M20 33h8"/></svg>',
    grid: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M10 10h11v11H10zM27 10h11v11H27zM10 27h11v11H10zM27 27h11v11H27z"/></svg>',
    bed: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M8 18v20M8 28h32M40 24v14M14 24h9M25 28v-8h9a6 6 0 0 1 6 6v2M12 38v4M38 38v4"/></svg>',
    food: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M14 7v15M20 7v15M10 7v12a7 7 0 0 0 14 0V7M17 25v16M34 7v34M30 7h8v17h-8z"/></svg>',
    water: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 6s12 14 12 24a12 12 0 0 1-24 0C12 20 24 6 24 6zM19 31a5 5 0 0 0 6 5"/></svg>',
    wash: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M10 21h28v10a10 10 0 0 1-10 10h-8a10 10 0 0 1-10-10V21zM15 16h18M19 10h10M14 21v-3M34 21v-3"/></svg>',
    toilet: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M13 7h18v17a9 9 0 0 1-9 9h-9V7zM31 16h5a4 4 0 0 1 4 4v3a10 10 0 0 1-10 10h-8M18 33v8M15 41h19M18 14h8"/></svg>',
    shower: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M15 17a9 9 0 0 1 18 0M13 19h22M24 25v2M17 27v2M31 27v2M20 34v2M28 34v2M12 42h24"/></svg>',
    medical: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M19 8h10v11h11v10H29v11H19V29H8V19h11z"/></svg>',
    alert: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 6 43 40H5L24 6zM24 17v12M24 35v1"/></svg>',
    clothes: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M18 8h12l9 8-6 7-4-3v21H19V20l-4 3-6-7 9-8zM20 8a4 4 0 0 0 8 0"/></svg>',
    addiction: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M15 33 33 15M18 10l20 20a7 7 0 0 1-10 10L8 20a7 7 0 0 1 10-10z"/></svg>',
    documents: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M14 6h15l7 7v29H14zM29 6v9h7M19 24h13M19 30h13M19 36h8"/></svg>',
    station: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M13 8h22a5 5 0 0 1 5 5v17a8 8 0 0 1-8 8H16a8 8 0 0 1-8-8V13a5 5 0 0 1 5-5zM14 16h20M15 38l-4 5M33 38l4 5M17 30h.1M31 30h.1"/></svg>',
    question: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M16 17a8 8 0 1 1 13 7c-4 2-5 4-5 8M24 39v1"/></svg>',
    person: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 23a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM11 42a13 13 0 0 1 26 0"/></svg>',
    child: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 21a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM14 42l4-14h12l4 14M18 31h12"/></svg>',
  };
  return icons[icon] || icons.question;
}

function buttonContent(icon, label) {
  return `<span class="button-icon" aria-hidden="true">${iconMarkup(icon)}</span><span class="button-label"></span>`;
}

function setIconButton(button, icon, label) {
  button.innerHTML = buttonContent(icon, label);
  button.querySelector(".button-label").textContent = label;
  button.setAttribute("aria-label", label);
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
  elements.endConversationButton.disabled = state.submitting || state.recording;
}

function scheduleSessionExpiry() {
  clearSessionTimer();
  if (!state.sessionId) {
    return;
  }
  state.sessionTimerId = window.setTimeout(() => {
    state.sessionId = null;
    state.sessionNotice = getCopy().session.expired;
    cancelCurrentSpeech();
    showPlaceholder();
    clearSymbolResults();
    elements.manualQuestionInput.value = "";
    showScreen("language", { push: false });
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
  elements.cancelRequestButton.disabled = !(state.submitting || state.recording || state.currentAudio);
  updateLanguageButtons();
}

function renderCopy() {
  const copy = getCopy();
  const mapCopy = getMapCopy();
  const screenCopy = getScreenCopy();
  document.documentElement.lang = state.language;
  document.title = copy.title;
  elements.brandEyebrow.textContent = copy.brandEyebrow;
  elements.appTitle.textContent = copy.title;
  elements.appSubtitle.textContent = screenCopy.languageSubtitle;
  elements.languageLabel.textContent = copy.languageLabel;
  elements.languageHint.textContent = copy.languageHint;
  elements.homeTitle.textContent = screenCopy.homeTitle;
  elements.homeHint.textContent = screenCopy.homeHint;
  elements.voiceTextModeLabel.textContent = screenCopy.voiceTextMode;
  elements.textModeLabel.textContent = screenCopy.textMode;
  elements.symbolModeLabel.textContent = screenCopy.symbolMode;
  elements.emergencyModeLabel.textContent = screenCopy.emergencyMode;
  setIconButton(elements.backButton, "back", screenCopy.back);
  setIconButton(elements.homeButton, "home", screenCopy.home);
  setIconButton(elements.changeLanguageButton, "language", screenCopy.language);
  setIconButton(elements.cancelRequestButton, "cancel", screenCopy.cancel);
  setIconButton(elements.helpButton, "help", screenCopy.help);
  setIconButton(elements.emergencyNavButton, "alert", screenCopy.emergency);
  setIconButton(elements.endConversationButton, "end", screenCopy.endSession);
  renderStaticIcons();
  elements.symbolTitle.textContent = screenCopy.symbolsTitle;
  elements.symbolHint.textContent = screenCopy.symbolsHint;
  elements.moreHelpSummary.textContent = screenCopy.moreHelp;
  elements.symbolSubstepTitle.textContent = screenCopy.substepTitle;
  elements.symbolSubstepHint.textContent = screenCopy.substepHint;
  elements.symbolResultsTitle.textContent = screenCopy.resultsTitle;
  elements.symbolResultsHint.textContent = screenCopy.resultsHint;
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
  if (state.symbolConfig) {
    renderSymbolCategories();
  }
  if (state.selectedSymbolCategory) {
    renderSymbolSubsteps(state.selectedSymbolCategory);
  }
  if (state.latestSymbolAnswer) {
    renderSymbolResults(state.latestSymbolAnswer);
  }
}

function renderStaticIcons() {
  for (const target of document.querySelectorAll("[data-icon]")) {
    target.innerHTML = iconMarkup(target.dataset.icon);
  }
}

async function loadSymbolConfig() {
  if (state.symbolConfig && state.symbolConfigLanguage === state.language) {
    return state.symbolConfig;
  }
  const response = await fetch(`/api/symbol/config?language=${encodeURIComponent(state.language)}`);
  if (!response.ok) {
    throw new Error("symbol_config_failed");
  }
  state.symbolConfig = await response.json();
  state.symbolConfigLanguage = state.language;
  renderSymbolCategories();
  return state.symbolConfig;
}

function renderSymbolCategories() {
  if (!state.symbolConfig?.categories) {
    return;
  }
  elements.primarySymbolGrid.replaceChildren();
  elements.secondarySymbolGrid.replaceChildren();
  for (const category of state.symbolConfig.categories) {
    if (category.id === "hygiene" && category.substeps?.length) {
      for (const substep of category.substeps) {
        const button = createSymbolTile(substep.label, substep.icon);
        button.addEventListener("click", () => {
          state.selectedSymbolCategory = category;
          state.selectedSymbolSubstep = substep;
          void submitSymbolAction(category.id, substep.id);
        });
        elements.primarySymbolGrid.append(button);
      }
      continue;
    }
    const button = createSymbolTile(category.label, category.icon, category.id === "emergency");
    button.addEventListener("click", () => handleSymbolCategory(category));
    if (category.group === "secondary") {
      elements.secondarySymbolGrid.append(button);
    } else {
      elements.primarySymbolGrid.append(button);
    }
  }
}

function createSymbolTile(label, icon, emergency = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `symbol-tile${emergency ? " symbol-tile--emergency" : ""}`;
  button.innerHTML = `<span class="symbol-tile__icon">${iconMarkup(icon)}</span><span class="symbol-tile__label"></span>`;
  button.querySelector(".symbol-tile__label").textContent = label;
  button.setAttribute("aria-label", label);
  return button;
}

function handleSymbolCategory(category) {
  state.selectedSymbolCategory = category;
  state.selectedSymbolSubstep = null;
  if (category.substeps?.length) {
    renderSymbolSubsteps(category);
    showScreen("symbol-substep");
    return;
  }
  void submitSymbolAction(category.id);
}

function renderSymbolSubsteps(category) {
  if (!category) {
    return;
  }
  state.selectedSymbolCategory = category;
  elements.symbolSubstepTitle.textContent = category.label;
  elements.symbolSubstepHint.textContent = `${getScreenCopy().selectedPrefix} ${category.label}`;
  elements.symbolSubstepGrid.replaceChildren();
  for (const substep of category.substeps || []) {
    const button = createSymbolTile(substep.label, substep.icon);
    button.addEventListener("click", () => {
      state.selectedSymbolSubstep = substep;
      void submitSymbolAction(category.id, substep.id);
    });
    elements.symbolSubstepGrid.append(button);
  }
}

function clearSymbolResults() {
  state.latestSymbolAnswer = null;
  elements.symbolAnswerText.textContent = "";
  elements.symbolNoMapReason.hidden = true;
  elements.symbolNoMapReason.textContent = "";
  elements.symbolResultList.replaceChildren();
}

function selectedSymbolLabel() {
  return state.selectedSymbolSubstep?.label || state.selectedSymbolCategory?.label || "";
}

function symbolLabelForAction(categoryId, substepId = null) {
  const category = state.symbolConfig?.categories?.find((item) => item.id === categoryId);
  if (category) {
    const substep = substepId ? category.substeps?.find((item) => item.id === substepId) : null;
    return substep?.label || category.label;
  }
  if (categoryId === "emergency") {
    return getScreenCopy().emergency;
  }
  return selectedSymbolLabel();
}

async function submitSymbolAction(categoryId, substepId = null) {
  const controller = startCancelableRequest();
  if (state.symbolConfig?.categories?.length) {
    state.selectedSymbolCategory = state.symbolConfig.categories.find((item) => item.id === categoryId) || state.selectedSymbolCategory;
    state.selectedSymbolSubstep =
      state.selectedSymbolCategory?.id === categoryId && substepId
        ? state.selectedSymbolCategory.substeps?.find((item) => item.id === substepId) || null
        : null;
  }
  cancelCurrentSpeech();
  clearMapPanel();
  clearSymbolResults();
  state.submitting = true;
  updateInputModeUi();
  setStatus("processing");
  try {
    const response = await fetch("/api/symbol/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        category_id: categoryId,
        substep_id: substepId,
        language: state.language,
        session_id: state.sessionId,
      }),
    });
    if (!response.ok) {
      throw new Error("symbol_answer_failed");
    }
    const answer = await response.json();
    applySessionResponse(answer);
    renderSymbolResults(answer);
    renderMap(answer);
    showScreen("symbol-results");
    setStatus(answer.status === "crisis" ? "idle" : "speaking");
    await speakAnswer(answer.answer_text, controller.signal);
  } catch (error) {
    if (!isAbortError(error)) {
      handleUiError(error);
      showScreen("voice");
    }
  } finally {
    finishCancelableRequest(controller);
    state.submitting = false;
    updateInputModeUi();
    if (state.statusKey !== "error") {
      setReadyStatus();
    }
  }
}

function renderSymbolResults(answer) {
  state.latestSymbolAnswer = answer;
  const screenCopy = getScreenCopy();
  const label = symbolLabelForAction(answer?.category_id, answer?.substep_id);
  elements.symbolResultsHint.textContent = label ? `${screenCopy.selectedPrefix} ${label}` : screenCopy.resultsHint;
  elements.symbolAnswerText.textContent = answer?.answer_text || "";
  if (answer?.no_map_reason) {
    elements.symbolNoMapReason.hidden = false;
    elements.symbolNoMapReason.textContent = answer.no_map_reason;
  } else {
    elements.symbolNoMapReason.hidden = true;
    elements.symbolNoMapReason.textContent = "";
  }
  elements.symbolResultList.replaceChildren();
  for (const card of answer?.cards || []) {
    const article = document.createElement("article");
    article.className = "symbol-result-card";
    article.setAttribute("role", "listitem");

    const title = document.createElement("h3");
    title.className = "symbol-result-card__title";
    title.textContent = card.title;
    article.append(title);

    const address = document.createElement("p");
    address.className = "symbol-result-card__line";
    address.textContent = card.address || screenCopy.noAddress;
    article.append(address);

    if (card.opening_hours?.length) {
      const hours = document.createElement("ul");
      hours.className = "symbol-result-card__hours";
      for (const line of card.opening_hours) {
        const item = document.createElement("li");
        item.textContent = line;
        hours.append(item);
      }
      article.append(hours);
    } else {
      const noHours = document.createElement("p");
      noHours.className = "symbol-result-card__line symbol-result-card__muted";
      noHours.textContent = screenCopy.noHours;
      article.append(noHours);
    }

    if (card.phone) {
      const phone = document.createElement("p");
      phone.className = "symbol-result-card__line";
      phone.textContent = `${screenCopy.phone}: ${card.phone}`;
      article.append(phone);
    }

    if (card.description) {
      const description = document.createElement("p");
      description.className = "symbol-result-card__line";
      description.textContent = card.description;
      article.append(description);
    }

    const action = document.createElement("p");
    action.className = "symbol-result-card__action";
    action.textContent = card.action;
    article.append(action);

    if (card.last_updated) {
      const updated = document.createElement("p");
      updated.className = "symbol-result-card__updated";
      updated.textContent = `${screenCopy.lastUpdated}: ${card.last_updated}`;
      article.append(updated);
    }

    if (card.has_map_location) {
      article.tabIndex = 0;
      article.addEventListener("click", () => selectMapDestination(card.page_id));
      article.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectMapDestination(card.page_id);
        }
      });
    }

    elements.symbolResultList.append(article);
  }
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

function isAbortError(error) {
  return error?.name === "AbortError" || error?.message === "request_cancelled";
}

function startCancelableRequest() {
  if (state.activeRequestController) {
    state.activeRequestController.abort();
  }
  state.activeRequestController = new AbortController();
  return state.activeRequestController;
}

function finishCancelableRequest(controller) {
  if (state.activeRequestController === controller) {
    state.activeRequestController = null;
  }
}

function cancelRecording() {
  const recorderActive = state.mediaRecorder && state.mediaRecorder.state !== "inactive";
  state.recordingCancelled = Boolean(recorderActive);
  if (state.browserRecognition) {
    try {
      state.browserRecognition.stop();
    } catch {}
  }
  if (recorderActive) {
    try {
      state.mediaRecorder.stop();
    } catch {}
  } else {
    state.recordingCancelled = false;
  }
  state.chunks = [];
  state.recording = false;
}

function cancelCurrentRequest() {
  if (state.activeRequestController) {
    state.activeRequestController.abort();
    state.activeRequestController = null;
  }
  cancelRecording();
  cancelCurrentSpeech();
  state.submitting = false;
  updateInputModeUi();
  setStatus("idle");
  showPlaceholder();
  clearSymbolResults();
  goHome();
  setStatusMessage(getScreenCopy().cancelDone);
}

function setStatusMessage(message) {
  state.statusKey = "";
  elements.statusText.textContent = message;
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
    [/Str\./g, language === "de" ? "Straße" : "Street"],
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

async function transcribeAudio(blob, language, debugTranscript = null, signal = undefined) {
  const form = new FormData();
  form.append("audio", blob, "recording.webm");
  form.append("language", language);
  if (debugTranscript) {
    form.append("debug_transcript", debugTranscript);
  }
  const response = await fetch("/api/speech/transcribe", {
    method: "POST",
    body: form,
    signal,
  });
  if (!response.ok) {
    throw new Error("transcription_failed");
  }
  return response.json();
}

async function answerQuery(transcript, language, signal = undefined) {
  const response = await fetch("/api/query/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript, language, session_id: state.sessionId }),
    signal,
  });
  if (!response.ok) {
    throw new Error("answer_generation_failed");
  }
  return response.json();
}

async function synthesizeAnswer(text, language, signal = undefined) {
  const speechText = normalizeSpeechText(text, language);
  const response = await fetch("/api/speech/synthesize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: speechText, language }),
    signal,
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
    updateInputModeUi();
    const finish = () => {
      if (state.currentAudio === audio) {
        state.currentAudio = null;
      }
      updateInputModeUi();
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

async function speakAnswer(text, signal = undefined) {
  const synthesis = await synthesizeAnswer(text, state.language, signal);
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
  const controller = startCancelableRequest();
  state.submitting = true;
  updateInputModeUi();
  setStatus("processing");

  try {
    const answer = await answerQuery(transcript, state.language, controller.signal);
    applySessionResponse(answer);
    showAnswerState(answer);
    showAnswer(answer.answer_text);
    renderMap(answer);
    setStatus(answer.status === "clarification_needed" ? "clarifying" : "speaking");
    await speakAnswer(answer.answer_text, controller.signal);
  } catch (error) {
    if (!isAbortError(error)) {
      throw error;
    }
  } finally {
    finishCancelableRequest(controller);
    state.submitting = false;
    state.recording = false;
    updateInputModeUi();
    if (state.statusKey !== "error") {
      setReadyStatus();
    }
  }
}

async function processAudio(blob) {
  const controller = startCancelableRequest();
  setStatus("processing");
  try {
    const transcription = await transcribeAudio(blob, state.language, null, controller.signal);
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

    finishCancelableRequest(controller);
    await submitTranscript(transcript);
  } catch (error) {
    if (!isAbortError(error)) {
      throw error;
    }
  } finally {
    finishCancelableRequest(controller);
  }
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
    if (state.recordingCancelled) {
      state.recordingCancelled = false;
      state.chunks = [];
      return;
    }
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
  if (state.submitting || state.recording) {
    return;
  }
  if (!state.sessionId) {
    returnToLanguageSelection();
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
    elements.manualQuestionInput.value = "";
    showPlaceholder();
    clearSymbolResults();
    showScreen("language", { push: false });
  } catch (error) {
    handleUiError(error);
  }
}

function setLanguage(language) {
  if (!SUPPORTED_LANGUAGES.includes(language)) {
    return;
  }
  cancelCurrentSpeech();
  const changed = language !== state.language;
  state.language = language;
  clearSessionState(getCopy().session.inactive);
  persistLanguage(language);
  if (changed) {
    state.symbolConfig = null;
    state.symbolConfigLanguage = null;
  }
  state.screenHistory = [];
  elements.manualQuestionInput.value = "";
  showPlaceholder();
  clearSymbolResults();
  renderCopy();
  setReadyStatus();
  showScreen("home", { push: false });
}

async function openSymbolMode() {
  try {
    await loadSymbolConfig();
    clearSymbolResults();
    showScreen("symbols");
  } catch (error) {
    handleUiError(error);
    showScreen("voice");
  }
}

function openVoiceMode(options = {}) {
  clearSymbolResults();
  clearMapPanel();
  showScreen("voice");
  if (options.focusText) {
    focusManualQuestion();
  }
}

function showHelp() {
  cancelCurrentSpeech();
  clearMapPanel();
  hideAnswerState();
  showAnswer(getScreenCopy().helpText);
  showScreen("voice");
  setReadyStatus();
}

elements.backButton.addEventListener("click", () => {
  goBack();
});

elements.homeButton.addEventListener("click", () => {
  goHome();
});

elements.changeLanguageButton.addEventListener("click", () => {
  returnToLanguageSelection();
});

elements.cancelRequestButton.addEventListener("click", () => {
  cancelCurrentRequest();
});

elements.helpButton.addEventListener("click", () => {
  showHelp();
});

elements.emergencyNavButton.addEventListener("click", () => {
  void submitSymbolAction("emergency");
});

elements.voiceTextModeButton.addEventListener("click", () => {
  openVoiceMode();
});

elements.textModeButton.addEventListener("click", () => {
  openVoiceMode({ focusText: true });
});

elements.symbolModeButton.addEventListener("click", () => {
  void openSymbolMode();
});

elements.emergencyModeButton.addEventListener("click", () => {
  void submitSymbolAction("emergency");
});

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
showScreen("language", { push: false });
void loadHealth().then(() => {
  updateInputModeUi();
  if (!state.runtimeHealth) {
    setReadyStatus();
  }
});
