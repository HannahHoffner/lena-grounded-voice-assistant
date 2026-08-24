# Exakte Eigennamenbindung und redigierte Formulatordiagnose

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-24
- Last updated: 2026-08-24

## Objective

Der Groundingvalidator muss veränderte Eigennamen wie `Rücken` statt `Rücke`
atomar verwerfen. Verbleibende `formulator_ungrounded_claim`-Fehler sollen in
ignorierten WP9B-Laufreports durch geschlossene, inhaltsfreie Diagnosecodes
unterschieden werden, ohne Modellrohausgaben oder Evidence-Werte zu speichern.

## Acceptance contract

- [x] Zitierte Anzeigenamen und Aliase müssen als vollständige, exakt geschriebene
  Textspanne erscheinen; bloße Präfixe in veränderten Wörtern genügen nicht.
- [x] `Rücken` wird für den freigegebenen Namen `Rücke` abgewiesen; `Rücke` bleibt gültig.
- [x] Jeder `formulator_ungrounded_claim` aus dem Groundingmodul besitzt einen
  geschlossenen, nicht sensitiven Diagnosecode.
- [x] Der öffentliche/runtimewirksame Fehlercode bleibt unverändert
  `formulator_ungrounded_claim`; Diagnosewerte erscheinen nur in lokalen,
  ignorierten Evaluationsreports.
- [x] Reportstore akzeptiert ausschließlich allowlist-basierte Diagnosewerte.
- [x] Providerfreie fokussierte und vollständige Tests bestehen.
- [x] Keine Provideraufrufe, Thesis- oder Präsentationsänderungen.

## Scope

### In scope

- Exakte Namens-/Aliasprüfung in `app/grounding.py`.
- Geschlossenes Diagnose-Enum und optionale interne Fehlerdiagnose.
- Redigierte Persistenz in WP9B-`stage-results.jsonl` und
  `redacted-errors.jsonl`.
- Grounding-, Reportstore- und Runnerregressionstests.
- Unmittelbar betroffene technische Dokumentation.

### Out of scope

- Speicherung von Modellrohausgaben, Sätzen, Faktenwerten oder Prompts bei Fehlern.
- Lockerung von Grounding-, Rollen-, Fakten-, Sprach- oder Safetyprüfungen.
- Weitere Promptänderung ohne präzisen Diagnosebefund.
- Live-Wiederholung, Stufe 3, Modell- oder Providerkonfiguration.

## Repository review

### Current behavior

- HEAD `16c46744351333900f009550162bb644f9eeb1a2`, Arbeitsbaum vor diesem Plan sauber.
- Der freigegebene Stufe-2-Lauf `run_6d5cb18bd50245448a0d7861c0e56af5`
  stoppte nach 6 gültigen Selector- und 4 Formulatorcalls an drei Fehlern.
- Die einzige validierte Formulatorantwort schrieb den Namen `Rücke` als
  `Rücken`. `_validate_sentence()` erkennt Namen per Teilstring und prüft danach
  erneut nur den Teilstring; deshalb gilt `Rücke in Rücken` fälschlich als exakt.
- Drei weitere Antworten wurden korrekt als `formulator_ungrounded_claim`
  verworfen. Die 21 Auslösestellen verwenden denselben öffentlichen Code, und
  Rohantworten werden absichtlich nicht gespeichert; die genaue Regel ist daher
  nachträglich nicht unterscheidbar.
- `EvaluationReportStore.append_error()` besitzt bereits eine geschlossene
  Allowlist für Providerfehlerarten. Dieses Muster kann für Groundingdiagnosen
  wiederverwendet werden.

### Relevant architecture and data flow

`BlabladorProvider.formulate_answer()` parst `FormulatorResponse` und ruft
`validate_formulation()` auf. `FormulatorError` propagiert den redigierten
Runtimecode. Der isolierte Runner fängt diesen Fehler ab und schreibt nur
strukturierte Resultate sowie `redacted-errors.jsonl` in den gitignorierten
Evaluationsbereich.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| `FormulatorError` | `app/formulation.py` | optionalen geschlossenen Diagnosewert ergänzen |
| Groundingvalidator | `app/grounding.py` | Namenprüfung korrigieren, Auslösestellen klassifizieren |
| Providerdiagnose-Allowlist | `app/providers/diagnostics.py` | Sicherheitsmuster nachbilden, keine Freitexte |
| Reportstore | `app/live_evaluation_runtime.py` | optionales allowlist-validiertes Feld ergänzen |
| Stufe-2-Runner | `app/live_evaluation_runner.py` | Diagnosewert ohne Inhalt weiterreichen |

