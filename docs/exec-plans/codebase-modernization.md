# Execution Plan: Modernisierung der LENA-Codebasis

## Status

- State: In progress
- Owner: Codex
- Created: 2026-07-15
- Last updated: 2026-07-17
- Review source: `docs/architecture/codebase-review.md`

## Ziel

LENA soll schrittweise auf einen sicheren, nachvollziehbaren und wartbaren
Entwicklungsstand gebracht werden, ohne die bewährte WFS-Grounding-Architektur
oder das deterministische Fallbackverhalten in einem Big-Bang-Refactoring zu
gefährden. Jedes Arbeitspaket ist separat reviewbar und soll möglichst einem
eigenen Pull Request entsprechen.

## Akzeptanzkriterien

- [ ] P0-Sicherheitsbefunde besitzen fachlich/technisch freigegebene Lösungen
      und Regressionstests.
- [x] `Code3/` besitzt eine kanonische Git-Historie und CI-fähige Baseline.
- [ ] Nutzer-, WFS- und Übersetzungsdaten werden atomar, begrenzt und
      nachvollziehbar verarbeitet.
- [ ] Fallbacks sind redigiert beobachtbar, ohne Secrets oder Nutzerdaten zu
      protokollieren.
- [x] Ein gebautes Artefakt enthält alle benötigten statischen Ressourcen und
      hat eine definierte Datenstrategie.
- [ ] Handgeschriebene Dateien bleiben möglichst unter 400 Zeilen oder enthalten
      eine dokumentierte Kohäsionsbegründung.
- [ ] Fachlogik ist unabhängig von HTTP, Dateisystem und externen Providern
      gezielt testbar.
- [ ] Frontend-Backend-Verträge, Accessibility und Hauptabläufe sind
      automatisiert abgesichert.
- [ ] Konfiguration, Betrieb und Architektur entsprechen dem implementierten
      Stand.
- [ ] Bestehendes geerdetes Antwort-, Karten-, Session-, Speech- und
      WFS-Verhalten bleibt erhalten, sofern ein Paket es nicht ausdrücklich und
      fachlich freigegeben ändert.

## Scope

### In Scope

- Sicherheitsgrenzen für Browser, Akutgefahr und Speech-Requests
- Versionskontrolle und reproduzierbare Quality-Gates
- Logging, Fehler- und Health-Verträge
- Session- und WFS-Persistenz
- Packaging, Versionsführung und Pfadauflösung
- schrittweise Backend- und Frontend-Modularisierung
- Typisierung, Tests, Accessibility und technische Dokumentation
- Klärung oder Entfernung bestätigter wirkungsloser Zustände

### Out of Scope

- vollständiger Rewrite oder Frameworkwechsel
- Einführung von Microservices
- Vektor-RAG ohne belegten fachlichen Bedarf
- Datenbankserver nur als Architekturkosmetik
- neue Fachangebote außerhalb der autoritativen Quelle
- Änderung von WFS-Fakten ohne Reviewprozess
- neue Endnutzerfunktionen, solange P0/P1-Grundlagen offen sind
- gleichzeitige Umbenennung und Verschiebung großer Modulbereiche
- Bearbeitung von `app/static/vendor/` außer gezieltem Vendor-Upgrade

## Betroffene Bereiche

| Bereich | Hauptpfade | Rolle im Zielbild |
|---|---|---|
| API/Komposition | `app/main.py`, `app/__main__.py` | dünne Adapter und Verdrahtung |
| Query/Fachlogik | `app/service.py`, `app/retrieval.py`, `app/temporal.py`, `app/offer_roles.py` | providerunabhängige Regeln |
| Modelle | `app/models.py` | stabile Verträge |
| Provider | `app/providers/llm.py`, `app/speech.py` | externe I/O-Adapter |
| Persistenz | `app/sessions.py`, `app/i18n.py`, `app/kb_loader.py`, `app/wfs_sync.py` | atomare Stores/Releasezugriff |
| Wartungs-CLI | `app/translate_offers.py`, `app/wfs_sync.py` | explizite Reviewprozesse |
| Frontend | `app/static/index.html`, `app/static/app.js`, `app/static/styles.css` | sichere, modulare UI |
| Build | `pyproject.toml`, künftige CI-Dateien | reproduzierbares Artefakt |
| Tests | `tests/` | Fach-, Adapter-, API- und Browsernachweise |
| Dokumentation | `README.md`, `docs/` | aktueller Betriebs- und Architekturvertrag |

## Abhängigkeiten und notwendige Vorarbeiten

1. Kanonisches Git-Ziel und Baseline müssen festgelegt werden.
2. Fachverantwortliche müssen den Akutgefahr-Pfad und Übersetzungen freigeben.
3. Betriebsziel muss geklärt werden: lokaler Einzelprozess oder öffentlicher
   Mehrnutzerbetrieb.
4. Datenschutzvorgaben für Sessions und externe Provider müssen vorliegen.
5. Datenstrategie des Distributionsartefakts muss entschieden werden.
6. Erst Characterization-Tests, dann strukturelle Extraktionen.

## Repository Review

### Current Behavior

Eine FastAPI-App liefert ein statisches Frontend. `QueryService` orchestriert
Sessions, deterministisches Retrieval, Zeit-/Schlafregeln, optionale zweistufige
Blablador-Nutzung, Übersetzung, Karten und Fallbacks. Nutzeranfragen lesen nur
`data/canonical/offers.json`; WFS-Sync läuft separat oder im Hintergrund.

### Relevant Architecture and Data Flow

- Start: `app.__main__` -> Uvicorn -> `app.main:create_app`.
- Query: Browser -> `/api/query` -> `QueryService` -> Retrieval/LLM -> Karten ->
  Session -> Browser.
- WFS: Live-Quelle -> Validierung -> Pending oder sequenzielle Promotion.
- Translation: explizite CLI -> Translation-Store; laufender Dienst lädt nicht
  automatisch neu.
- Speech: Browser -> FastAPI -> OpenAI-kompatibler Dienst oder Edge-TTS.

### Existing Structures to Reuse

| Struktur | Pfad | Reuse-Entscheidung |
|---|---|---|
| App-Factory | `app/main.py:create_app` | erhalten und verschlanken |
| Vertragsmodelle | `app/models.py` | erweitern statt duplizieren |
| deterministisches Retrieval | `app/retrieval.py` | erhalten und isoliert testen |
| Zeitregeln | `app/temporal.py` | als Fachpolicy erhalten |
| Rollenklassifikation | `app/offer_roles.py` | erhalten |
| Grounding-Validator | `app/providers/llm.py` | extrahieren, nicht neu erfinden |
| WFS-Validierung/Hashes | `app/wfs_sync.py` | Grundlage des Releasevertrags |
| Translation-Hash/Overrides | `app/i18n.py` | erhalten |
| Fehlerklassen | mehrere Module | vereinheitlichen, Semantik bewahren |
| lokale WFS-Fixture | `tests/fixtures/` | für Adaptertests wiederverwenden |
| deutsche Docs | `README.md`, `docs/` | bestehende Struktur fortsetzen |

### Existing Tests and Commands

- `python -m pytest` — aktuell 81 bestandene Tests.
- `python -m compileall -q app` — Syntax-Smoke.
- `python -m pip wheel . --no-deps` — Build möglich, Artefakt unvollständig.
- Relevante Tests: `tests/test_api.py`, `tests/test_kb_loader.py`,
  `tests/test_retrieval.py`, `tests/test_sessions.py`, `tests/test_wfs_sync.py`.

### Working Tree Considerations

Zum Zeitpunkt des ursprünglichen Reviews war `Code3/` kein Git-Repository;
Nutzeränderungen, Branches und Diffs waren dort nicht unterscheidbar. Paket 1
hat diesen Stand inzwischen auf einem neuen Branch des bestehenden
LENA-Repositories versioniert. `.env` und `.env.local` wurden nicht gelesen.
`runtime/`, `.pytest_cache/`, `__pycache__/` und lokale Secrets sind generiert;
`app/static/vendor/` ist Drittanbieter-Code. Aktivierte Dateien unter `data/`
dürfen nur über definierte Wartungsprozesse verändert werden.

## Dead-End-Risiken

| Potenzieller Dead End | Evidenz | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Sicherheitsfix in falschem Projektstand | benachbarte Repositories, `Code3/` ohne Git | Fix geht im falschen Stand verloren | zuerst kanonische Baseline | Remote/Branch und Diff prüfen |
| Big-Bang-Aufteilung von `service.py`/`app.js` | breite Pfade, unvollständige Browsertests | schwer reviewbare Regressionen | Characterization-Tests und kleine Extraktionen | Diff- und E2E-Nachweis je PR |
| HTML nur „escapen“ an einer Stelle | mehrere Popupwerte | verbleibende Injektion | DOM-API statt HTML-Strings | Payload-basierter DOM-Test |
| Krisentext ohne Fachfreigabe | hochsensibler Einsatz | falsche/gefährliche Empfehlung | fachliche Entscheidung als Gate | mehrsprachiger Acceptance-Test |
| Pending-Payload trotz Hashabweichung promoten | Quelle kann sich ändern | ungeprüfte Daten | Hash als Freigabeparameter | Check/Promote-Race-Test |
| nur Einzeldatei-Atomizität behalten | mehrere Artefakte bilden Release | Mischstand | Release-Manifest + atomarer Zeiger | Fault-Injection/Recovery |
| SQLite vorschnell einführen | Betriebsziel unbekannt | unnötige Migration | zunächst atomarer Single-Process-Store | Last-/Parallelitätsziel prüfen |
| Packaging durch bloßes `package-data` lösen | Daten liegen außerhalb `app/` | weiter unklarer Daten-Lifecycle | Datenstrategie vor Konfiguration | Clean-Wheel-Smoke |
| Fallbacks für grüne Tests verschlucken | bestehendes Muster | Produktionsfehler unsichtbar | Logs + expliziter degraded status | `caplog` und Health-Test |
| neue Abstraktionsschicht ohne zweiten Use Case | kleines Projekt | Navigation wird schlechter | nur reale I/O-Grenzen abstrahieren | Plan-/Diff-Review |

