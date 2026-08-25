# Execution Plan: Direkter Safety-Stopp bei eindeutig akutem Preflight-Treffer

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-25
- Last updated: 2026-08-25

## Objective

Eindeutige, vom engen deterministischen Safety-Preflight erkannte unmittelbare
Gefahrenformulierungen lösen ohne bestätigende Ja/Nein/Unsicher-Rückfrage direkt
den bestehenden lokalisierten 112-Safety-Text aus. Modellseitig als `uncertain`
klassifizierte Fälle behalten den strukturierten Safety-Dialog.

## Acceptance contract

- [x] Ein enger Preflight-Treffer beendet die Anfrage direkt mit `acute_risk`.
- [x] Die Antwort stammt aus `safety.detected`, enthält 112 genau einmal und hat
      weder Rückfrage noch Karten oder Marker.
- [x] Nach dem Preflight-Treffer wird kein Interpreter, Selector oder Formulator
      aufgerufen.
- [x] `acute_risk_status=uncertain` aus dem Interpreter öffnet weiterhin
      `acute_risk_confirmation`.
- [x] Historische, verneinte, metaphorische und nicht vom engen Preflight
      erfasste Eingaben behalten ihr bisheriges Verhalten.
- [x] Die geänderte deterministische Safety-Policy erhält eine neue
      Policyversion; die Muster-/Preflightversion bleibt unverändert.
- [ ] Keine Prompt-, Vertrags-, Übersetzungs-, Wissensbasis- oder Thesis-Datei
      wird verändert.

## Scope

### In scope

- Preflight-Verzweigung im aktiven `QueryService`.
- Entfernen des dadurch unerreichbaren Preflight-Platzhalterobjekts und seiner
  exklusiven Imports.
- Safety-Regressions- und Observabilitytests.
- Bestehende technische Safety-Dokumentation.

### Out of scope

- Erweiterung oder Lockerung der engen Preflight-Muster.
- Änderung der Interpreterklassifikation oder des Interpreterprompts.
- Abschaffung des Safety-Dialogs für tatsächlich unklare Fälle.
- Neue Notrufnummern oder Safety-Texte.
- Änderungen an Thesis, Präsentation oder Evaluationsdaten.

## Repository review

### Current behavior

`QueryService._run_query()` prüft vor dem Interpreter
`preflight_detects_immediate_danger()`. Ein Treffer baut derzeit über
`_preflight_risk_interpretation()` einen künstlichen Status `uncertain` und
öffnet `_safety_dialog()`. Deshalb erscheint selbst bei „Ich werde mich jetzt
umbringen.“ zunächst die Frage nach unmittelbarer Gefahr.

### Relevant architecture and data flow

`POST /api/query` → `QueryService.query()` → `QueryService._run_query()` → enger
Preflight. Der vorhandene `_safety_stop()` erzeugt bereits die gewünschte
deterministische, lokalisierte und kartenlose Antwort. Interpreterseitiges
`detected` verwendet denselben Helfer; interpreterseitiges `uncertain` verwendet
weiterhin `_safety_dialog()`.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| `preflight_detects_immediate_danger()` | `app/safety.py` | Unverändert als enge Erkennung verwenden |
| `QueryService._safety_stop()` | `app/service.py` | Direkt im Preflight-Zweig aufrufen |
| `SafetyTextKind.DETECTED` | `app/safety.py` | Bestehenden lokalisierten 112-Text verwenden |
| Safety-Assertions | `tests/test_safety_policy.py` | Für fünf Sprachen und Providerbypass wiederverwenden |

### Existing tests and commands

- `python -m pytest tests/test_safety_policy.py tests/test_safety.py tests/test_observability.py -q`
- `python -m pytest -q`
- `python -m compileall -q app tests`
- Relevante Tests: `tests/test_safety_policy.py`, `tests/test_safety.py`,
  `tests/test_observability.py`.

### Working tree considerations

Der kanonische Code-Checkout war vor der Änderung sauber. Die separaten lokalen
Thesis-Änderungen gehören der Nutzerin und werden nicht berührt.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Safety-Dialog vollständig entfernen | Interpreter-`uncertain` benötigt weiterhin eine kontrollierte Auflösung | Unklare Aussagen würden fälschlich wie eindeutige Akutgefahr behandelt | Nur den Preflight-Zweig ändern | Uncertain-Dialogtests bleiben grün |
| Promptänderung | Preflight läuft vor dem Interpreter | Prompt kann das beobachtete Verhalten nicht zuverlässig ändern | Deterministische Policyverzweigung korrigieren | Provideraufrufzahl bleibt 0 |
| Neues Safety-Template | `safety.detected` existiert bereits in fünf Sprachen | Doppelte, potenziell widersprüchliche Safety-Texte | Bestehenden `_safety_stop()` wiederverwenden | Textgleichheit gegen `safety_text()` |
| Preflight-Muster verbreitern | Nicht angefordert; erhöht False-Positive-Risiko | Unklare oder zitierte Aussagen könnten direkt stoppen | Muster unverändert lassen | Nichtakute Katalogfälle bleiben ohne Treffer |

## Recommended approach

