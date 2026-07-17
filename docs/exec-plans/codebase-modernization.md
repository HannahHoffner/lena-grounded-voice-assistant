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

### Paket 3A (P1): Nachvollziehbares technisches Logging und Interaktionsprotokoll

**Status:** Abgeschlossen und lokal verifiziert auf
`modernization/prototype-logging` (Stand 2026-07-17).

**Ziel und Akzeptanzvertrag:** Der lokale wissenschaftliche Prototyp erzeugt
redigierte technische Ereignisse für HTTP-, Query-, Retrieval-, LLM-, Speech-
und Sessionpfade. Zusätzlich schreibt genau der HTTP-Adapter von `/api/query`
nach der vollständig abgeschlossenen Serviceverarbeitung ein validiertes
Anfrage-Antwort-Paar nach `runtime/logs/interactions.jsonl`. Schreibfehler des
Interaktionsprotokolls verändern die Nutzerantwort nicht. Runtime-Daten bleiben
außerhalb von Git, CI und Wheel. Eine produktive Consent-, Forschungsdaten- oder
Datenschutzarchitektur ist ausdrücklich nicht Teil dieses Pakets.

**Repository-Review und tatsächlicher Antwortpfad:** `app/main.py:answer_query`
validiert die Requestgrenze und ruft `QueryService.query()` auf.
`app/service.py:QueryService.query` löst die kurzlebige Session auf, delegiert an
`_query_core`, erzeugt anschließend Karten-/Sessiondaten und liefert damit erst
den final sichtbaren `QueryResponse`. `_query_core` kann über Selbstbeschreibung,
Klärung, LLM-Router, kontrollierten Akutgefahrtext, LLM-Formulator,
deterministisches Retrieval oder Template-Fallback zurückkehren. Providerfehler
werden derzeit überwiegend ohne Ereignis auf Template-Logik abgebildet;
`SessionStore` verwirft Lesefehler still; STT/TTS übersetzen Providerfehler nur
in HTTP 503. Allein `app/providers/llm.py` protokolliert ungültige strukturierte
Routerantworten bereits redigiert.

**Wiederverwendete Strukturen:** Die zentrale `Settings`-Dataclass und
`.env.example` bleiben der einzige Konfigurationspfad. `QueryRequest` und
`QueryResponse` bleiben der API-Vertrag; interne Pfadmetadaten werden vom
öffentlichen Response-Dump ausgeschlossen. Die vorhandene Session-ID dient nur
als kurzlebige Zuordnung. Das bereits vollständig ignorierte `runtime/` ist der
Speicherort. Python `logging`, Pydantic, eine pro Writer geltende
`threading.Lock`-Sperre und append-basiertes UTF-8-JSONL genügen ohne neue
Abhängigkeit oder Infrastruktur.

**Gespeicherte Felder:** Schema-Version 1, UTC-Zeitstempel, Session-ID, Sprache,
`input_mode` (`text`/`speech`), vollständige tatsächlich verarbeitete
`user_query`, vollständige sichtbare `assistant_answer`, Antwortpfad,
Quellen-IDs, Retrieval-Trefferzahl, Akutgefahr- und Fallbackstatus sowie die
Version aus den installierten Projektmetadaten. Nicht gespeichert werden
Header, Cookies, IP-Adressen, Schlüssel/Tokens, Systemprompts, rohe Provider-
Requests/-Responses, interne Begründungen, Credential-Pfade, Stacktraces oder
Audioartefakte.

**Eingriffspunkte und erwartete Dateien:**

| Datei | Änderung | Begründung/Risiko |
|---|---|---|
| `app/interactions.py` | typisiertes Modell und synchronisierter JSONL-Writer | eine kohärente Persistenz; Fehler dürfen Antwort nicht blockieren |
| `app/models.py` | `input_mode` und intern ausgeschlossene Laufzeitmetadaten | tatsächlichen Sprachpfad und finalen Route-/Fallbackstatus transportieren, ohne öffentlichen Response zu erweitern |
| `app/config.py` | Aktivierung, fester Pfad und technischer Log-Level | zentrale, testbare Konfiguration |
| `app/main.py` | Request-/Speech-Events und genau ein Interaktions-Schreibpunkt | finale sichtbare Antwort liegt hier vollständig vor |
| `app/service.py` | stabile Router-, Retrieval-, Formulator-, Fallback- und Safety-Events sowie Pfadmetadaten | bisher stille kontrollierte Pfade sichtbar machen |
| `app/sessions.py` | redigierte Lese-/Schreibfehler | keine Sessioninhalte im technischen Log |
| `app/static/app.js` | `input_mode` nach erkannter/transkribierter Spracheingabe mitsenden | realen Browserpfad korrekt kennzeichnen |
| `.env.example` | sichere Standardkonfiguration erläutern | Prototypverhalten explizit machen |
| `tests/test_observability.py` und bestehende Test-Fixtures | reale Pfade, Fehler, Parallelität und Ausschlüsse | Integration statt Prompt-only-Tests |
| bestehende Architektur-, Datenfluss-, Konfigurations-, Setup- und Testdokumentation | Prototypgrenzen und Masterarbeitsformulierungen | keine parallele Dokumentation |

**Technische Events:** `request.started`, `request.completed`,
`request.failed`, `query.router.completed`, `query.router.failed`,
`query.retrieval.completed`, `query.formulation.completed`,
`query.formulation.failed`, `query.fallback.used`,
`safety.acute_risk_detected`, `stt.completed`, `stt.failed`, `tts.completed`,
`tts.failed`, `session.read.failed`, `session.write.failed` und
`interaction.write.failed`. Metadaten beschränken sich auf Pfad, Methode,
Status, Laufzeit, Provider-/Pfadstatus und Zähler; vollständige Interaktionstexte
erscheinen ausschließlich in JSONL.

**Dead Ends und Mitigation:**

