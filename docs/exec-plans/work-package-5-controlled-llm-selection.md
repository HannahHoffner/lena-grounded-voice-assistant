# Arbeitspaket 5: Kontrollierte LLM-Kandidatenauswahl

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-01
- Last updated: 2026-08-01

## Objective

LENA verwendet nach Interpreter, deterministischem `CandidateSelector` und gegebenenfalls Dialog eine eigene strikt validierte LLM-Auswahlstufe. Das Modell sieht nur kompakte, fachlich bereits zulaessige auswählbare Kandidaten. Verbindliche Kandidaten bleiben deterministisch erhalten, bedingte und ausgeschlossene Angebote bleiben vollständig außerhalb des Selector- und Formulatorpfads.

## Acceptance contract

- [x] Der Kandidatenvertrag trennt versioniert `mandatory_candidates`, `selectable_candidates`, `conditional_candidates` und `excluded_candidates`.
- [x] Ein eigener LLM-Selectorvertrag mit eigenem Prompt, Timeout, Fehlercodes und Positivlistenpayload ist aktiv zwischen deterministischer Begrenzung und Formulator.
- [x] Der Selector wird nur bei erfolgreicher Interpretation, ohne Safety-/Scope-Abbruch oder offenen Dialog und bei mindestens zwei sinnvoll auswählbaren Kandidaten aufgerufen.
- [x] Alle Modell-IDs werden als unteilbare Antwort strikt gegen exakt den aktuellen auswählbaren Index geprüft.
- [x] Mandatory-Kandidaten und kuratierte Reihenfolge werden nach dem Modell deterministisch durchgesetzt; maximal vier finale Angebote erreichen Karten und Formulator.
- [x] Selectorfehler übernehmen keine Teilantwort, verwenden ausschließlich die deterministische `CandidateDecision` und sperren denselben Provider requestlokal für den Formulator.
- [x] Health und redigiertes Interaktionslogging weisen Selectorversionen, Verfügbarkeit, Auswahlquelle, Mengen und Fehlerstatus aus.
- [x] Interpreter, Dialog, CandidateSelector, Formulator, Runtime-Kuration und Ausschluss der IDs 1 bis 4 bleiben wirksam.
- [x] Arbeitspakete 6 und 7 sowie Infrastruktur-, Distanz-, Import- und abschließende Safety-Arbeiten bleiben unberührt.

## Scope

### In scope

- Erweiterter deterministischer Kandidatenvertrag und Klassifikation mandatory/selectable.
- Strikter LLM-Selectorvertrag, minimaler Payload, Prompt, Parser und Provideraufruf.
- Auswahlorchestrierung, Bypass-, Fallback- und Formulatorübergabestatus.
- Eigener `LLM_SELECTOR_TIMEOUT_SECONDS` mit Health-/Dokumentationssicht.
- Redigierte technische Beobachtbarkeit und Vertrags-, Pfad-, Mehrsprachigkeits-, Injection- und Regressionstests.
- Entfernung eindeutig ersetzter Kandidatenindex- und erste-vier-Übergangsreste.

### Out of scope

- Neuer Formulatorvertrag oder grundlegender Umbau der Antwortgenerierung.
- Übersetzungsfreigabe, Toiletten-/Trinkbrunnenimporte und allgemeines geografisches Ranking.
- Neue Safety-Policy für `acute_risk_status=uncertain` oder globales Requestbudget.
- Reale Provideraufrufe, Thesis- und Präsentationsdateien.

## Repository review

### Current behavior

`QueryService._query_core()` ruft den Interpreter und anschließend `CandidateSelector.select()` auf. WP4 behandelt Dialoge vor der normalen Formulierung. Danach bildet der Service aus `decision.candidates` eine Angebotsliste, begrenzt sie mit `[:4]` und übergibt sie direkt an `BlabladorProvider.answer()`. Der Formulator darf innerhalb dieser Liste Karten-IDs zurückgeben. Eine eigene semantische Auswahlstufe, ein Selectorvertrag und ein requestlokaler Providerfehlerzustand existieren nicht.

