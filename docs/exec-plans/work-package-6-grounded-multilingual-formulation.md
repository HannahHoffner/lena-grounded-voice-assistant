# Arbeitspaket 6: Faktengebundene mehrsprachige Antwortgenerierung

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-01
- Last updated: 2026-08-01

## Objective

LENA erzeugt reguläre, Verweis-, Kein-Treffer-, Hilfebus- und eng gebundene
Out-of-Scope-Antworten aus einem versionierten Faktenpaket. Jeder sichtbare
Modellsatz trägt Angebotsfakten oder freigegebene Policyreferenzen. Das Backend
validiert Vertrag, Kartenbindung, Sprache, einfache formale Grenzen und robuste
Groundingmerkmale atomar. Fehler fallen auf lokalisierte, rollenrichtige
Templates zurück. Ein requestlokales monotones Gesamtbudget begrenzt die drei
LLM-Stufen; TTS akzeptiert nur den zuletzt gespeicherten sichtbaren Antworttext.

## Acceptance contract

- [x] Evidence-Vertrag 1 enthält nur finale Runtime-Angebote, opake stabile Faktenreferenzen und freigegebene Policies.
- [x] Formulatorvertrag 2 liefert ausschließlich 1 bis 3 kurze belegte Sätze, Zielsprache und finale Karten-IDs.
- [x] Fakten-, Rollen-, Karten-, Sprach-, Längen-, Markdown-/HTML-, ID- und klare Mischsprachenfehler werden atomar abgelehnt.
- [x] Kapazitäts-, Echtzeit-, erfundene Kontakt-, Adress-, Zeit-, URL-, Alters-, Zielgruppen- und Leistungsbehauptungen lösen redigierte Fehler aus, soweit strukturell oder robust lexikalisch erkennbar.
- [x] Out-of-Scope, kein verifiziertes Ergebnis und unklare Hilfe besitzen begrenzte LLM-Verträge mit lokalisiertem Templatefallback; Dialog, Systembeschreibung und Akutgefahr bleiben deterministisch.
- [x] Interpreter, Selector und Formulator teilen ein kumulatives monotones externes LLM-Zeitbudget; kein Stufenaufruf überschreitet Restbudget oder eigene Grenze.
- [x] TTS verwendet ausschließlich den zur aktiven Session gespeicherten finalen Antworttext; Metadaten gelangen nicht in die Synthese.
- [x] Kartenübersetzungen können kuratierte Kontakte, Adressen, Zeiten oder andere geschützte operative Tokens nicht überschreiben.
- [x] Health und Interaktionsprotokoll enthalten nur Versionen, Antworttyp, redigierte Status- und Mengendaten.
- [x] Candidate-/Dialog-/Selector-/Safety-/Runtime-Invarianten sowie IDs 1 bis 4 bleiben unverändert wirksam.
- [x] WP7, neue Infrastrukturimporte, Distanzranking und abschließende Safety-Policy bleiben unberührt.

## Scope

### In scope

- Formulator-Evidence, Satzvertrag, Grounding und lokalisierte Fallbacks.
- Normale, Referral-, Out-of-Scope-, Kein-Treffer- und Hilfebus-Formulierung.
- Kumulatives requestlokales LLM-Budget und stufenspezifische Restzeit.
- TTS-Bindung an die persistierte sichtbare Antwort.
- Schutz operativer Kartenfakten gegen Übersetzungsüberschreibung.
- Health, redigierte Interaktionsmetadaten, Tests und bestehende technische Dokumentation.

### Out of scope

- Formale fachliche oder sprachliche Freigabe vorhandener Übersetzungen.
- Neue Toiletten-, Trinkbrunnen- oder Geodaten und allgemeines Distanzranking.
- Neue Policy für `acute_risk_status=uncertain` oder Interpreterausfälle.
- Reale Provideraufrufe, Thesis- oder Präsentationsänderungen.

## Repository review

### Current behavior

`QueryService._query_core()` übergibt nach WP5 maximal vier finale
`OfferRecord`s und einen redigierten Routingkontext an
`BlabladorProvider.formulate_answer()`. Der Provider baut eine flache
`FormulatorOfferView`, fordert `{answer, card_ids}`, toleriert Markdown-Fences
und prüft hauptsächlich Zahlen, Kontakte, Zeiten und einige
Verfügbarkeitsphrasen. Sätze besitzen keine Fakten- oder Policybindung;
Rollenbehauptungen sind nur promptseitig abgesichert.

