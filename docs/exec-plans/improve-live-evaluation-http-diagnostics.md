# Execution Plan: Redigierte HTTP-Diagnostik für Live-Evaluationen

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-24
- Last updated: 2026-08-24

## Objective

Ein später erneut freigegebener WP9B-Interpreterlauf soll bei einem
`interpreter_http_error` erkennen lassen, ob der Provider beispielsweise mit
Rate-Limit, anderem 4xx, 5xx, Verbindungs- oder Protokollfehler reagierte. Der
ignorierte Evaluationsreport speichert dafür nur eine feste redigierte
Fehlerklasse und bei einer HTTP-Antwort den numerischen Statuscode. Secrets,
Header, Antwortkörper, URLs und Exceptiontexte bleiben ausgeschlossen.

## Acceptance contract

- [ ] Der bestehende Runtimecode `interpreter_http_error` und sein sicherer
  Fallback bleiben kompatibel.
- [ ] HTTP 429, sonstige 4xx, 5xx, Verbindungs-, Protokoll- und sonstige
  Transportfehler werden über eine geschlossene Fehlerklassifikation getrennt.
- [ ] Ein HTTP-Status wird nur als validierte Ganzzahl aus einer tatsächlichen
  `httpx.HTTPStatusError`-Antwort übernommen.
- [ ] `redacted-errors.jsonl` und das zugehörige fehlgeschlagene Stufenergebnis
  enthalten ausschließlich die redigierte Klasse und gegebenenfalls den Status.
- [ ] Keine Providerantwort, Header, URL, Exceptionnachricht oder sonstige
  sensible Information gelangt in den Report.
- [ ] Providerfreie Tests decken Klassifikation, Speicherung, Redigierung und
  die bestehende Fehlergrenze ab; reale Provideraufrufe bleiben null.

## Scope

### In scope

- Redigierte Klassifikation technischer Interpreter-Providerfehler.
- Weitergabe dieser sicheren Diagnose an den isolierten WP9B-Stufe-1-Runner.
- Allowlist-basierte atomare Speicherung im Evaluationsreport.
- Fokussierte Tests und Aktualisierung der bestehenden Live-Evaluationsdokumentation.

### Out of scope

- Erneute Live-Evaluation oder andere reale Provideraufrufe.
- Änderung von Retry-, Timeout-, Fehlergrenzen-, Prompt- oder Vertragslogik.
- Speicherung von Providerantworten, Headern, URLs oder Exceptiontexten.
- Änderungen an Selector/Formulator, fachlicher Runtimepolitik, Thesis oder Präsentation.

## Repository review

### Current behavior

`BlabladorProvider._post()` ruft `raise_for_status()` auf. `interpret_query()`
fasst danach jede `httpx.HTTPError` unter `InterpreterError("interpreter_http_error")`
zusammen. `run_interpreter_live_gate()` speichert nur `exc.code`; daher ist für
den Lauf `run_7484e6b2e8564f349e9c275fe474c72c` nachträglich weder der HTTP-Status
noch die Transportfehlerklasse bestimmbar. Nach drei Fehlern beendet
`AtomicRunCounter.record_failure()` den Lauf entsprechend dem unveränderten
Kataloglimit.

### Relevant architecture and data flow

`BlabladorProvider._post()` → `BlabladorProvider.interpret_query()` →
`InterpreterError` → `run_interpreter_live_gate()` →
`EvaluationReportStore.append_result()` / `append_error()` → ignorierter Pfad
`runtime/live-evaluations/<run-id>/`.

Der normale Anfragepfad liest weiterhin ausschließlich `InterpreterError.code`
und darf keine zusätzlichen Providerdetails in Nutzerantworten oder das
Interaktionsprotokoll übernehmen.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| `InterpreterError` | `app/providers/llm.py` | Um sichere optionale Diagnosefelder erweitern; Fehlercode beibehalten |
| `EvaluationReportStore` | `app/live_evaluation_runtime.py` | Atomaren JSONL-Pfad erweitern und Eingaben defensiv allowlisten |
| `run_interpreter_live_gate()` | `app/live_evaluation_runner.py` | Diagnose nur im isolierten Stufe-1-Report weiterreichen |
| Providerparsertests | `tests/test_interpreter.py` | HTTP-/Transportklassifikation providerfrei testen |
| WP9B-Runnertests | `tests/test_live_evaluation.py` | Reportinhalt und Secret-Redaktion testen |
| Live-Betriebsdokument | `docs/live-provider-evaluation.md` | Redigierte Diagnostik und Grenze bestehender Reports dokumentieren |

### Existing tests and commands

- `python -m pytest tests/test_interpreter.py tests/test_live_evaluation.py -q`
- `python -m pytest -q`
- `python -m compileall -q app tests`
- `git diff --check`

