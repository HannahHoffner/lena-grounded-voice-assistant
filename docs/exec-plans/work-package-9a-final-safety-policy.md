# Arbeitspaket 9A: abschließende Safety- und Fehlerpolitik

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-03
- Last updated: 2026-08-03

## Objective

LENA behandelt erkannte und nicht sicher auszuschließende unmittelbare
Gefahrenlagen vor Scope, Fachdialogen, Auswahl, Formulierung und Karten. Der
LLM-Interpreter bleibt die primäre sprachliche Klassifikation; eine eng
begrenzte vorgelagerte Prüfung schützt zusätzlich nur eindeutig formulierte
Akutfälle. Alle verbindlichen Entscheidungen, die Nummer 112, sichtbare
Safety-Texte, Kartenleere und Fehlerfallbacks bleiben deterministisch.

## Acceptance contract

- [x] 112 ist ein versionierter zentraler Policyfakt mit BBK- und EU-Referenz;
  WP9A ergänzt keine weitere Notfall- oder Krisennummer.
- [x] Die Reihenfolge ist Eingabevalidierung, eng begrenzte vorgelagerte
  Prüfung, Interpreter/Vertragsvalidierung, Safety-Policy und erst danach Scope,
  Dialog, CandidateSelector, LLM-Selector, Formulator und Infrastruktur.
- [x] `detected` beendet die Anfrage mit zentralem 112-Text, leeren Karten und
  Markern sowie ohne jeden nachgelagerten Provider- oder Angebotspfad.
- [x] Ein erstmaliges `uncertain` eröffnet einen atomaren, fingerprintgebundenen
  Safety-Dialog; Ja und Unsicher führen zu 112, nur ein eindeutig validiertes
  Nein öffnet den ursprünglichen strukturierten Bedarf wieder.
- [x] Unverständliche Safety-Antworten erhalten höchstens einen erneuten
  Versuch; Themenwechsel und Sprachwechsel umgehen den Dialog nicht.
- [x] Interpretertimeout, HTTP-/JSON-/Schema-/Vertragsfehler, Budgeterschöpfung
  und Nichtverfügbarkeit fallen geschlossen auf einen lokalisierten technischen
  Text mit bedingtem 112-Hinweis zurück; keine lexikalische Fachauswahl bleibt.
- [x] Safety ist stärker als Out-of-Scope, Fachdialog, Hilfebus, Toilette,
  Trinkwasser, allgemeine Hilfe und Sessionfortsetzung.
- [x] API, Session, Frontend, TTS, Health und minimierte Interaktionsmetadaten
  bilden den Safety-Zustand nachvollziehbar ab, ohne Risikoprofil oder
  Gefahrenfreitext zusätzlich zu speichern.
- [x] Deutsch bleibt höchstens `review_pending`, EN/PL/RO/RU bleiben `machine`;
  112 bleibt in jeder sichtbaren Safety-Antwort unverändert.
- [x] Ein versionierter synthetischer Szenariokatalog deckt in allen fünf
  Sprachen akut, unklar, nicht akut, Dialog, Providerfehler und Regressionen ab.
- [x] WP1–WP8B, Hilfebuspriorität, fachliche Angebote, Quellen, Thesis und
  Präsentation bleiben außerhalb der erforderlichen Safety-Integration
  unverändert; WP9B und Live-Tests werden nicht begonnen.
- [x] Sämtliche Tests und Smokes verwenden nur Test-Doubles; externe LLM-, STT-,
  TTS-, WFS-, Toiletten- und Trinkbrunnenaufrufe bleiben null.

## Scope

### In scope

- Zentrale Policy für `detected`, `uncertain` und Interpreterausfall.
- Enger, fünfsprachiger und versionierter Defense-in-Depth-Preflight.
- Erweiterung des einzigen vorhandenen Dialog- und Sessionvertrags um
  `acute_risk_confirmation`.
- Zentrale mehrsprachige Safety-Ressourcen, API-Antworttyp, Kartenleere,
  Frontendsemantik, TTS-Bindung, Health und minimierte Metadaten.
