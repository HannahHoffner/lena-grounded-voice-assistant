# Execution Plan: Interpretersemantik für Risiko, Scope und Bedarf präzisieren

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-24
- Last updated: 2026-08-24

## Objective

Der Interpreterprompt soll reine unmittelbare Gefahrenaussagen konsistent als
Teil der Safety-Domäne einordnen und daraus nicht ohne ausdrücklichen
medizinischen Bedarf `need=medical` ableiten. Die deterministische Safety-Policy
und ihr toleranter Vertrag bleiben unverändert.

## Acceptance contract

- [ ] Eine primäre konkrete oder mögliche unmittelbare Gefahrenaussage verlangt
  im Prompt `scope_status=in_scope`.
- [ ] Eine zusätzlich enthaltene eindeutig fachfremde Anfrage darf unabhängig
  davon `out_of_scope` bleiben; Safety und Scope bleiben getrennte Signale.
- [ ] Reine Selbst-/Fremdgefährdung verlangt `need=general_help|unknown`;
  `medical` setzt ausdrückliche medizinische Hilfe, Symptome oder einen akuten
  medizinischen Zustand voraus.
- [ ] Nur die Promptversion steigt von `7` auf `8`; Contractversion `4`, Schema,
  Safety-Priorität und Evaluationsszenarien bleiben unverändert.
- [ ] Providerfreie Tests sichern Prompttext, Versionierung und den bestehenden
  Safety-Vorrang bei `detected + out_of_scope` ab.
- [ ] Es erfolgen keine realen Provideraufrufe.

## Scope

### In scope

- Präzisierung des vorhandenen Interpreter-Systemprompts.
- Erhöhung und technische Nachverfolgbarkeit der Promptversion.
- Fokussierte Regressionstests und Aktualisierung der bestehenden WP9B-Dokumentation.

### Out of scope

- Änderung von Interpretervertrag, Pydanticschema oder Safety-Policy.
- Normalisierung oder Überschreiben einer validen Modellantwort.
- Anpassung der vorab festgelegten Evaluationserwartungen an den letzten Lauf.
- Live-Evaluation, Selector, Formulator, STT/TTS, Thesis oder Präsentation.

## Repository review

### Current behavior

Promptversion `7` verlangt eine unabhängige Risiko- und Scopebewertung, definiert
aber nicht eindeutig, wie reine Gefahrenaussagen in `scope_status` und `need`
abzubilden sind. Im Live-Lauf `run_710dc865c58c4b25af8f16cad85184ca`
entstanden deshalb zwei formal valide Inhaltsabweichungen: `medical` bei einer
reinen Suizidankündigung sowie `out_of_scope` bei einer unmittelbaren
Fremdgefährdung.

### Relevant architecture and data flow

`INTERPRETER_SYSTEM_PROMPT` und `INTERPRETER_PROMPT_VERSION` →
`BlabladorProvider.interpret_query()` → strikte `QueryInterpretation` →
`QueryService`, das `acute_risk_status` vor `scope_status` verarbeitet.

Der Live-Runner vergleicht die rohe validierte Interpretation mit unveränderten,
vorab gebundenen Erwartungen. Es findet keine nachträgliche Normalisierung statt.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Interpreterprompt/-version | `app/interpreter.py` | nur Safety-Abschnitt präzisieren und Version erhöhen |
| Promptvertragstests | `tests/test_interpreter.py` | zwei semantische Aussagen explizit absichern |
| Safety-Vorrangstest | `tests/test_safety_policy.py` | unverändert als Defense-in-Depth-Regel erhalten |
| WP9B-Betriebsdokument | `docs/live-provider-evaluation.md` | neue Promptversion und Anlass ergänzen |

### Existing tests and commands

- `python -m pytest tests/test_interpreter.py tests/test_safety_policy.py tests/test_live_evaluation.py -q`
- `python -m pytest -q`
- `python -m compileall -q app tests`
- `git diff --check`

### Working tree considerations

Der Arbeitsbaum war vor dieser Änderung auf Commit
`ea9a522e2274b132cbc479855e2107df44322055` sauber. Der neue Live-Report liegt
im ignorierten Runtimebereich und wird nicht verändert oder versioniert.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| `detected → in_scope` im Schema erzwingen | bestehender Test akzeptiert absichtlich `detected + out_of_scope` und priorisiert Safety | korrekt erkanntes Risiko würde als Schemafehler verworfen | Vertrag tolerant lassen, Prompt präzisieren | fünfsprachiger Safety-Policy-Test |
| Modellantwort deterministisch umschreiben | Live-Evaluation soll rohe Modellqualität messen | Fehler würde verborgen | keine Normalisierung | Runner-/Promptreview |
| Szenarioerwartungen nachträglich lockern | Erwartungen waren vor dem Lauf gebunden | methodisch unzulässiges Verschieben des Maßstabs | Erwartungen unverändert lassen | Katalogdiff |
| `medical` für jede Gefahr verbieten | akute medizinische Notfälle benötigen `medical` | falsche Klassifikation realer Symptome | nur Gefahr ohne medizinische Angabe abgrenzen | Prompttest |

## Recommended approach

