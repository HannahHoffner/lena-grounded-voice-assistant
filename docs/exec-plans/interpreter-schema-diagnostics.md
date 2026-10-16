# Execution Plan: Sichere Interpreter-Schemadiagnosen und Prompt-Vertrag

## Status

- State: Complete
- Owner: Codex
- Created: 2026-10-16
- Last updated: 2026-10-16

## Objective und Acceptance contract

- [x] Schemafehler liefern begrenzte Feldpfade und geschlossene Fehlercodes,
  ohne Eingaben, Rohantworten, unbekannte Feldnamen oder freie Exceptiontexte.
- [x] Diagnose erreicht Anwendungslog, Stufe-1-Berichte und E2E-Stufenfehler.
- [x] Prompt nennt alle semantischen Validatorregeln; Promptversion erhöhen.
- [x] Lokale Positiv-, Negativ-, Datenschutz- und Integrationstests bestehen.
- [x] Validatoren, Gates, Fallbacks, Modelle und Aufrufzahlen unverändert.

## Scope

In scope: freigegebene Schritte 1–3 (Diagnose, Promptabgleich, lokale Tests).
Out of scope: neue Live-Aufrufe, Interpreter-Retry, Lockerung der Kriterien,
Thesis, Abhängigkeiten, Paketierung, Commit und Versionshistorie.

## Repository review

Code `2fc0059bd2478ce43d6318dbad3aab5a7fd34ecd` ist sauber. Thesis enthält
zwei vorhandene Änderungen in Approach und Solution; beide bleiben unangetastet.
Keine AGENTS-/Contribution-Anweisung in Workspace/Eltern gefunden.
Python/FastAPI/Pydantic, setuptools; pytest ohne Cache/Bytecode und mit
`tests/conftest.py` zur Netz- und Runtime-Isolation. Keine Installation nötig.

`BlabladorProvider.interpret_query` parst JSON und validiert
`QueryInterpretation`. Pydantic-Fehler werden bisher auf einen Code reduziert.
`InterpreterError` trägt bereits redigierte HTTP-Diagnosen.
`EvaluationReportStore.append_error` prüft erlaubte Diagnosewerte;
`LimitedEvaluationProvider` ist die vorhandene Diagnosegrenze vor dem Service.
Stufe 1 fängt Exceptions direkt; E2E sieht nur den Service-Fallback.
Wiederverwendung dieser Wege statt öffentlicher API-/Interaktionsschemaänderung.

Promptreview: Typen, Pflichtfelder, Grenzen, Eindeutigkeit, Alterskonsistenz,
leerer District und Klärungsflag sind beschrieben. Die zusätzliche Kopplung
`out_of_scope`/`unknown` ist nicht explizit beschrieben. Keine Änderung der
Validatorsemantik erforderlich; Ursachen der ursprünglichen Live-Verwerfungen
bleiben mangels gespeicherter Details unbekannt. Zwei neue Diagnoseproben
waren gültig und ersetzen die gescheiterte Evaluation nicht.

## Dead-end analysis und verworfene Alternativen

| Risiko / Alternative | Beleg / Auswirkung | Maßnahme / Nachweis |
|---|---|---|
| Pydantic `errors()` unverändert loggen | input/msg/ctx und zusätzliche Feldnamen können Inhalte enthalten | Nur statische Pfadteile, geschlossene Typen; Datenschutztests |
| Nur Logger erweitern | Stufe 1 speichert aktuell keine Details | Auch Exception und bestehenden Reportstore anbinden |
| Öffentliche Response erweitern | unnötiger Datenvertrag und Diagnoseexposition | Diagnose nur intern, E2E über vorhandenen Providerwrapper |
| Stale Diagnose bei Folgeturn/Preflight | geteilter Providerzustand kann falsch zugeordnet werden | pro Aufruf/Turn leeren, Mehrturntest |
| Regeln lockern oder blind wiederholen | Originalursache unbekannt; Gateumgehung | unveränderte Validatoren und keine Live-Aufrufe |
| Neue generische Providerabstraktion | bestehendes `providers/diagnostics.py` vorhanden | dort kohäsiv ergänzen |

## Recommended approach und File impact

| Datei | Aktion / Zweck |
|---|---|
| `app/providers/diagnostics.py` | geschlossene, begrenzte Schemadiagnose und Serialisierung |
| `app/providers/llm.py` | Diagnose am vorhandenen Fehlerpfad; Logger/Exception |
| `app/interpreter.py` | fehlende Kopplungsregel, Promptversion 11 |
| `app/live_evaluation_runtime.py` | sicherer Reportstore, E2E-Wrappergrenze |
| `app/live_evaluation_runner.py` | Stage-1- und E2E-Diagnose in vorhandenen Reports |
| `tests/test_interpreter.py` | Versionsassertion aktualisieren, keine Assertions entfernen |
| `tests/test_interpreter_diagnostics.py` | fokussierte Regression/Datenschutz/Integration |
| `docs/architecture.md`, `docs/live-provider-evaluation.md`, `docs/data-flow.md` | finalen Diagnosevertrag und aktuelle Promptnummern beschreiben |