## Empfohlener Ansatz

Die Modernisierung erfolgt risikoorientiert: zuerst Sicherheits- und
Reproduzierbarkeitsgrundlage, danach beobachtbare und atomare Betriebswege,
anschließend Packaging und strukturelle Teilung. Vor jeder Extraktion wird der
Istpfad durch Tests charakterisiert. Neue Protokolle werden nur an Provider- und
Storage-Grenzen eingeführt; reine Fachfunktionen bleiben einfache Funktionen.

## Alternatives Rejected

| Alternative | Grund der Ablehnung |
|---|---|
| kompletter Rewrite | verliert geprüfte Grounding-/Fallbacklogik |
| Microservices | keine Last- oder Teamgrenze rechtfertigt Betriebsaufwand |
| sofortiges React/Vue-Frontend | löst Sicherheit/Testbarkeit nicht automatisch und fügt Toolchain hinzu |
| generisches Repository-/DI-Framework | für Projektgröße ohne konkreten Nutzen |
| Vektor-RAG als Modernisierung | Datenbestand klein; ID-Routing ist besser prüfbar |
| sofortige Mehrprozess-Datenbank | Betriebsziel und Retention ungeklärt |
| flächige Formatierung zuerst | ohne Git-Diff nicht sicher reviewbar |

## Priorisierte Refactoring-Pakete

### Paket 0A (P0): Popup-XSS schließen

**Ziel:** Alle extern oder wartbar gespeisten Popupwerte werden ohne HTML-
Interpretation gerendert.

- Status: Completed (2026-07-15).
- Erwartete Dateien: `app/static/app.js`,
  `tests/test_frontend_security.py`, dieser ExecPlan und vorhandene
  Sicherheits-/Architekturdokumentation, soweit `code-documentation` dies nach
  der Implementierung erfordert.
- Tests: bösartige Labels/Adressen; normale Popupstruktur; optionale/leere
  Adressen; kein `innerHTML` oder dynamischer HTML-String für Popupwerte.
- Nutzen: sehr hoch. Aufwand: klein. Änderungsrisiko: niedrig.
- Regressionen: Popupformatierung und Leaflet-Interaktion.
- Abbruchkriterium: Wenn Leaflet keinen DOM-Node akzeptiert, wird vor einem
  alternativen Escaper dessen Vollständigkeit nachgewiesen.

#### Paket-0A-Review vor Implementierung

**Bestätigter Pfad:** `app/static/app.js:renderMap()` erzeugt genau zwei
Leaflet-Popups. Der Origin-Marker bindet aktuell in Zeile 546 und jeder
Destination-Marker in Zeile 559 einen dynamischen Template-String an
`bindPopup()`. `label` und `address` werden dadurch als HTML interpretiert.

**Datenquellen:**

- `MapOrigin.label` und `MapOrigin.address` stammen aktuell aus der lokalen
  Konstante `LEIPZIG_HBF` in `app/maps.py`, sind aber Teil des dynamischen API-
  Vertrags.
- `MapDestination.address` stammt aus `OfferRecord.address`, normalisiert aus
  WFS `properties["adr"]` in `app/wfs_sync.py`, oder aus lokal definierten
  Standorten in `app/maps.py`.
- `MapDestination.label` stammt zunächst aus WFS-/KB-`OfferRecord.name` oder
  lokalen Standorten. `QueryService.query()` überschreibt es bei passenden
  Karten mit `OfferCard.name`; dieser Wert kann aus
  `data/i18n/offer_translations.json` und
  `data/i18n/manual_overrides.json` kommen.
- Beschreibung, Telefonnummern und Öffnungszeiten werden im Backend an
  `MapDestination` angehängt, aktuell aber nicht im Popup gerendert. Sie bleiben
  dennoch dynamische Daten und dürfen bei späterer Erweiterung nur als Text oder
  über protokollgeprüfte DOM-Links ergänzt werden.

**Bestehende sichere Strukturen:** `renderCards()`, `addField()`,
`renderHistory()` und die Kartenliste in `renderMap()` erzeugen DOM-Knoten und
setzen dynamische Werte über `textContent`. Dieses Muster wird wiederverwendet.
Ein enger Helper `buildMapPopup(label, address)` ist gerechtfertigt, weil beide
produktiven Popup-Pfade dieselbe Struktur benötigen. Er erzeugt ausschließlich
`div`, `strong`, optional `br` und einen Textknoten; Leaflet erhält den DOM-Knoten
direkt.

**Akzeptanzkriterien:**

- [x] Beide produktiven `bindPopup()`-Aufrufe erhalten DOM-Knoten, keine Strings.
- [x] Label und Adresse gelangen nur über `textContent`/`createTextNode()` in den
      Popup-Knoten.
- [x] Leere oder fehlende Adressen erzeugen weder `undefined`/`null` noch einen
      unnötigen Zeilenumbruch.
- [x] Payloads mit `img`, `script`, `svg` und Event-Handlern bleiben Text und
      erzeugen keine entsprechenden DOM-Elemente/Attribute.
- [x] Kartenliste, Marker, Bounds, Mehrsprachigkeit und normale Popupstruktur
      bleiben erhalten.
- [x] Es verbleibt kein dynamischer HTML-String in einem Popup-Pfad.
- [x] Das vorhandene statische `categoryIcons`-`innerHTML` wird als außerhalb
      des Popup-Pfads bewertet und in diesem Paket nicht refaktoriert.

**Teststrategie:** Das Repository besitzt kein Node/npm, keine JavaScript-
Testumgebung und keinen installierten Browser-DOM-Harness. Ohne neue Abhängigkeit
ist daher kein automatischer ausführender DOM-Test möglich. Ein fokussierter
Pytest-Regressionstest liest den tatsächlich ausgelieferten `app/static/app.js`
und erzwingt die produktive Verdrahtung: DOM-Helper mit Text-APIs, beide
`bindPopup(buildMapPopup(...))`-Pfade, keine Popup-Template-Strings und keine
dynamischen HTML-Sinks im Helper. Dieser Test würde vor der Änderung fehlschlagen.
Er wird durch einen manuellen Browser-Test mit XSS-Payloads und normalen/leeren
Werten ergänzt. Das verbleibende Restrisiko ist, dass der statische Test keine
reale Browser-DOM-Ausführung simuliert; Paket 10 sieht Browser-E2E vor.

**Dead Ends und Mitigation:**

| Dead End | Auswirkung | Mitigation | Verifikation |
|---|---|---|---|
| nur Destination oder Origin absichern | alternativer XSS-Pfad bleibt | gemeinsamer Helper für beide Aufrufe | Referenzsuche nach allen `bindPopup` |
| manuelles Escaping | unvollständige HTML-/Attributbehandlung | DOM-Knoten und Text-APIs | Test verbietet Popup-HTML-Strings |
| Kartenliste übersehen | alternative unsichere Darstellung | bestehenden `textContent`-Pfad bestätigen | Sink-Suche und Test |
| sichere Erstellung später serialisieren | DOM-Sicherheit geht verloren | DOM-Knoten direkt an Leaflet binden | Verdrahtungsassertion |
| unsichere Links ergänzen | Protokoll-/Tabnabbing-Risiko | keine Links hinzufügen; spätere Links nur allowlisted per DOM | Link-/Popup-Suche |
| Frontend parallel modularisieren | großer, schwer reviewbarer Security-Diff | nur enger Helper in `app.js` | Scope-Review |

**Rückfallrisiken:** Abweichende Popupformatierung, fehlender Zeilenumbruch,
Anzeige von `undefined`/`null`, versehentlich nur ein abgesicherter Markerpfad
oder spätere Erweiterung um ungeprüfte Links/Felder.

**Rollback:** Die Änderung besteht aus einem lokalen Helper, zwei ersetzten
`bindPopup()`-Argumenten und einem fokussierten Test. Eine Rücknahme erfolgt als
expliziter Patch dieser Stellen; das unsichere HTML-String-Muster darf nicht als
Rollbackziel wiederhergestellt werden. Bei Leaflet-Inkompatibilität wird der
DOM-Node-Ansatz anhand der vendored Leaflet-Version geprüft, bevor eine andere
Lösung erwogen wird.

**Geplante Verifikation:**

- `python -m pytest tests/test_frontend_security.py`
- `python -m pytest`
- `python -m compileall -q app`
- Suche nach `innerHTML`, `insertAdjacentHTML`, `outerHTML`, `bindPopup`,
  `setPopupContent`, Popup-Template-Strings und dynamischen Links
- statischer JavaScript-Syntaxcheck, falls ein lokales Werkzeug verfügbar ist
- manueller Browser-/DOM-Test mit normalen, fehlenden und bösartigen Werten

### Paket 0B (P0): LLM-basierter Akutgefahr-Hinweis

**Ziel:** Die bestehende routende LLM-Stufe erkennt ein einfaches boolesches
Akutgefahr-Signal. Die Anwendung validiert dieses Signal und ersetzt bei `true`
den gesamten normalen Antwortpfad durch einen fest hinterlegten, lokalisierten
Hinweis auf 112. Es entstehen weder Risikostufen noch eine zweite
Klassifikationspipeline.

- Status: Completed (2026-07-17).
- Nutzen: sehr hoch. Aufwand: klein–mittel. Änderungsrisiko: mittel.
- Scope: LLM-Routervertrag und -prompt, unmittelbare Auswertung im
  `QueryService`, kontrollierte Texte, TTS-Normalisierung, gezielte Tests und
  bestehende Dokumentation.
- Nicht im Scope: Keyword-Klassifikation, Risikoscoring, Diagnose, dauerhafter
  Session-Risikozustand, externe Safety-Dienste oder allgemeine
  `QueryService`-/Provider-Modularisierung.

#### Paket-0B-Review vor Implementierung