### Existing tests and commands

- `tests/test_formulation.py`: Namen, Alias, Rollen und Groundingangriffe.
- `tests/test_live_evaluation.py`: Runner- und Reportstore-Redaktion.
- `tests/test_api.py`: öffentlicher Formulatorfehler-/Fallbackpfad.
- Verifikation: fokussiertes und vollständiges Pytest, Compileall, Dry-Run,
  `git diff --check`.

### Working tree considerations

Die Live-Reports bleiben ignoriert und unverändert. Es bestanden vor Plananlage
keine Nutzeränderungen. Kein Commit wird durch Codex erstellt.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Nur `fact.value in text` verwenden | `Rücke in Rücken` ist wahr | veränderte Namen passieren | Wortgrenzen plus exakte Schreibweise | expliziter Regressionstest |
| Freie Diagnosemeldungen speichern | könnten Fakten/Modelltext enthalten | Datenschutz- und Secret-Risiko | geschlossenes Enum, Store-Allowlist | Negativtest für unbekannten Wert |
| Rohantwort speichern | nicht erforderlich und bisher verboten | unnötige Inhaltsablage | nur Regelklasse persistieren | Reportinventartest |
| Alle Fehler als eine neue grobe Klasse markieren | keine bessere Ursachenklärung | weitere Änderungen bleiben blind | jede bestehende Schutzklasse separat codieren | Test jeder Hauptklasse |
| Validator lockern, um Gate zu bestehen | drei Antworten waren unbelegt | Halluzinationsrisiko | Schutzregeln unverändert | bestehende Angriffstests |

## Recommended approach