| Dead End | Beleg/Auswirkung | Mitigation | Verifikation |
|---|---|---|---|
| Speicherung in Route und Service | würde dasselbe Paar doppelt schreiben | ausschließlich `answer_query` schreibt nach `QueryService.query()` | Zeilenzahl je Request |
| Speicherung innerhalb `_query_core` | Antwort kann danach durch Safety, Übersetzung, Session/Map ergänzt sein | interner Trace wird nur transportiert; Schreibpunkt nach finalem Service-Return | Safety-/Fallback-Integrationstests |
| technische Logs mit Freitext | Anfrage/Antwort können besonders sensible Inhalte enthalten | Ereignisse verwenden nur stabile Namen und nicht-inhaltliche Metadaten | `caplog` mit eindeutigen Geheimtestwerten |
| Interaktionsfehler blockiert Antwort | lokales Dateisystem kann fehlen oder schreibgeschützt sein | Writer fängt erwartbare Schreibfehler, loggt ohne Datensatzinhalt und liefert Status | absichtlich fehlerhafter Zielpfad |
| parallele Appends beschädigen JSONL | synchrone Requests können gleichzeitig schreiben | kleine pro Writer geltende Sperre und ein Write pro kompletter Zeile; Mehrprozessbetrieb bleibt ausgeschlossen | parallele Schreibtests und JSON-Parsing jeder Zeile |
| Browser-STT bleibt als Text markiert | bisher kennt `QueryRequest` keinen Eingabemodus | UI setzt `speech` nach Browser- oder Servertranskription, danach Rücksetzen auf `text` | Frontend-Vertrag und API-Test |
| Runtime-/Testdaten gelangen in Git/Packaging | JSONL enthält vollständige sensible Freitexte | Pfad unter bereits ignoriertem `runtime/`; Tests verwenden `tmp_path` | `git status`, `git check-ignore`, Wheel-Inhalt |
| produktive Datenschutzreife wird suggeriert | einfacher lokaler Prototyp besitzt keine Einwilligung/Löschung | Dokumentation nennt Zweck, Sensibilität und offene Produktivanforderungen ausdrücklich | Dokumentationsreview |

**Alternativen verworfen:** Separate Anfrage-/Antwortdateien verlieren die
Transaktionsbeziehung. Session-Datei als Forschungsprotokoll vermischt Zustände
und besitzt andere Lebensdauer. Datenbank, Queue, Cloudtelemetrie, dauerhafte
Nutzerkennung und Consent-Backend überschreiten den Prototypumfang. Allgemeines
Log-Level als Aktivierungsschalter koppelt zwei bewusst getrennte Protokollarten.

**Teststrategie und geplante Verifikation:** Fokussierte Tests ersetzen LLM und
Speech ausschließlich an bestehenden Providergrenzen und rufen den realen
FastAPI-/Query-Pfad auf. Abgedeckt werden Retrieval-, Formulator-, Fallback-,
Akutgefahr-, Kein-Treffer- und Speech-markierte Anfragen; exakt eine valide
JSONL-Zeile mit finaler Antwort; deaktivierter Writer; fehlendes Verzeichnis;
Schreibfehler; parallele Appends; Eventnamen und Redaktionsgrenzen; Session-,
STT- und TTS-Fehler. Danach laufen `python -m pytest`,
`python -m compileall -q app`, `python -m app --help`, `git diff --check`,
`git status`, eine Prüfung ignorierter Runtime-Daten sowie der finale Diff- und
Secret-Review. Der Code-Dokumentationsskill prüft anschließend Plan, bestehende
Dokumente, Konfigurationsnamen, Pfade und Prototypgrenzen; betroffene Checks
werden erneut ausgeführt.

**Rollback:** Die lokalen, thematisch getrennten Commits können ohne Datenmigration
revertiert werden. Das Entfernen der zwei Konfigurationswerte und des Writers
beendet neue Interaktionseinträge; vorhandene lokale JSONL-Dateien werden bei
einem Rollback nicht automatisch gelöscht. Der Schalter
`INTERACTION_LOGGING_ENABLED=false` deaktiviert Schreibvorgänge sofort, ohne den
Query-Pfad zu verändern.

**Fortschritt:**

- [x] Git-Ausgangslage und kanonischen Branch geprüft; Arbeitsbaum war sauber.
- [x] Verbindliche Dokumentation, Runtime-Pfade und bestehende Tests geprüft.
- [x] Antwortpfad, Wiederverwendung, Dead Ends und Dateiauswirkungen geplant.
- [x] Implementierung und fokussierte Tests abgeschlossen: 12 Tests bestanden.
- [x] Gesamtsuite (115 Tests), Compile-/CLI-Checks und Grenzprüfungen erfolgreich.
- [x] `code-documentation` angewendet und bestehende Dokumentation gegengeprüft.
- [x] Paket 3A nach finalem Diff-, Secret- und Runtime-Review abgeschlossen.

**Verifikationsergebnis:** `python -m pytest tests/test_observability.py -q`
meldete 12 bestandene Tests; `python -m pytest` meldete 115 bestandene Tests.
`python -m compileall -q app`, `python -m app --help` und
`git diff --check` waren erfolgreich. `git check-ignore -v
runtime/logs/interactions.jsonl` bestätigt die bestehende `runtime/`-Regel.
Manuell über den realen TestClient-Pfad geprüft wurden normale Retrieval- und
Formulatorantwort, kontrollierter Provider-Fallback, Akutgefahrtext,
Kein-Treffer-Pfad, Speech-Markierung, deaktivierte Speicherung, nicht blockierender
Schreibfehler und redigierte technische Logs. Vierzig parallele Appends ergaben
vierzig einzeln parsebare JSON-Zeilen. Es fand kein Remote-Lauf statt.

**Bekannte Grenzen:** Die Sperre schützt nur Threads desselben Prozesses, nicht
mehrere Uvicorn-Worker. JSONL besitzt noch keine Rotation, Verschlüsselung,
Zugriffskontrolle, Aufbewahrungs- oder Löschautomatik. Volltexte einschließlich
Kriseninhalten sind nicht anonym und müssen vor produktiver oder institutioneller
Forschungsnutzung neu bewertet werden. Paket 3B kann die übrigen Health- und
Fehlerverträge behandeln, ohne diese lokale Prototyppersistenz auszuweiten.

### Paket 3B (P1): Provider-Timeouts und kontrollierte Ressourcenbegrenzung

**Status:** Abgeschlossen und lokal verifiziert auf
`modernization/provider-timeouts` (Stand 2026-07-17).

**Ziel und Akzeptanzvertrag:** Alle tatsächlich verwendeten externen Provider
besitzen zentral konfigurierte, positive und im realen Aufrufpfad wirksame
Timeouts. LLM-Router und -Formulator haben getrennte Gesamtgrenzen, STT und TTS
enden kontrolliert, und WFS verwendet getrennte Verbindungs- und Lesetimeouts.
Bestehende Query-Fallbacks, Akutgefahrlogik, Requestgrenzen, 112-Normalisierung
und das Interaktionsprotokoll bleiben erhalten. Es entstehen weder neue Retries
noch eine Queue oder verteilte Ressourcensteuerung.