- Synthetischer Safety-Szenariokatalog, Tests und unmittelbar betroffene
  bestehende Dokumentation.

### Out of scope

- Diagnose, psychologische oder medizinische Bewertung, Risikoscore,
  automatische Alarmierung, Standortübermittlung oder Anrufauslösung.
- 110, 116117, Telefonseelsorge, lokale Krisendienste, Krankenhäuser,
  Hilfebustelefon oder andere noch nicht freigegebene Krisenkontakte.
- Live-Provider- oder Sprachqualitätstest, menschliche Sprach-/Hörfreigabe,
  Produktivfreigabe, WP9B oder nachfolgende Pakete.
- Allgemeine Refactorings, fachliche Kandidatenänderungen, neue Infrastruktur,
  Thesis- oder Präsentationsdateien.

## Repository review

### WP8B-Eingangskontrolle

Die zwingende read-only Eingangskontrolle ist bestanden:

| Prüfung | Nachweis | Ergebnis |
|---|---|---|
| Kombinierte Wasserkarte | `select_drinking_water_results()` plus `drinking_water_map_data()`; einmaliger read-only Integrationsassert | zwei positiv belegte soziale Wasserresultate und 21 Brunnen ergeben 23 Ziele mit gültiger Geometrie |
| Reihenfolge | `app/infrastructure_results.py:176-260`, bestehender Test `test_water_selection_combines_only_positive_social_evidence_and_approved_fountains` | fachliche Zulässigkeit vor Aufnahme, Mandatory vor Rest, Brunnen nur in belegter Saison, Rest nach HBF-Luftlinie und stabiler ID |
| Saisonfakten | `DrinkingFountainRecord.season_start/season_end`, Bootstrap und Saisonprüfung | ausschließlich `april`/`october`; keine erfundenen Tagesdaten |
| Bestehende Suite | `python -m pytest tests/test_drinking_fountains.py -q` | 29 bestanden |

Der erste Integrationsassert verwendete irrtümlich nur Bindestrich-Präfixe und
erkannte die gültige namespacierte Hilfebus-Standort-ID `21:hbf-west` nicht.
Nach Korrektur des read-only Asserts war die reale 23-Ziele-Projektion grün; es
liegt kein WP8B-Defekt vor.

### Current behavior

| Ausgangslage | aktuelles Verhalten | gewünschtes Verhalten | Änderung erforderlich |
|---|---|---|---|
| Eindeutige Akutformulierung vor Interpreter | keine vorgelagerte Safety-Prüfung vorhanden | kleine versionierte Defense-in-Depth-Prüfung nur für explizite unmittelbare Hochrisikophrasen | ja |
| Interpreter `detected` | früher Template-Return mit lokalisiertem `fallback.acute_risk`; vor Scope/Selector/Formulator, Karten leer | versionierter Policyreturn mit 112, explizitem API-Typ und zentraler Metadatenpflege | ja, vorhandenen Stop wiederverwenden |
| Interpreter `uncertain` | wird ignoriert und kann in Scope, Dialog oder Angebotsauswahl laufen | eigener Safety-Dialog vor jedem Fachpfad | ja, sicherheitskritisch |
| Interpretertimeout/HTTP/JSON/Schema/Vertrag/Budget bei konfiguriertem Provider | technischer Text ohne 112; aktiver Fachdialog wird wieder geöffnet | fail-closed technischer Text mit bedingtem 112-Hinweis, keine Ergebnisse/Providerfolge | ja |
| Interpreter nicht konfiguriert | lexikalische Interpretation kann reguläre Angebote liefern | fail-closed technischer Fallback, keine lexikalische Fachklassifikation | ja |
| Safety und Out-of-Scope | `detected` gewinnt bereits; `uncertain` nicht | alle Safety-Entscheidungen gewinnen | ja für `uncertain`/Fehler |
| Safety und offener Fachdialog | `detected` beendet/ersetzt Dialog; Fehler öffnet Fachdialog wieder | erkanntes/ungeklärtes Risiko beendet oder ersetzt Fachdialog durch Safety-Zustand | ja |
| Session | Dialog atomar, TTL/Fingerprint/Claim vorhanden; Safety-Freitext landet als normaler Turn | denselben Store nutzen, keinen zweiten Zustand; Safety-Eingaben redigiert und kein Risikoprofil | ja |
| TTS | nur letzter Sessiontext gleicher Sprache; 112 zentral in Einzelziffern normalisiert | beibehalten und für neue Safety-Texte testen | Tests/Dokumentation |
| Frontend | Karten werden vor Request und beim Rendern geleert; Dialogbuttons nativ; keine Safety-Kennzeichnung | explizite nicht nur farbliche Safety-Kennung, Fokus ohne doppelte Live-Ausgabe | ja |
| Interaktionsprotokoll | vollständige Query plus Boolean `acute_risk_detected` | minimale strukturierte Safety-Metadaten; Safety-Freitext nicht zusätzlich speichern | ja |
| Health | Interpreter-/Dialog-/Textversionen, kein Safety-Vertrag | redigierte Policy-, Dialog-, Sprach- und Fallbackinformationen | ja |