Out-of-Scope, Kein-Treffer, Hilfebus, Akutgefahr, Dialoge und
Systembeschreibung sind aktuell rein deterministische frühe Rückgaben. Bei
normalen Ergebnissen entscheidet der Formulator über optionale Karten;
Mandatory wird seit WP5 serverseitig ergänzt. Es bestehen drei Einzelgrenzen
von 15, 10 und 30 Sekunden, aber kein Gesamtbudget.

`/api/speech/synthesize` akzeptiert beliebigen Text vom Client. Das Frontend
verändert vor dem Senden zusätzlich deutsche und englische Zeitangaben. Damit
ist nicht technisch erzwungen, dass ausschließlich der validierte sichtbare
Antworttext synthetisiert wird.

Kartenübersetzungen werden hashgebunden geladen, dürfen über
`TRANSLATED_FIELDS` aber derzeit auch Telefonnummern, Öffnungs-/Standzeiten und
Notizen ersetzen. Die Adresse wird bereits immer aus der kuratierten
Runtime-Sicht wiederhergestellt.

### Relevant architecture and data flow

- API: `app/main.py:answer_query()` -> `app/service.py:QueryService.query()`.
- Interpreter/Selector: `app/providers/llm.py` mit getrennten Verträgen und
  Timeouts; Aufrufsteuerung in `QueryService._query_core()`.
- Finale Menge: `SelectionOutcome.final_ids` -> Runtime-Records -> Formulator.
- Karten: `app/i18n.py:localize_offer_card()`; Marker: `app/maps.py`.
- TTS: Frontend `speakText()` -> `/api/speech/synthesize` ->
  `SpeechSynthesizer.synthesize()`.
- Session: `SessionStore` speichert den sichtbaren Antworttext atomar im letzten
  `ChatTurn` und ist bereits an den Runtime-KB-Fingerprint gebunden.
- Beobachtbarkeit: `QueryInteraction` -> `InteractionRecord`; Health in
  `app/main.py`.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Strikte Pydantic-Verträge | `app/interpreter.py`, `app/llm_selection.py` | Für Evidence und Satzvertrag fortführen |
| Finale `SelectionOutcome` | `app/llm_selection.py` | Einzige Quelle der erlaubten Angebotsmenge |
| Rollen und Reason Codes | `app/candidate_contract.py` | Evidence-Rollen ohne neue Fachlogik übernehmen |
| Runtime-Positivliste | `OfferRecord` und bisheriger `FormulatorOfferView` | Durch engeren Evidence-Builder aus freigegebenen Feldern ersetzen |
| Karten-/Markerpfad | `app/i18n.py`, `app/maps.py` | Beibehalten; operative Überschreibungen härten |
| SessionStore | `app/sessions.py` | Letzte sichtbare Antwort für TTS-Bindung wiederverwenden |
| Stage-Timeouter | `BlabladorProvider._request_with_timeout()` | Mit vom Service berechnetem Restbudget aufrufen |
| Lokalisierte Dialogressourcen | `app/resources/bootstrap/dialogue/messages.json` | Dialogfragen und Hilfebus-Template unverändert weiterverwenden |

### Existing tests and commands

- Formulator/Provider/API: `tests/test_api.py`, `tests/test_provider_timeouts.py`
- Candidate/Selector/Dialog: `tests/test_candidates.py`,
  `tests/test_llm_selection.py`, `tests/test_dialogue.py`
- Safety/TTS: `tests/test_safety.py`, `tests/test_request_boundaries.py`
- I18n/Kuration: `tests/test_curation.py`, `tests/test_i18n.py`
- Observability/Packaging: `tests/test_observability.py`, `tests/test_packaging.py`
- WP5-Ausgangssuite: 364 Tests erfolgreich.

### Working tree considerations