**Review der blockierenden Pfade:**

| Pfad | Bibliothek/Schnittstelle | Aktueller Stand | gewünschte Grenze und Fehlerpfad |
|---|---|---|---|
| LLM-Router | asynchrones `httpx.AsyncClient.post` in `BlabladorProvider._post` | `BLABLADOR_TIMEOUT_SECONDS` gilt als allgemeiner HTTPX-Phasentimeout; zwei Transportversuche können die Dauer verdoppeln | `LLM_ROUTER_TIMEOUT_SECONDS=15`; Gesamtgrenze mit `asyncio.timeout`, HTTPX-Transportgrenze und `ProviderTimeoutError`; vorhandener deterministischer Fallback, keine Safety-Aussage |
| LLM-Formulator | derselbe asynchrone HTTPX-Transport | gleicher gemeinsamer Wert und Retry wie Router | `LLM_FORMULATOR_TIMEOUT_SECONDS=30`; getrennte Gesamtgrenze, Template-Fallback und redigiertes Timeout-Event |
| Übersetzungswartung | asynchrones `httpx.AsyncClient.post` | gemeinsamer Blablador-Wert, kein Retry | Formulatorwert als Wartungs-Providergrenze; generischer `TranslationError`, keine halbe Store-Aktualisierung |
| Server-STT | asynchrones multipart HTTPX-POST, Audiodaten liegen nur im Speicher | `SPEECH_TRANSCRIPTION_TIMEOUT_SECONDS=45` als HTTPX-Phasentimeout | `STT_TIMEOUT_SECONDS=45` als Gesamt- und Transportgrenze; HTTP 503, kein Query-/Interaktionsdatensatz |
| OpenAI-TTS | asynchrones HTTPX-POST, Audio nur im Speicher | `SPEECH_SYNTHESIS_TIMEOUT_SECONDS=45` als HTTPX-Phasentimeout | `TTS_TIMEOUT_SECONDS=45`; HTTP 503, sichtbare bereits gespeicherte Textantwort bleibt unverändert |
| Edge-TTS | asynchroner `edge_tts.Communicate.stream()` | keine explizite Gesamtgrenze; Byte-Chunks nur im Speicher | derselbe TTS-Gesamtwert um den Stream; Cancellation wird an den asynchronen Stream weitergereicht, ohne Garantie über providerseitige Verarbeitung |
| WFS | asynchrones `httpx.AsyncClient.get` | fest codierte 30 Sekunden, keine Trennung | `WFS_CONNECT_TIMEOUT_SECONDS=10`, `WFS_READ_TIMEOUT_SECONDS=30`; `WfsTimeoutError`, bestehender aktiver Stand bleibt vor Validierung/Schreiben unverändert |
| lokale Modelle/Subprozesse | Suche in `app/` | nicht vorhanden | keine scheinbare Timeout- oder Prozessbeendigungsgarantie implementieren |

HTTPX unterstützt getrennte Connect-, Read-, Write- und Poolgrenzen. Für LLM,
STT und TTS begrenzt zusätzlich `asyncio.timeout` die gesamte asynchrone
Operation; Cancellation erreicht den HTTPX-Aufruf und dessen Client-Kontext.
Bei Edge-TTS wird der asynchrone Stream abgebrochen, aber LENA kann nicht
garantieren, dass ein externer Dienst bereits begonnene serverseitige Arbeit
beendet. WFS benötigt gemäß Betriebsprofil getrennte Connect-/Read-Grenzen; die
Write-/Poolwerte werden aus diesen beiden sicheren Grenzen abgeleitet.

**Wertebegründung:** Der Router verarbeitet nur den kompakten Index und soll mit
15 Sekunden schneller auf deterministisches Retrieval zurückfallen. Der
Formulator darf wegen größerem Kontext 30 Sekunden benötigen. STT und TTS
behalten ihre bisherigen 45 Sekunden als kompatible Gesamtgrenze. WFS erhält
10 Sekunden für Verbindungsaufbau und 30 Sekunden für die vollständige kleine
GeoJSON-Antwort. Tests überschreiben alle Werte mit Millisekundenwerten, ohne
reale Wartezeit. Null, negative, nicht endliche und ungültige Werte fallen beim
zentralen Laden auf die positiven Standards zurück; direkte `Settings`-Objekte
werden beim Erzeugen der Provider zusätzlich geprüft.

**Fallback- und Fehlervertrag:** Router-Timeout ist ein Providerfehler und setzt
weder `acute_risk_detected=true` noch eine Aussage über ausgeschlossene Gefahr;
`QueryService` verwendet den bestehenden deterministischen Pfad. Ein
Formulator-Timeout nutzt ausschließlich den vorhandenen Template-Fallback.
STT/TTS bleiben HTTP 503 mit generischem Text. STT erzeugt ohne Transkript keine
`/api/query`-Interaktion. TTS läuft nach der Textinteraktion separat und ändert
deren JSONL-Datensatz nicht. WFS schreibt erst nach vollständigem Download,
JSON- und Vertragscheck; ein Timeout berührt aktive Dateien nicht. Technische
Events sind `query.router.timeout`, `query.formulation.timeout`, `stt.timeout`,
`tts.timeout` und `wfs.sync.failed` mit redigiertem Fehlertyp.

**Nebenläufigkeit und Retries:** Es gibt keine lokalen Modell- oder
Subprozessaufrufe. Alle geprüften Provider sind externe asynchrone Dienste;
konkrete lokale Kapazitäts- oder Kontingentgrenzen sind nicht im Repository
belegt. Daher wird keine Semaphore eingeführt. Der bestehende LLM-Retry bei
jedem `httpx.TransportError` wird entfernt, weil er die Maximaldauer verdoppelt
und auch Timeoutfehler wiederholt. Es gibt keine weiteren automatischen
Provider-Retries im Runtime-Pfad. Eine spätere Semaphore wäre nur pro Prozess
wirksam und benötigt reale Last-/Providerdaten.

Der explizite Übersetzungs-Wartungsbefehl versucht nach einem fehlgeschlagenen
Mehrsprachenaufruf jede der höchstens vier Zielsprachen einzeln. Dieser
bestehende, endliche CLI-Fallback kann kumulativ bis zu fünf
Formulator-Timeouts benötigen, blockiert aber keinen Nutzerrequest und schreibt
fehlgeschlagene Einträge nicht als erfolgreiche Übersetzung. Eine Änderung
dieser Wartungspolitik ist nicht Teil von 3B.