### Relevant architecture and data flow

`POST /api/query` validiert Körper und `QueryRequest` → `QueryService.query()`
beansprucht atomar einen gegebenenfalls offenen Dialog → `_query_core()` startet
das monotone LLM-Budget und ruft `interpret_query()` → Pydantic validiert den
dreiwertigen Risikostatus → bisher existiert nur ein früher `detected`-Return →
danach Scope, Dialogmerge, Infrastruktur oder Candidate/Selector/Formulator →
`query()` persistiert Turn, Karten und Trace → `main.py` schreibt das lokale
Interaktionspaar. TTS akzeptiert ausschließlich den letzten sichtbaren
Sessionantworttext derselben Sprache.

WP9A setzt eine einzige zentrale Safety-Policy zwischen Eingabe und allen
Fachpfaden. Der vorhandene Dialog- und Sessionstore bleibt alleinige
Persistenzschicht; der Formulator erhält niemals Safety-Texte oder -Fakten.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Dreiwertiger Risikostatus | `app/interpreter.py::AcuteRiskStatus` | unverändert als primäres externes Signal verwenden |
| Strikter Interpreterparser | `app/providers/llm.py::interpret_query` | unverändert fail-closed verwenden; nur Promptversion erhöhen |
| Einziger Dialogzustand | `app/dialogue.py::DialogState` | versioniert um Safety-Typ und minimalen strukturierten Resume-Kontext erweitern |
| Atomare Claim-/TTL-/Fingerprintlogik | `app/sessions.py::SessionStore` | ohne zweiten Store wiederverwenden |
| Zentrale Policyfakten | `app/policy_facts.py` | 112 um Version und Quellenreferenzen ergänzen |
| Anwendungstexte | `app/application_texts.py`, Paket-JSON | Safety-Texte/Labels in bestehender fünfsprachiger Ressource ergänzen |
| API-Antwort und Trace | `app/models.py`, `app/interactions.py`, `app/main.py` | Antworttyp und minimale Safety-Metadaten ergänzen |
| TTS-Bindung | `app/main.py`, `app/speech.py` | unverändert erhalten; neue Texte und 112-Normalisierung testen |
| Providerisolation | `tests/conftest.py` | unverändert; jeder Netztransport muss Tests fehlschlagen lassen |

### Existing tests and commands

- `python -m pytest tests/test_drinking_fountains.py -q` → 29 bestanden.
- Ausgangslauf der 13 relevanten Safety-/Interpreter-/Dialog-/API-/Auswahl-/
  Infrastrukturmodule: 427 bestanden, zwei bereits vor WP9A vorhandene Fehler.
- Baselinefehler 1: `test_tts_rejects_an_older_answer_after_a_new_session_turn`
  verwendet zwei aktuell identische Templateantworten; der nur an sichtbaren
  Text gebundene TTS-Vertrag kann sie nicht unterscheiden.