Ein `GroundingDiagnosticCode`-Enum benennt ausschließlich Validatorregelklassen.
`FormulatorError` trägt optional diesen Enumwert zusätzlich zum unveränderten
öffentlichen Code. Eine kleine Literalprüfung verlangt Wortgrenzen und exakte
Schreibweise für zitierte Namen/Aliase und erkennt teilstringartige Abwandlungen.
Der Live-Runner persistiert ausschließlich den Enumwert; der Store validiert ihn
gegen die geschlossene Allowlist.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Linguistische Stemming-/Flexionslogik | Eigennamen dürfen gerade nicht flektiert werden; unnötig komplex |
| Diagnosecode als beliebiger String | keine belastbare Redaktionsgrenze |
| Öffentliche API-Fehler detaillieren | interne Validatorstruktur gehört nicht in Nutzerantworten oder Health |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/formulation.py` | Modify | geschlossenes Diagnosemodell im bestehenden Fehlervertrag | klein |
| `app/grounding.py` | Modify | exakte Namenbindung und Regelklassifikation | mittel, sicherheitsrelevant |
| `app/live_evaluation_runtime.py` | Modify | Diagnose-Allowlist bei Persistenz erzwingen | klein |
| `app/live_evaluation_runner.py` | Modify | Diagnosecode in lokalen Report weiterreichen | klein |
| `tests/test_formulation.py` | Modify | Namen- und Diagnosefälle | mittel |
| `tests/test_live_evaluation.py` | Modify | Runner-/Store-Redaktion | mittel |
| `docs/live-provider-evaluation.md` | Modify | Diagnosegrenze dokumentieren | klein |
| dieser Plan | Create/Update | Review- und Prüfnachweis | Dokumentation |

## Milestones

### Milestone 1: Review and design

- [x] Aktuellen Commit, Laufreport, Namenprüfung und alle Groundingauslöser geprüft.
- [x] Reportstore-Allowlist und Runnerfehlerpfad verfolgt.
- [x] Datenschutz- und Dead-End-Grenzen festgelegt.

### Milestone 2: Implementation

- [x] Diagnosemodell und exakte Namenbindung implementieren.
- [x] Runner und Store allowlist-basiert verbinden.
- [x] Tests ergänzen.

Evidence: `GroundingDiagnosticCode`, `_contains_exact_literal()`, strikt
validierender `EvaluationReportStore` sowie Namen-/Runner-/Storetests.

### Milestone 3: Verification

- [x] Fokussierte und vollständige Tests ausführen.
- [x] Syntax, Dry-Run und Diff prüfen.
- [x] Finalen Diff nach Review-Template prüfen.

Evidence: 149 fokussierte und 751/751 vollständige Tests bestanden; Compileall,
providerfreier Stufe-2-Dry-Run und `git diff --check` erfolgreich.

### Milestone 4: Documentation

- [x] `code-documentation` auf finalen Diff anwenden.
- [x] Dokumentation prüfen und betroffene Tests wiederholen.

Evidence: bestehende `docs/live-provider-evaluation.md` um Zweck, Allowlist und
Datenschutzgrenze der Groundingdiagnose ergänzt; keine neue parallele Anleitung.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Namenbindung | fokussierter `tests/test_formulation.py`-Test | `Rücken` abgelehnt, `Rücke` akzeptiert |
| Diagnoseklassen | Groundingtests | öffentlicher Code gleich, interner Enumwert präzise |
| Reportredaktion | `tests/test_live_evaluation.py` | nur allowlist-basierter Code, kein Inhalt |
| API-Regression | `tests/test_api.py` | sicherer Fallback unverändert |
| Gesamt | `pytest -q` | vollständig grün |
| Static | `python -m compileall -q app tests`; `git diff --check` | erfolgreich |

## Rollback and recovery

Keine Datenmigration. Alle Änderungen sind additive Fehlerdiagnose oder eine
engere Validierung und können hunkweise zurückgenommen werden. Runtime-KB,
Übersetzungen und Providerkonfiguration bleiben unverändert.

## Progress log

- 2026-08-24 — Review abgeschlossen und Plan vor Quellcodeänderung erstellt.
- 2026-08-24 — Exakte Namenbindung und geschlossene Diagnosen implementiert.
- 2026-08-24 — 751/751 Tests, Syntax, Dry-Run und Diffprüfung bestanden; technische Dokumentation aktualisiert.

## Decision log

- Decision: Groundingdiagnosen als geschlossenes Enum, nicht als Freitext.
  - Context: Ursachen müssen unterscheidbar sein, ohne Modellinhalt zu speichern.
  - Choice: technische Regelklassen mit Allowlist.
  - Consequences: neue Fälle müssen bewusst versioniert/ergänzt werden.
- Decision: Eigennamen wortbegrenzt und case-sensitiv prüfen.
  - Context: Substringprüfung akzeptierte `Rücken` für `Rücke`.
  - Choice: exakte Literalspanne; teilstringartige Abwandlung wird verworfen.
  - Consequences: bewusst keine automatische Flexion kuratierter Eigennamen.

## Discoveries

- Der neue Lauf beseitigte den früheren Schemafehler, offenbarte aber eine
  unabhängig davon bestehende Teilstringlücke der Namenprüfung.
- `app/grounding.py` und `app/formulation.py` liegen bereits aufgrund ihrer
  zusammenhängenden Vertrags-/Validatorinventare über dem 400-Zeilen-Richtwert.
  Eine Extraktion nur für diese eng begrenzte Korrektur würde Sicherheitslogik
  verteilen und den Diff unverhältnismäßig vergrößern; sie wurde bewusst nicht
  vorgenommen.

## Final verification summary

- Acceptance requirements: erfüllt.
- Tests: 149 fokussierte und 751/751 vollständige Tests bestanden.
- Build: Packaging-/Clean-Install-Regressionspfade der vollständigen Suite grün;
  `python -m compileall -q app tests` erfolgreich.
- Manual verification: providerfreier Stufe-2-Dry-Run erfolgreich; Quellsuche
  bestätigt, dass kein direkter undiagnostizierter Groundingfehlerpfad verbleibt.
- Documentation: bestehende technische Evaluationsanleitung aktualisiert;
  keine Thesis- oder Präsentationsdatei geändert.
- Residual risks: Die drei konkreten realen Groundingregelklassen sind erst im
  nächsten autorisierten Lauf sichtbar. Danach ist eine belegbasierte, getrennte
  Entscheidung nötig; Stufe 3 bleibt bis zu einem bestandenen Gate gesperrt.