**Betroffene Dateien:**

| Datei | Änderung | Risiko |
|---|---|---|
| `app/config.py` | neue zentrale positive Timeoutwerte und Legacy-Aliase | Konfigurationskompatibilität |
| `app/providers/llm.py` | getrennte Gesamtgrenzen, Timeouttyp, kein Retry | korrekter Template-Fallback |
| `app/speech.py` | Gesamtgrenzen um HTTPX und Edge-Stream | Cancellation und generische 503 |
| `app/wfs_sync.py` | expliziter HTTPX-Connect-/Read-Timeout und Typ | aktiver Stand darf unverändert bleiben |
| `app/translate_offers.py` | Formulatorgrenze im Wartungspfad | keine Teilaktualisierung |
| `app/main.py` / `app/service.py` | stabile redigierte Timeout-Events | keine Volltexte im Log |
| `.env.example`, bestehende Dokumentation | Werte, Wirkung und Grenzen | keine übertriebene Abbruchgarantie |
| `tests/test_provider_timeouts.py` und bestehende Fixtures | schnelle reale Providergrenzentests | keine zeitabhängigen/flakigen Tests |

**Dead Ends und Mitigation:**

| Dead End | Auswirkung | Mitigation | Verifikation |
|---|---|---|---|
| nur API-`wait_for` | interner Providervertrag bleibt unbegrenzt | Timeout direkt in LLM-/Speech-/WFS-Adaptern | Adapter- und realer API-Pfad |
| synchroner Code im Event Loop | Timeout beendet Blockade nicht | nur vorhandene asynchrone Netzwerk-/Streamaufrufe umschließen; keine lokalen Sync-Modelle vorhanden | Call-Path-Review |
| LLM-Retry verdoppelt Grenze | Timeout wird erneut ausgeführt | Retry entfernen; genau ein Transportversuch | Aufrufzähler im Test |
| Router-Timeout als Safety-`false` | falsche Sicherheitsbehauptung | `ProviderTimeoutError` führt unverändert in deterministischen Fallback, Safety bleibt nicht erkannt | Query- und JSONL-Test |
| Edge-Timeout als harter Serverabbruch dokumentiert | falsche Garantie | nur Cancellation des lokalen Streams zusagen, externe Grenze dokumentieren | Doku-Review |
| TTS-Timeout löscht Textantwort | Nutzer verliert bereits sichtbaren Inhalt | TTS-Endpunkt bleibt getrennt; Interaktionsdatensatz vor TTS unverändert | API-/JSONL-Test |
| WFS-Timeout schreibt Teilstand | aktive Fachdateien werden beschädigt | Download vollständig vor `canonical_payload` und jedem Write | Hash-/Dateiinhalt vor/nach Timeout |
| Semaphore ohne belegtes Limit | unnötige lokale Engstelle, keine Worker-Garantie | keine Begrenzung in 3B; Risiko transparent dokumentieren | finaler Diff |
| Exceptiontexte im Log | URLs oder Inhalte können austreten | nur Eventname und Exception-Klassenname | `caplog` mit Geheimwerten |
| langsame Sleeps in Tests | flakige Suite | kontrollierte blockierende Coroutines, Millisekundenwerte und Events | Laufzeit der fokussierten Suite |

**Teststrategie:** Konfigurationstests prüfen positive Standards, Legacy-Aliase,
ungültige Werte und tatsächlich an Provider übergebene kleine Werte. LLM-Tests
patchen nur `_post`, blockieren kontrolliert bis zur Cancellation und prüfen
Router-/Formulatorfallback, je einen erfolgreichen Pfad, genau einen Aufruf,
Timeout-Events, kein Safety-Signal und keine Query im Log. Speech-Tests ersetzen
HTTPX beziehungsweise Edge an der bestehenden Providergrenze, prüfen Erfolg,
Timeout, Cancellation, 503, 112-Regression und unverändertes JSONL. WFS-Tests
simulieren `httpx.ConnectTimeout` und `ReadTimeout`, prüfen Timeoutobjekt,
unveränderte aktive Dateien und keine Pending-/Promotiondateien. Danach laufen
`python -m pytest tests/test_provider_timeouts.py -q`, die relevanten Safety-,
Request- und Observabilitytests, `python -m pytest`, `python -m compileall -q
app`, `python -m app --help`, `git diff --check` sowie Runtime-, Secret- und
Dependency-Diff-Review.

**Rollback:** Die getrennten lokalen Implementierungs-, Test- und
Dokumentationscommits können ohne Datenmigration revertiert werden. Die neuen
Variablen besitzen kompatible Standards und akzeptieren die bisherigen
`BLABLADOR_TIMEOUT_SECONDS`, `SPEECH_TRANSCRIPTION_TIMEOUT_SECONDS` und
`SPEECH_SYNTHESIS_TIMEOUT_SECONDS` als Legacy-Fallback. Ein Rollback berührt
weder aktive WFS-Daten noch lokale Interaktionsprotokolle.

**Fortschritt:**

- [x] sauberer Paket-3A-Stand und neuer lokaler Branch geprüft.
- [x] Dokumentation, Provider, HTTP-Clients, Retries, Subprozesse und Tests geprüft.
- [x] Timeoutwirkung, Dead Ends, Werte, Dateien und Verifikation geplant.
- [x] Implementierung und fokussierte Tests abgeschlossen: 11 Tests bestanden.
- [x] Gesamtsuite (126 Tests) und manueller Reliability-Review erfolgreich.
- [x] `code-documentation` angewendet und Dokumentation gegengeprüft.
- [x] Paket 3B nach vollständiger Verifikation abgeschlossen.

**Verifikationsergebnis:** `python -m pytest tests/test_provider_timeouts.py
-q` meldete 11 bestandene Tests; `python -m pytest` meldete 126 bestandene
Tests in unter fünf Sekunden. `python -m compileall -q app`, `python -m app
--help` und `git diff --check` waren erfolgreich. Kontrollierte Fakes belegten
Cancellation des Router-, Formulator-, STT- und Edge-TTS-Aufrufs, die
HTTPX-Timeoutübersetzung von OpenAI-TTS, WFS-Connect-/Read-Timeouts ohne
Dateiänderung, den einzelnen LLM-Transportversuch sowie den begrenzten
Übersetzungsaufruf. Logs enthielten weder Testanfragen noch private
Exceptiontexte. JSONL enthielt bei Query-Timeout genau die kontrollierte finale
Fallbackantwort; STT erzeugte keinen Datensatz und TTS veränderte den vorhandenen
Textdatensatz nicht. Es wurden keine Runtime-Dateien, Abhängigkeiten oder
Remote-Einstellungen geändert.

