# Formulator-Vertrag und WP9B-Stufe-2-Evidence angleichen

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-24
- Last updated: 2026-08-24

## Objective

Der reale Formulator soll den bereits strikt validierten Vertrag zuverlässig
erfüllen können. Die isolierte WP9B-Stufe 2 soll dabei exakt denselben
lokalisierten Evidence-Aufbau wie der aktive Anwendungspfad prüfen. Die
Grounding-, Rollen-, Fakten- und Sicherheitsgrenzen werden nicht gelockert.

## Acceptance contract

- [x] Der Prompt ordnet jeden `answer_type` eindeutig dem zulässigen ersten
  `claim_type` zu, insbesondere `grounded_referral` zu `referral`.
- [x] Der Prompt beschreibt Referenzfelder und den kleinsten sicheren Satzaufbau
  so eindeutig, dass keine zusätzlichen Fakten erforderlich sind.
- [x] Promptversion und technische Beobachtbarkeit werden nachvollziehbar erhöht.
- [x] Die isolierten mehrsprachigen Formulator-Fixtures verwenden denselben
  Übersetzungskatalog und dieselbe Runtime-Policy wie `QueryService`.
- [x] Strikte Schema-, Grounding-, Rollen-, ID-, Sprach- und Injectionprüfungen
  bleiben unverändert wirksam.
- [x] Providerfreie Tests, vollständige Suite, Syntax und Diffprüfung bestehen.
- [x] Es erfolgen keine realen Provideraufrufe und keine Änderungen an Thesis
  oder Präsentation.

## Scope

### In scope

- Präzisierung und Versionierung des vorhandenen Formulator-Systemprompts.
- Angleichung des WP9B-Stufe-2-Evidence-Aufbaus an den produktiven Pfad.
- Fokussierte Vertrags-, Prompt-, Lokalisierungs- und Regressionstests.
- Unmittelbar betroffene technische Evaluationsdokumentation.

### Out of scope

- Lockerung oder Entfernung irgendeines Groundingvalidators.
- Vertrags-, Evidence- oder API-Schemaänderung.
- Retries im isolierten Live-Gate oder Änderungen an Produktivfallbacks.
- Neue Fachregeln, Modelle, Timeouts, Providerkonfiguration oder Live-Aufrufe.
- Dokumentation fehlgeschlagener Zwischenläufe in der Masterarbeit.

## Repository review

### Current behavior

- HEAD ist `d0d2018ba4e61288b613cc378c08e1a6c996af87` auf
  `maintenance/repository-cleanup`; der Arbeitsbaum war vor diesem Plan sauber.
- WP9B-Stufe 2 (`run_9b50a3e9dc31478caf0b15d0f5cc0312`) validierte sechs
  Selectorantworten vollständig. Der Formulator scheiterte anschließend mit
  zweimal `formulator_ungrounded_claim` und einmal `formulator_schema_error`;
  die vorab gebundene Drei-Fehler-Grenze stoppte den Lauf nach 9 Calls.
- Rohantworten werden absichtlich nicht gespeichert. Der genaue Wortlaut der
  verworfenen Antworten ist deshalb ungeklärt und wird nicht nachträglich
  behauptet.
- `FORMULATOR_SYSTEM_PROMPT` verlangt die wichtigste Handlung zuerst und erklärt
  `candidate_role`, nennt aber nicht die durch `validate_formulation()`
  erzwungene Zuordnung des ersten `claim_type` je `answer_type`.
- Für `referral_contact` verwirft `_validate_sentence()` sowohl `action` als auch
  `service`; nur `referral` ist zulässig. Eine an sich natürliche Modellstruktur
  mit `claim_type="action"` ist damit promptkonform, aber validatorinkompatibel.
- `QueryService._formulate_or_fallback()` übergibt Katalog und Runtime-Policy an
  `build_formulator_evidence()`. `_run_formulator_scenario()` lässt beide weg;
  seine EN/PL/RO/RU-Evidence enthält deshalb deutsche übersetzbare Kartenfelder.

### Relevant architecture and data flow

Produktiv baut `QueryService` aus der finalen Angebotsmenge über
`build_formulator_evidence()` ein positiv gelistetes Evidence-Paket, lässt
`BlabladorProvider.formulate_answer()` JSON parsen und durch Pydantic sowie
`validate_formulation()` atomar prüfen. WP9B-Stufe 2 ruft denselben Provider
isoliert auf, konstruiert Evidence bislang jedoch ohne Runtime-Lokalisierung.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Formulatorprompt und Version | `app/formulation.py` | bestehenden Prompt präzisieren, keine zweite Variante |
| Übersetzungskatalog | `app/i18n.py::load_translation_catalog` | im isolierten Runner identisch laden |
| Runtime-Policy | `TranslationRuntimePolicy` | Einstellung wie im `QueryService` auswerten |
| Evidence-Builder | `app/formulation.py::build_formulator_evidence` | unverändert als einzige Projektion verwenden |
| Groundingvalidator | `app/grounding.py::validate_formulation` | unverändert erhalten |
| Live-Gate | `app/live_evaluation_runner.py` | nur produktionsgleichen Evidence-Aufbau ergänzen |