Zwei kurze Regeln werden in den vorhandenen Safety-Absatz integriert. Sie
definieren reine Gefahrenaussagen als `in_scope`, lassen kombinierte fachfremde
Anfragen unabhängig klassifizierbar und grenzen `medical` anhand ausdrücklicher
medizinischer Angaben ab. Promptversion `8` macht die Messreihe reproduzierbar;
Contractversion und Szenariokatalog bleiben gleich.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Schema-/Contractversion erhöhen | keine Strukturänderung und würde sicheren toleranten Pfad unnötig verengen |
| Evaluationserwartungen erweitern | würde die beobachteten Abweichungen nachträglich passend machen |
| Safety-Policy ändern | Runtime reagiert bereits korrekt und deterministisch |
| Promptbeispiele mit konkreten Szenarios ergänzen | größerer, potenziell überangepasster Eingriff als zwei allgemeine Regeln |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/interpreter.py` | Modify | Promptsemantik und Version `8` | sehr klein |
| `tests/test_interpreter.py` | Modify | statische semantische Promptregression | klein |
| `docs/live-provider-evaluation.md` | Modify | aktive Version und Änderungsgrund dokumentieren | klein |
| diese Datei | Create/Update | Review- und Verifikationsnachweis | Dokumentation |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Prompt, Schema, Live-Erwartungen, Safety-Priorität und zugehörige Tests
wurden auf dem sauberen Ausgangscommit geprüft.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

Evidence: Nur Promptabsatz und Promptversion wurden geändert. Der vorhandene
Interpretervertrag, das Schema, der Safety-Kontrollfluss und der Szenariokatalog
sind unverändert. `app/interpreter.py` bleibt unter 400 Zeilen.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run lint/format/type checks.
- [x] Run integration/build checks where relevant.
- [x] Verify registration, imports, routes, configuration, and packaging.
- [x] Review final diff.

Evidence: 183 fokussierte Interpreter-, Safety- und Live-Evaluationstests sowie
die vollständige Suite mit 747 Tests bestanden. `compileall` und
`git diff --check` bestanden. Der providerfreie Dry-Run meldete Vertrag `4`,
Prompt `8`, unveränderten Szenariohash und
`live_provider_calls_authorized=false`.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: `code-documentation` wurde zu Beginn geladen. Das vorhandene
WP9B-Betriebsdokument trennt nun den abgeschlossenen Prompt-7-Lauf vom noch
nicht live evaluierten Prompt `8` und dokumentiert die unveränderten Grenzen.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Promptsemantik | fokussierte `tests/test_interpreter.py` | beide allgemeinen Regeln und Version `8` vorhanden |
| Safety-Regression | `tests/test_safety_policy.py` | `detected` gewinnt weiterhin auch bei `out_of_scope` |
| Evaluation | `tests/test_live_evaluation.py` | unveränderte Erwartungen/Katalog funktionieren providerfrei |
| Full suite | `python -m pytest -q` | vollständig grün, kein externer Transport |
| Syntax/Diff | `compileall`, `git diff --check` | Exit 0, keine Fremdhunks |

## Rollback and recovery

Keine Datenmigration oder Runtimepersistenz wird verändert. Eine Rücknahme
betrifft ausschließlich Prompttext, Promptversionskonstante, Test und
Dokumentationshunk; bestehende Live-Reports bleiben unverändert vergleichbar.

## Progress log

- 2026-08-24 — Review abgeschlossen und Minimalplan vor Quellcodeänderungen angelegt.
- 2026-08-24 — Promptversion `8`, zwei allgemeine Safety-Nebenfeldregeln und
  statische Regression implementiert; weder Schema noch Erwartungen geändert.
- 2026-08-24 — Fokussierte und vollständige Tests, Syntax, Diff und
  providerfreier Evaluations-Dry-Run erfolgreich abgeschlossen.

## Decision log

- Decision: Prompt präzisieren, Vertrag und Erwartungsdaten beibehalten.
  - Context: Zwei formal gültige, runtime-sicher behandelte Inhaltsabweichungen.
  - Options: Prompt, Schema, Normalisierung oder Erwartungsänderung.
  - Choice: allgemeine Promptregeln plus Versionsanhebung.
  - Consequences: Modellanforderung wird eindeutig; Defense in Depth und
    methodisch vorab gebundener Bewertungsmaßstab bleiben erhalten.

## Discoveries

- `tests/test_safety_policy.py::test_interpreter_detected_wins_over_scope_and_returns_no_results`
  schützt bewusst die Kombination `detected + out_of_scope` in allen Sprachen.
- Die bestehende Live-Evaluation bewertet nur einen verfehlten Risiko-Kernstatus
  als kritisch; Nebenfeldabweichungen bleiben sichtbar, ohne Safety zu umgehen.

## Final verification summary

- Acceptance requirements: erfüllt; Promptsemantik präzisiert, Vertrag und
  Defense in Depth unverändert.
- Tests: 183 fokussierte und 747 vollständige Tests bestanden.
- Build: vorhandene Packagingtests waren Bestandteil der vollständigen Suite;
  keine Paketressource oder Konfiguration wurde geändert.
- Manual verification: finaler Diff enthält keine Anpassung von Contractversion,
  Szenariokatalog, Safety-Policy oder Runtimeauswahl.
- Documentation: vorhandenes WP9B-Dokument aktualisiert und gegen Dry-Run geprüft.
- Residual risks: Mock- und statische Tests belegen Vertrag und Verdrahtung,
  nicht die reale mehrsprachige Modellbefolgung. Prompt `8` benötigt dafür nach
  sauberem Commit eine erneut ausdrücklich freigegebene Stufe-1-Evaluation.