**Strukturentscheidung:** `app/providers/llm.py`, `app/service.py` und
`app/wfs_sync.py` bleiben trotz mehr als 400 Zeilen unverändert zugeschnitten.
Die Ergänzungen betreffen jeweils ihre vorhandene Provider-, Orchestrierungs-
beziehungsweise WFS-Transportverantwortung. Eine Aufteilung in Paket 3B würde
die ausdrücklich ausgeschlossene allgemeine Modularisierung vorziehen und den
Reliability-Diff unnötig vergrößern.

### Paket 4 (P1): Sessions atomar und begrenzt speichern

**Status:** Abgeschlossen auf `modernization/session-persistence` (Stand
2026-07-17); lokale Commits, nicht gepusht.

**Ziel und Akzeptanzvertrag:** Das bestehende, rückwärts kompatible
`runtime/sessions.json` bleibt eine JSON-Map für den lokalen
Einzelprozess-Prototyp. Der vollständige Zyklus Lesen, Bereinigen, Ändern,
Validieren und atomar Schreiben wird innerhalb eines Prozesses geschützt.
Abgelaufene und überzählige Sessions werden physisch entfernt. Lese-, Recovery-
und Schreibfehler verhindern weder eine fachliche Antwort noch das getrennte
Interaktionsprotokoll. Eine Mehrprozess-, Datenbank- oder Forschungsdatenlösung
ist nicht Teil dieses Pakets.

**Aktuelles Datenmodell und Pfade:** `ConversationSession` in
`app/sessions.py` enthält eine zufällige 32-stellige UUID4-Hex-ID (128 Bit),
`Language`, timezone-aware `created_at` und `last_activity_at`, höchstens acht
`ChatTurn`-Paare sowie `pending_clarification`. `QueryRequest.session_id` ist auf
80 Zeichen begrenzt. Die ID wird ausschließlich als Schlüssel innerhalb der
JSON-Map verwendet und beeinflusst keinen Dateinamen. `QueryService` erzeugt
genau einen `SessionStore` für `runtime/sessions.json`, ruft vor dem asynchronen
Antwortpfad `resolve()` und danach `add_turn()` auf. Das Frontend verwirft seine
ID nach drei Minuten oder bei Reset/Sprachwechsel; ein serverseitiger Reset- oder
Löschendpunkt existiert nicht. Das Interaktionsprotokoll speichert die
kurzlebige Session-ID separat in `runtime/logs/interactions.jsonl`.

**Bestandsverhalten vor Paket 4 und behobene Race Conditions:** `_load_all()` las bei jedem Zugriff
die gesamte Map. `save()` führt ohne Sperre Load–Modify–Write aus;
`_dump_all()` überschreibt die Hauptdatei direkt. Ablauf wird nur in `resolve()`
für die angefragte Session mit `now - last_activity_at > timeout` geprüft;
abgelaufene fremde Einträge bleiben dauerhaft gespeichert. Zwei parallele
Erstellungen können denselben Ausgangszustand lesen und eine Session verlieren.
Zwei parallele `add_turn()`-Aufrufe derselben Session können jeweils veraltete
Objekte schreiben und einen Turn verlieren. Ungültiges JSON und nicht lesbare
Dateien werden als leer behandelt; einzelne ungültige Records werden
übersprungen. Seit Paket 3A waren Fehler redigiert sichtbar, Schreibfehler wurden
aber noch bis zum Nutzerrequest weitergereicht. Paket 4 ersetzt genau diesen
Pfad durch den nachfolgend beschriebenen Lock-, Recovery- und Atomic-Write-Vertrag.

**Architekturentscheidung:** JSON genügt bei kleinem Bestand und genau einem
Anwendungsprozess. Ein pro absolutem Pfad gemeinsam registriertes
`threading.RLock` schützt auch mehrere `SessionStore`-Instanzen im selben
Prozess. Jeder mutierende Pfad hält es über Lesen, TTL-Pruning,
Kapazitätspruning, Mutation, Pydantic-Validierung und Replace. `add_turn()` lädt
unter dem Lock die neueste persistierte Version derselben Session und hängt den
Turn in Abschlussreihenfolge an; damit gehen parallele Updates derselben Session
nicht verloren. Die Sperre schützt keine getrennten Prozesse oder mehrere
Uvicorn-Worker. Dafür wäre später eine prozessübergreifende Sperre oder
Datenbankmigration erforderlich; Paket 4 behauptet diese Sicherheit nicht.

**Atomarer Write:** Der vollständig serialisierte und validierte Zustand wird
über `tempfile.NamedTemporaryFile(delete=False, dir=Zielverzeichnis)` in eine
eindeutige Datei desselben Dateisystems geschrieben. Nach `flush()` und
`os.fsync()` ersetzt `os.replace()` atomar die Hauptdatei. Ein `finally` entfernt
ein verbliebenes Temp-Artefakt. Die Hauptdatei wird vor erfolgreichem Replace
nicht geöffnet oder geleert. Verzeichnis-`fsync` wird plattformübergreifend nicht
zugesagt; Dateidaten und atomarer Namenswechsel werden abgesichert.

**TTL und Begrenzung:** Die bestehende fachliche TTL bleibt
`SESSION_TIMEOUT_SECONDS=180`; exakt an der Grenze bleibt eine Session wie
bisher aktiv, erst `>` gilt als abgelaufen. Opportunistische Bereinigung erfolgt
bei Sessionzugriffen, weil die JSON-Map ohnehin vollständig gelesen werden muss;
geschrieben wird nur bei Mutation oder tatsächlicher Bereinigung. Nach der
TTL-Bereinigung begrenzt `SESSION_MAX_ENTRIES=500` den Zustand. Entfernt werden
deterministisch die ältesten Sessions nach `last_activity_at`, dann
`created_at`, dann `session_id`. Es gibt kein separates Dateigrößenlimit, weil
maximal acht begrenzte Query-/Antwortpaare je Session und die Eintragsgrenze das
Wachstum bereits nachvollziehbar begrenzen.