### Working tree considerations

`docs/live-provider-evaluation.md` war vor dieser Änderung bereits durch die
Nutzerin beziehungsweise den vorausgehenden freigegebenen Evaluationslauf
geändert. Diese Hunks bleiben erhalten; die neue Dokumentation wird nur
ergänzt. Keine vorhandene Änderung wird zurückgesetzt oder neu formatiert.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Gesamten Exceptiontext speichern | `httpx`-Fehler können URL, Requestdetails oder Providertext enthalten | Secret-/Datenschutzrisiko | geschlossene Enumklasse plus optionale Statuszahl | Tests mit eingebettetem Geheimtext |
| Nur HTTP-Status speichern | Verbindungs- und Protokollfehler besitzen keinen Status | Ursache bleibt erneut unklar | getrennte sichere Transportklassen | parametrischer Klassifikationstest |
| Runtime-Fehlercodes aufsplitten | Service/Safety/Tests erwarten `interpreter_http_error` | unnötiger API- und Fallbackumbau | öffentlichen Code unverändert lassen | bestehende Interpreter-/Safetytests |
| Fehlerklasse aus `str(exc)` ableiten | instabil und potenziell sensibel | falsche Klassifikation/Leak | ausschließlich `isinstance()` und Statuszahl verwenden | adversarialer Redigierungstest |
| Aktuellen alten Report nachträglich ergänzen | Originalstatus wurde nicht gespeichert | erfundene Diagnose | alten Report unverändert lassen; Verbesserung gilt nur für neue Läufe | Dokumentationsprüfung |

## Recommended approach

