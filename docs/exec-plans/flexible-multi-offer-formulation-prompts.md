# Execution Plan: Flexible faktengebundene Mehrangebotsantworten

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-25
- Last updated: 2026-08-25

## Objective

LENA darf mehrere final ausgewählte, fachlich passende Angebote natürlich und
mit hilfreichen belegten Details nennen. Bei einer ausdrücklichen Dienstagsfrage
nach Essen kann dadurch neben einem allgemeinen Angebot auch die belegte
Essensausgabe am Schwanenteich erscheinen. Normale Antworten sind nicht mehr an
das starre Muster `Nutze „NAME“` gebunden.

## Acceptance contract

- [x] Der Selector darf und soll mehrere komplementäre, gleich passend belegte
  Kandidaten bis zur bestehenden Höchstgrenze auswählen.
- [x] Eine ausdrückliche Zeitangabe bevorzugt Kandidaten mit passendem
  strukturiertem Zeitstatus; die Auswahl erfindet keine Zeitpassung.
- [x] Der Formulator kann ein bis drei finale Angebote in Evidence-Reihenfolge
  nennen und jedes genannte Angebot mit eigenen Fakten belegen.
- [x] Der wichtigste nächste Schritt bleibt zuerst, aber ohne festes
  `Nutze ...`-/`Melde dich ...`-Muster für normale Antworten.
- [x] Eigennamen, Rollen, operative Fakten, Kartenbindung und Grounding bleiben
  streng validiert.
- [x] Der eng begrenzte Injection-Pfad behält ein sicheres festes Ein-Satz-Muster.
- [x] Providerfreie Fokus- und Gesamttests bestehen.

## Scope

### In scope

- Selectorprompt und Promptversion
- Formulatorprompt und Promptversion
- unmittelbar zugehörige Prompt-, Vertrags-, API- und Regressionstests
- bestehende Architektur-, Datenfluss- und Live-Evaluationsdokumentation

### Out of scope

- CandidateSelector-, Zeit-, Eignungs- oder Prioritätsregeln
- Vertrags-, Evidence- oder Grounding-Schemata
- Wissensbasis-, Karten-, Übersetzungs- oder Fallbackdaten
- reale Provideraufrufe und Live-Evaluation
- Thesis- und Präsentationsdateien

## Repository review

### Current behavior

Formulatorprompt 13 erzwingt für jede normale Angebotsantwort den festen ersten
Satz `Nutze „NAME“` beziehungsweise dessen rollen- und sprachabhängige Variante.
Der zweite Satz muss erneut das erste Angebot erläutern; nur ein optionaler
dritter Satz kann ein weiteres Angebot nennen. Selectorprompt 2 erlaubt zwar
mehrere IDs, fordert aber nur die Kandidaten an, die "best match" sind, und gibt
keine Regel für mehrere komplementäre oder gleich passende Optionen vor.

### Relevant architecture and data flow

`CandidateSelector` prüft Essenszeiten strikt. Der bestehende API-Test
`test_tuesday_food_names_schwanenteich_stand_time` belegt, dass Angebot 14 am
Dienstag zulässig ist und Karte sowie Marker `14:schwanenteich` erzeugt. Erst
`app.llm_selection.selected_outcome()` begrenzt die finalen IDs auf die gültige
Modellauswahl. `QueryService` übergibt höchstens drei geordnete finale Angebote
an `build_formulator_evidence()`. `app.grounding.validate_formulation()` prüft
jeden Satz gegen genau ein ausgewähltes Angebot und dessen Fakt-IDs.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| kompakter Selectorindex | `app/llm_selection.py` | Prompt präzisieren; Positivliste unverändert |
| finale Evidence-Reihenfolge | `app/service.py`, `app/formulation.py` | unverändert verwenden |
| Satz- und Kartenvalidierung | `app/grounding.py` | unverändert beibehalten |
| Dienstag-Essensregression | `tests/test_api.py` | um Mehrangebotsfluss ergänzen |
| Promptvertragstests | `tests/test_llm_selection.py`, `tests/test_formulation.py` | Versionen und neue Regeln absichern |

### Existing tests and commands

- `python -m pytest -q tests/test_llm_selection.py tests/test_formulation.py tests/test_api.py`
- `python -m pytest -q`
- `python -m compileall -q app tests`
- `python -m app.multilingual_review live-dry-run --stage selector-formulator`
- `git diff --check`

### Working tree considerations

Der Arbeitsbaum war zu Beginn sauber. Branch
`maintenance/repository-cleanup`, HEAD
`e63ff4529a179fec8486db7b9e4ecb73c706fbfc`. Es existieren keine
Repository-spezifischen `AGENTS.md`- oder Beitragsanweisungen.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| nur Formulatorprompt ändern | Nicht ausgewählte IDs fehlen vollständig in Evidence | Schwanenteich kann weiterhin unerreichbar bleiben | auch Selectorprompt minimal präzisieren | Selectorpayload-/API-Test |
| Schwanenteich im Formulator hartcodieren | Formulator sieht nur finale Evidence und keine Fachauswahl | parallele, ungeerdete Auswahl | keine Namen oder IDs in Prompts | Promptinventartest |
| Kandidaten deterministisch mandatory machen | Nutzer wünscht Flexibilität, keine neue bindende Fachpriorität | unnötiger Eingriff in WP3-Regeln | nur Auswahlverhalten des Modells präzisieren | CandidateSelector unverändert |
| starres Muster ersatzlos entfernen | Frühere Live-Läufe veränderten Namen und Referral-Rollen | erneute Groundingfehler möglich | exakte Namen und Rollen weiter explizit verlangen; Injectionmuster behalten | Grounding-/Prompttests |
| alle Karteninhalte vorlesen | maximal drei Sätze und TTS-Kürze | überladene Antwort | je Angebot nur einen hilfreichen belegten Aspekt | Vertragstests |