**Aktueller produktiver LLM-Pfad:** `POST /api/query` ruft
`QueryService.query()` und danach `_query_core()` auf. Wenn Blablador
konfiguriert ist und der Angebotsindex in das Kontextlimit passt, ruft
`_query_core()` zuerst `BlabladorProvider.route()` auf. Diese Stufe sendet Frage,
Konversationskontext, Kategoriehinweis und `OFFER_INDEX` an den vorhandenen
JSON-Modus und validiert die Antwort mit `LLMRoute`. Nur bei einer normalen,
gültigen Route folgt `BlabladorProvider.answer()`; andernfalls greift das
vorhandene deterministische Retrieval-/Template-Fallback.

**Bisheriger Sicherheitsmechanismus:** `app/service.py` prüft vor dem LLM eine
kleine feste Menge `DANGER_PATTERNS` und gibt `DANGER_BOUNDARY` ohne Notrufnummer
aus. Der Mechanismus deckt nur exakte Teilstrings ab, ist nicht LLM-basiert und
würde eine Gefahr vor dem neuen strukturierten Vertrag abfangen. Er wird nicht
erweitert oder parallel weitergeführt. Die wirkungslosen Zustände `kb_error`
und `pending_clarification` werden nicht als Safety-Zustand wiederverwendet.

**Vorgesehener Eingriffspunkt und Vertrag:** `LLMRoute` erhält das verpflichtende
strikte boolesche Feld `acute_risk_detected`. `BlabladorProvider.route()` gibt
es in `ProviderRoute` weiter. Direkt nach dem erfolgreichen `route()`-Aufruf und
vor `out_of_scope`, Klärung, Angebotsauswahl, Retrieval und Formulator prüft
`QueryService._query_core()` dieses Feld. Bei `true` liefert der Service eine
reine Template-Antwort ohne Karten; `answer()` wird nicht aufgerufen. Damit kann
die zweite LLM-Stufe das Signal oder den Sicherheitstext nicht überschreiben.

Das Feld fehlt absichtlich ohne Default im externen Pydantic-Vertrag. Fehlende
oder nicht-boolesche Werte machen die Routerantwort ungültig und nutzen das
bestehende `ProviderError`-/Template-Fallback; die Anwendung erfindet dabei kein
Risiko. Der Provider protokolliert nur ein strukturiertes Fehlerereignis mit
Fehlerklasse, niemals den vollständigen Fragetext. `ProviderRoute` behält für
interne Test-Doubles einen rückwärtskompatiblen Default `False`; produktive
LLM-Antworten passieren ausschließlich den strengeren `LLMRoute`-Vertrag.

**Systemprompt:** Der bestehende Routerprompt fordert genau die fünf Felder
`intent`, `offer_ids`, `needs_clarification`, `out_of_scope` und
`acute_risk_detected`. Das Signal ist bei wahrgenommener akuter Selbst- oder
Fremdgefährdung, konkreter Gewalt, medizinischer oder vergleichbarer
unmittelbarer Gefahr zu setzen. Metaphorische, historische und klar vergangene
nicht akute Aussagen dürfen es nicht ohne Grund setzen. Das Modell stellt keine
Diagnose und nennt weder Telefonnummer noch Einrichtung; die Reaktion bleibt
Anwendungsverantwortung.

**Kontrollierte Sicherheitstexte:** Die Texte folgen den vorhandenen
sprachindizierten Service-Konstanten. Sie werden nicht in den angebotsbezogenen
Store `offer_translations.json` gelegt, weil dieser ausschließlich
hashgebundene `OfferCard`-Felder lokalisiert und für Systemtexte im Laufzeitpfad
wirkungslos wäre.

| Sprache | Visueller Text | Reviewstatus |
|---|---|---|
| Deutsch | Das klingt nach einer akuten Gefahr. Bitte rufe jetzt die 112 an oder bitte eine Person in deiner Nähe, den Notruf für dich anzurufen. | vorgegeben |
| Englisch | This sounds like an immediate danger. Please call 112 now, or ask someone near you to call the emergency services for you. | Übersetzungsentwurf, menschlich zu prüfen |
| Polnisch | To brzmi jak bezpośrednie zagrożenie. Zadzwoń teraz pod numer 112 albo poproś osobę w pobliżu, aby zadzwoniła po pomoc za ciebie. | Übersetzungsentwurf, menschlich zu prüfen |
| Rumänisch | Pare să fie un pericol imediat. Sună acum la 112 sau roagă o persoană din apropiere să apeleze serviciul de urgență pentru tine. | Übersetzungsentwurf, menschlich zu prüfen |
| Russisch | Похоже, это непосредственная опасность. Позвони сейчас по номеру 112 или попроси человека рядом вызвать экстренную помощь за тебя. | Übersetzungsentwurf, menschlich zu prüfen |

**TTS:** Die visuelle API-Antwort behält `112`. Die vorhandene zentrale
`SpeechSynthesizer.synthesize()`-Grenze ersetzt das eigenständige Token vor
jedem Edge-/OpenAI-TTS-Aufruf sprachabhängig durch `eins eins zwei`,
`one one two`, `jeden jeden dwa`, `unu unu doi` oder `один один два`. Damit gilt
die Aussprache auch für direkte API-Verbraucher und nicht nur für den Browser;
es entsteht keine parallele TTS-Pipeline.

**Betroffene Dateien:**

| Datei | Änderung | Begründung/Risiko |
|---|---|---|
| `app/models.py` | `LLMRoute` um striktes Pflichtfeld erweitern | interner Providervertrag; fehlende/ungültige Werte müssen scheitern |
| `app/providers/llm.py` | Prompt, Providervertrag und redigiertes Validierungslog | produktive Erkennung; keine Nutzereingaben im Log |
| `app/service.py` | kontrollierte Texte und früher Abbruch bei Signal | zentrale Reaktion; keine Karten/Formulatorantwort |
| `app/speech.py` | sprachabhängige 112-Normalisierung | visuelle Ausgabe unverändert, TTS verständlich |
| `tests/test_safety.py` | reale Query-/Providergrenze und Fehlerfälle | fokussiertes Safety-Regressionsnetz |
| vorhandene Architektur-/Datenflussdokumentation und dieser Plan | Ist-Verhalten, Grenzen und Status | keine parallelen Dokumente |

**Akzeptanzkriterien:**

- [x] Der produktive Routerprompt kann `acute_risk_detected` setzen.
- [x] Pydantic akzeptiert ausschließlich ein vorhandenes boolesches Signal.
- [x] `true` bricht vor Formulator, Retrieval, Karten und normalen Antworten ab.
- [x] Der Service gibt ausschließlich den kontrollierten lokalisierten 112-Text
      ohne LLM-Umformulierung aus.
- [x] `false` lässt normale Router-, Formulator- und Fallbackpfade unverändert.
- [x] Fehlende/ungültige Felder und Providerfehler erfinden kein Risiko und
      fallen technisch wie bisher zurück.
- [x] Validierungslogs enthalten Ereignis und Fehlerklasse, nicht den Fragetext.
- [x] Alle fünf visuellen Texte enthalten `112`; TTS spricht die Ziffern je
      Sprache einzeln.
- [x] Keine Keyword-Liste, Risikostufe, Diagnose oder persistente Safety-Session
      wird neu eingeführt.

**Teststrategie:** `tests/test_safety.py` setzt Test-Doubles ausschließlich an
der vorhandenen Providergrenze ein und ruft den realen `/api/query`-Pfad auf.
Parametrisierte Fälle decken akute Selbstgefährdung, Fremdgefährdung und
medizinische Gefahr, alle Sprachen, keine Karten und den nicht aufgerufenen
Formulator ab. `false` wird mit normaler Wissensbasisanfrage sowie
metaphorischer, historischer und vergangener nicht akuter Formulierung geprüft.
Provider-Vertragstests simulieren JSON mit fehlendem/ungültigem Feld,
unvalidierbare Antwort und Transportfehler; `caplog` prüft redigiertes Logging.
Ein Synthesizer-Test kontrolliert den Text unmittelbar vor der vorhandenen
Providergrenze. Die vollständige Suite schützt normale Query-, Grounding-,
Session-, Übersetzungs- und Speech-Pfade.

**Dead Ends und Mitigation:**

| Dead End | Auswirkung | Mitigation | Verifikation |
|---|---|---|---|
| Feld nur im Prompt | Signal geht bei Validierung verloren | Pflichtfeld in `LLMRoute` und `ProviderRoute` | Provider-Vertragstest |
| Auswertung erst nach `answer()` | Formulator kann Signal überschreiben | sofortiger Return direkt nach `route()` | Fake zählt `answer()`-Aufrufe |
| nur Formulator erhält Feld | Gefahr kann vor Retrieval nicht abbrechen | bestehende erste Routerstufe erweitern | Payload-/Query-Pfadtest |
| Keyword-Pfad bleibt davor aktiv | LLM-Vertrag wird für klare Fälle umgangen | alte `DANGER_PATTERNS` entfernen | Referenzsuche und Query-Test |
| Safety-Text vom LLM | Nummer/Text frei veränderbar | sprachindizierte Anwendungskonstante | absichtlich falsche LLM-Antwort bleibt unsichtbar |
| Texte im Angebots-Translation-Store | im Runtimepfad nie gelesen | bestehendes Service-Textmuster nutzen | alle Sprachen über API testen |
| `112` nur im Browser normalisieren | direkte TTS-API spricht Zahl weiter | zentrale Synthesizergrenze normalisieren | Provider-Payloadtest |
| ungültiges Signal als `true` coercen | falscher Safety-Abbruch | `StrictBool` im externen Vertrag | String-/Integer-Test |
| vollständige Frage loggen | sensible Krisenäußerung wird persistiert | konstantes Event plus Fehlerklasse | `caplog`-Negativassertion |
| Safety-Zustand in Session speichern | veraltete Gefahr beeinflusst Folgefragen | nur aktuelle Routerantwort auswerten | Session-/Referenzsuche |