**Beschädigte Persistenz und Recovery:** Ungültiges JSON oder ein falsches
Root-Format wird nicht still überschrieben. Die Datei wird unter demselben
ignorierten Runtime-Pfad per atomarem `os.replace()` nach
`sessions.corrupt.<UTC-Zeit>.<UUID>.json` verschoben; anschließend beginnt ein
leerer Zustand. Das Umbenennen vervielfältigt sensible Daten nicht. Scheitert
Lesen oder Quarantäne, bleibt die Hauptdatei unangetastet und der aktuelle
Request arbeitet nur mit leerem/In-Memory-Zustand ohne Persistenzerfolg.
Ungültige einzelne Records werden redigiert als
`session.validation.failed` gezählt, aus dem aktiven Zustand ausgeschlossen und
bei der nächsten erfolgreichen Mutation entfernt. Recovery-Dateien bleiben
unter `runtime/`, werden weder versioniert noch automatisch gelöscht.

**Fehler- und Loggingvertrag:** `SessionStore` fängt erwartbare
Dateisystemfehler an der Persistenzgrenze. `create`, `resolve`, `save` und
`add_turn` liefern weiterhin ein gültiges In-Memory-Modell, sodass
`QueryService` Antwort und Session-ID ausgeben und danach das unabhängige JSONL
schreiben kann. Ereignisse sind `session.load.failed`,
`session.validation.failed`, `session.corrupt_file.detected`,
`session.write.failed`, `session.write.completed`,
`session.cleanup.completed` und `session.capacity.enforced`. Logs enthalten nur
Zähler, Dauer und Fehlerklasse, niemals Session-ID, Frage, Antwort oder
Dateiinhalt. Es gibt keine falsche API-Erfolgsaussage über Persistenz; der
öffentliche Vertrag kennt weiterhin keinen Persistenzstatus.

**Wiederverwendung und betroffene Dateien:**

| Datei | Änderung | Begründung/Risiko |
|---|---|---|
| `app/sessions.py` | zentraler Lock, Cleanup/Capacity, Quarantäne und atomarer Writer | Kern des Pakets; Fehler dürfen nicht propagieren |
| `app/config.py` | positive zentrale `session_max_entries`; bestehende TTL-Validierung | alternative Testwerte ohne Hardcoding |
| `app/service.py` | neue Kapazität an bestehenden Store übergeben | keine zweite Sessionarchitektur |
| `.env.example` | TTL und Maximalzahl erläutern | sichere Prototypstandards |
| `tests/test_session_persistence.py`, bestehende Session-/Observabilitytests | Konkurrenz, Fault Injection, Recovery und API-Fallback | reale Read–Modify–Write-Pfade |
| README und bestehende Architektur-/Datenfluss-/Setup-/Testdokumentation | Betriebsmodell und Grenzen | keine parallele Dokumentation |

**Dead Ends und Mitigation:**

| Dead End | Auswirkung | Mitigation | Verifikation |
|---|---|---|---|
| Lock nur um Write | verlorene Read–Modify–Write-Updates | gemeinsames Pfad-RLock um gesamten Zyklus | parallele Erstellung und Updates |
| Lock nur pro Store | zwei App-/Store-Instanzen kollidieren im Prozess | Registry nach absolutem Pfad | parallele Stores auf einer Datei |
| feste Temp-Datei | Kollision und fremdes Cleanup | eindeutiges NamedTemporaryFile im Zielordner | Temp-Pfad- und Paralleltest |
| Hauptdatei vor Replace verändern | Absturz hinterlässt Teil-JSON | nur Temp öffnen, flush/fsync, `os.replace` | Fault Injection vor Replace |
| Kapazität vor TTL | aktive Einträge werden unnötig verdrängt | zuerst TTL, danach ältestes `last_activity_at` | kombinierter Test |
| Cleanup schreibt bei jedem Read | unnötige IO und Lockdauer | nur bei tatsächlicher Entfernung schreiben | Write-Spion |
| beschädigtes Root still überschreiben | Recovery unmöglich | atomar umbenennen oder Persistenz für Zugriff sperren | JSON-/Root-/Quarantänefehler |
| Writefehler blockiert Antwort | fachlicher Request schlägt fehl | In-Memory-Session zurückgeben, redigiert loggen | API und Interaktions-JSONL |
| RLock als Worker-Sicherheit | falsches Betriebsversprechen | Einzelprozessgrenze überall dokumentieren | Doku- und Startpfadreview |
| Sessioncleanup berührt JSONL | Forschungsprotokoll wird unbeabsichtigt gelöscht | ausschließlich `sessions.json` und eigene Recovery-/Tempdateien anfassen | Sentinel-Interaktionsdatei |
| reale Sleeps in Zeit-/Concurrencytests | flakige Suite | injizierbares `utc_now`, Barriers und Events | schnelle fokussierte Suite |

**Teststrategie:** Atomtests prüfen vollständiges parsebares JSON, Tempdatei im
Zielordner, `flush`/`fsync`/Replace, unveränderte Hauptdatei und Temp-Cleanup bei
Fault Injection. Kontrollierte Threads/Barriers prüfen parallele Erstellungen,
verschiedene und gleiche Sessionupdates, gemeinsame Locks mehrerer Stores,
Exceptionfreigabe und parsebare Enddatei. Zeitinjektion prüft aktive,
abgelaufene und exakt an der TTL liegende Sessions sowie persistiertes Cleanup.
Kapazitätstests prüfen Reihenfolge, alternative Limits und TTL vor Capacity.
Recoverytests decken ungültiges JSON, falsches Root, ungültige Records,
Quarantäne- und Lesefehler sowie redigierte Events ab. Ein realer FastAPI-Test
simuliert Writefehler und belegt Nutzerantwort, Session-ID, genau ein korrektes
Interaktionspaar und keine Inhalte im technischen Log. Die vorhandenen Session-,
Safety-, Request-, Timeout- und Observabilitytests bleiben Regressionstor.

**Verifikationsergebnis:** 26 fokussierte Session-, Persistenz- und
Observabilitytests sowie die Gesamtsuite mit 138 Tests bestanden in jeweils
unter fünf Sekunden. `python -m compileall -q app`, `python -m app --help` und
`git diff --check` waren erfolgreich. Fault Injection belegte unveränderte
Hauptdateien und Temp-Cleanup bei Replace-Fehlern, Recovery beziehungsweise
bewussten In-Memory-Betrieb bei beschädigter Persistenz sowie die Freigabe des
Locks nach Fehlern. Kontrollierte parallele Store-Zugriffe hinterließen eine
parsebare Map ohne verlorene Sessions oder Turns. TTL-Grenze, Cleanup vor
Kapazitätsbegrenzung, ein API-Writefehler mit weiterhin genau einem
Interaktionsdatensatz und die Trennung vom Interaktions-JSONL sind getestet.
`git check-ignore -v` bestätigt den Ausschluss von Session-, Recovery- und
Interaktionsdateien durch `runtime/`; der Diff enthält keine Runtime-Dateien,
Secrets oder Abhängigkeitsänderungen.