## Recommended approach

Selectorprompt 3 verlangt bei mehreren gleich oder komplementär passenden
Kandidaten eine begrenzte Mehrfachauswahl und priorisiert bei explizitem
Zeitbezug den strukturierten `schedule_match_status=matched`. Formulatorprompt 14
ersetzt das feste normale Eröffnungsmuster durch natürliche rollenrichtige
Sätze, nennt bei mehreren finalen Angeboten bis zu drei Optionen in
Evidence-Reihenfolge und bindet jede Nennung an Anzeigename plus passenden Fakt.
Nur der Injectionfall nutzt weiterhin feste sichere Sprachmuster.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| neuer Vertragsstatus für Mehrfachauswahl | vorhandenes `selected_ids` unterstützt bereits mehrere IDs |
| mehr als drei Sätze/Angebote | widerspricht bestehender Kürze-, TTS- und Kartenbegrenzung |
| serverseitig zweiten Namen anhängen | erzeugt einen parallelen Formulierungsweg außerhalb des LLM-Vertrags |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/llm_selection.py` | Modify | Selectorprompt 3 | klein |
| `app/formulation.py` | Modify | Formulatorprompt 14 | klein |
| `tests/test_llm_selection.py` | Modify | Mehrfachauswahl-/Promptregression | klein |
| `tests/test_formulation.py` | Modify | natürliche Mehrangebotsantwort | klein |
| `tests/test_api.py` | Modify | Dienstag-End-to-End mit beiden Angeboten | klein |
| `docs/architecture.md` | Modify | aktive Promptsemantik | klein |
| `docs/data-flow.md` | Modify | Mehrangebotsfluss | klein |
| `docs/live-provider-evaluation.md` | Modify | aktive Promptidentität und Live-Grenze | klein |
| dieser Plan | Create/Update | Review- und Verifikationsnachweis | klein |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Angebot 14 ist dienstags bereits deterministisch zulässig. Die
verbleibende Reduktion findet im LLM-Selector statt; der Formulator kann nur
dessen finale Evidence verwenden.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

Evidence: Ausschließlich beide Promptkonstanten und Prompttexte wurden im
Runtimecode geändert. Verträge, CandidateSelector, Evidence, Grounding und
Ergebnisgrenzen blieben unverändert.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run integration/build checks where relevant.
- [x] Verify providerfreien Versionspfad.
- [x] Review final diff.

Evidence: 139 fokussierte Tests und 751 Gesamttests bestanden. `compileall`
und `git diff --check` waren erfolgreich. Der providerfreie Dry-Run meldete
Selectorprompt 3, Formulatorprompt 14 und
`live_provider_calls_authorized=false`.

### Milestone 4: Documentation

- [x] Apply the `code-documentation` checklist.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: Architektur, Datenfluss und Live-Evaluationsidentität dokumentieren
Mehrfachauswahl, natürliche Mehrangebotsantwort und das noch ausstehende reale
Modellgate.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Promptverträge | fokussierte Selector-/Formulatortests | Versionen und Mehrangebotsregeln stimmen |
| Dienstag Essen | API-Test mit Test-Double | Bahnhofsmission und Schwanenteich können final genannt werden |
| Regression | `python -m pytest -q` | vollständige Suite grün |
| Static quality | `compileall`; `git diff --check` | erfolgreich |
| Beobachtbarkeit | providerfreier Dry-Run | neue Promptversionen, 0 Provideraufrufe |

## Rollback and recovery

Es ändern sich keine Daten oder Schemas. Prompt-, Test- und Dokumentationshunks
können isoliert zurückgenommen werden.

## Progress log

- 2026-08-25 — Repository und aktiver Auswahl-/Formulierungsfluss geprüft; Plan
  vor Quellcodeänderung erstellt.
- 2026-08-25 — Promptversionen 3/14, Regressionstests und technische
  Dokumentation umgesetzt; vollständige providerfreie Verifikation bestanden.

## Decision log

- Decision: Selector- und Formulatorprompt gemeinsam, aber keine Fachlogik ändern.
  - Context: Ein nicht final ausgewähltes Angebot kann der Formulator nicht nennen.
  - Options: nur Formulator, deterministische neue Priorität, beide Prompts.
  - Choice: beide Prompts minimal präzisieren.
  - Consequences: flexiblere Mehrfachantwort ohne Umgehung der Fach- und Groundingregeln; reale Modellbefolgung bleibt separat zu evaluieren.

## Discoveries

- Angebot 14 und Bahnhofsmission (22) sind bei ausdrücklicher Dienstagsfrage
  beide bereits mit `schedule_match_status=matched` im Selectorindex. Die
  bestehende Ergebnisordnung stellt 22 vor 14; diese Reihenfolge gelangt
  unverändert in Evidence.

## Final verification summary

- Acceptance requirements: erfüllt
- Tests: 139 fokussierte und 751 vollständige Tests bestanden
- Build: Python-Syntaxprüfung erfolgreich; keine Paketressourcen geändert
- Manual verification: Dienstagspayload, finale Evidence-Reihenfolge und Diff geprüft
- Documentation: Architektur, Datenfluss und Live-Evaluation aktualisiert
- Residual risks: reale Providerbefolgung nur durch gesonderten Live-Lauf messbar
