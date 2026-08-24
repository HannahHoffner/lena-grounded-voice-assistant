# Formulator-Zitierdisziplin: Promptversion 9

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-24
- Last updated: 2026-08-24

## Objective

Der Formulator soll im sicheren Minimalmodus keine Leistungs- oder
Zielgruppenaussage aus der Nutzerfrage wiederholen, wenn er den dafür
erforderlichen Evidence-Fakt nicht im selben Satz referenziert. Der bestehende
strikte Groundingvertrag bleibt unverändert.

## Acceptance contract

- [x] Promptversion 9 verbietet, `current_query` als Faktenquelle zu behandeln.
- [x] Referral-Antworten verwenden standardmäßig nur Kontaktverb plus exakten Namen.
- [x] Direct-Service-Antworten verwenden standardmäßig nur Handlung plus exakten Namen.
- [x] Servicewörter verlangen im selben Satz einen zitierten Service-, Capability-
  oder Description-Fakt; Zielgruppenwörter einen Zielgruppen-, Geschlechts-,
  Alters- oder Access-Fakt.
- [x] Bei Unsicherheit lässt das Modell Details weg, statt Fakten zu ergänzen.
- [x] Vertrag, Evidence, Grounding, Modelle, Timeouts und Laufgrenzen bleiben gleich.
- [x] Providerfreie fokussierte und vollständige Tests bestehen; keine Live-Aufrufe.
- [x] Keine Thesis- oder Präsentationsdatei wird verändert.

## Scope

### In scope

- Ausschließlich `FORMULATOR_SYSTEM_PROMPT` und dessen Version.
- Prompt-/Health-/Payloadregressionstests.
- Unmittelbar betroffene technische Evaluationsdokumentation.

### Out of scope

- Grounding- oder Vertragsänderungen.
- Automatisches Ergänzen fehlender Faktenreferenzen.
- Retry-, Modell-, Token-, Timeout- oder Provideränderungen.
- Live-Evaluation oder Stufe 3.

## Repository review

### Current behavior

- HEAD `2a3a510f3525b7e2833bb944cdf45a9a35bae84f`, sauberer Arbeitsbaum vor Plananlage.
- Der Lauf `run_4c052751169e48098691e9b5955b64ac` lieferte nach sechs
  gültigen Selectorantworten exakt `service_fact_missing` für deutschen Normal-
  und Injectionfall sowie `target_fact_missing` für den englischen Normalfall.
- Die Validatoren fanden damit belegbar sichtbare Service-/Zielgruppenwörter,
  während die jeweils zitierten `fact_ids` keine passende Faktenklasse enthielten.
- Prompt 8 empfiehlt bereits eine minimale Antwort, formuliert aber nicht
  ausdrücklich, dass `current_query` keine Faktenquelle ist und dass bei fehlender
  Referenz das sichtbare Service-/Zielgruppenwort vollständig entfallen muss.

### Relevant architecture and data flow

Der Prompt wird als unveränderter Systemtext an
`BlabladorProvider.formulate_answer()` übergeben. `FormulatorEvidence.current_query`
ist untrusted Kontext; nur `selected_offers[].facts` und `binding_policies` dürfen
Behauptungen belegen. Pydantic und `validate_formulation()` prüfen anschließend
atomar. Health und WP9B-Manifeste beziehen die Promptversion aus derselben Konstante.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Formulatorprompt | `app/formulation.py` | bestehenden Prompt präzisieren |
| Prompttests | `tests/test_formulation.py` | Diagnoseanforderungen als Stringinvarianten ergänzen |
| Health/Manifest | `app/main.py`, `app/live_evaluation_plan.py` | unverändert automatische Versionsübernahme |

### Existing tests and commands

- `tests/test_formulation.py`: Prompt, Vertrag, Grounding und Health.
- `tests/test_api.py`: realer Payload-/Fallbackpfad mit Doubles.
- `tests/test_live_evaluation.py`: stufengebundener Runner.
- Geplant: fokussiertes Pytest, vollständiges Pytest, Compileall, Dry-Run,
  `git diff --check`.

### Working tree considerations

Keine lokalen Änderungen vor Plananlage. Ignorierte Live-Reports werden nicht
verändert. Codex erstellt keinen Commit.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Validator lockern | Diagnose belegt fehlende Referenz | Halluzinationen würden passieren | nur Prompt ändern | Angriffsregression bleibt grün |
| Fact-ID automatisch ergänzen | sichtbare Semantik ist nicht vollständig maschinell ableitbar | falsches Grounding | Modell muss selbst korrekt zitieren oder Detail weglassen | Providerparsertests |
| Service-/Zielgruppenwortlisten vergrößern | bestehende Erkennung hat korrekt ausgelöst | behebt Modellzitat nicht | Prompt an vorhandene Faktenklassen binden | Prompttest |
| Live-Gate mit Fallback als bestanden zählen | misst nicht mehr Modellvertrag | methodisch falsches Ergebnis | Gate unverändert | Runnerregression |