**Rollback und Wiederherstellung:** Das JSON-Rootformat und alle Sessionfelder
bleiben unverändert; es gibt keine Datenmigration. Die lokalen Implementierungs-,
Test- und Dokumentationscommits können unabhängig revertiert werden. Vorhandene
`sessions.corrupt.*.json` werden bei Rollback nicht automatisch gelöscht oder
wieder eingespielt. Eine bewusste Wiederherstellung erfolgt offline nach Prüfung
des Inhalts durch Zurückbenennen bei gestoppter Anwendung. Bei dauerhaftem
Schreibfehler kann LENA mit kurzlebigen In-Memory-Sessions weiterantworten, ohne
Persistenzerfolg zu behaupten.

**Fortschritt:**

- [x] sauberer Paket-3B-Stand und neuer lokaler Branch geprüft.
- [x] Dokumentation, Modelle, Query-/Resetpfade, Logging und Tests geprüft.
- [x] Race Conditions, JSON-Entscheidung, Recovery und Grenzen geplant.
- [x] Implementierung und fokussierte Tests abgeschlossen (26 Session-/Observabilitytests).
- [x] Gesamtsuite (138 Tests) und manueller Persistence-/Concurrency-Review erfolgreich.
- [x] `code-documentation` angewendet und bestehende Dokumentation gegengeprüft.
- [x] Paket 4 nach vollständiger Verifikation abgeschlossen.

### Paket 5 (P1): WFS-Releasevertrag

**Status:** Abgeschlossen auf `modernization/wfs-release-contract`
(2026-07-17); lokale Commits, nicht gepusht.

**Ziel und Scope:** Ein WFS-Abruf erzeugt genau einen unveränderlichen,
vollständig validierten Pending-Release. Eine spätere Promotion aktiviert exakt
diesen Stand ohne erneuten Download. Anwendung und Rollback bestimmen alle
zusammengehörigen Daten durch einen kleinen atomaren Pointer. Datenbanken,
verteilte Locks, automatische Freigabe und Admin-Oberfläche sind nicht Teil des
Pakets.

**Aktueller Datenfluss:** `fetch_wfs()` lädt genau eine GeoJSON-
FeatureCollection per HTTPX. `validate_feature_collection()` prüft
Vollständigkeit, Feldvertrag, Pflichtwerte, IDs und Geometrien;
`canonical_payload()` erzeugt sortierte `OfferRecord`s und den Dataset-Hash.
`diff_canonical()` vergleicht mit `settings.kb_path`. Ein Check schreibt aktuell
drei feste Dateien unter `runtime/wfs/`. `--promote` lädt erneut vom Live-WFS
und ersetzt danach einzeln `data/wfs/current.geojson`,
`data/canonical/offers.json` und `data/wfs/last_change_report.json`. Die
Anwendung lädt den festen kanonischen Pfad beim Start und nach Auto-Promotion.

**Bestätigte Dead Ends:** Check und Promotion können verschiedene Downloads
verwenden. Ein Fehler zwischen den aktiven Einzeldatei-Writes erzeugt einen
Mischstand. Die feste Tempdatei von `_atomic_json()` kann bei Parallelität
kollidieren. Pending-Artefakte besitzen weder Manifest noch Bindung an
Basisrelease, Dateigröße oder gespeicherte Bytes; ihre Hashes werden vor
Promotion nicht geprüft. Ein Pointer nur im Wartungscode wäre wirkungslos,
solange `main.py` weiter den festen Pfad lädt. Übersetzungen bleiben außerhalb
des atomaren Release: Ihre bestehende Offer-Hashprüfung verwirft veraltete
Einträge bereits sicher, ein zusätzlicher unabhängiger Write würde den
Gesamtvertrag dagegen wieder mehrteilig machen.

**Releaseformat und ID:** `app/wfs_releases.py` kapselt Manifest, Persistenz,
Verifikation, Pointer und lokalen Lock. Aktive Releases liegen unter
`data/wfs/releases/<release-id>/`, Pending-Releases unter
`runtime/wfs/pending/<release-id>/`. Jeder enthält exakt `offers.json`,
`snapshot.geojson`, `diff.json` und `manifest.json`. `WfsReleaseManifest`
(Pydantic, `schema_version=1`, Extra-Felder verboten) enthält Release-ID,
UTC-Erstellung, kontrollierte Quellenkennung/-URL, Datensatzanzahl,
Basisrelease, Validierungsstatus sowie SHA-256 und Bytezahl aller drei
Nutzdateien. Der deterministische Manifesthash umfasst alle Manifestfelder außer
`manifest_sha256` und ist nicht selbstreferenziell. IDs bestehen aus
kontrolliertem UTC-Zeitstempel, zwölf Zeichen Content-Hash und acht zufälligen
UUID-Hexzeichen; WFS-Werte gelangen nicht in Pfade.

**Erstellung, Unveränderlichkeit und Verifikation:** Der Check lädt einmal,
normalisiert einmal und serialisiert die drei Nutzdateien in einen eindeutigen
`.tmp-<UUID>`-Ordner. Manifest und Hashes beziehen sich auf exakt diese Bytes.
Erst nach vollständiger Verifikation wird der Ordner per `os.replace()` unter
der Pending-ID sichtbar; bestehende IDs werden nie überschrieben.
`verify_release()` akzeptiert nur kontrollierte IDs und Wurzeln, prüft exakte
Dateimenge, Verzeichnis-/Manifest-ID, Pydantic-Vertrag, Manifesthash, alle
Dateihashes/-größen, GeoJSON-Grundstruktur, kanonische `OfferRecord`s,
Datensatzanzahl, Content-Hash und `diff.base_release_id`.

**Atomare Aktivierung und Lesen:** Promotion verschiebt einen verifizierten
Pending-Ordner in die unveränderliche Releasewurzel, validiert erneut und
ersetzt zuletzt genau einen Pointer `data/wfs/active_release.json`. Der Pointer
bindet Release-ID und Manifesthash und wird über eindeutige Tempdatei,
`flush()`, `fsync()` und `os.replace()` aktiviert. Ein Fehler lässt den alten
Pointer unverändert; höchstens ein vollständiger inaktiver Release bleibt.
`load_active_knowledge_base()` liest den Pointer einmal, verifiziert den
Release und lädt nur dessen `offers.json`. Bei noch fehlendem Pointer gilt der
bisherige `settings.kb_path` als dokumentierter Legacy-Fallback; ein
beschädigter Pointer fällt niemals auf Pending-Daten zurück.