**Rollback:** Das Paket verändert keine externen Datenformate, Persistenz oder
Abhängigkeiten. Ein expliziter Rücknahme-Patch entfernt Feld, Promptanweisung,
frühen Service-Return, kontrollierte Texte, TTS-Ersetzung und fokussierte Tests
gemeinsam. Der alte Keywordpfad darf nicht isoliert als scheinbar gleichwertiger
Safety-Ersatz reaktiviert werden. Bei Provider-Inkompatibilität bleibt das
vorhandene Template-Fallback aktiv; Paket 0B wird dann nicht als abgeschlossen
markiert, bis der strukturierte JSON-Vertrag nachgewiesen ist.

**Geplante Verifikation:**

- `python -m pytest tests/test_safety.py -q`
- `python -m pytest tests/test_api.py tests/test_safety.py -q`
- `python -m pytest`
- `python -m compileall -q app`
- Referenzsuche nach `acute_risk_detected`, `DANGER_PATTERNS`, `112`, allen
  `route()`-/`answer()`-Aufrufen und TTS-Eingängen
- Safety-Selbstreview anhand `REVIEW_TEMPLATE.md`
- Dokumentationsabgleich mit `$code-documentation`, danach erneute Tests

### Paket 1 (P1): Kanonische Git- und CI-Baseline

**Ziel:** Der geprüfte `Code3`-Stand wird auf einem neuen Branch des bestehenden
LENA-Repositories nachvollziehbar übernommen. Geeignete Laufzeitdaten werden
bewusst versioniert, lokale Zustände und Secrets ausgeschlossen und die bereits
lokal funktionierenden Python-Prüfungen als minimale GitHub-Actions-Baseline
verdrahtet.

- Status: Completed (2026-07-17).
- Entscheidungspfad: **A – bestehendes kanonisches Repository gefunden**.
- Nutzen: sehr hoch. Aufwand: mittel. Änderungsrisiko: mittel–hoch wegen des
  bewussten Wechsels vom bisherigen v1/v2-Baum auf den geprüften Code3-Baum.
- Nicht im Scope: Remoteänderung oder Push, Merge nach `main`, Packaging-Fix,
  neue Lint-/Typ-/Security-Abhängigkeiten, Node-/Browser-CI oder Übernahme
  historischer Runtime-/Sessiondaten.

#### Paket-1-Review vor Git- und CI-Änderungen

**Repository-Suche:** Die Suche war auf das lokale Projektverzeichnis
`MA Projekt/` begrenzt. Weder `Code3` noch seine direkten Eltern besitzen
Git-Metadaten. Folgende Kandidaten wurden geprüft:

| Pfad | Remote/Branch/letzter Commit | Beziehung zu Code3 | Bewertung/Risiko |
|---|---|---|---|
| `MA Projekt/code` | `HannahHoffner/lena-grounded-voice-assistant.git`; `feature/lena-v2-clean-rebuild`; `c20a38a` vom 2026-07-08 | aktives LENA-v1/v2-Repository mit passendem Produktnamen, sauber und mit Remote synchron | eindeutig kanonischer Anwendungskandidat; Code3 ist ein weitgehender Nachfolger, kein identischer Export |
| `legacy_review_backup/.../Chatbot-MA/Chatbot-MA2/Code` | gleicher LENA-Remote; `main`; `86cf872` vom 2026-04-21; stark verändert | eingefrorener älterer Anwendungsstand in einem ausdrücklich benannten Backup | kein kanonisches Ziel; Übernahme würde neuere Historie verlieren |
| weitere `.git` unter `legacy_review_backup` | überwiegend `Chatbot-MA.git`, April 2026 | Thesis-/Backupstände, teils verschachtelt und verändert | nicht als aktive LENA-Anwendung verwenden |
| `MA Projekt/thesis` | `Chatbot-MA.git`, Branch `bell` | Thesis mit lokalen Nutzeränderungen | fachfremd; nicht verändern |
| `MA Projekt/presentations` | `ma-introduction-beamer.git`, Branch `main` | Präsentationen | fachfremd; nicht verändern |

**Entscheidung:** `MA Projekt/code` ist das bestehende kanonische
LENA-Repository. Es ist der einzige aktive Kandidat mit dem spezifischen
Anwendungsremote, enthält LENA-v1/v2-Tags und einen bis 2026-07-08 entwickelten,
remote-synchronen Clean-Rebuild-Branch. Die Backupkopien teilen Historie oder
Thesis-Remote, sind aber ausdrücklich archiviert. Ein neues `.git` in `Code3`
würde eine parallele Historie erzeugen und ist deshalb ausgeschlossen.

**Herkunfts-/Dateivergleich:** Gegen
`feature/lena-v2-clean-rebuild@c20a38a` besitzt Code3 51 für die Baseline
geeignete Dateien. Die vollständige Einordnung wird nach der Übernahme mit
`git diff --name-status c20a38a` reproduzierbar; vorab ergeben sich:

- **identisch (5):** die fünf Dateien unter
  `app/static/vendor/leaflet/` einschließlich drei Markerbildern,
  `leaflet.css` und `leaflet.js`;
- **verändert (19):** `.env.example`, `.gitignore`, `README.md`, zwölf
  gleichnamige Python-/Frontenddateien unter `app/` sowie
  `tests/test_api.py`, `tests/test_retrieval.py` und
  `tests/test_sessions.py`;
- **neu (27):** acht Code3-Module (`i18n`, `kb_loader`, `offer_roles`,
  `providers/llm`, `service`, `speech`, `translate_offers`, `wfs_sync`), sieben
  aktivierte Datenartefakte unter `data/canonical`, `data/i18n` und `data/wfs`,
  sieben bestehende Code3-Dokumente, `pyproject.toml`, die WFS-Testfixture und
  vier zusätzliche Testmodule;
- **entfernt (127):** die ausschließlich im Vorgänger vorhandenen v1/v2-,
  Scraper-, SQLite-/Published-KB-, Ollama-/Piper-, Evaluation-, Docker-,
  Maintenance- und zugehörigen Testdateien. Git-Historie und der Basiskommit
  erhalten diese Inhalte vollständig; sie werden nur auf dem neuen
  Code3-Baseline-Branch aus dem Arbeitsbaum entfernt.
- **unklar (0 für den Baseline-Import):** Alle 51 importierten Dateien wurden im
  Code3-Review klassifiziert. Historische v1/v2-Dateien werden nicht selektiv in
  Code3 gemischt, weil dies eine ungetestete Parallelarchitektur erzeugen würde.

**Git-, Branch- und Commitstrategie:** Ausgangspunkt ist der saubere,
remote-synchrone Branch `feature/lena-v2-clean-rebuild` bei `c20a38a`. Es wird
lokal der neue Branch `modernization/code3-baseline` angelegt. Der erste Commit
`chore: establish reviewed LENA codebase baseline` ersetzt den Arbeitsbaum
kontrolliert durch die 51 geprüften Code3-Dateien plus sichere
Baseline-Metadaten. Er repräsentiert ausdrücklich nicht die ursprüngliche
Entwicklungsgeschichte; die Vorgängerhistorie bleibt als Elternhistorie
erhalten. Ein zweiter kleiner Commit `ci: add minimal Python verification
workflow` fügt nur den Workflow und die zugehörige Dokumentation hinzu. Es wird
weder Remote konfiguriert noch gepusht oder gemergt.

**`.gitignore`- und Datenstrategie:** Die vorhandene Code3-Datei wird vor dem
Import projektgerecht erweitert. Ignoriert werden `.env`/`.env.*` mit expliziter
Ausnahme für `.env.example`, virtuelle Umgebungen, Python-/Test-/Coverage-/Build-
Artefakte, IDE-/OS-/OneDrive-Konfliktdateien, Logs/temporäre Dateien,
`runtime/` und Sessions, Audio, lokale Datenbanken, Modelle/Weights,
Browserprofile sowie WFS-Staging-/Tempdateien. Ganze `app/`, `tests/`, `docs/`
oder `data/` werden nicht pauschal ignoriert.

| Datenklasse | Entscheidung |
|---|---|
| `data/canonical/offers.json` | versionierter aktivierter Laufzeitstand; notwendig für Start und Tests |
| `data/wfs/current.geojson`, `last_change_report.json`, `snapshots/*.geojson` | versionierter geprüfter Quellen-/Reviewstand |
| `data/i18n/*.json` | versionierte aktive Übersetzungen und manuelle Overrides |
| `tests/fixtures/` | versionierte lokale Testdaten; ersetzt Live-WFS in Tests |
| `runtime/`, insbesondere `runtime/sessions.json` | lokal erzeugt, kann Nutzerfragen enthalten, niemals versionieren |
| `runtime/wfs/`, `*.tmp` | lokales Staging/temporäre Promotion, niemals versionieren |
| Audio, Browserprofile, lokale DBs und Modellartefakte | lokal erzeugt/heruntergeladen, niemals versionieren |

**Secret- und Datenschutzgate:** `.env` und `.env.local` existieren in Code3,
werden nicht gelesen, kopiert oder indiziert. Vor jedem Commit werden Index und
Arbeitsbaum auf Schlüssel-/Token-/Passwort-/Private-Key-Muster, private URLs,
Zertifikate, Sessioninhalte, Browserzustände und lokale absolute Pfade geprüft;
Treffer werden ausschließlich als Pfad/Regel, nie mit vollständigem Geheimnis
ausgegeben. Testwerte wie `test-token` und sichere Platzhalter in
`.env.example` sind zulässig. Dateien über 1 MiB und Binärtypen werden gesondert
inventarisiert; die drei kleinen Leaflet-PNGs sind erwartete vendorte Assets.