### Existing tests and commands

- `tests/test_formulation.py`: Prompt-, Schema-, Grounding-, Rollen- und
  Mehrsprachigkeitsregressionen.
- `tests/test_live_evaluation.py`: isolierter Stufe-2-Runner mit Fake-Provider.
- `tests/test_api.py`: produktiver Evidence- und Retrypfad.
- Geplante Checks: fokussiertes Pytest, vollständiges Pytest,
  `python -m compileall -q app tests`, `git diff --check`.

### Working tree considerations

Vor dem Plan bestand kein lokaler Diff. Live-Reports liegen im ignorierten
Runtimebereich und werden weder geändert noch in Git/Thesis übernommen.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Groundingregeln lockern | Fehlercode ist grob; Rohtext fehlt | echte Halluzinationen könnten passieren | ausschließlich Prompt an bestehenden Validator angleichen | Angriffs- und Groundingtests bleiben grün |
| Fehler mit Templates verdecken | Produktivfallback existiert bereits | Modellvertrag bliebe in WP9B rot | Stufe-2-Vertrag direkt verbessern | isolierte Fake-Provider-Vertragstests |
| Zusätzlichen Retry in Stufe 2 einbauen | Gate soll Einzelantwort-Kompatibilität messen | schwächt Messung und erhöht Calls | kein Evaluationsretry | Callzähltests unverändert |
| Nur englische Fixturetexte hartkodieren | fünf Sprachen und Runtime-Policy existieren bereits | zweite, driftende Evidence-Pipeline | bestehenden Katalog/Policy wiederverwenden | Capture-Test über fünf Sprachen |
| Rohantworten dauerhaft protokollieren | bisherige Datenschutzgrenze verbietet dies | unnötige Datenpersistenz | redigierte Codes beibehalten | Reportinventartests |

## Recommended approach

