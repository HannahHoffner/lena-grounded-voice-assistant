# Formulator: unveränderliche Eigennamen und enger Referral-Prompt (Version 10)

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-24
- Last updated: 2026-08-24

## Objective

Der reale Formulator soll kuratierte Eigennamen exakt und unverändert aus dem
Evidence-Paket übernehmen. Referral-Antworten sollen weder den Bedarf noch eine
Leistung nennen, wenn dafür kein passender Fakt im selben Satz zitiert wird.

## Acceptance contract

- [ ] Ausschließlich der Formulator-Systemprompt und seine Version ändern.
- [ ] Eigennamen Zeichen für Zeichen kopieren; keine Flexion, Übersetzung,
  Abkürzung oder Endung.
- [ ] `referral_contact` auf Kontaktaufforderung plus exakten Anzeigenamen
  begrenzen, sofern kein zusätzlicher Fakt sicher zitiert wird.
- [ ] Bedarf und Leistung ohne passenden Service-/Capability-/Description-Fakt
  vollständig weglassen.
- [ ] Vertrag, Evidence, Grounding, Fallback, Modelle und Limits unverändert lassen.
- [ ] Providerfreie Fokus- und Gesamttests bestehen; keine Live-Aufrufe.
- [ ] Keine Thesis- oder Präsentationsdatei ändern.

## Scope

### In scope

- `FORMULATOR_SYSTEM_PROMPT` und `FORMULATOR_PROMPT_VERSION`.
- Prompt-, Health- und Beobachtbarkeitstests.
- Unmittelbar betroffene technische Evaluationsdokumentation.

### Out of scope

- Formulatorvertrag, Evidence oder Groundingvalidatoren.
- Automatische Textkorrektur oder nachträgliche Namensnormalisierung.
- Provider-, Modell-, Timeout- oder Retryänderungen.
- Ein weiterer Live-Lauf oder WP9B-Stufe 3.

## Repository review

### Current behavior

Der saubere HEAD `550cebf8604dc3a6f5b4e3fab7841af6a150767c` verwendet
Formulatorprompt 9. Der autorisierte Stufe-2-Lauf
`run_852281b82fb44f9287dd63dc8580d58c` bestand alle tatsächlich ausgeführten
Selectorfälle sowie beide englischen Formulatorfälle, wurde aber nach drei
Formulatorfehlern beendet: zweimal `proper_name_not_exact` für das deutsche
Rücke-Referral und einmal `service_fact_missing` für das polnische
Hilfebus-Referral. Die atomare Groundingprüfung verwarf alle drei Antworten.

### Relevant architecture and data flow

`FORMULATOR_SYSTEM_PROMPT` wird in `app/formulation.py` kanonisch versioniert
und vom Provider als Systemtext verwendet. Das Modell erhält nur das validierte
Evidence-Paket. `validate_formulation()` prüft anschließend Namen, Faktklassen,
Rollen und Karten atomar. Health, Dry-Run und Live-Manifeste lesen die Version
aus derselben Konstante.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Kanonischer Formulatorprompt | `app/formulation.py` | Bestehenden Prompt präzisieren |
| Prompt-/Healthtests | `tests/test_formulation.py` | Invarianten auf Prompt 10 erweitern |
| Evaluationsdokumentation | `docs/live-provider-evaluation.md` | Aktive Version und Grenze korrigieren |

### Existing tests and commands

- `tests/test_formulation.py`: Prompt-, Vertrag-, Grounding- und Healthregression.
- `tests/test_api.py`: Formulatorpayload und Fallbackpfad mit Test-Doubles.
- `tests/test_live_evaluation.py`: Runner, Manifest und redigierte Diagnosen.
- Geplant: fokussiertes Pytest, vollständiges Pytest, Compileall, WP9B-Dry-Run
  und `git diff --check`.

### Working tree considerations