**CI-Plattform und Umfang:** Der kanonische Remote liegt eindeutig auf GitHub.
Der Workflow `.github/workflows/test.yml` verwendet die am 2026-07-17 anhand
der offiziellen Release-Seiten geprüften Major-Versionen `actions/checkout@v7`
und `actions/setup-python@v6`, minimale `contents: read`-Berechtigung,
`ubuntu-latest` und Python 3.11 aus `pyproject.toml`. Er installiert
`python -m pip install -e ".[dev]"` und führt ausschließlich
`python -m pytest` sowie `python -m compileall -q app` aus. Kein Cache, Secret,
Deployment, Node-, Browser-, Lint-, Typ- oder Securityschritt wird ergänzt.

**Betroffene Dateien/Arbeitsbereiche:**

| Pfad | Änderung | Risiko |
|---|---|---|
| bestehendes Repository `MA Projekt/code` | neuer lokaler Branch und zwei Commits | Historie bleibt erhalten; kein Push |
| 51 geprüfte Code3-Dateien | kontrollierte Baseline-Übernahme | bewusster vollständiger Anwendungswechsel |
| `.gitignore` | projektgerechte Ausschlüsse | zu enge/weite Regeln werden mit `check-ignore` geprüft |
| `.github/workflows/test.yml` | minimaler GitHub-Actions-Workflow | nur lokal syntaktisch/plausibel prüfbar, kein Remote-Lauf |
| `README.md`, `docs/setup.md`, `docs/testing.md`, Architektur/ExecPlan | Git-/CI-/Datenstatus aktualisieren | bestehende Dokumentation, keine Paralleldatei |

**Akzeptanzkriterien:**

- [x] Kanonischer LENA-Remote und Ausgangscommit sind dokumentiert und bleiben
      unverändert erreichbar.
- [x] `modernization/code3-baseline` basiert auf `c20a38a`; kein neuer Remote,
      Push oder Merge erfolgt.
- [x] Der Branch enthält ausschließlich geprüfte Source-, Dokumentations-,
      Fixture- und aktivierte Laufzeitdaten sowie minimale CI-Metadaten.
- [x] `.env*`, Sessions, Runtime-Staging, Caches, Builds, Audio, DBs, Modelle,
      Browserprofile und OneDrive-Konflikte sind wirksam ausgeschlossen.
- [x] Keine ungeeignete Datei über 1 MiB und keine unerwartete Binärdatei ist im
      Index; die drei Leaflet-PNGs sind bewusst versioniert.
- [x] `python -m pytest` und `python -m compileall -q app` laufen vor den Commits
      sowie auf dem finalen Branch erfolgreich.
- [x] GitHub Actions bildet exakt diese lokal erfolgreichen Prüfungen ohne
      Secrets oder Schreibrechte ab; ein Remote-Lauf wird nicht behauptet.
- [x] `git status`, `git diff --check`, `git ls-files`, `git check-ignore` und
      Secret-/Datenschutzprüfungen liefern nachvollziehbare Ergebnisse.
- [x] Baseline- und CI-Commit sind getrennt und behaupten keine verlorene
      Entwicklungshistorie.

**Dead Ends und Mitigation:**

| Dead End | Evidenz/Auswirkung | Mitigation | Verifikation |
|---|---|---|---|
| neues Repo in Code3 | vorhandener spezifischer LENA-Remote würde parallelisiert | Pfad A und neuer Branch im bestehenden Repo | `git remote -v`, Commit-Eltern |
| Backup als Ziel | Aprilstand ist älter und lokal verändert | nur aktives `MA Projekt/code` verwenden | Pfad/Commit-/Remotevergleich |
| Legacy und Code3 mischen | zwei unvereinbare Runtime-/Datenarchitekturen | Code3 als kohärenten Branchbaum übernehmen; Legacy über Historie erhalten | Tests und Dateiinventar |
| ungeprüfte Massenlöschung | 127 Vorgängerdateien fallen aus aktuellem Baum | exakte Name-Status-Liste, unter 1.000, eigener Branch, Basiskommit bleibt | `git diff --name-status c20a38a` |
| Secrets/Sessions übernehmen | `.env*` und `runtime/sessions.json` vorhanden | Ignore vor Staging, Index-/Patterncheck | `git check-ignore`, `git grep --cached` |
| aktive Daten pauschal ignorieren | App/Tests würden in leerer Umgebung scheitern | kanonische/WFS-/i18n-Daten und Fixture bewusst versionieren | `git ls-files data tests/fixtures`, Tests |
| Zeilenenden-Massendiff | Windows/OneDrive-Arbeitsbaum | kein Formatter und keine neue `.gitattributes`-Normalisierung in diesem Paket | `git diff --check`, numstat/Dateitypen |
| CI mit unkonfigurierten Tools | keine Ruff/MyPy/Node-Konfiguration | nur nachgewiesene Pytest-/Compile-Befehle | lokale identische Befehle |
| Plattform vermuten | wäre ohne Remote unzulässig | GitHub ist durch bestehenden Remote belegt | `git remote get-url origin` |
| unbeabsichtigter Remote-Schreibzugriff | Nutzer hat keinen Push beauftragt | ausschließlich lokale Branches/Commits | Reflog/status; kein `git push` |

**Rollback und Recovery:** Vor der Übernahme muss der Ausgangsbranch sauber sein.
`c20a38a` bleibt unverändert und ist zugleich lokal sowie als
`origin/feature/lena-v2-clean-rebuild` erreichbar. Ein Abbruch vor dem ersten
Commit erfolgt nur, solange keine ungesicherten Änderungen bestehen. Nach den
Commits wird nicht destruktiv zurückgesetzt; Rücknahme geschieht über einen
expliziten Revert oder durch Wechsel auf den unveränderten Ausgangsbranch. Ohne
Push kann der lokale Baseline-Branch zusätzlich gelöscht werden, jedoch nur nach
ausdrücklicher Nutzerentscheidung.

**Geplante Verifikation:**

- Kandidat: `git status --short --branch`, `git remote -v`, `git branch -a -vv`,
  `git log -1`, `git diff --name-status c20a38a`
- lokal/CI-identisch: `python -m pytest`, `python -m compileall -q app`
- Index: `git status --short`, `git diff --cached --check`, `git ls-files`,
  `git check-ignore -v .env .env.local runtime/sessions.json build/...`
- Umfang: Datei-/Typ-/Größeninventar, keine Massenlöschung über 1.000 Dateien
- Sicherheit: redigierter Secret-/Private-Key-/Zertifikat-/Session-/Pfadscan im
  Index; keine sensiblen Werte ausgeben
- CI: YAML-Struktur und verwendete Befehle lokal prüfen; Remote-Ausführung bleibt
  bis zu einem späteren Push/PR **nicht verifiziert**
- Infrastruktur-Selbstreview nach `REVIEW_TEMPLATE.md`, danach
  `$code-documentation` und erneute vollständige Prüfung

### Paket 2 (P1): Request-Grenzen und sichere Exposition

**Ziel:** Query-, STT- und TTS-Eingaben sowie öffentlich bindbare Serverprofile
haben explizite Grenzen.

- Status: Completed (2026-07-17).
- Erwartete Dateien: `app/config.py`, `app/main.py`, `app/models.py`, API-Tests,
  `app/__main__.py`, `.env.example`, `docs/configuration.md` und dieser ExecPlan.
- Tests: Grenzwerte, 413/422, ungültige Formate, lokale Standardbindung.
- Nutzen: hoch. Aufwand: klein–mittel. Risiko: niedrig.
- Regressionen: lange legitime Aufnahme; Grenzwerte müssen realistisch sein.

#### Paket-2-Review vor Implementierung

**Aktuelle Laufzeitpfade:**

- `POST /api/query` validiert `QueryRequest` in `app/models.py` und ruft danach
  unmittelbar `QueryService.query()` auf. `query` besitzt bereits ein statisches
  Pydantic-Limit von 1.000 Zeichen; die Grenze ist weder konfigurierbar noch in
  der Konfigurationsreferenz sichtbar.
- `POST /api/speech/transcribe` liest mit `await request.body()` den gesamten
  Body vor Größen- oder Formatprüfung in den Speicher und reicht ihn danach an
  den vorhandenen `SpeechTranscriber` weiter.
- `POST /api/speech/synthesize` akzeptiert ein untypisiertes Dictionary. Text
  ist unbegrenzt; unbekannte Sprachwerte fallen still auf Deutsch zurück.
- `python -m app` bindet standardmäßig sicher an `127.0.0.1`, erlaubt über
  `--host` aber jede öffentliche Adresse ohne explizites Sicherheits-Gate.

**Bestehende Strukturen zur Wiederverwendung:** `Settings` und die vorhandenen
`_env_*`-Parser bleiben die einzige Konfigurationsquelle. Pydantic-Modelle in
`app/models.py` bleiben der JSON-Vertrag. Die vorhandenen Speech-Adapter werden
nicht dupliziert; Größen- und Medientypprüfung erfolgen davor am HTTP-Rand.
`argparse`/`uvicorn.run()` bleiben der einzige Serverstartpfad.

**Vorgesehene Grenzen und Verträge:**

| Eingabe | Standard | absolute Obergrenze | Verhalten |
|---|---:|---:|---|
| Query-Text | 1.000 Zeichen | 10.000 Zeichen | konfigurierbare Überschreitung: 422 |
| STT-Audio | 10 MiB | 25 MiB | früh und während Streaming: 413 |
| TTS-Text | 4.000 Zeichen | 20.000 Zeichen | leer/ungültig/zu lang: 422 |

STT akzeptiert die tatsächlich vom Frontend angebotenen Audiofamilien WebM,
Ogg, MP4, MPEG/MP3 und WAV. Fehlender `Content-Type` behält aus
Kompatibilitätsgründen den bisherigen WebM-Standard; explizit nicht erlaubte
Typen erhalten 415. Die Grenzwerte werden über
`QUERY_MAX_CHARS`, `SPEECH_TRANSCRIPTION_MAX_BYTES` und
`SPEECH_SYNTHESIS_MAX_CHARS` gesetzt und sicher auf ihre absoluten Grenzen
beschränkt.