Branch `maintenance/repository-cleanup`, Ausgangscommit
`9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`. Die freigegebenen, nicht
committeten Arbeitspakete 1 bis 5 bleiben Nutzerbestand und werden weder
zurückgesetzt noch pauschal formatiert. Kein `AGENTS.md` wurde gefunden.
WP6-Hunks bleiben auf Formulation, Budget, Provider-/Serviceintegration,
TTS-Bindung, I18n-Schutz, Health/Logging, Tests und technische Dokumentation
begrenzt.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| `fact_ids` ungeprüft vertrauen | Modelltext und Referenzen können semantisch widersprechen | Scheingrounding | Angebot/Fakt-Zuordnung, exakte operative Tokens, Rollen-Claimtyp und klare Claim-Denylist prüfen | Falsches Angebot/Fakt und erfundene Fakten testen |
| Flachen `answer`-String erweitern | Keine Satzgrenzen oder atomare Teilbelege | Teilantworten könnten trotz Fehler sichtbar werden | Neues Satzmodell; sichtbaren Text nur serverseitig aus vollständig validierten Sätzen bauen | Prosa/Markdown/Teilfehler testen |
| Gesamtbudget als Request-Deadline | Deterministische Dialog-/CPU-Zeit würde fälschlich als LLM-Wartezeit zählen | Methodisch falsches Budget und fragile Tests | Ausschließlich tatsächliche monotone Dauer der drei Providerawaits kumulieren | Injizierbare Uhr und Stufenrestbudget testen |
| Budget nur im Provider halten | Provider kennt nicht die vorherigen Stufen | Drei Einzelgrenzen können weiter 55 Sekunden kumulieren | Eine Budgetinstanz pro `_query_core`, Restzeit explizit an jede Stufe geben | Interpreter->Selector->Formulator-Test |
| OOS-LLM mit freier Anfrage und ohne Policyvertrag | Modell könnte die fachfremde Frage beantworten | Weltwissen/erfundene Fakten | Angebotsfreies Evidence mit `out_of_scope_boundary` und `supported_domains`; atomare Prüfung und Templatefallback | Sachantwort-/Ortsfaktangriff testen |
| Alle sprachlichen Aussagen per Keywordliste absichern | Fünf Sprachen und natürliche Formulierungen | Fragile, workaroundlastige Scheinsicherheit | Nur robuste formale, Skript-, operative Token-, Claimtyp- und Hochrisikoprüfungen; semantische Grenze dokumentieren | Mehrsprachige Positiv-/Negativfixtures |
| Bestehende Übersetzungsfelder unverändert verwenden | Telefonnummern/Zeiten/Notizen können kuratierte Fakten ersetzen | Sichtbare alte oder veränderte Fakten | Operative Felder nie übersetzen; übrige Übersetzung nur bei identischen geschützten Tokens | Manipulierte Übersetzungsfixtures |
| TTS-Text nur im Frontend als final annehmen | Endpoint akzeptiert beliebigen Text und Frontend transformiert ihn | Metadaten/fremder Text könnten vorgelesen werden | Session-ID verlangen, Text exakt mit letztem Turn vergleichen, erst danach serverseitig normalisieren | Fremdtext/alte Session/112/Zeit testen |
| Fachtemplates in Prompt oder UI duplizieren | Datenänderungen würden auseinanderlaufen | Veraltete Kontakte/Zeiten | Fallbacks aus finalen Runtime-Records und vorhandenen Dialogressourcen aufbauen | Hilfebus-/Scharni-Inventartest |

## Recommended approach