`CandidateDecision` trennt aktuell `candidates`, `conditional_candidates` und `excluded`; verbindliche kuratierte Prioritäten sind lediglich Reason Codes und `priority_tier`. `BlabladorProvider` besitzt bereits getrennte Interpreter- und Formulator-Gesamtgrenzen, aber keinen Selector-Timeout. `CandidateOfferView` ist ein nicht aktiver Vorläufer eines Kandidatenpayloads und enthält mehr Felder als die neue Auswahlstufe benötigt.

### Relevant architecture and data flow

- Einstieg: `app/main.py:answer_query()` -> `app/service.py:QueryService.query()` -> `_query_core()`.
- Interpretation: `BlabladorProvider.interpret_query()` mit Interpretervertrag 3, ohne Angebotsindex.
- Fachliche Begrenzung: `app/candidates.py:CandidateSelector.select()` ausschließlich auf der kuratierten Runtime-KB.
- Dialog: `app/dialogue_flow.py` und der einzige atomare Zustand in `SessionStore`.
- Aktuelle Übergabe: `decision.candidates` -> erste vier Runtime-Records -> `BlabladorProvider.answer()` -> Karten-ID-Validierung.
- Ausgabe: Formulator oder Template, danach Karten-/Markeraufbau ausschließlich aus finalen Runtime-Records.
- Beobachtbarkeit: `QueryInteraction` -> `InteractionRecord` sowie `/api/health`.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Strikte Pydantic-Modelle | `app/interpreter.py`, `app/candidate_contract.py`, `app/models.py` | Für Selectorvertrag und Positivlisten fortführen |
| Deterministische Fachregeln | `app/candidates.py` | Alleinige Instanz für Eignung, Ausschluss, Bedingungen und Mandatory-Klassifikation |
| Runtime-KB | `app/kb_loader.py` | Ausschließlich vorhandene validierte 26-Angebote-Projektion verwenden |
| Providertransport und Gesamtgrenzen | `app/providers/llm.py` | HTTP-Transport wiederverwenden, aber eigene Selector-Methode und Gesamtgrenze einführen |
| Dialogvorrang | `app/service.py`, `app/dialogue_flow.py` | Vor Selector unverändert beibehalten |
| Formulator-Positivliste | `FormulatorOfferView` | Nur finale IDs in vollständige Ansichten auflösen |
| Redigierte Interaktionsmetadaten | `app/models.py`, `app/interactions.py` | Um nicht-sensitive Selectorstatus erweitern |

### Existing tests and commands

- Kandidaten: `tests/test_candidates.py`
- Provider/API: `tests/test_api.py`, `tests/test_provider_timeouts.py`
- Dialog/Safety/Scope: `tests/test_dialogue.py`, `tests/test_safety.py`, `tests/test_interpreter.py`
- Inventar/Packaging: `tests/test_curation.py`, `tests/test_packaging.py`
- Vollständige Ausgangssuite: zuletzt 335 Tests erfolgreich.

### Working tree considerations

