# Execution Plan: Nachweisbare Interpreter-Fehlerfixture

## Status

- State: Complete
- Owner: Codex
- Created / Last updated: 2026-10-20

## Objective and acceptance contract

- [x] Das Katalogflag löst am Evaluationsprovider tatsächlich einen geschlossenen
  Interpreterfehler aus, ohne externen Aufruf; die echte QueryService-Fehlerbehandlung läuft.
- [x] Reiz, Auslösung und Aufrufdifferenzen werden pro Turn protokolliert.
- [x] Nur ein bestätigter injizierter Fehler mit korrektem Fallback und ohne
  Folgestufenaufrufe gilt als erfolgreicher Fehlerpfad; unerwartete Fehler bleiben Fehler.
- [x] Gespeicherte E2E-Verwerfungen werden lokal differenziert eingeordnet.
- [x] Providerfreie Regression, bestehende Laufgrenzen und historische Reports bleiben erhalten.

## Scope

In scope: Evaluationswrapper, E2E-Runner/-Prüfer, Fehlerfixture, lokale Tests,
vorhandene Evaluationsdokumentation. Out of scope: neue Live-Aufrufe, Thesis,
produktive Service-/Groundingänderungen, Änderung anderer Szenarioerwartungen,
Modell-/Promptänderungen, manuelle Evaluation oder neue Resultatbehauptungen.

## Repository review

Current behavior: `app/resources/bootstrap/evaluation/live_scenarios.json:67`
setzt `inject_interpreter_error`, aber `_run_e2e_scenario()` übergibt nur normale
QueryRequests. `LimitedEvaluationProvider` kapselt bereits jeden realen Aufruf,
zählt Versuche und sichert Verwerfungen. `QueryService` behandelt InterpreterError
selbst und liefert den lokalisierten technischen Hilfebuspfad. Der E2E-Runner
markiert jeden Stagefehler als technisch ungültig, ohne absichtliche Reize zu trennen.
`_evaluate_e2e()` prüft nur beobachtbare Kriterien; Unbekanntes bleibt None.

Existing structures: `app/live_evaluation_runtime.py` (Wrapper/Counter),
`app/live_evaluation_runner.py` (echter Anfragepfad),
`app/live_evaluation_checks.py` (versionierte Kriterien),
`tests/test_live_evaluation.py` (FakeFullPipelineProvider/Settings),
`tests/conftest.py` (Netzwerksperre/Runtimeisolation).
Python/FastAPI, pytest; keine Installation nötig.

Working tree: code sauber auf fa670f4569982694febfcc3d53dc44d62928193c.
Thesis hat zwei vorbestehende Änderungen (Approach/Solution); nicht anfassen.
Keine AGENTS-Dateien im Workspace oder kanonischen Repository gefunden.

## Dead-end analysis / rejected alternatives

| Ansatz | Problem | Gegenmaßnahme / Nachweis |
|---|---|---|
| Nur Fixtureerwartung auf clarification ändern | Testet keinen Ausfall | echten Fehler an Wrappergrenze injizieren |
| Beliebige Interpreterfehler ignorieren | Maskiert reale Ausfälle | nur bestätigten künstlichen Reiz mit passendem Fallback ausnehmen |
| Fehler vor service.query werfen | Umgeht App-Fehlerbehandlung | erst in interpret_query werfen |
| Globalen Provider patchen | Leckt in Folgeszenarien | eng begrenzter Kontext mit finally-Rücksetzung |
| Alle Verwerfungen lockern | Vermischt Unterbelegung und Parsergrenzen | zunächst Report-/Codeanalyse, keine pauschale Änderung |
| Alle ungeprüften Kriterien als bestanden zählen | Unzulässige Vollständigkeit | None und Unvollständigkeitsanzeige beibehalten |

## Recommended approach / file impact