**Migration, Rollback und Aufbewahrung:** Der vorhandene validierte aktive Stand
kann vor dem ersten Check ohne Netzwerkzugriff idempotent als
`legacy-<content-hash>` übernommen und per Pointer aktiviert werden. Die festen
Dateien bleiben zunächst als Fallback bestehen. Rollback akzeptiert nur eine
kontrollierte ID aus `data/wfs/releases`, verifiziert vollständig und wechselt
nur den Pointer; kein Download und keine Einzeldateikopie. Aktiver und
unmittelbarer Vorgänger werden nicht automatisch gelöscht. Rotation bleibt
Betriebsfolgearbeit.

**Nebenläufigkeit und Logging:** Ein prozessweiter `threading.RLock` schützt
Finalisierung, Migration, Promotion, Rollback und Pointerwechsel, bietet aber
keinen Mehrprozessschutz. Ereignisse sind `wfs.release.created`,
`wfs.release.validation_failed`, `wfs.release.verified`,
`wfs.promotion.started/completed/failed`, `wfs.rollback.completed` und
`wfs.active_release.loaded`. Keine Payloads, Adressen oder Credentials werden
geloggt.

**Interaktionsmetadaten:** `KnowledgeBase` erhält die einmal geladene optionale
`release_id`. `QueryService` übernimmt sie zu Anfragebeginn in
`QueryInteraction`; der zentrale HTTP-Schreibpunkt persistiert sie als
`data_release_id`. Ein späterer Pointerwechsel etikettiert bestehende Antworten
nicht um. Im Legacy-Fallback bleibt das Feld `null`.

**Betroffene Dateien:**

| Datei | Änderung | Grund |
|---|---|---|
| `app/wfs_releases.py` | Manifest, Verify, Release-/Pointerwrites, Rollback | neue kohärente Verantwortung statt weiteres Wachstum von `wfs_sync.py` |
| `app/wfs_sync.py` | einmaliger Check, Migration, releasebasierte CLI/Auto-Promotion | bestehende Normalisierung und Timeouts wiederverwenden |
| `app/kb_loader.py`, `app/main.py` | zentraler pointerbasierter Ladeweg | Pointer im produktiven Start-/Reloadpfad wirksam machen |
| `app/models.py`, `app/service.py`, `app/interactions.py` | tatsächliche Release-ID pro Interaktion | wissenschaftliche Nachvollziehbarkeit |
| `tests/test_wfs_releases.py`, bestehende WFS-/Timeout-/Observabilitytests | Manipulation, Fault Injection, Race, Migration, Rollback, Integration | reale Grenzen statt nur Helpertests |
| bestehende README-/Architektur-/Datenfluss-/Setup-/Testdokumente | Betriebsvertrag und Grenzen | keine parallele Dokumentation |

**Teststrategie:** Fixtures prüfen einen Fetch je Check, Manifestbytes, Hashes,
Counts, Basisrelease und unsichtbare Tempstände. Manipulationen an Nutzdatei,
Manifest, ID und Pointer müssen scheitern. Fault Injection vor/beim
Pointer-Replace belegt den unveränderten aktiven Stand. Threads prüfen eindeutige
IDs, serialisierte Promotion und Lockfreigabe. Pointerwechsel während eines
Ladevorgangs darf keinen Mischstand erzeugen. Migration und Rollback laufen ohne
Fetch. Ein API-/JSONL-Test bindet die tatsächlich geladene Release-ID an die
Antwort. Bestehende Normalisierungs-, Timeout-, Query-, Karten-, Session- und
Packagingtests bleiben Regressionstor.

**Rollbackstrategie:** Implementierungs-, Test- und Dokumentationscommits sind
getrennt revertierbar. Solange die Legacy-Dateien bestehen, kann der Pointer-
Ladeweg ohne Datenmigration zurückgenommen werden. Releaseordner werden nicht
automatisch gelöscht. Operativer Rollback validiert einen früheren Release und
wechselt atomar nur den Pointer.

**Verifikationsergebnis:** 43 fokussierte WFS-Release-, WFS-Sync-, Timeout- und
Observabilitytests sowie die Gesamtsuite mit 153 Tests bestanden in rund fünf
Sekunden. `python -m compileall -q app`, `python -m app --help`,
`python -m app.wfs_sync --help`, der read-only `--list`-Smoke und
`git diff --check` waren erfolgreich. Fault Injection belegte unveränderten
Pointer bei Replace-Fehler und wiederholbare Promotion des bereits vollständig
verschobenen Releases. Manipulationen an Manifest und jeder Nutzdatei,
unkontrollierte IDs, Zusatzdateien und beschädigte Pointer wurden abgewiesen.
Migration, Rollback, eindeutige parallele Erstellung, einmaliges Pointerlesen
und `data_release_id` im tatsächlichen API-/JSONL-Pfad sind getestet. Timeout-
Tests bestätigen den unveränderten aktiven Stand ohne Runtime-Artefakte im Diff;
`git check-ignore` deckt Pending-Releases und Interaktionsdaten ab.

**Strukturentscheidung:** `app/wfs_releases.py` bleibt mit weniger als 400
Zeilen auf die neue Persistenzverantwortung begrenzt. `app/wfs_sync.py` liegt
weiter über 400 Zeilen, enthält aber weiterhin nur Transport, fachliche
Validierung/Normalisierung, Migration und die bestehende Wartungs-CLI. Eine
weitere Aufteilung wäre ein allgemeines Refactoring außerhalb des
Releasevertrags; die transaktionale Verantwortung wurde bereits kohärent
extrahiert.

**Fortschritt:**

- [x] sauberer Paket-4-Stand und neuer lokaler Branch geprüft.
- [x] Dokumentation, Datenpfade, Loader, CLI, Tests, Hashes und Timeouts geprüft.
- [x] Race Conditions, Releaseformat, Migration, Pointer und Rollback geplant.
- [x] Releasevertrag und produktiver Ladeweg implementiert.
- [x] fokussierte und vollständige Verifikation erfolgreich (153 Tests).
- [x] `code-documentation` angewendet und Dokumentation gegengeprüft.
- [x] Paket 5 abgeschlossen.

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