Ein kohäsives `app/formulation.py` definiert AnswerType, Evidence- und
Formulatorverträge, opake Hashreferenzen, Prompt und Builder. Ein getrenntes
`app/grounding.py` validiert den vollständig geparsten Vertrag gegen exakt das
Evidence-Paket und erzeugt erst danach sichtbaren Text und Kartenreihenfolge.
`BlabladorProvider` bleibt Transportgrenze und übersetzt Fehler in stabile
Formulatorcodes. `QueryService` besitzt pro Anfrage eine kleine
`LLMRequestBudget`-Instanz, orchestriert frühe Policyantworten und verwendet
einen gemeinsamen Formulationshelper für LLM oder lokalisierte Templates.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Freien Text nachträglich nur per Regex prüfen | Keine Satz-/Faktenbindung und unzureichende Rollenprüfung |
| Chain-of-Thought oder Modellbegründung verlangen | Nicht erforderlich und datenschutz-/validierungsseitig schädlich |
| Einen zweiten Übersetzungsspeicher für Antworten anlegen | WP7 vorweggenommen und parallele Architektur |
| OOS und Akutgefahr gemeinsam formulieren | Akutgefahr muss deterministisch und ohne Provider bleiben |
| TTS-Signatur oder neuer persistenter Audiotokenstore | Session enthält bereits den erforderlichen sichtbaren Text; zusätzliche Persistenz unnötig |
| Semantische Vollprüfung durch einen vierten LLM-Aufruf | Umgeht das Zeitbudget und verschiebt Vertrauen statt es deterministisch zu begrenzen |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/formulation.py` | Create | AnswerType, Evidence, Satzvertrag, Prompt und Builder | Hoch, neue zentrale Grenze |
| `app/grounding.py` | Create | Atomare Text-, Fakten-, Rollen-, Sprach- und Kartenprüfung | Hoch, sicherheitsrelevant |
| `app/llm_budget.py` | Create | Kumulatives monotones Providerzeitbudget | Klein |
| `app/providers/llm.py` | Modify | Evidence-Payload, strikter Parser, Fehlercodes und Resttimeout | Hoch |
| `app/service.py` | Modify | Budgetorchestrierung und gemeinsame Formulations-/Fallbackpfade | Hoch |
| `app/models.py`, `app/interactions.py`, `app/main.py` | Modify | Antworttyp, TTS-Vertrag, Health und redigierte Metadaten | Mittel |
| `app/config.py`, `.env.example` | Modify | `LLM_REQUEST_BUDGET_SECONDS` | Klein |
| `app/i18n.py` | Modify | Operative Fakten gegen Übersetzungsüberschreibung schützen | Mittel |
| `app/speech.py`, `app/static/app.js` | Modify | TTS ausschließlich aus validiertem Sessiontext, serverseitige Normalisierung | Mittel |
| `tests/test_formulation.py` | Create | Evidence, Vertrag, Grounding, Sprache, Rollen, Angriffe | Hoch |
| bestehende API/Timeout/Safety/TTS/I18n/Selector/Observabilitytests | Modify | Integrations- und Regressionserwartungen | Mittel |
| README und bestehende technische Dokumentation | Modify | Implementierten WP6-Stand dokumentieren | Klein |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Formulator-, Provider-, Service-, OOS-, Hilfebus-, Safety-, Karten-,
Übersetzungs-, TTS-, Session-, Health-, Logging-, Konfigurations- und Testpfade
wurden vor der ersten Implementierungsänderung verfolgt.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep new source files cohesive and below 400 lines.
- [x] Update this plan with discoveries.

Evidence: `app/formulation.py`, `app/grounding.py` und `app/llm_budget.py`
enthalten die getrennten neuen Grenzen. Provider, Service, TTS, Karten-I18n,
Health und Logging wurden ohne neue Fachauswahl oder WP7-Übersetzungsfreigabe
integriert. Der tote WP5-`formulator_routing_context` wurde entfernt.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run syntax and JavaScript checks where available.
- [x] Run integration/build checks.
- [x] Verify registration, provider separation, prompt inventory, TTS binding and packaging.
- [x] Review final diff with `REVIEW_TEMPLATE.md`.

Evidence: 415 Pytests erfolgreich; `compileall` erfolgreich; 7 Packagingtests
einschließlich Wheel, sdist, Wheel-Neubau, Clean-Install außerhalb des
Checkouts und Template-Smoke erfolgreich; 26 Runtime-Angebote gegen das exakte
Evidence-Positivlisteninventar geprüft; `git diff --check` erfolgreich. Node,
Deno und Bun sind nicht installiert, daher war kein Laufzeit-`--check` möglich;
die statischen Frontendregressionen liefen in der Gesamtsuite.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: README sowie Architektur-, Datenfluss-, Konfigurations- und Testseite
beschreiben Evidence-/Satzvertrag, Groundinggrenzen, Gesamtbudget,
TTS-Sessionbindung und geschützte operative Kartenfakten. Die vollständige Suite
und der Diff-Check wurden danach erneut ausgeführt.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Formulator/Evidence/Grounding | `python -m pytest tests/test_formulation.py tests/test_api.py -q` | Strikte Verträge, Rollen, Sprache und atomare Fallbacks |
| Budget/Timeout | `python -m pytest tests/test_provider_timeouts.py -q` | Kumulatives Budget und getrennte Fehlercodes |
| Candidate/Dialog/Safety | `python -m pytest tests/test_candidates.py tests/test_llm_selection.py tests/test_dialogue.py tests/test_safety.py -q` | Frühe Grenzen unverändert |
| I18n/TTS | `python -m pytest tests/test_i18n.py tests/test_request_boundaries.py -q` | Operative Fakten und Sessiontextbindung |
| Vollständige Regression | `python -m pytest -q` | Gesamte Suite erfolgreich |
| Syntax/JS | `python -m compileall -q app tests` und verfügbare JS-Laufzeit | Keine Syntaxfehler |
| Distribution | `tests/test_packaging.py` | Wheel, sdist, Neubau, Clean-Install und Template-Smoke erfolgreich |
| Diff | `git diff --check`, Referenz-/Prompt-/Payloadsuche | Keine Scope-, Whitespace-, Rohdaten- oder Legacyfehler |

## Rollback and recovery

Es gibt keine Datenmigration und keinen externen Zustand. Das neue
Interaktionsschema ist append-only; ältere JSONL-Zeilen bleiben unverändert.
TTS nutzt weiterhin den bestehenden SessionStore. Ein gezielter Rollback
betrifft nur die File-Impact-Tabelle; Reset-/Checkout-Befehle bleiben wegen des
nicht committeten Nutzerbestands ausgeschlossen.

## Progress log

- 2026-08-01 - Review-First- und Code-Dokumentations-Skills sowie Plan- und Reviewvorlage vollständig gelesen.
- 2026-08-01 - Aktiven Formulator-, OOS-, Hilfebus-, Timeout-, TTS-, Übersetzungs- und Observabilitypfad geprüft.
- 2026-08-01 - Dead Ends und begrenzte Integrationsstrategie vor Quellcodeänderungen dokumentiert.
- 2026-08-01 - Evidence-Vertrag 1, Formulatorvertrag/Prompt 2, atomare Groundingprüfung und Drei-Stufen-Budget implementiert.
- 2026-08-01 - OOS-, Kein-Treffer- und Hilfebusverträge, TTS-Sessionbindung sowie Schutz operativer Kartenfakten integriert.
- 2026-08-01 - 415 Tests, Syntax-, Packaging-/Clean-Install-, Promptinventar- und Diff-Prüfungen erfolgreich abgeschlossen.

## Decision log

- Decision: Faktenreferenzen werden als gekürzte SHA-256-Bindung aus Angebots-ID, Typ, Position und Wert erzeugt.
  - Context: Referenzen müssen stabil, intern und nicht durch einfache Feldnamen erratbar sein.
  - Choice: Präfix `f_` plus 16 Hexzeichen; Kollisionen werden beim Evidence-Bau abgelehnt.
  - Consequences: Gleiche freigegebene Fakten bleiben stabil, Änderungen erzeugen neue Referenzen.
- Decision: Das Budget misst nur kumulierte Providerawait-Zeit.
  - Context: Deterministische Verarbeitung und Dialogzeit gehören nicht zum externen LLM-Wartebudget.
  - Choice: Monotone Uhr und Begin/Finish pro LLM-Stufe; Timeout ist `min(Stufenlimit, Restbudget)`.
  - Consequences: Harte externe Obergrenze ohne vierte konkurrierende Timeoutquelle.
- Decision: TTS bindet Text über die vorhandene Session statt eines neuen Tokenstores.
  - Context: Jede sichtbare Antwort wird bereits atomar als letzter Turn persistiert.
  - Choice: Session-ID und exakte Antwortübereinstimmung vor Synthese; Normalisierung erst serverseitig.
  - Consequences: Keine parallele Persistenz, Replay bleibt möglich, beliebiger Text wird abgewiesen.

## Discoveries

- Der bestehende Formulatorparser entfernt Markdown-Fences; WP6 muss reines JSON verlangen.
- Die bisherige Groundingprüfung bindet Zahlen und Kontakte nur an die Gesamtmenge, nicht an Satz, Fakt oder Angebot.
- `TRANSLATED_FIELDS` umfasst derzeit Telefonnummern, Öffnungs-/Standzeiten und Notizen; dies widerspricht dem Schutz kuratierter operativer Fakten.
- Das Frontend verändert Zeitangaben vor TTS und der öffentliche TTS-Endpunkt prüft keine Herkunft des Texts.
- `service.py` und `providers/llm.py` überschreiten bereits vor WP6 den 400-Zeilen-Richtwert; neue Verträge, Grounding und Budget müssen ausgelagert werden, ohne WP7 vorwegzunehmen.

## Final verification summary

- Acceptance requirements: vollständig erfüllt, soweit im WP6-Scope automatisierbar.
- Tests: 415/415 erfolgreich; keine realen Provideraufrufe.
- Build: Wheel und sdist, Wheel aus sdist sowie Clean-Install/Template-Smoke erfolgreich.
- Manual verification: vollständiger Prompt und 26-Angebote-Evidence-Inventar lokal ohne Provider geprüft; JavaScript-Laufzeit nicht vorhanden.
- Documentation: bestehende technische Dokumentation aktualisiert; keine Thesis- oder Präsentationsdatei verändert.
- Residual risks: Strukturelle und lexikalische Groundingprüfungen sind keine vollständige semantische oder linguistische Qualitätsgarantie. Übersetzungen bleiben bis WP7 maschinell beziehungsweise ungeprüft; `acute_risk_status=uncertain` und Interpreterausfälle behalten die bereits dokumentierte spätere Safety-Grenze.