Promptversion 8 ergänzt eine kleine Entscheidungstabelle für den ersten Satz,
explizite Referenzinvarianten und einen sicheren Minimalpfad. Der Runner lädt
einmal den bestehenden Übersetzungskatalog und reicht ihn samt Runtime-Policy an
den unveränderten Evidence-Builder weiter. Diese Änderungen beseitigen die
belegten Vertragslücken, ohne irgendeine Sicherheitsprüfung zu schwächen.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| JSON-Schema-Responseformat neu erzwingen | Providerunterstützung ist nicht belegt und wäre eine Transportänderung |
| Formulatorvertrag vereinfachen | würde Grounding- und Kartenbindung abschwächen |
| Modell oder Tokenlimit ändern | die beobachteten Fehler belegen keine Timeout- oder Konfigurationsursache |
| Rohantwort anhand des Fehlercodes erraten | methodisch unzulässig; genaue Ausgabe wurde nicht gespeichert |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/formulation.py` | Modify | Promptversion und eindeutige Vertragsabbildung | klein, sicherheitsrelevant |
| `app/live_evaluation_runner.py` | Modify | produktionsgleiche lokalisierte Evidence | klein |
| `tests/test_formulation.py` | Modify | Prompt-/Validatorausrichtung absichern | klein |
| `tests/test_live_evaluation.py` | Modify | Lokalisierung im echten Stufe-2-Aufrufpfad erfassen | mittel |
| `docs/live-provider-evaluation.md` | Modify | neue Promptversion und erneute Gatepflicht dokumentieren | klein |
| dieser Plan | Create/Update | Review-, Entscheidungs- und Prüfnachweis | Dokumentation |

## Milestones

### Milestone 1: Review and design

- [x] Repository, Status, Anweisungen, Skills und Planvorlagen geprüft.
- [x] Prompt, Providerparser, Evidence-Aufbau, Grounding und Stufe-2-Runner verfolgt.
- [x] Produktions- und Evaluationspfad verglichen.
- [x] Dead Ends und kleinsten sicheren Eingriff bestimmt.

Evidence: oben dokumentierte Symbol- und Pfadverfolgung; keine Quellcodeänderung
vor Abschluss dieses Plans.

### Milestone 2: Implementation

- [x] Prompt präzisieren und Version erhöhen.
- [x] Stufe-2-Evidence an Runtime-Lokalisierung angleichen.
- [x] Providerfreie Regressionstests ergänzen.

Evidence: `FORMULATOR_PROMPT_VERSION=8`; der Runner lädt
`TranslationCatalog`/`TranslationRuntimePolicy`; neue Prompt- und
Evidence-Capture-Regressionstests.

### Milestone 3: Verification

- [x] Fokussierte Tests ausführen.
- [x] Vollständige Suite und Syntaxprüfung ausführen.
- [x] Finalen Diff nach Review-Template prüfen.

Evidence: 108 Formulator-/Live-Tests und zuvor 147 inklusive API bestanden;
749/749 Tests vollständig bestanden; Compileall und Diffprüfung erfolgreich.

### Milestone 4: Documentation

- [x] `code-documentation` auf finalen Diff anwenden.
- [x] Dokumentationsstand prüfen und betroffene Tests wiederholen.

Evidence: `docs/live-provider-evaluation.md` auf Promptversion 8,
produktionsgleichen Evidence-Aufbau und erneute Live-Gatepflicht aktualisiert;
betroffene Tests anschließend erneut bestanden.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Promptvertrag | `pytest -q tests/test_formulation.py` | neue Rollenzuordnung und alle Groundingangriffe grün |
| Live-Fixture | gezielte Tests in `tests/test_live_evaluation.py` | EN/PL/RO/RU nutzen Runtimeübersetzungen |
| API-Regression | `pytest -q tests/test_api.py` | Produktivpfad unverändert grün |
| Gesamtsuite | `pytest -q` | keine Regression |
| Syntax | `python -m compileall -q app tests` | erfolgreich |
| Diff | `git diff --check` | keine Whitespacefehler |

## Rollback and recovery

Es gibt keine Datenmigration. Prompt-, Runner-, Test- und Dokumentationshunks
können einzeln auf die vorherige Version zurückgeführt werden. Grounding,
Runtime-KB und gespeicherte Übersetzungen werden nicht verändert.

## Progress log

- 2026-08-24 — Providerfreier Review abgeschlossen; Plan vor Quellcodeänderung erstellt.
- 2026-08-24 — Promptversion 8 und produktionsgleiche lokalisierte Stufe-2-Evidence implementiert.
- 2026-08-24 — 749/749 Tests, Syntax, Dry-Run und Diffprüfung bestanden; technische Dokumentation aktualisiert.

## Decision log

- Decision: Validatoren unverändert lassen und Prompt explizit an sie binden.
  - Context: Die Validatoren haben die unsicheren Ausgaben korrekt abgefangen;
    die aktuelle Promptbeschreibung lässt aber validatorwidrige Strukturen zu.
  - Options: Validator lockern, Retry ergänzen, Prompt präzisieren.
  - Choice: Prompt präzisieren.
  - Consequences: Vertrag bleibt streng; erneute Live-Evaluation ist nötig.
- Decision: Stufe-2-Evidence über bestehende Runtime-Lokalisierung bauen.
  - Context: Der aktive Pfad lokalisiert Kartenfelder; der isolierte Runner nicht.
  - Options: Fixtureübersetzungen duplizieren oder Runtimepfad wiederverwenden.
  - Choice: Katalog und Policy wiederverwenden.
  - Consequences: Stufe 2 misst denselben Formulatorinput wie die Anwendung.

## Discoveries

- Exakte Modellrohausgabe der fehlgeschlagenen Stufe 2 ist absichtlich nicht
  vorhanden; Aussagen über einzelne Halluzinationen bleiben ungeklärt.
- `app/live_evaluation_runner.py` überschreitet bereits vor dieser Änderung den
  400-Zeilen-Richtwert, bleibt aber kohäsiv als stufenspezifischer Runner. Eine
  Extraktion wäre für die 18 Integrationszeilen ein unverhältnismäßiger und
  sachfremder Umbau; sie wurde bewusst nicht vorgenommen.

## Final verification summary

- Acceptance requirements: erfüllt.
- Tests: 749/749 vollständig sowie 108 fokussierte Tests bestanden.
- Build: Paket-/Clean-Install-Abdeckung der vollständigen Suite bestanden;
  `python -m compileall -q app tests` erfolgreich.
- Manual verification: providerfreier Stufe-2-Dry-Run zeigt Formulatorprompt 8,
  16 gebundene Szenarien und keine automatische Folgestufe.
- Documentation: bestehende technische Live-Evaluationsdokumentation aktualisiert;
  keine Thesis- oder Präsentationsdatei verändert.
- Residual risks: Die reale Modellkonformität nach Promptänderung ist noch nicht
  gemessen. Ein neuer Lauf benötigt einen sauberen Commit und eine separate
  Freigabe; bis dahin darf Stufe 3 nicht starten.