- Baselinefehler 2:
  `test_service_passes_only_validated_food_selection_to_formulator` erwartet
  eine andere Reihenfolge als die vom Test-Selector ausdrücklich umgedrehte und
  vom aktiven Pfad weitergereichte Auswahl.
- Relevante Module: `tests/test_safety.py`, `tests/test_interpreter.py`,
  `tests/test_dialogue.py`, `tests/test_sessions.py`,
  `tests/test_session_persistence.py`, `tests/test_provider_timeouts.py`,
  `tests/test_api.py`, `tests/test_observability.py`,
  `tests/test_frontend_security.py`, `tests/test_provider_isolation.py`.

### Working tree considerations

Branch `maintenance/repository-cleanup`, Ausgangscommit
`9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`. Sämtliche vorhandenen Änderungen
aus WP1–WP8B gehören der Nutzerin. Es existiert keine anwendbare `AGENTS.md`-
Datei. `.env`/`.env.local` wurden nicht gelesen. Änderungen dürfen nur in den
aufgelisteten WP9A-Hunks erfolgen; keine bestehende Änderung wird zurückgesetzt
oder breit formatiert.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| `uncertain` wie `detected` ohne Rückfrage behandeln | Dreiwertiger Vertrag und ausdrücklicher Dialogauftrag | unnötige Notrufantworten und Verlust kontrollierter Verneinung | eigener begrenzter Safety-Dialog | Ja/Nein/Unsicher/Text/STT/Retry-Tests |
| Neue Safety-Session neben `DialogState` | atomarer Store und Fingerprint existieren bereits | konkurrierende Zustände, Replay-/TTL-Lücken | `acute_risk_confirmation` als normaler versionierter Dialogtyp | Persistenz-, Claim-, Replay- und Fingerprinttests |
| Einzelwörter als Preflight | Nutzer untersagt Pseudointerpretation; hohe False-Positive-Gefahr | historische/metaphorische Aussagen blockiert | nur explizite Person+Handlung+Unmittelbarkeit; negatives Inventar | fünfsprachige Positiv-/Negativtests |
| `not_detected` bei neuer Fachfrage als Safety-Nein lesen | Safety-Dialog darf Themenwechsel nicht akzeptieren | Toilette/Angebot umgeht offene Safety-Frage | Resume nur bei zum offenen Dialog kompatibler, validierter Verneinung; sonst Retry/112 | Themenwechseltests |
| Interpreterfehler lexikalisch klassifizieren | aktueller `_lexical_fallback_interpretation()` setzt selbst `uncertain` und läuft weiter | ungeprüfte Gefahr erreicht Angebote | aktiven Legacyfallback entfernen; immer technischer Safety-Fallback | Timeout-/HTTP-/JSON-/Budget-/Provider-unavailable-Tests |
| Safety-Text durch Formulator erzeugen | Formulatorprompt kennt keine 112; LLM dürfte Nummer/Text verändern | unkontrollierte Kriseninformation | ausschließlich zentrale Ressourcen plus Policyfakt | Providerdouble muss unaufgerufen bleiben |
| Alte Karten nur serverseitig leeren | Frontend besitzt Zustand und Leaflet-Layer | vorherige Orte bleiben sichtbar | bestehendes `clearMap()` plus Antworttyp- und Frontendregression | Safety nach Angebots-/Toiletten-/Brunnenantwort |
| Vollständigen Safety-Freitext weiter in Session/JSONL speichern | bestehender Store speichert normale Query vollständig | zusätzliche sensible Langzeitspur | Safety-Eingabe durch lokalisierten Sessionhinweis bzw. technischen Logtoken ersetzen | Persistenz-/Observabilitytests |
| Weitere Notfallkontakte ergänzen | keine fachliche Freigabe in WP9A | falsche oder unkuratierte Eskalation | einzig 112, Quellen im Policyfakt | Ressourcen-/Promptinventar |

## Recommended approach