Große bestehende Provider-/Runnerdateien werden nur an bestehenden Grenzen
verdrahtet; die Diagnoseprojektion bleibt im kohäsiven Diagnosemodul. Keine
breite Dateiaufteilung im Messfinalisierungsschritt.

## Milestones

- [x] Review, Datenfluss, Wiederverwendung und Risiken prüfen.
- [x] Implementierung und negative Regression vor Implementierung nachweisen.
- [x] Gezielte Tests, breite Suite ohne Packaging, AST und Diffprüfung.
- [x] Skill `code-documentation` anwenden, Dokumentation und Diff selbst prüfen.

## Validation plan

`PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
`LENA_ENV_FILE_MODE=disabled`, `LENA_ALLOW_LIVE_SMOKE=false`.

- `python -B -m pytest -p no:cacheprovider tests/test_interpreter_diagnostics.py tests/test_interpreter.py tests/test_live_evaluation.py tests/test_observability.py`
- `python -B -m pytest -p no:cacheprovider --ignore=tests/test_packaging.py`
- AST aller Pythondateien; `git diff --check`, abschließender Status und Diff.
- Kein Build/Packaging, kein JUnit im Repo, keine automatischen Formatierungen.

## Rollback and recovery

Nur additive interne Diagnosen und versionierter Prompttext. Keine Migration,
Persistenzänderung regulärer Interaktionen oder Datenänderung. Bei Bedarf
gezielter inverser Patch nach Freigabe, kein destruktiver Git-Befehl.

## Progress / Decision log

- 2026-10-16: Plan vor Implementierung erstellt. Sichere Whitelist-Projektion
  statt freier Fehlertexte; keine Heilung/Normalisierung ungültiger Antworten.
- Neue Tests vor Implementierung scheitern beim Import des noch fehlenden
  Diagnosevertrags. Nach Implementierung: 217 gezielte Tests bestanden;
  nach zusätzlicher Absicherung beider Puffergrenzen 219 bestanden (57,12 s).
- `code-documentation` angewendet: vorhandene Architektur- und
  Live-Evaluationsdokumentation ergänzt, keine neue parallele Anleitung.
  Beispiel, Felder, acht Einträge, Leerdiagnosen, Datenschutz und Grenzen geprüft.
  Aktuelle Promptangaben in Datenflussbeschreibung und Identitätstabelle mit
  Konstanten abgeglichen (Interpreter 11, Formulator unverändert 18);
  historische Messberichte nicht umgeschrieben.
- AST aller 95 Pythondateien erfolgreich; alle Interpreter-Vertragsklassen
  einschließlich Validatoren AST-identisch zu HEAD. `git diff --check` bestanden.
  Die bestehenden großen Dateien bleiben Verdrahtungspunkte (Provider 423,
  Runner 976 Zeilen); Projektion im Diagnosemodul (123), neue Tests 211 Zeilen.
  Keine breite Refaktorierung kurz vor der Messung.

## Discoveries und Final verification summary

Gezielte Suite: 219 bestanden (57,12 s), eine vorhandene
Starlette-Deprecationwarnung. Breite Suite: 1063 bestanden, ein bekannter
strict xfail, eine vorhandene Starlette-Deprecationwarnung (212,83 s).
23 zusätzliche Fälle im neuen Testmodul. Alle Akzeptanzpunkte lokal belegt.
Keine Live-Aufrufe, keine Packagingprüfung und keine Thesisänderung.
Lokale Reports der Tests bleiben in pytest-Temporärverzeichnissen.
Abschließender Diff-/Statuscheck: nur die elf geplanten Code-, Test-, Plan-
und Dokumentationsdateien geändert beziehungsweise neu; die zwei bestehenden
Thesisänderungen bleiben unangetastet. Keine Commits angelegt.

Selbstreview nach `REVIEW_TEMPLATE.md`: Änderungen auf freigegebene Diagnose
und Promptvorgaben begrenzt; keine API-/Interaktionsschemaänderung, kein neuer
Retry, kein geändertes Gate und keine zusätzlichen Produktivaufrufe. Import und
beide Reportwege durch echte Provider-/Servicepfade mit gemocktem Transport
getestet. Sichere Ausgabe prüft unbekannte Feldnamen, Werte, Exceptiontexte,
Typen, Mengenbegrenzung, negative Vertragsfälle und Turn-/Aufrufgrenzen.
Bestehende Nutzeränderungen bleiben erhalten. Keine ungenutzten Symbole oder
neuen Abhängigkeiten im Diff. Kein Linter/Typechecker in pyproject konfiguriert;
keine Tools nachinstalliert, keine automatischen Formatierungen.

Restrisiko: neue Live-Vertragstreue ist lokal nicht beweisbar;
Originalverwerfungen sind rückwirkend nicht rekonstruierbar. Die begrenzte
Whitelist muss bei zukünftigen Vertragsänderungen überprüft werden. Neue
Pydantic-Fehlertypen werden auf `validation_error` reduziert, unbekannte
Value-Fehler auf `value_error` statt auf freie Exceptiontexte.