Branch `maintenance/repository-cleanup`, Ausgangscommit `9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`. Der Arbeitsbaum enthält die freigegebenen, nicht committeten Arbeitspakete 1 bis 4. Diese Änderungen sind Nutzerbestand und werden weder zurückgesetzt noch bereinigt. Es wurde kein `AGENTS.md` im Repositorybaum gefunden. WP5-Hunks bleiben auf Kandidatenvertrag, LLM-Selector, Orchestrierung, Konfiguration, Beobachtbarkeit, Tests und vorhandene technische Dokumentation begrenzt.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Zweiter CandidateSelector mit eigenen Fachregeln | Neuer LLM-Payload könnte direkt aus `OfferRecord` gefiltert werden | Widersprüchliche Eignung und Umgehung von Kuration | Payload ausschließlich aus `CandidateDecision.selectable_candidates` bauen | Promptinventar und Pfadtests |
| Bedingte Angebote im Selectorindex | `conditional_candidates` liegt neben zulässigen Kandidaten | Modell könnte ungeklärte Eignung als passend erklären | Separate Vertragsfelder; Builder akzeptiert nur selectable | Conditional-ID- und Payloadtests |
| Teilweise gültige Modellantwort | Mehrere IDs können einzeln geprüft werden | Fremde ID würde verdeckt, Rest übernommen | Gesamte Antwort atomar ablehnen | Misch-ID-Test |
| Mandatory über Modell steuern | Ein gemeinsamer Index würde verbindliche Kandidaten auswählbar machen | Rücke/Roßplatz könnten verschwinden oder umsortiert werden | Mandatory nie an das Modell übergeben und deterministisch voranstellen | Mandatory- und Reihenfolgetests |
| Formulator nach Selector-Timeout erneut aufrufen | Alle drei Stufen teilen denselben Provider | Zweiter langer Timeout und schlechte UX | Requestlokaler `selector_provider_failed`-Status sperrt Formulator | Timeout-/HTTP-Pfadtest |
| Alte erste-vier-Logik bleibt parallel | `selected_offers[:4]` in `service.py` | Selector wäre wirkungslos oder nur Schattenpfad | Eine finale Auswahlfunktion als einzige Quelle für Formulator/Templates | Callsite- und Diffreview |
| Rohdaten/Contacts im Selectorprompt | `CandidateOfferView` enthält Adresse und Suchphrasen | Unnötige Daten und alte Fakten im Prompt | Neue engere `SelectorCandidateView`; alten inaktiven View entfernen | Positivlisten-Inventartest |
| Ein Kandidat erzeugt dritten Modellaufruf | Aktuell kennt Service nur eine Liste | Unnötige Latenz/Kosten | Explizite Bypassgründe und deterministische Finalisierung | Call-count-Tests |
| Providervertrag bleibt `answer()` | Aktuelle Methode benennt Stufe nicht klar | Vermischte oder tote Verträge | Auf `formulate_answer()` umstellen und alte Callsite vollständig entfernen | Referenzsuche |
| Fehlender globaler Requestetat | Drei Gesamtgrenzen addieren sich | Theoretisch lange maximale Wartezeit | Grenzen transparent addieren; kein viertes Timeout in WP5 | Konfig-/Doku-/Health-Test |

## Recommended approach