**Öffentliche Bindung:** Loopback-Adressen und `localhost` bleiben ohne Zusatz
zulässig. Jede andere Adresse benötigt neben `--host` zusätzlich
`--allow-public`. Das Gate behauptet keine Produktionsreife und ersetzt weder
TLS, Authentifizierung, Proxy-Limits noch ein Datenschutzkonzept.

**Akzeptanzkriterien:**

- [x] Query-Grenze wirkt im realen `/api/query`-Pfad; normale und kategoriebasierte
      leere Anfragen bleiben kompatibel.
- [x] STT prüft `Content-Length` früh und zählt auch chunked empfangene Bytes;
      Oversize erreicht den Provider nicht.
- [x] Leeres Audio ergibt 422, nicht erlaubtes Audio 415, Oversize 413.
- [x] TTS verwendet ein Pydantic-Modell; leere, zu lange und unbekanntsprachige
      Payloads ergeben 422 statt Provideraufruf oder Sprach-Fallback.
- [x] Normale Query-, STT- und TTS-Anfragen bleiben unverändert erfolgreich.
- [x] Öffentliche Hosts werden ohne `--allow-public` abgewiesen; Loopback bleibt
      der Standard und funktioniert ohne Flag.
- [x] Limits sind dokumentiert und `.env.example` enthält nur sichere Werte.
- [x] Keine Anfrageinhalte oder Secrets werden zusätzlich protokolliert.

**Teststrategie:** API-Tests verwenden `TestClient` am realen FastAPI-Routing
und mocken ausschließlich die bestehende Speech-Providergrenze. Grenzwert-1,
Grenzwert und Grenzwert+1 werden für relevante Eingaben geprüft. Ein Request
ohne `Content-Length` prüft den Streaming-Zähler. CLI-Tests prüfen die reine
Hostvalidierung und die Parser-Defaults; Uvicorn wird nicht gestartet.

**Dead-End-Prüfung:**

| Dead End | Auswirkung | Mitigation | Verifikation |
|---|---|---|---|
| nur `Content-Length` prüfen | chunked Requests umgehen das Limit | Bytes aus `request.stream()` mitzählen | Test ohne Header |
| erst nach `request.body()` prüfen | Speichergrenze wirkt zu spät | begrenztes Streaming vor Provider | Oversize-Provider bleibt ungerufen |
| zweite Speech-Pipeline bauen | divergente Provider-/TTS-Regeln | vorhandene Adapter nur nach Validierung aufrufen | Monkeypatch an Adaptergrenze |
| TTS-Dictionary manuell weiter parsen | unbekannte Sprache fällt weiter still zurück | Pydantic-Vertragsmodell mit `Language` | 422-Test |
| nur Frontend begrenzen | direkte API-Aufrufe bleiben offen | serverseitige Grenzen sind autoritativ | API-Tests |
| `0.0.0.0` pauschal verbieten | bewusster Proxy-/LAN-Betrieb unmöglich | explizites `--allow-public` | CLI-Tests |
| Public-Flag als Produktionsschutz darstellen | falsches Sicherheitsgefühl | Dokumentation nennt verbleibende TLS/Auth-/Proxy-Pflichten | Doku-Review |

**Rollback:** Änderungen sind auf Modelle, HTTP-Adapter, Settings und CLI-Gate
begrenzt und besitzen keine Datenmigration. Ein Revert stellt die bisherigen
Verträge wieder her; bei zu engen Betriebswerten werden zunächst nur die
konfigurierbaren Standards innerhalb der dokumentierten absoluten Grenzen
angepasst, nicht die Schutzlogik entfernt.

**Geplante Verifikation:**

- `python -m pytest tests/test_request_boundaries.py -q`
- `python -m pytest`
- `python -m compileall -q app`
- `python -m app --help`
- `git diff --check` und finaler Secret-/Scope-Review

#### Paket-2-Verifikation

- `tests/test_request_boundaries.py`: 20 Tests bestanden. Geprüft sind
  Grenze/Überschreitung, kategoriebasierte Leeranfrage, früher und gestreamter
  STT-Abbruch, 413/415/422, typisierte TTS-Sprache, Konfigurations-Clamping und
  lokale/öffentliche Hostprofile.
- `python -m pytest`: 103 Tests bestanden.
- `python -m compileall -q app`: erfolgreich.
- `python -m app --help`: `--allow-public` sichtbar; realer Aufruf mit
  `--host 0.0.0.0` ohne Freigabe endet vor Uvicorn mit Exit-Code 2.
- Referenzsuche bestätigt je einen produktiven Query-, STT-, TTS- und
  `uvicorn.run()`-Pfad. Der frühere `request.body()`-Pfad ist entfernt.
- `$code-documentation` wurde auf README, Setup, Konfiguration, Datenfluss,
  Architekturreview und diesen ExecPlan angewendet.
- `git diff --check`: erfolgreich; keine Secrets, Daten- oder Provideränderung.

**Verbleibende Grenzen:** Das Public-Gate verhindert versehentliche Bindung,
ist aber kein Zugriffsschutz. Rate-Limiting, TLS, Trusted-Host-Prüfung und
Reverse-Proxy-Limits bleiben Teil eines später festzulegenden Betriebsprofils.
Die 10-MiB-STT-Vorgabe ist ein sicherer Ausgangswert, muss aber mit realen
langen Aufnahmen beobachtet werden.

### Paket 3 (P1): Beobachtbarkeit und Fehlerverträge

**Ziel:** WFS-, LLM-, Speech-, Session- und Fallbackfehler sind redigiert
diagnostizierbar.

- Erwartete Dateien: `app/main.py`, `app/service.py`, Provider/Stores,
  Logging-Konfiguration, Tests.
- Tests: `caplog`, kein Secret/Fragetext im Standardlog, degraded Health.
- Nutzen: hoch. Aufwand: mittel. Risiko: niedrig.
- Regressionen: Lograuschen oder versehentliche personenbezogene Daten.

### Paket 4 (P1): Sessions atomar und begrenzt speichern

**Ziel:** Kein unbeschränktes Wachstum, kein direkter nicht-atomarer Write und
klarer Einzel-/Mehrprozessvertrag.

- Erwartete Dateien: `app/sessions.py`, `app/config.py`, Sessiontests,
  Datenschutz-/Betriebsdokumentation.
- Tests: Pruning, atomarer Fehlerfall, parallele Tasks, beschädigte Datei,
  maximale Turns/Sessions.
- Nutzen: hoch. Aufwand: mittel. Risiko: mittel.
- Rollback: altes JSON vor Migration sichern; neues Format zunächst kompatibel
  lesen.
- Abbruchkriterium: Retention oder Betriebsmodell nicht geklärt.

### Paket 5 (P1): WFS-Releasevertrag

**Ziel:** Review und Promotion beziehen sich auf denselben Hash; Aktivierung ist
als Release recoverbar.

- Erwartete Dateien: `app/wfs_sync.py`, eventuell kleines Release-/Store-Modul,
  `tests/test_wfs_sync.py`, Datenflussdokumentation.
- Tests: Quelle ändert sich zwischen Check/Promote; Hash-Mismatch; Fault-
  Injection je Schritt; Neustart-Recovery; idempotente Promotion.
- Nutzen: sehr hoch. Aufwand: mittel–hoch. Risiko: mittel–hoch.
- Rollback: bisherige Snapshots/Canonical-Datei unangetastet halten, bis neuer
  Manifestzeiger erfolgreich geschrieben ist.
- Abbruchkriterium: fehlender Recovery-Nachweis oder unklare Datenmigration.

### Paket 6 (P1): Packaging und Versionsführung

**Ziel:** Ein Wheel startet in einer leeren Umgebung mit Frontend und klarer
Runtime-Datenquelle; eine Version gilt für Paket und API.

- Erwartete Dateien: `pyproject.toml`, Ressourcen-/Pfadauflösung, Packagingtests,
  README/Setup.
- Tests: Wheel bauen, in temporärer Umgebung installieren, `/` und `/api/health`
  testen, fehlende/externe Daten bewusst behandeln.
- Nutzen: hoch. Aufwand: mittel. Risiko: mittel.
- Abbruchkriterium: keine Entscheidung eingebetteter versus externer Datenstand.

### Paket 7 (P2): Testnetz und Quality-Gates

**Ziel:** Lücken in Safety, Karten, Temporal, i18n, Translation, Speech und
Frontend werden geschlossen; Lint/Typen werden schrittweise eingeführt.

- Erwartete Dateien: neue fokussierte Testmodule, `pyproject.toml`, CI.
- Tests: bestehende Suite plus Coverage-Baseline, Formatter-Check, Type-Check.
- Nutzen: hoch. Aufwand: mittel. Risiko: niedrig.
- Regel: keine Massenformatierung zusammen mit Fachänderungen.

### Paket 8 (P2): QueryService kohäsiv teilen

**Ziel:** Orchestrierung, Safety-/Schlafpolicy und Templateformulierung sind
getrennt testbar; Verhalten und API bleiben gleich.

- Erwartete Dateien: `app/service.py`, wenige neue kohäsive Module unter dem
  bestehenden `app/`, fokussierte Tests.
- Tests: Characterization aller Rückgabepfade vor Extraktion; Provider nicht
  aufgerufen bei deterministischen Pfaden; Fallbackreihenfolge identisch.
- Nutzen: hoch. Aufwand: mittel. Risiko: mittel.
- Abbruchkriterium: PR vermischt Dateiverschiebung mit Verhaltensänderung.

### Paket 9 (P2): Provider-Transport und Validierung trennen

**Ziel:** HTTP-Retry, Promptbau, Schema- und Groundingvalidierung besitzen klare
Grenzen ohne generisches Framework.

- Erwartete Dateien: `app/providers/llm.py`, ein Transport- und/oder Validator-
  Modul, Provider-Contract-Tests.
- Tests: Transportfehler, 4xx/5xx, ungültiges JSON, Grounding, Retry/Backoff.
- Nutzen: mittel–hoch. Aufwand: mittel. Risiko: mittel.