| Datei | Änderung / Risiko |
|---|---|
| app/live_evaluation_runtime.py | begrenzte Fehlerinjektion am Wrapper, klein |
| app/live_evaluation.py | Katalogversion und strikte Boolean-/Single-Turn-Prüfung der Fehlerfixture |
| app/live_evaluation_runner.py | Kontext, Turnprovenienz, enge Erwartungsfehlerbehandlung; bestehende große Orchestrierungsdatei, keine sachfremde Aufteilung |
| app/live_evaluation_checks.py | nachweisbare Fallback-/Injektionskriterien, Assessmentversion erhöhen |
| app/resources/bootstrap/evaluation/live_scenarios.json | Hilfebus-konforme Fehlerfixture, Hash bindet Änderung |
| tests/test_live_evaluation_fault_injection.py | fokussierte Regression über echte QueryService-Orchestrierung |
| docs/live-provider-evaluation.md | aktueller Prüfpfad, Grenzen, Diagnoseeinordnung |

## Milestones

- [x] Review und Wiederverwendung / Risiken geprüft; Plan vor Codeänderung gespeichert.
- [x] Implementierung und negative Regression.
- [x] Zieltests, gesamte pytest-Suite ohne Cache/Bytecode; git diff --check.
- [x] Selbstreview nach REVIEW_TEMPLATE und code-documentation anwenden.

## Validation plan

`python -B -m pytest -p no:cacheprovider tests/test_live_evaluation_fault_injection.py
tests/test_live_evaluation.py tests/test_live_evaluation_checks.py`;
danach gesamte Suite mit externem Temp-Verzeichnis, ohne Live-/Quellaufrufe.
Nachweis: Fixture ausgelöst, 0 echte Calls, lokaler Hilfebuskontakt ohne Karte auf
Landkarte, Zustand nach Fehler/Exception zurückgesetzt; fehlende Injektion,
falscher Fallback und zusätzliche Fehler bestehen nicht. Bestehende Gates und
Budgets nur mit explizit ausgewiesener erfolgreicher Fehlerfixture kompatibel.

## Rollback and recovery

Nur reviewbare Quelldiffs; keine Migration, Abhängigkeit, Datenaktivierung oder
Laufreportänderung. Einzelne Hunks können nach Review zurückgenommen werden.

## Discoveries and decision log

- Die bisherige Fehlerfixture verbietet offer_card pauschal; das widerspricht
  dem freigegebenen optionalen Hilfebuskontakt. Stattdessen erlaubt die Prüfung
  ausschließlich dessen ID und verbietet jegliche Standort-/Markerempfehlung.
- Absichtlicher Fehler muss als gemessener Reiz sichtbar bleiben; kein stilles
  Löschen des stage_errors-Eintrags. Der Versionswechsel bindet die neue Auswertung.
- Bestätigt: echte QueryService-Orchestrierung liefert bei injiziertem Fehler
  die Hilfebusvorlage, mit 0 realen Provideraufrufen; nächster Turn ruft wieder
  den normalen Provider auf. Auch Exception und fehlender Wrapper sind geprüft.
- Zielprüfung: 106 bestanden in 23,24 s, davon 22 neue Fixture-/Negativfälle.
- Providerfreie Nachanalyse auf unverändertem KB-Fingerprint: e_water und
  e_dialog_continuation über echten Anfragepfad mit kontrollierter Interpretation
  und Wiedergabe der gespeicherten Formulatoroutputs; alle verwendeten Fakt-IDs
  im aufgebauten Paket. Verwerfung an grounding.py:486 (фонтан), :491
  (bez barier), :403 (tel.). Bestätigte Erkennungs-/Negations-/Abkürzungsgrenzen,
  keine nachgewiesene Unwahrheit dieser drei einzelnen Formulierungen.
- Sozialangebotspakete lokal rekonstruiert: alle deklarierten Fakt-IDs der
  untersuchten Food-/Hilfebussätze vorhanden. Imbiss‑Mittagessen löst kein
  food-Konzept aus; der Hilfebus-Serviceclaim scheitert dagegen wegen des
  bewusst eingeschränkten Kontaktpakets. Andere Zusatzbehauptungen sind damit
  nicht semantisch validiert.