`InterpreterError` erhält optionale, typisierte und nicht im Fehlertext
enthaltene Diagnosefelder. Eine kleine deterministische Funktion klassifiziert
`httpx`-Ausnahmen ausschließlich anhand ihres Typs und – bei
`HTTPStatusError` – des numerischen Status. Der Live-Runner übernimmt diese
Felder in Ergebnis und Fehlerdatei. Der Store akzeptiert nur bekannte Klassen
und Statuswerte von 100 bis 599. Damit bleibt der normale Runtimepfad
unverändert und der nächste autorisierte Lauf ist ohne sensible Rohdaten
diagnostizierbar.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Vollständige Providerantwort oder Stacktrace archivieren | nicht erforderlich und mit Secret-/Datenschutzgrenzen unvereinbar |
| Nur Konsole ausführlicher loggen | nicht reproduzierbar an die opake Run-ID gebunden |
| Alle LLM-Stufen gleichzeitig umbauen | überschreitet die konkrete Diagnose des Stufe-1-Abbruchs |
| Sofortiger erneuter Live-Lauf | nicht freigegeben; die Änderung wird ausschließlich providerfrei geprüft |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/providers/diagnostics.py` | Create | zentrale geschlossene Fehlerklassifikation | klein |
| `app/providers/llm.py` | Modify | sichere Fehlerklassifikation und Diagnosefelder | klein, kompatibel |
| `app/live_evaluation_runtime.py` | Modify | defensiv redigierte Reportfelder | klein |
| `app/live_evaluation_runner.py` | Modify | Diagnose an Stufe-1-Report weitergeben | klein |
| `tests/test_interpreter.py` | Modify | Klassifikations- und Redigierungstests | klein |
| `tests/test_live_evaluation.py` | Modify | Report- und Abbruchregression | klein |
| `docs/live-provider-evaluation.md` | Modify | Betriebsdokumentation ergänzen, bestehende Hunks erhalten | klein |
| diese Datei | Create/Update | Review-, Plan- und Verifikationsnachweis | Dokumentation |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Status, bestehender Diff, Skills, WP9B-Plan, Provider-, Runner-, Store-
und Testpfad wurden am 2026-08-24 vor Quellcodeänderungen geprüft.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

Evidence: `InterpreterError` trägt eine typisierte Diagnose, der Runner gibt sie
nur an den Evaluationsstore weiter, und der Store erzwingt Allowlist sowie eine
konsistente Statusbindung. Die kohäsive Klassifikation liegt in
`app/providers/diagnostics.py`; dadurch bleibt `app/providers/llm.py` unter 400
Zeilen. `app/live_evaluation_runner.py` war bereits vor dieser Änderung größer
und erhielt nur einen lokalen, kohäsiven Hunk.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run lint/format/type checks.
- [x] Run integration/build checks where relevant.
- [x] Verify registration, imports, routes, configuration, and packaging.
- [x] Review final diff.

Evidence: 151 fokussierte Interpreter-/Live-Evaluationstests bestanden nach der
ersten Implementierung und erneut nach der Modulextraktion. Die vollständige
providerisolierte Suite bestand mit 745 Tests auf dem finalen Anwendungscode.
Der danach ergänzte reine Regressionstest für `transport_error` bestand mit dem
gesamten Interpretermodul. `compileall` und `git diff --check` bestanden; die
bereits bestehende Starlette-Deprecation-Warnung bleibt unverändert.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: `code-documentation` wurde zu Beginn geladen; die bestehende
WP9B-Betriebsdokumentation beschreibt nun die neuen Felder, ihre geschlossene
Semantik, die Redaktionsgrenze und die Nichtrekonstruierbarkeit des alten Laufs.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Providerklassifikation | `python -m pytest tests/test_interpreter.py -q` | 429/4xx/5xx/Connect/Protocol/Transport korrekt, keine Secrets |
| Evaluationsreport | `python -m pytest tests/test_live_evaluation.py -q` | sichere Diagnosefelder, dritter Fehler bricht weiterhin ab |
| Regression | `python -m pytest -q` | vollständige Suite ohne Netzwerkzugriff grün |
| Static quality | `python -m compileall -q app tests` | Exit 0 |
| Diff | `git diff --check` und manueller Hunkreview | keine Whitespacefehler oder Fremdhunks |

## Rollback and recovery

Die Änderung migriert keine Daten und verändert keine aktiven Runtimepointer.
Neue optionale JSONL-Felder sind rückwärtskompatibel; alte Reports bleiben
unverändert lesbar. Eine Rücknahme umfasst ausschließlich die hier aufgeführten
Hunks und diese Planergänzung. Es werden keine Nutzeränderungen zurückgesetzt.

## Progress log

- 2026-08-24 — Plan nach vollständiger Pfad- und Diffprüfung erstellt; reale
  Provideraufrufe bleiben ausdrücklich ausgeschlossen.
- 2026-08-24 — Typisierte Providerdiagnose, defensiver Reportstore und
  Stufe-1-Weitergabe implementiert; Runtimecode blieb kompatibel.
- 2026-08-24 — Klassifikation nach Diffreview in ein kohäsives Providermodul
  extrahiert; Dokumentation aktualisiert und alle vorgesehenen Prüfungen
  providerfrei abgeschlossen.

## Decision log

- Decision: Fehlercode und redigierte Providerdiagnose trennen.
  - Context: Der bestehende Code schützt Runtime und Logs, verliert aber die
    Ursache technischer Evaluationsfehler.
  - Options: Rohfehler speichern, Runtimecodes aufsplitten, typisierte Diagnose
    ergänzen.
  - Choice: typisierte optionale Diagnose nur für den Live-Report.
  - Consequences: Neue Läufe sind auswertbar; alte Läufe bleiben ehrlich
    unbestimmt; Runtimekompatibilität und Secret-Redaktion bleiben erhalten.

## Discoveries

- Der aktuelle Report enthält nur `interpreter_http_error`; eine nachträgliche
  Rekonstruktion des Status ist technisch nicht möglich.
- Die drei technischen Fehler dauerten jeweils rund 0,4 Sekunden, was einen
  Timeout ausschließt, aber keine konkrete HTTP-Ursache beweist.
- Die normale Runtime benötigt keine Änderung: Sie liest weiterhin nur
  `InterpreterError.code`; Diagnosefelder erreichen weder Nutzerantwort noch
  Interaktionsprotokoll.
- Beim ersten Diffreview überschritt `app/providers/llm.py` 400 Zeilen. Die
  geschlossene Klassifikation wurde deshalb in `app/providers/diagnostics.py`
  extrahiert und vom Client sowie Store gemeinsam wiederverwendet.

## Final verification summary

- Acceptance requirements: erfüllt; sichere Klasse und optionaler Status werden
  nur für neue lokale Live-Evaluationsreports ausgegeben.
- Tests: fokussierte Module grün; vollständiger Anwendungscode mit 745 Tests
  grün; zusätzlicher abschließender Transportklassentest ebenfalls grün.
- Build: Packagingpfade waren Bestandteil der grünen Vollsuite; das neue
  Pythonmodul wird über das bestehende Paketlayout aufgenommen.
- Manual verification: vollständiger Diff auf Scope, Redigierung,
  Runtimekompatibilität und vorhandene Nutzerhunks geprüft.
- Documentation: bestehendes WP9B-Betriebsdokument ergänzt; keine parallele
  Dokumentation erzeugt.
- Residual risks: Der konkrete Status des Laufs vom 2026-08-24 bleibt mangels
  damaliger Speicherung unbekannt. Eine konkrete Diagnose entsteht erst bei
  einem erneut ausdrücklich freigegebenen Lauf.