### Paket 10 (P2): Frontend modularisieren und Accessibility absichern

**Ziel:** API, Zustand, Rendering, Karte und Speech sind kleine ES-Module; kein
Framework- oder Bundlerzwang ohne Bedarf.

- Erwartete Dateien: `app/static/app.js`, neue Module, `index.html`, Browsertests.
- Tests: Sprache, Query, Session, Karte, STT/TTS-Fallback, Tastatur, Axe-/ARIA-
  Smoke; `<html lang>` folgt Auswahl.
- Nutzen: hoch. Aufwand: mittel–hoch. Risiko: mittel.
- Abbruchkriterium: keine Browser-Smokes vor Aufteilung.

### Paket 11 (P2): Konfiguration und Reload-Semantik

**Ziel:** Validierte Betriebsprofile, nachvollziehbare Priorität und definierter
Translation-/KB-Reload.

- Erwartete Dateien: `app/config.py`, App-Komposition, i18n/KB-Service, Tests,
  Konfigurationsdokumentation.
- Tests: Prozessenv versus `.env.local`, ungültige Werte, Reload während Betrieb.
- Nutzen: mittel. Aufwand: mittel. Risiko: mittel.

### Paket 12 (P3): Bereinigung bestätigter wirkungsloser Zustände

**Ziel:** `full_context_recommended`, `kb_error`, `pending_clarification`,
redundante Health-Felder und CLI-Semantik werden genutzt oder kompatibel
deprecatiert.

- Erwartete Dateien: jeweils betroffene Module und Contract-Tests.
- Nutzen: gering–mittel. Aufwand: klein. Risiko: niedrig–mittel.
- Voraussetzung: öffentliche Verbraucher und Git-Historie prüfen.

## Reihenfolge und Begründung

1. **0A/0B:** unmittelbare Sicherheitsgrenzen.
2. **1:** ohne Git/CI sind alle weiteren Diffs und Rollbacks unsicher.
3. **2/3:** Eingaben begrenzen und Fehler sichtbar machen, bevor Persistenzpfade
   verändert werden.
4. **4/5:** Datenintegrität und Retention absichern.
5. **6:** ein reproduzierbares, startbares Artefakt herstellen.
6. **7:** Testnetz und statische Gates als Refactoring-Sicherheitsnetz.
7. **8/9/10/11:** kohäsive strukturelle Verbesserungen in getrennten PRs.
8. **12:** risikoarme Bereinigung nach Klärung öffentlicher Verträge.

Paket 0A und die fachliche Vorarbeit für 0B können parallel geplant werden.
Überlappende Source-Dateien dürfen nicht gleichzeitig bearbeitet werden.

## File Impact

Dieser Review-Durchlauf ändert ausschließlich:

| Datei | Action | Reason | Expected size/risk |
|---|---|---|---|
| `docs/architecture/codebase-review.md` | Create | evidenzbasierter Gesamtbericht | groß, nur Dokumentation |
| `docs/exec-plans/codebase-modernization.md` | Create | lebender, PR-fähiger Modernisierungsplan | groß, nur Dokumentation |

Die in den Paketen genannten Source-Dateien sind erwartete spätere Auswirkungen,
nicht Teil dieses Durchlaufs.

## Milestones

### Milestone 1: Review and Design

- [x] Alle anwendbaren Skills und Repository-Dokumente gelesen.
- [x] Git-/Arbeitsstand geprüft; fehlendes Repository dokumentiert.
- [x] Start-, Query-, WFS-, Translation-, Speech- und Frontendpfad verfolgt.
- [x] Wiederverwendbare Strukturen und Dead Ends bewertet.
- [x] SOTA-Zielbild ohne Big-Bang-Architektur abgeleitet.

Evidence: `docs/architecture/codebase-review.md`, Referenzsuchen, AST-Auswertung,
Wheel-Inventar und Testausführung.

### Milestone 2: Implementation

- [x] Nur die zwei freigegebenen Dokumente erstellt.
- [x] Keine produktiven Source-Dateien oder Abhängigkeiten verändert.
- [x] Plan mit Befunden, Unsicherheiten und Abbruchkriterien vervollständigt.

Evidence: Dateiinventar und abschließende Inhaltsprüfung.

### Milestone 3: Verification

- [x] Zielgerichtete Struktur-, Routen-, Import- und Referenzchecks ausgeführt.
- [x] Vollständige relevante Pytest-Suite ausgeführt.
- [x] Packaging real gebaut und Inhalt kontrolliert.
- [x] Finalen Dokumentationsumfang selbst geprüft.
- [x] Git-Diff für Paket 1 im kanonischen Repository geprüft; beim ursprünglichen
      Review war dies in `Code3/` noch nicht möglich.

Evidence: 58 Tests bestanden; `compileall` und Import-Smoke erfolgreich; Wheel
ohne Static/Data bestätigt.

### Milestone 4: Documentation

- [x] `code-documentation` auf Bericht und Plan angewendet.
- [x] Pfade, Links, Symbole, Befehle und Prioritäten gegengeprüft.
- [x] Dokumentationsprüfungen nach finaler Korrektur wiederholt.

Evidence: UTF-8-/Fence-/Abschnittsprüfung, Symbolreferenzsuche, Secret-Scan,
Pfadinventar und erneute Test-/Compile-Ausführung.

## Validation Plan

| Check | Command oder Methode | Erwartetes Ergebnis |
|---|---|---|
| Regression | `python -m pytest` | alle bestehenden Tests bestehen |
| Syntax | `python -m compileall -q app` | Exit 0 |
| Imports | Import von Main, Service, WFS und Translation | keine Importzyklen/Fehler |
| Packaging | `python -m pip wheel . --no-deps` im Temp-Verzeichnis | Befund reproduzierbar |
| Dokumentpfade | alle Backtick-Pfade gegen Dateisystem/Symbole prüfen | keine unbelegten Ist-Aussagen |
| Scope | Inventar der nach Review geänderten Dateien | nur zwei Zieldokumente |
| Secrets | Musterprüfung nur in neuen Dokumenten | keine geheimen Werte |
| Self-review | `REVIEW_TEMPLATE.md` | Befunde dokumentiert, keine Scope-Ausweitung |

## Rollback and Recovery

Der ursprüngliche Review-Durchlauf änderte nur zwei Markdown-Dateien. Seine
Rollbacknotiz entstand vor der Git-Baseline. Seit Paket 1 erfolgen Rücknahmen im
kanonischen Repository als explizite Reverts; destruktive Resets bleiben
ausgeschlossen.

Für spätere Pakete gilt:

- Sicherheitsfixes: kleiner revertierbarer PR mit Regressionstest.
- Sessionmigration: alte JSON-Datei sichern und rückwärtskompatibel lesen.
- WFS-Release: bisherigen Canonical-/Snapshot-Stand bis zum erfolgreichen
  atomaren Umschalten unverändert halten.
- Packaging: editable Entwicklungsstart bis zum bestandenen Wheel-Smoke erhalten.
- Modulteilung: keine Verhaltensänderung im selben PR.

## Risiken

- Ohne Git kann die Baseline unvollständig oder nicht der spätere Zielstand sein.
- P0-Safety besitzt fachliche, nicht nur technische Anforderungen.
- Neue Tests können bestehende, bisher maskierte Fehler sichtbar machen.
- Persistenzänderungen betreffen potenziell personenbezogene Sessiondaten.
- Packaging- und Pfadänderungen können lokale editable Workflows brechen.
- Frontendaufteilung kann Browser-/Speech-Zustände regressieren.
- Externe Providerverträge wurden nicht live verifiziert.

## Dokumentationsanforderungen je Paket

- Aktualisiere bestehende Dokumente statt parallele Architekturtexte anzulegen.
- Halte README als Einstieg; Details bleiben in `docs/`.
- Dokumentiere neue Konfiguration mit Pflichtstatus, Default und Sicherheitsfolge.
- Dokumentiere API-/Persistenzänderungen und Migrations-/Rollbackpfad.
- Trenne implementiert, konfigurationsabhängig und geplant.
- Führe `code-documentation` nach Implementierung und Verifikation aus.
- Prüfe Befehle, Pfade, Links, Versionsangaben und Einschränkungen.

## Abbruchkriterien

Ein Arbeitspaket wird gestoppt und nicht „fertig“ erklärt, wenn:

- der kanonische Repository-/Branch-Stand unklar ist;
- bestehende Nutzeränderungen nicht sicher abgegrenzt werden können;
- eine fachliche Safety- oder Datenschutzentscheidung fehlt;
- ein Datenformat ohne Recovery-/Rollbacknachweis geändert würde;
- neue Architektur keinen konkreten zweiten Use Case besitzt;
- Tests den realen Pfad nicht charakterisieren;
- der Diff mehrere unabhängige Pakete vermischt;
- Security-, Grounding- oder Fallbacktests regressieren;
- das Wheel-/Runtime-Datenmodell ungeklärt bleibt;
- erforderliche externe Verträge nicht kontrolliert simuliert werden können.

## Progress Log

- 2026-07-15 — Skills `review-first-coding` und `code-documentation` vollständig
  gelesen; Scope auf zwei Dokumente begrenzt.
- 2026-07-15 — Repository-Instruktionen und Arbeitsstand inventarisiert; kein
  Git-Root und keine ExecPlan-Konvention gefunden.
- 2026-07-15 — Runtime-, Frontend-, Provider-, Persistenz- und Testpfade
  verfolgt; Dead-End-Matrix erstellt.
- 2026-07-15 — 58 Tests, Compile- und Import-Smoke erfolgreich.
- 2026-07-15 — Wheel gebaut; fehlende Static-/Data-Artefakte bestätigt.
- 2026-07-15 — Review-Bericht und Modernisierungsplan erstellt.
- 2026-07-15 — `code-documentation`-Check auf Konsistenz, tatsächliche Symbole,
  Pfade, Prioritäten, Geheimnisse und implementiert-vs.-geplant angewendet.