## Recommended approach

Promptversion 9 ergänzt wenige imperative Regeln: `current_query` ist niemals
Evidence; sichere Standardsätze nennen nur den exakten Namen; sichtbare Service-
und Zielgruppeninformationen sind nur bei passender Faktenklasse zulässig;
ansonsten werden sie weggelassen. Das ist der kleinste belegbasierte Eingriff.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Neuer Formulatorvertrag | beobachteter Fehler liegt in der Vertragserfüllung, nicht im Schema |
| Deterministische vollständige Antwort statt LLM | würde die vorgesehene Formulatorstufe ersetzen |
| Weitere Diagnoseinstrumentierung | die benötigten Regelklassen sind jetzt präzise bekannt |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/formulation.py` | Modify | Promptversion 9 und Zitierdisziplin | klein |
| `tests/test_formulation.py` | Modify | Prompt-/Healthregression | klein |
| `docs/live-provider-evaluation.md` | Modify | aktive Promptversion und Änderungsgrenze | klein |
| dieser Plan | Create/Update | Review- und Prüfnachweis | Dokumentation |

## Milestones

### Milestone 1: Review and design

- [x] Aktuellen Lauf, Diagnosecodes, Prompt und Validatoranforderungen geprüft.
- [x] Dead Ends und kleinsten Eingriff bestimmt.

### Milestone 2: Implementation

- [x] Promptversion 9 implementieren.
- [x] Regressionstests aktualisieren.

Evidence: `FORMULATOR_PROMPT_VERSION="9"` und explizite Promptinvarianten in
`tests/test_formulation.py` sowie Health-/Dry-Run-Beobachtbarkeit.

### Milestone 3: Verification

- [x] Fokussierte und vollständige Tests ausführen.
- [x] Compileall, Dry-Run und Diff prüfen.
- [x] Finalen Diff nach Review-Template prüfen.

Evidence: 149 fokussierte und 751/751 vollständige Tests bestanden; Compileall,
providerfreier Stufe-2-Dry-Run und `git diff --check` erfolgreich.

### Milestone 4: Documentation

- [x] `code-documentation` auf finalen Diff anwenden.
- [x] Dokumentation prüfen und Tests wiederholen.

Evidence: bestehende `docs/live-provider-evaluation.md` auf Promptversion 9 und
die belegte Referenzdisziplin aktualisiert; keine Thesisdatei verändert.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Promptregeln | `tests/test_formulation.py` | alle neuen Invarianten vorhanden |
| API/Runner | fokussierte Tests | bestehender Vertrag unverändert |
| Gesamt | `pytest -q` | vollständig grün |
| Static | Compileall, Dry-Run, Diffprüfung | erfolgreich, Provideraufrufe 0 |

## Rollback and recovery

Keine Datenmigration. Prompt- und Testhunks können einzeln zurückgenommen
werden; Grounding, Runtime-KB und Providerkonfiguration bleiben unangetastet.

## Progress log

- 2026-08-24 — Review abgeschlossen; Plan vor Quellcodeänderung erstellt.
- 2026-08-24 — Promptversion 9 und Regressionstest implementiert.
- 2026-08-24 — 751/751 Tests, Syntax, Dry-Run und Diffprüfung bestanden; technische Dokumentation aktualisiert.

## Decision log

- Decision: Sichtbare Details weglassen, sofern passende Faktenreferenz fehlt.
  - Context: reale Antworten nannten Service/Zielgruppe ohne korrekte Faktklasse.
  - Choice: sicherer Namens-/Handlungsminimalmodus im Prompt.
  - Consequences: kürzere Antworten; operative Details bleiben in den Karten.

## Discoveries

- Die neue Diagnose trennte zuverlässig fehlende Service- von fehlenden
  Zielgruppenreferenzen; eine weitere Validatoränderung ist nicht begründet.

## Final verification summary

- Acceptance requirements: erfüllt.
- Tests: 149 fokussierte und 751/751 vollständige Tests bestanden.
- Build: Packaging-/Clean-Install-Regressionspfade der Gesamtsuite grün;
  `python -m compileall -q app tests` erfolgreich.
- Manual verification: Dry-Run zeigt Formulatorprompt 9 bei unverändertem
  Vertrag, Szenariohash, Runtime-KB-Fingerprint und Stufe-2-Limits.
- Documentation: bestehende technische Evaluationsdokumentation aktualisiert;
  keine Thesis- oder Präsentationsdatei geändert.
- Residual risks: reale Modellkonformität erfordert nach sauberem Commit eine
  neue ausdrückliche Stufe-2-Freigabe; Stufe 3 bleibt gesperrt.