- out_of_scope-Verwerfungen: Varianten der Grenzformel plus fehlende
  unterstützte Domänen. Enumfehler des Sprachwechsels nur redigiert belegt,
  konkrete falsche Werte nicht rekonstruierbar.
- code-documentation nach Implementierung angewandt: vorhandene
  docs/live-provider-evaluation.md aktualisiert, veralteten aktuellen
  Runnerbefund ersetzt, historische Reports/Review unverändert gelassen.

## Concrete follow-up decisions (not implemented here)

1. Hoch: Negationsbezug von „bez barier“ begrenzen und echte Leistungsverneinung
   weiterhin zurückweisen; zusätzliche Abkürzung tel. ohne Mehrsatzfreigabe.
2. Mittel: geschlossenen Leistungswortschatz um die belegten Essenskomposita
   und den ausgewählten Trinkbrunnen-Kontext erweitern, jeweils mit Negativfällen.
3. Mittel: Hilfebus-Betriebszeit als operativen Fakt statt SERVICE ausgeben;
   Domänengrenzformeln / Pflichtinhalte gezielt auf Prompt und Validator abstimmen.
4. Hoch vor neuer finaler Messung: nicht akute Hilfesituation fachlich behandeln
   (Rückfrage statt out_of_scope), keine pauschale Lockerung der Erwartung.
5. Interpreter-Enumfehler separat am Vertrag bearbeiten, keine erfundenen Rohwerte.

## Final verification summary

- Acceptance: alle Punkte für die Runnerkorrektur und Diagnose erfüllt.
- Targeted: 106 bestanden, 23,24 s; 22 neue Fixturefälle durch collect-only bestätigt.
- Full regression: `python -B -m pytest -p no:cacheprovider
  --junitxml=C:/Users/User/AppData/Local/LENA/evaluations/20261020-fa670f4/fault-fixture-engineering-results.xml`:
  1141 bestanden, ein bekannter strict xfail, eine vorhandene
  Starlette-Deprecationwarnung, 311,68 s. Testtransporte netzwerkgesperrt.
- Static: AST aller 59 Pythondateien unter app gültig; git diff --check bestanden
  (nur bestehende Git-LF/CRLF-Konfigurationshinweise). Keine Formatter ausgeführt.
- Build: nicht ausgeführt; Paketstruktur/Abhängigkeiten unverändert, JSON bleibt
  unter bestehendem Package-Data-Glob. Keine Browser-/STT-/TTS-/Livevalidierung.
- Self-review nach REVIEW_TEMPLATE: Änderungen auf Evaluationspfad begrenzt,
  echter QueryService statt nachgebautem Fallback, keine globalen Providerpatches,
  Kontext auch bei Ausnahme zurückgesetzt; Positiv-/Negativfälle geprüft.
  Alle neuen Strukturen über Runner importiert/verwendet bzw. pytest-discovered.
  Kein Public-API-/Konfigurations-/Produktivschemawechsel; keine Geheimnisse in
  neuen Beobachtungsfeldern. Große bestehende Runnerdatei nur gezielt erweitert;
  zusätzliche Extraktion würde hier sachfremde Orchestrierungsänderungen erzeugen.
- Documentation: vorhandene Evaluationsdokumentation aktualisiert; keine
  historische Messung, Gates oder Ergebnisartefakte umgeschrieben.
- Working tree: ausschließlich die neun geplanten App-Repositorydateien geändert
  bzw. neu; nicht committet. Thesis unverändert mit den zwei vorbestehenden Änderungen.
- Residual risks: bestätigte Grounding-Fehlalarme, fachlicher nonacute-Pfad und
  Interpreter-Schemafehler sind konkrete Folgeschritte, keine verdeckten Fixes.
  Keine neue Live-Messung oder abschließende E2E-Freigabe durchgeführt.