Der Arbeitsbaum war vor der Plananlage sauber. Ignorierte Live-Reports werden
nicht verändert. Es wird kein Commit erstellt.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Grounding lockern | Die Validatoren erkannten reale Vertragsverstöße korrekt | Falsche Namen oder unbelegte Leistungen könnten sichtbar werden | Validatoren unverändert lassen | Groundingtests bleiben grün |
| „Rücken“ automatisch zu „Rücke“ korrigieren | Modellrohausgaben werden bewusst nicht persistiert; allgemeine Normalisierung wäre mehrdeutig | Unkontrollierte Inhaltsänderung | Exaktes Kopieren bereits im Prompt erzwingen | Promptinvariant und bestehende Namensregression |
| Leistungsfakt automatisch ergänzen | Sichtbare Aussage und passender Fakt sind nicht sicher mechanisch zuzuordnen | Scheingrounding | Unbelegte Leistung im Prompt vollständig verbieten | Referral-/Injectiontests |
| Live-Lauf sofort wiederholen | Messreihen dürfen nicht während einer Änderung fortgesetzt werden | Nicht reproduzierbare Evaluation | Erst providerfrei verifizieren, dann gesonderte Freigabe | Reale Calls = 0 |

## Recommended approach

Promptversion 10 ergänzt wenige imperative Regeln: Anzeigenamen sind
unveränderliche Ausgabetokens und werden Zeichen für Zeichen kopiert; auch
Grammatik rechtfertigt keine Veränderung. Der Referral-Minimalmodus darf nur
Kontaktverb plus Anzeigename enthalten. Bedarf oder Leistung entfallen, wenn
kein passender Fakt sicher zitiert wird. Das ist der kleinste Eingriff, der die
drei beobachteten Fehler direkt adressiert, ohne die Sicherheitsprüfung zu
schwächen.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Vertrag oder Grounding ändern | Fehler liegt in der Modellausgabe, nicht im Schutzvertrag |
| Deterministische Vollformulierung | Würde die freigegebene LLM-Formulatorstufe ersetzen |
| Mehrsprachige Regex-Ausnahmen | Fragil und würde unbelegte Behauptungen eher akzeptieren |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/formulation.py` | Modify | Promptversion 10 und präzisere Invarianten | klein |
| `tests/test_formulation.py` | Modify | Prompt-/Healthregression | klein |
| `docs/live-provider-evaluation.md` | Modify | aktive Promptversion und Evaluationsgrenze | klein |
| dieser Plan | Create/Update | Review- und Prüfnachweis | Dokumentation |

## Milestones

### Milestone 1: Review and design

- [x] Anweisungen, Arbeitsbaum, Promptpfad, Tests und Laufdiagnosen geprüft.
- [x] Wiederverwendbare Struktur und Dead Ends bestimmt.

Evidence: sauberer HEAD; Diagnosecodes aus dem ignorierten lokalen Laufreport;
Prompt 9 und `validate_formulation()` im aktiven Pfad nachvollzogen.

### Milestone 2: Implementation

- [x] Promptversion 10 implementieren.
- [x] Regressionstests aktualisieren.

Evidence: `FORMULATOR_PROMPT_VERSION="10"`; unveränderliche Namens-Tokens,
Referral-Minimalmodus und abschließende stille Vertragsprüfung sind im
kanonischen Systemprompt verankert. Health- und Prompttests erwarten Version 10.

### Milestone 3: Verification

- [x] Fokussierte und vollständige Tests ausführen.
- [x] Compileall, Dry-Run und Diff prüfen.
- [x] Finalen Diff anhand des Review-Templates prüfen.

Evidence: 149 fokussierte Tests sowie 751/751 Tests im abschließenden
Gesamtlauf bestanden. Compileall und `git diff --check` erfolgreich. Der
providerfreie Stufe-2-Dry-Run meldet Formulatorprompt 10, unveränderte Verträge,
`live_provider_calls_authorized=false` und den erwarteten KB-Fingerprint.

### Milestone 4: Documentation

- [x] `code-documentation` auf den finalen Diff anwenden.
- [x] Dokumentation prüfen und betroffene Checks wiederholen.

Evidence: `docs/live-provider-evaluation.md` beschreibt die Ursache und die
enge Prompt-10-Entscheidung ohne eine Freigabe oder erfolgreiche Live-Evaluation
zu behaupten. Keine Thesis- oder Präsentationsdatei wurde verändert.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Promptregeln | `pytest -q tests/test_formulation.py` | Prompt 10 und bestehende Groundingregeln grün |
| Integrationsregression | fokussierte API-/Live-Evaluationstests | Version beobachtbar, Verträge unverändert |
| Gesamt | `pytest -q` | vollständige Suite grün |
| Static/Plan | Compileall, providerfreier Dry-Run, Diffprüfung | erfolgreich, Provideraufrufe 0 |

## Rollback and recovery

Keine Daten- oder Schemamigration. Prompt-, Test- und Dokumentationshunks sind
isoliert rücknehmbar; Grounding, Runtime-Wissensbasis und Providerkonfiguration
bleiben unverändert.

## Progress log

- 2026-08-24 — Plan nach vollständiger Review vor Quellcodeänderung erstellt.
- 2026-08-24 — Promptversion 10 und Regressionstests implementiert; 149
  fokussierte Tests bestanden.
- 2026-08-24 — Erster Gesamtlauf: 750 Tests bestanden, ein unveränderter
  Sessiontest scheiterte einmal an `session.write.failed`; isolierte Wiederholung
  bestand. Abschließender Gesamtlauf: 751/751 bestanden.
- 2026-08-24 — Compileall, providerfreier Stufe-2-Dry-Run, Dokumentationsreview,
  Scopekontrolle und `git diff --check` erfolgreich; Plan abgeschlossen.

## Decision log

- Decision: Prompt-only-Nachbesserung bei unverändert strenger Validierung.
  - Context: Drei reale Formulatorantworten verletzten Namen- beziehungsweise
    Faktenbindung; die Prüfungen arbeiteten korrekt.
  - Options: Prompt präzisieren, Validator lockern, Modelltext korrigieren.
  - Choice: Prompt präzisieren.
  - Consequences: Das Modell erhält engere sprachliche Freiheit; ungültige
    Antworten fallen weiterhin sicher auf Templates zurück.

## Discoveries

- Der globale `pytest`-Befehl ist in der aktuellen PowerShell nicht im `PATH`;
  `python -m pytest` verwendet die bereits vorhandene Umgebung ohne Installation.
- `app/formulation.py` umfasst 570 Zeilen. Eine Extraktion nur wegen der
  Promptänderung wäre sachfremd und riskanter als der kleine bestehende Hunk;
  die Modulstruktur wurde deshalb bewusst nicht verändert.
- Ein Sessiontest zeigte in einem von drei relevanten Läufen einen atomaren
  Schreibfehler im unveränderten Sessionpfad. Isolierte und vollständige
  Wiederholung bestanden; innerhalb dieses Promptpakets besteht kein belegter
  Änderungsbedarf am Sessioncode.

## Final verification summary

- Acceptance requirements: erfüllt; ausschließlich Promptversion, Prompttest
  und unmittelbar betroffene technische Dokumentation geändert.
- Tests: 149 fokussierte und abschließend 751/751 vollständige Tests bestanden.
- Build: `python -m compileall -q app tests` erfolgreich; kein Packagingbedarf
  durch reine Python-Konstanten-/Dokumentationsänderung.
- Manual verification: Stufe-2-Dry-Run zeigt Promptversion 10 bei unverändertem
  Vertrag, Szenariohash, KB-Fingerprint und Laufgrenzen; reale Provideraufrufe 0.
- Documentation: bestehende technische WP9B-Dokumentation aktualisiert; keine
  Thesis- oder Präsentationsdatei geändert.
- Residual risks: Reale Modellkonformität kann erst ein gesondert freigegebener
  erneuter Stufe-2-Lauf belegen.