Eine neue kleine `app/safety.py` bündelt Policyversion, enge Preflightprüfung,
zulässige Safety-Pfade und validierte Ressourcenausgabe. `QueryService` ruft sie
vor und unmittelbar nach dem bestehenden Interpreter auf. Der vorhandene
Dialogvertrag erhält genau einen Safety-Typ und speichert nur den strukturierten
ursprünglichen Bedarf/Faktenkontext, keinen Risikofreitext. Dadurch bleiben LLM-
Interpretation und deterministische Systementscheidung getrennt und es entsteht
weder ein zweiter Router noch eine zweite Sessionverwaltung.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Nur den bestehenden `detected`-Return erweitern | lässt `uncertain` und Interpreterausfälle offen |
| Jede unklare Eingabe sofort als Akutgefahr behandeln | würde reguläre kurze Hilfeanfragen unnötig blockieren |
| Freie Modellbegründung oder Risikoscore ergänzen | für Systementscheidung unnötig, sensibel und nicht verlässlich kalibrierbar |
| Deterministische mehrsprachige Vollklassifikation | zu fragil und widerspricht der Rolle des Interpreters |
| Hilfebus oder lokale Dienste als Safety-Ergänzung | nicht als Notfallquelle freigegeben und ausdrücklich ausgeschlossen |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/safety.py` | Create | zentrale Policy, Preflight, Textvalidierung und Szenariovertrag | hoch, sicherheitskritisch; unter 400 Zeilen |
| `app/policy_facts.py` | Modify | versionierter 112-Fakt und zwei offizielle Referenzen | klein |
| `app/interpreter.py` | Modify | präzisierter Risikoprompt und Safety-Dialogkontext | hoch, externer Promptvertrag |
| `app/dialogue.py`, `app/dialogue_flow.py` | Modify | Safety-Dialogtyp, Choices, Retry und strukturierter Resume-Kontext | hoch |
| `app/service.py` | Modify | verbindliche Priorität, Fehlerfallback und Entfernung aktiver lexikalischer Umgehung | sehr hoch; große bestehende Orchestrierung |
| `app/models.py` | Modify | expliziter öffentlicher Antworttyp und Safety-Trace | mittel |
| `app/interactions.py`, `app/main.py` | Modify | minimierte Metadaten, Redaktion und Health | mittel |
| `app/application_texts.py`, `app/resources/bootstrap/i18n/application_texts.json` | Modify | fünfsprachige zentrale Safety-Texte und Integritätsprüfung | hoch, sichtbare Safety-Daten |
| `app/resources/bootstrap/safety/scenarios.json` | Create | versionierter synthetischer Fünfsprachenkatalog | Daten |
| `app/static/app.js`, `app/static/index.html`, `app/static/styles.css` | Modify | Kennzeichnung, Fokus, Alertsemantik und Kartenresetregression | mittel |
| `tests/test_safety.py`, `tests/test_safety_policy.py` | Modify/Create | Policy-, Dialog-, Mehrsprachigkeits- und Fehlerkatalog | hoch |
| betroffene Interpreter/Dialog/Session/API/Health/Frontend/Packagingtests | Modify | geschlossene Versions- und Regressionsverträge | mittel |
| README und unmittelbar betroffene `docs/*.md` | Modify | implementierte Safety- und Fehlergrenzen | Dokumentation |

## Milestones

### Milestone 1: Review and design

- [x] Skills, Anlage, Repositoryanweisungen, Status, Dokumentation und WP1–WP8B-Pfade prüfen.
- [x] WP8B-Eingangskontrolle ohne Repositoryänderung bestehen.
- [x] Safety-Kontrollfluss, Verträge, Providerfehler, Session, TTS, Frontend, Logging und Health verfolgen.
- [x] Kontrollflusstabelle, Reuse-Entscheidungen und Dead Ends dokumentieren.

Evidence: 29 WP8B-Tests, 23-Ziele-Integrationsassert, Quellpfade und Tabelle oben.

### Milestone 2: Implementation

- [x] Zentrale Safety-Policy, Policyfakt und Preflight implementieren.
- [x] Interpreter-, Dialog-, Session- und Orchestrierungspfad integrieren.
- [x] API, I18n, Frontend, TTS-Nachweis, Health und minimierte Metadaten ergänzen.
- [x] Synthetischen Szenariokatalog und fokussierte Tests implementieren.
- [x] Plan mit tatsächlichen Entdeckungen aktualisieren.

### Milestone 3: Verification

- [x] Fokussierte Safety-, Interpreter-, Dialog-, Session-, API-, TTS- und Frontendtests ausführen.
- [x] Fünfsprachige Szenarien, Injection, Providerfehler und Budget prüfen.
- [x] Candidate-/Selector-/Formulator-, Toiletten- und Brunnenregressionen ausführen.
- [x] Vollständige Suite, Python-Syntax und Providerisolation ausführen; Node.js war lokal nicht verfügbar.
- [x] Wheel/sdist, sdist→Wheel, Clean-Install und providerfreien Template-Smoke ausführen.
- [x] Finalen Diff anhand `REVIEW_TEMPLATE.md` und `git diff --check` prüfen.

### Milestone 4: Documentation

- [x] `code-documentation` auf den finalen Safety-Diff anwenden.
- [x] Bestehende Dokumente und Safety-/Fehlerpolitik gegen Runtime und Tests prüfen.
- [x] Betroffene Prüfungen nach Dokumentation erneut ausführen.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Safety/Interpreter | `python -m pytest tests/test_safety.py tests/test_safety_policy.py tests/test_interpreter.py -q` | detected/uncertain/not_detected und Promptvertrag grün |
| Dialog/Session/API | `python -m pytest tests/test_dialogue.py tests/test_sessions.py tests/test_session_persistence.py tests/test_api.py -q` | atomarer Safety-Dialog, Sprache/Thema/TTL/Replay grün |
| Fehler/Budget/TTS | `python -m pytest tests/test_provider_timeouts.py tests/test_formulation.py tests/test_observability.py -q` | fail-closed plus 112, gebundene TTS-Ausgabe, minimiertes Log |
| Fachregression | Candidate-, Selector-, Formulator-, Toiletten- und Trinkbrunnentests | kein Safety-Falschabbruch in Normalpfaden |
| Providergrenze | `python -m pytest tests/test_provider_isolation.py -q` | null externe Transporte |
| Full suite | `python -m pytest -q` | grün oder ausschließlich dokumentierte unveränderte Baselinefehler |
| Syntax | `python -m compileall -q app tests`; `node --check` falls vorhanden | keine Syntaxfehler |
| Distribution | `python -m build`; Packagingtests | neue Module/Ressourcen in Wheel und sdist, Clean-Install grün |
| Diff | `git diff --check`; Hunkreview gegen WP8B-Stand | keine Fremdhunks oder Whitespacefehler |

## Rollback and recovery

WP9A migriert keine fachlichen Quelldaten und erzeugt keine externen
Nebenwirkungen. Ein veralteter Dialogvertrag wird vom vorhandenen validierenden
Sessionloader verworfen; der Store bleibt atomar. Die Änderung kann durch
Rücknahme ausschließlich der WP9A-Hunks und der neuen paketierten
Safety-Ressource entfernt werden. Bereits vorhandene WP1–WP8B-Hunks bleiben
unangetastet. Tests schreiben nur in temporäre Verzeichnisse.

## Progress log

- 2026-08-03 — Vollständige WP9A-Anforderung, beide Skills und Templates gelesen.
- 2026-08-03 — Arbeitsbaum, Dokumentation, Runtimepfad und relevante WP1–WP8B-
  Implementierungen read-only geprüft; keine `AGENTS.md` vorhanden.
- 2026-08-03 — WP8B-Gate mit 29 Tests und kombiniertem 23-Ziele-Assert bestanden.
- 2026-08-03 — Aktuellen Safety-Kontrollfluss und zwei unabhängige
  Ausgangstestfehler dokumentiert; Plan als erste WP9A-Datei angelegt.
- 2026-08-03 — Zentrale 112-Policy, enger fünfsprachiger Preflight,
  Safety-Dialog, fail-closed Interpreterfehler, API/Session/Frontend/Health und
  redigierte Interaktionsmetadaten umgesetzt.
- 2026-08-03 — Synthetischen fünfsprachigen Szenariokatalog und umfassende
  Safety-, Fehler-, Prioritäts-, Persistenz-, TTS- und Packagingregressionen ergänzt.
- 2026-08-03 — Fokussierte Safety-/Provider-Isolationstests (32), vollständige
  Suite und Packagingtests (7) grün; sdist und Wheel erfolgreich gebaut,
  `compileall` und `git diff --check` bestanden. Node.js war nicht verfügbar.

## Decision log

- Decision: Keine neue Risikobegründung im Interpretervertrag.
  - Context: Der dreiwertige Status trägt detected/uncertain/not_detected; freie
    Gründe würden sensible, nicht benötigte Modellinhalte erzeugen.
  - Choice: Prompt und offener Dialogkontext präzisieren, Ausgabevertrag klein halten.
  - Consequences: Menschliche Sprachqualität bleibt später separat zu evaluieren.
- Decision: Safety-Dialog in `DialogState`, nicht in einer zweiten Sessionstruktur.
  - Context: Claim, TTL, Fingerprint und Replay-Schutz existieren.
  - Choice: versionierter neuer Dialogtyp mit minimalem Resume-Kontext.
  - Consequences: alte Dialogzustände werden kontrolliert verworfen.
- Decision: Interpreterausfall beendet fachliche Auswahl auch im Templatebetrieb.
  - Context: Ohne validierte Risikoklassifikation ist eine Angebotsantwort nicht
    sicher freigabefähig; lexikalischer Fallback setzt selbst `uncertain` und
    ignoriert diesen Zustand bisher.
  - Choice: technischer Safety-Fallback mit bedingter 112-Zeile.
  - Consequences: providerloser Template-Smoke prüft künftig den sicheren
    Fehlerpfad statt einer fachlichen Antwort.

## Discoveries

- Der vorhandene `detected`-Stop ist korrekt vor Scope und Auswahl angeordnet,
  aber `uncertain` besitzt keinen Verbraucher.
- Eine vorgelagerte deterministische Safety-Prüfung ist im aktiven Repository
  nicht implementiert; frühere Dokumentation beschrieb nur die LLM-Stufe.
- Bei fehlender Providerkonfiguration wird aktuell `_lexical_fallback_interpretation()`
  verwendet, obwohl sie `acute_risk_status=uncertain` setzt; dieser Status wird
  danach nicht ausgewertet.
- Frontend und Backend leeren Karten bereits grundsätzlich, besitzen aber noch
  keinen expliziten Safety-Antworttyp oder nicht-farblichen Alertzustand.
- TTS ist bereits an den letzten sichtbaren Sessiontext und die Sprache gebunden;
  112 wird zentral je Sprache als einzelne Ziffern normalisiert.

## Final verification summary

- Acceptance requirements: vollständig erfüllt; WP9B wurde nicht begonnen.
- Tests: WP8B-Gate 29 grün; Safety/Provider-Isolation 32 grün; vollständige
  Suite 100 % grün; Packaging/Clean-Install 7 grün.
- Build: `python -m build` erzeugte sdist und Wheel; der Packagingtest baute das
  Wheel aus der sdist neu und prüfte den Clean-Install samt Template-Smoke.
- Syntax/Diff: Python-Compileall und `git diff --check` grün; Node.js war für
  einen zusätzlichen `node --check` nicht installiert.
- Manual verification: Safetypriorität, zentrale 112-Referenzen, Kartenleere,
  Session-/Logredaktion und fünfsprachige Ressourcen geprüft; Provideraufrufe null.
- Documentation: README, Architektur, Datenfluss, Konfiguration, Setup, Tests
  und die neue Safety-/Fehlerpolitik entsprechen dem implementierten Pfad.
- Residual risks: reale LLM-Klassifikations-, Übersetzungs- und akustische
  Qualität bleiben ohne Live-/Humanreview ungeprüft; die enge Vorprüfung ist
  bewusst kein vollständiger Gefahrenklassifikator; produktive Krisen- und
  Datenschutzprozesse liegen außerhalb WP9A.