Der `CandidateSelector` klassifiziert seine bereits zulässigen Ergebnisse in mandatory und selectable. Ein neues kohäsives Modul definiert Selectorvertrag, kompakten Index, Systemprompt, Payloadvalidierung und deterministische Finalisierung. `BlabladorProvider.select_candidates()` übernimmt ausschließlich den Transport und die strikte Antwortprüfung. `QueryService` ruft diese Stufe nach allen Dialogabzweigungen auf, zeichnet Bypass oder Fallback auf und übergibt ausschließlich die finalen maximal vier Runtime-Records an `formulate_answer()` oder Templates.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Mandatory-Kandidaten mit in den Prompt geben | Eröffnet dem Modell unzulässige Entfernungs- und Reihenfolgeentscheidungen |
| Auswahl direkt im bestehenden Formulatorprompt | Vermischt Auswahl und Formulierung und verhindert getrennte Fehler-/Timeoutbehandlung |
| Legacy-Retrieval als Selectorfallback | Ist nicht an die aktuelle `CandidateDecision` gebunden und könnte Fachfilter umgehen |
| LLM-Aufruf bei einem selectable Kandidaten | Keine echte Auswahl zwischen Alternativen, aber zusätzliche Latenz |
| Modellbegründung oder Scores speichern | Nicht erforderlich, erhöht Prompt-/Loggingrisiko und erschwert strikte Validierung |
| Globales Requesttimeout ergänzen | Sinnvoll, aber außerhalb WP5 und würde eine vierte Timeoutlogik schaffen |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/llm_selection.py` | Create | Selectorvertrag, View, Prompt, Payload, Validierung und Finalisierung | Mittel; neue zentrale Grenze |
| `app/candidate_contract.py` | Modify | Mandatory-/Selectable-/Conditional-/Excluded-Trennung, Vertrag 2 | Hoch; interner Kernvertrag |
| `app/candidates.py` | Modify | Deterministische Mandatory-Klassifikation | Mittel; Fachregression |
| `app/providers/llm.py` | Modify | `select_candidates()`, eigener Timeout und `formulate_answer()` | Hoch; Providergrenze |
| `app/service.py` | Modify | Selectoraufruf, Bypässe, Fehlerzustand und finale Übergabe | Hoch; aktiver Pfad |
| `app/config.py`, `.env.example` | Modify | Eigene Selector-Gesamtgrenze | Klein |
| `app/models.py`, `app/interactions.py`, `app/main.py` | Modify | Redigierte Beobachtbarkeit und Health | Mittel |
| `tests/test_llm_selection.py` | Create | Vertrag, Payload, Angriffe, Finalisierung, Mehrsprachigkeit | Hoch, isoliert |
| bestehende Candidate/API/Dialog/Safety/Timeout/Observability/Packagingtests | Modify | Vertrags- und Pfadregression | Mittel |
| `README.md`, `docs/architecture.md`, `docs/data-flow.md`, `docs/configuration.md`, `docs/testing.md` | Modify | Ausschließlich implementierten WP5-Stand dokumentieren | Klein |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Aktive Interpreter-, Candidate-, Dialog-, Provider-, Formulator-, Health-, Logging-, Konfigurations- und Testpfade wurden vor der ersten Implementierungsänderung verfolgt.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep new source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

Evidence: `app/llm_selection.py` bündelt Vertrag, Prompt, Positivlistenpayload,
Bypass, ID-Finalisierung und Fallback in 293 Zeilen. Providertransport,
Orchestrierung, Kandidatenvertrag, Konfiguration und Beobachtbarkeit wurden nur
an den neuen Selektorschritt angebunden.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run syntax and JavaScript checks where available.
- [x] Run integration/build/clean-install checks.
- [x] Verify provider separation, payload inventory, runtime path and packaging.
- [x] Review final diff with `REVIEW_TEMPLATE.md`.

Evidence: 364 Tests erfolgreich; davon sieben Packagingtests mit Wheel, sdist,
Wheel-Neubau, Clean-Install und Template-Smoke außerhalb des Checkouts.
`compileall` und `git diff --check` erfolgreich. Keine JavaScript-Laufzeit war
installiert; WP5 verändert keine JavaScript-Datei. Positivlisteninventar aller
26 Runtime-Angebote, IDs 1 bis 4, Conditional-/Excluded-Isolation,
Providerfehler und Legacyreferenzen wurden separat geprüft.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: README sowie Architektur-, Datenfluss-, Konfigurations- und
Testdokumentation beschreiben ausschließlich den implementierten WP5-Stand;
die vollständige Suite und Packagingprüfung wurden danach erneut ausgeführt.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Selectorvertrag/Provider | `python -m pytest tests/test_llm_selection.py tests/test_provider_timeouts.py -q` | Strikte Antworten, Fehlercodes und eigene Grenze |
| Candidate/Dialog/Safety | `python -m pytest tests/test_candidates.py tests/test_dialogue.py tests/test_safety.py -q` | Fachregeln, Dialogvorrang und Abbrüche unverändert |
| API/Observability/Inventar | `python -m pytest tests/test_api.py tests/test_observability.py tests/test_curation.py -q` | Reale Stufenkette, redigierte Status- und Positivlistenfelder |
| Vollständige Regression | `python -m pytest -q` | Gesamte Suite erfolgreich |
| Syntax | `python -m compileall -q app tests` | Keine Fehler |
| Build/Clean install | `python -m build --no-isolation` und `tests/test_packaging.py` | Wheel, sdist, Neubau und Installation erfolgreich |
| Template smoke | Lokale Anfrage ohne Provider | Kein externer Aufruf; ausschließlich deterministische Kandidaten |
| Diff | `git diff --check`, Referenzsuche und Statusreview | Keine Scope-, Whitespace- oder Legacyfehler |

## Rollback and recovery

Es gibt keine Datenmigration oder externe Mutation. Der Selector ist requestlokal und verändert weder Runtime-KB noch Sessions. Ein gezielter Rollback betrifft nur die in der File-Impact-Tabelle dokumentierten WP5-Hunks; Reset-/Checkout-Befehle bleiben wegen des nicht committeten Nutzerbestands ausgeschlossen.

## Progress log

- 2026-08-01 - Review-First- und Code-Dokumentations-Skills vollständig gelesen.
- 2026-08-01 - Aktiven Auswahlpfad, Verträge, Timeouts, Payloads, Tests und historische Reste geprüft.
- 2026-08-01 - Dead Ends und begrenzte Integrationsstrategie vor Quellcodeänderungen dokumentiert.
- 2026-08-01 - Kandidatenvertrag 2, Selectorvertrag/Prompt 1, Providerstufe,
  Orchestrierung, Positivlisten, Health und redigierte Interaktionsmetadaten implementiert.
- 2026-08-01 - Reviewkorrektur: Mandatory-Kandidaten bleiben auch gegenüber
  nachgelagerten Formulator-`card_ids` in der sichtbaren Kartenreihenfolge bindend.
- 2026-08-01 - 364 Tests, Packaging-/Clean-Install-Prüfung, Syntax,
  Template-Smoke, Legacyreferenzsuche und Diffprüfung erfolgreich abgeschlossen.

## Decision log

- Decision: Das LLM sieht ausschließlich `selectable_candidates`; Mandatory wird nie promptseitig dargestellt.
  - Context: Das Modell darf verbindliche Prioritäten weder entfernen noch umsortieren.
  - Choice: Deterministischer Prefix plus vom Modell ausgewählte Menge, anschließend stabile Candidate-Reihenfolge.
  - Consequences: Das Modell entscheidet nur über ergänzende Kandidaten.
- Decision: Der Selector läuft erst ab zwei auswählbaren Kandidaten.
  - Context: Ein einzelner optionaler Kandidat bietet keine semantische Auswahl zwischen Alternativen.
  - Choice: Ein Kandidat wird mit `single_candidate` deterministisch übernommen; nur Mandatory ergibt `mandatory_only`.
  - Consequences: Weniger unnötige Modellaufrufe; Mandatory-plus-ein-selectable bleibt vollständig deterministisch.
- Decision: Selectorfehler sperren denselben Provider für den Formulator in derselben Anfrage.
  - Context: Ein zweiter langer Aufruf nach technischem Fehler wäre unzumutbar.
  - Choice: Deterministische CandidateDecision-Fallbackauswahl und Templateformulierung.
  - Consequences: Keine doppelte Timeoutkaskade; Provider kann bei der nächsten Anfrage wieder verwendet werden.

## Discoveries

- `CandidateOfferView` und `compact_candidate_context()` sind kein aktiver Routerpfad und können durch den engeren Selector-View ersetzt werden.
- Der Formulator heißt noch `answer()`; eine klare Umbenennung zu `formulate_answer()` ist innerhalb der geforderten Stufentrennung erforderlich.
- `service.py` und `providers/llm.py` überschreiten bereits vor WP5 den 400-Zeilen-Richtwert; neue Vertrags-/Finalisierungslogik muss in ein kohäsives Modul ausgelagert werden, ohne WP6 vorwegzunehmen.
- Die aktuelle Maximalwartezeit beträgt 45 Sekunden für Interpreter plus Formulator; mit einem Selectorstandard von 10 Sekunden steigt sie ohne globales Requestbudget auf 55 Sekunden.

## Final verification summary

- Acceptance requirements: erfüllt; WP6 und spätere Pakete nicht begonnen.
- Tests: 364/364 erfolgreich; keine realen Provideraufrufe.
- Build: Wheel und sdist erfolgreich, Wheel aus sdist reproduziert und sauber außerhalb des Repositorys installiert.
- Manual verification: Stufentrennung, Promptinventar, Legacyreferenzen, Health und finaler Diff geprüft.
- Documentation: implementierter Stand in README und technischer Dokumentation nachgeführt.
- Residual risks: Ohne globales Requestbudget können 15 + 10 + 30 Sekunden Modellgrenzen kumulieren; reale mehrsprachige Modellqualität bleibt Evaluationsaufgabe; JavaScript-Laufzeit war lokal nicht verfügbar.