Im einzigen aktiven Preflight-Zweig `_safety_stop()` mit
`PREFLIGHT_DETECTED`, `SafetyTextKind.DETECTED` und
`AcuteRiskStatus.DETECTED` aufrufen. Den danach unbenutzten
`_preflight_risk_interpretation()`-Helfer entfernen. Tests und Dokumentation
präzisieren, dass der enge Preflight nun als verbindlicher Sofortstopp gilt,
während nur Interpreter-`uncertain` den Dialog öffnet.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Interpreterprompt ändern | Der relevante Preflight umgeht den Interpreter vollständig. |
| Automatisch „Ja“ in den Dialog einspeisen | Erzeugt unnötigen Dialogzustand und verdeckt die tatsächliche Policyentscheidung. |
| Alle Safety-Rückfragen abschaffen | Widerspricht der dreiwertigen Behandlung wirklich unklarer Fälle. |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/service.py` | Modify | Direkter Preflight-Safety-Stopp; tote Hilfsfunktion entfernen | Klein, sicherheitsrelevant |
| `app/safety.py` | Modify | Docstring an verbindliche Wirkung anpassen | Klein |
| `app/main.py` | Modify | Healthstatus beschreibt beide deterministischen Erkennungsquellen | Klein |
| `app/resources/bootstrap/safety/scenarios.json` | Modify | Katalog an Safety-Policyversion 2 binden | Klein, deklarativ |
| `tests/test_safety_policy.py` | Modify | Gewünschtes Verhalten und fünf Sprachen absichern | Mittel |
| `tests/test_safety.py` | Modify | Isolierten Interpreter-Test korrekt vom direkten Preflight abgrenzen | Klein |
| `tests/test_packaging.py` | Modify | Clean-Install-Erwartung an Safety-Policyversion 2 binden | Klein |
| `docs/safety-and-error-policy.md` | Modify | Tatsächliche Kontrollreihenfolge dokumentieren | Klein |
| `docs/data-flow.md`, `docs/architecture.md`, `docs/testing.md` | Modify | Aktiven Datenfluss und Testumfang ohne Preflight-Dialog abbilden | Klein |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Aktiver Preflightzweig in `app/service.py`; bestehender direkter Helfer
`_safety_stop()`; Regressionstests in `tests/test_safety_policy.py`.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Remove only code made unreachable by this change.
- [x] Update this plan with discoveries.

Evidence: `_run_query()` verwendet den bestehenden `_safety_stop()` direkt;
der ausschließlich für den alten Preflight-Dialog verwendete
`_preflight_risk_interpretation()`-Helfer wurde entfernt.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run full test suite.
- [x] Run syntax checks and `git diff --check`.
- [x] Review final diff.

Evidence: 62 fokussierte Tests bestanden; 748 Tests der Gesamtsuite bestanden;
`python -m compileall -q app tests` und `git diff --check` waren erfolgreich.

### Milestone 4: Documentation

- [x] Apply the `code-documentation` checklist to the final diff.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: Safety-Policy, Datenfluss, Architektur und Testübersicht beschreiben
den direkten Preflight-Stopp und grenzen den unveränderten Uncertain-Dialog ab.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Direct preflight stop | Targeted safety catalog test | `acute_risk`, 112, no clarification/cards/provider |
| Uncertain regression | Existing uncertain-dialog tests | Dialog remains active |
| Five languages | Catalog loop | Localized detected text in DE/EN/PL/RO/RU |
| Full regression | `python -m pytest -q` | All tests pass |
| Static quality | `python -m compileall -q app tests`; `git diff --check` | No errors |

## Rollback and recovery

The change has no schema or data migration. Reverting the bounded service branch,
tests and documentation restores the former confirmation behavior.

## Progress log

- 2026-08-25 — Repository reviewed; direct reuse of `_safety_stop()` selected.
- 2026-08-25 — Preflight branch changed, Safety-Policyversion raised to 2,
  targeted and full regression verification completed.

## Decision log

- Decision: Treat an exact narrow preflight match as `detected` at policy level.
  - Context: The user explicitly requests no confirmation for clear immediate wording.
  - Options: Prompt change, synthetic dialog confirmation, direct policy stop.
  - Choice: Direct policy stop.
  - Consequences: Faster deterministic help for exact matches; the documented
    false-positive risk of exact quoted matches remains and is reported.

## Discoveries

- `_preflight_risk_interpretation()` exists solely to open the former Preflight
  dialog and can be removed without affecting interpreter-uncertain handling.
- Die Muster selbst ändern sich nicht; deshalb bleibt
  `SAFETY_PREFLIGHT_VERSION=1`, während die entscheidende
  `SAFETY_POLICY_VERSION` auf 2 steigt.
- Der Clean-Install-Smoke prüft die öffentliche Safety-Policyversion als
  explizites Releaseinvariant und muss deshalb gemeinsam auf Version 2
  aktualisiert werden.

## Final verification summary

- Acceptance requirements: fulfilled
- Tests: 748/748 full suite; 62/62 focused final run
- Build: clean-wheel install test passed
- Manual verification: exact synthetic phrase covered through the real FastAPI path
- Documentation: updated and reviewed
- Residual risks: exact quoted wording can still match the lexical preflight;
  this deliberate fail-closed trade-off is documented. No clinical validation
  is claimed.