- 2026-07-15 — Paket 0A erneut gegen den aktuellen Runtime-Pfad geprüft: zwei
  unsichere `bindPopup()`-Template-Strings in `renderMap()`, keine alternative
  Popup-Implementierung; Datenherkunft und Testgrenzen dokumentiert.
- 2026-07-15 — Node/npm und Browser-DOM-Testharness lokal nicht verfügbar;
  fokussierter statischer Produktpfadtest plus manueller Browser-Test geplant,
  ohne neue Abhängigkeit einzuführen.
- 2026-07-15 — Paket 0A implementiert: gemeinsamer DOM-Helper eingeführt und
  beide produktiven `bindPopup()`-Pfade ohne HTML-Strings verdrahtet.
- 2026-07-15 — Vendortes Leaflet geprüft: Nicht-String-Popupinhalte werden per
  `appendChild` übernommen. Popup-Sink-Suche findet keine weitere dynamische
  HTML-Interpolation; statisches Icon-`innerHTML` bleibt bewusst außerhalb des
  Pakets.
- 2026-07-15 — `tests/test_frontend_security.py` (2 Tests), vollständige Suite
  (60 Tests) und `python -m compileall -q app` erfolgreich. Ein ausführender
  Browser-DOM-Test bleibt mangels lokalem Harness als Restrisiko offen.
- 2026-07-17 — Paket 0B gegen den aktuellen Query-, Router-, i18n- und TTS-Pfad
  geprüft und vor Source-Änderungen mit Vertrag, Dead Ends, Rollback und
  Teststrategie geplant.
- 2026-07-17 — `LLMRoute` um striktes Pflichtsignal erweitert, Routerprompt
  angepasst und früher kontrollierter 112-Return im `QueryService` umgesetzt;
  der alte Keywordpfad wurde nicht als parallele Klassifikation beibehalten.
- 2026-07-17 — Fünf visuelle Anwendungstexte und zentrale sprachabhängige
  TTS-Normalisierung ergänzt. Nichtdeutsche Texte bleiben als menschlich zu
  prüfende Übersetzungsentwürfe markiert.
- 2026-07-17 — 21 fokussierte Safety-Tests sowie vollständige Suite mit 81
  Tests und `python -m compileall -q app` erfolgreich; `code-documentation`
  auf Architektur, Datenfluss, Review und ExecPlan angewendet.
- 2026-07-17 — Projektumfeld begrenzt durchsucht: aktives
  `lena-grounded-voice-assistant`-Repository als kanonisch bestätigt; ältere
  LENA-/Thesis-Repositories als Backups beziehungsweise fachfremd verworfen.
- 2026-07-17 — Neuen lokalen Branch `modernization/code3-baseline` auf
  `c20a38a` angelegt und 51 geprüfte Code3-Dateien übernommen. Der Commit
  `43b88bc` bewahrt die Vorgängerhistorie und kennzeichnet den Stand als
  geprüfte Baseline, nicht als rekonstruierte Entstehungshistorie.
- 2026-07-17 — `.gitignore`, Index, Dateigrößen, Binärtypen, sensible Pfade und
  Secret-Muster geprüft. Lokale `.env*`, Sessions, Runtime-Staging und
  generierte Artefakte sind ausgeschlossen; aktive WFS-/i18n-/Canonical-Daten
  und Testfixtures bleiben versioniert.
- 2026-07-17 — Minimalen GitHub-Actions-Workflow mit `checkout@v7`,
  `setup-python@v6`, Python 3.11, Pytest und `compileall` ergänzt. Lokale
  Workflowbefehle und 81 Tests bestehen; ein Remote-CI-Lauf ist nicht erfolgt.
- 2026-07-17 — `$code-documentation` auf README, Setup, Testing,
  Architekturreview und ExecPlan angewendet; kein Remote verändert, kein Push
  oder Merge ausgeführt.
- 2026-07-17 — Python-3.11-Constraints ergänzt, Wheel um Frontend und aktive
  Daten vervollständigt und per Clean-Install-/Health-Smoke geprüft. Die
  unversionierte Vorläuferkopie wurde nach Vergleich reversibel in
  `Code3-archive-pre-git-20260717` umbenannt.
- 2026-07-17 — Branch veröffentlicht und Draft-PR #1 gegen `main` geöffnet;
  beide GitHub-Actions-Läufe auf Linux/Python 3.11 einschließlich Wheel-Smoke
  erfolgreich. Ein menschliches PR-Review steht noch aus.

## Decision Log

- Decision: Keine Source-Änderungen in diesem Durchlauf.
  - Context: Auftrag priorisiert Review und verbietet Refactoring.
  - Options: Sofortige P0-Fixes oder reine Dokumentation.
  - Choice: Befunde dokumentieren; Umsetzung in Paket 0A/0B.
  - Consequences: Risiken bleiben bis zum nächsten freigegebenen Paket bestehen.
- Decision: Kein Big-Bang-Zielbaum implementieren.
  - Context: Kleine Codebasis mit wertvoller bestehender Fachlogik.
  - Options: Komplettmigration oder schrittweise Extraktion.
  - Choice: Characterization-Tests und kohäsive PRs.
  - Consequences: Übergangsweise bleiben große Dateien bestehen.
- Decision: Packaging als P1, nicht kosmetischen Build-Befund behandeln.
  - Context: Reales Wheel enthält weder UI noch Daten.
  - Choice: Clean-Install-Smoke als späteres Acceptance-Gate.
- Decision: Bestehenden LENA-Remote statt neuem Code3-Repository verwenden.
  - Context: `MA Projekt/code` ist sauber, remote-synchron und besitzt die
    spezifische LENA-v1/v2-Historie; Code3 selbst hat keine Git-Metadaten.
  - Options: neues Repository, Backup übernehmen oder neuer Branch im aktiven
    LENA-Repository.
  - Choice: Pfad A mit `modernization/code3-baseline` ab `c20a38a`.
  - Consequences: Historie bleibt erreichbar; Code3 ersetzt auf diesem Branch
    bewusst die alte Parallelarchitektur.
- Decision: GitHub Actions auf bestehende lokale Prüfungen begrenzen.
  - Context: GitHub ist durch `origin` belegt; keine weiteren Quality-Tools sind
    konfiguriert.
  - Choice: Python 3.11, Pytest und `compileall`, nur `contents: read`.
  - Consequences: robuste minimale CI; Lint, Typen, Browser und Packaging folgen
    in getrennten Paketen.

## Discoveries

- `Code3/` selbst besitzt keine Git-Metadaten; der geprüfte Stand liegt nun im
  bestehenden LENA-Repository auf `modernization/code3-baseline`.
- Der Baseline-Vergleich umfasst 5 identische, 19 veränderte, 27 neue und 127
  nur im Vorgänger vorhandene Dateien. Der Baseline-Commit umfasst 172
  Statuszeilen einschließlich einer erkannten Umbenennung; mit dem separat
  ergänzten Workflow umfasst der finale Branchdiff 173 Pfade.
- Alle vom Frontend verwendeten IDs existieren im HTML; alle nutzerbezogenen
  Backendrouten sind verdrahtet.
- Popupdaten folgen seit Paket 0A dem bereits etablierten sicheren
  `textContent`-/DOM-Knoten-Muster.
- 453 Sessioneinträge bestätigen, dass fehlendes Pruning bereits sichtbar ist.
- `full_context_recommended`, `kb_error` und `pending_clarification` haben keine
  nachgelagerte Verhaltenswirkung.
- WFS-Promotion verwendet einen neuen Fetch statt des Pending-Artefakts.
- Der Wheel-Build enthält Frontend, Leaflet und aktive fachliche Daten; eine
  frische Installation findet ihren Daten-Root unter dem Umgebungspräfix.
- UTF-8-Dateien sind intakt; fehlerhafte Anzeige stammte aus der Konsole.

## Final Verification Summary

- Acceptance requirements: Review, Zielbild und PR-Pakete erstellt; Paket 0A
  schließt beide bestätigten Popup-HTML-Sinks. Paket 0B validiert das
  LLM-Akutgefahr-Signal und ersetzt bei `true` den normalen Pfad durch den
  kontrollierten, lokalisierten 112-Hinweis. Paket 1 bewahrt die bestehende
  LENA-Historie, versioniert Code3 auf einem lokalen Baseline-Branch und ergänzt
  minimale GitHub-CI.
- Tests: `python -m pytest tests/test_frontend_security.py -q` — 2 passed;
  `python -m pytest tests/test_safety.py -q` — 21 passed;
  `python -m pytest` — 81 passed.
- Build: Wheel gebaut, Inhalt geprüft und aus einer frischen virtuellen
  Umgebung gegen Startseite und Health-Endpunkt erfolgreich getestet.
- Manual verification: Popup-Aufrufpfade und Leaflets DOM-Node-Behandlung sowie
  alle Router-/Formulatoraufrufe, Pydantic-Verträge, früher Safety-Return,
  Sprachabdeckung und beide TTS-Providerpfade statisch nachvollzogen; keine
  Live-Provideraufrufe.
- Git/CI: Branch `modernization/code3-baseline`, Baseline-Commit `43b88bc` und
  Reproduzierbarkeits-Commit `e96fa2a`; Draft-PR #1 gegen `main`. Push- und
  PR-Workflow remote erfolgreich, kein Merge ausgeführt.
- Documentation: `code-documentation` angewendet; README, Setup, Testing,
  Architekturreview und ExecPlan mit Git-, CI-, Daten- und Secret-Regeln
  abgeglichen.
- Residual risks: fehlender Browser-E2E-Test für Paket 0A, LLM-Falschpositive
  und -negative sowie vier ungeprüfte Übersetzungsentwürfe in Paket 0B,
  ausstehendes menschliches PR-Review, Session-/WFS-Integrität, Constraints
  ohne Artefakthashes und nicht live geprüfte externe Dienste.
