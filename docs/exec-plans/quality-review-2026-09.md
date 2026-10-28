# Execution Plan: Vollständiger Qualitätsreview und konservative Bereinigung

## Status

- State: Complete — sichere lokale Prüfung; dokumentierte Live-Grenzen bleiben offen
- Arbeitsbereich: Repository-Wartung
- Created: 2026-09-16
- Ausgangscommit: `534ffba` auf `maintenance/repository-cleanup`

## Objective und Acceptance contract

- [x] Einstieg, Quellen, Konfiguration, Tests, Git und vorhandene Änderungen prüfen.
- [x] Alle aktiven Module und zugehörige Verträge anhand des Codes beurteilen.
- [x] Nur belegte Fehler mit kleinen Änderungen korrigieren.
- [x] Jede Bereinigung mit Referenzen, Risiko und Entscheidung dokumentieren.
- Zurückgestellt auf Nutzerwunsch: zusätzliche Mermaid-Diagramme.
- [x] Gezielte Regressionen, Syntax, Paketinhalt und finalen Diff prüfen.
- [x] Ergebnisse, Grenzen und dateiweisen Änderungsnachweis festhalten.

## Scope

Enthalten: Review der gesamten Anwendung in `code/`, gezielte Fehlerkorrekturen,
nachgewiesen unerreichbare interne Zweige und aktuelle Betriebsdokumentation.
Keine neuen Laufzeitabhängigkeiten, Architekturumbauten oder API-Neugestaltung.
Unverändert bleiben fachliche Kuration, Übersetzungen, Releases, Safety-Texte,
Legacy-Schnittstellen, Forschungsdaten, Zugangsdaten, Git-Historie und Branches.
Keine produktiven LLM-, STT-, TTS-, WFS-, CSV-, KML- oder Kartenabrufe.

## Repository review

### Ausgangslage und vorhandene Änderungen

Der ursprüngliche Stand war sauber, mit 407 versionierten Dateien. Der vor der
Unterbrechung gestartete eigene Baselinelauf endete mit **754 passed, 1 warning
in 234.28s**. `compileall`, `pip check`, `git diff --check` und `--version`
waren erfolgreich; Python 3.14.3, Paketversion 0.2.0. Die einzige Warnung betrifft
den vorhandenen Starlette-TestClient/httpx-Vertrag. CI zielt auf Python 3.11.

Bei Wiederaufnahme liegen Claudes Änderungen vor: 212 gestagte Löschungen unter
`.claude/worktrees/` und 27 ungestagte Code-/Test-/Dokumentänderungen. Sie werden
erhalten und separat vom eigenen Zusatzreview ausgewiesen. Der Nutzer liefert
Claudes Bericht mit 754 erfolgreichen Tests vor und nach dessen Änderungen,
Paketinventar- und Startupprüfungen. Diese Angaben sind Fremdevidenz; zusätzliche
eigene Prüfungen konzentrieren sich entsprechend dem aktualisierten Auftrag auf
neue Änderungen und Lücken statt auf einen erneuten vollständigen Testlauf.

Claudes Bericht beschreibt einen bestehenden Testisolationsfehler mit möglichem
Verlust lokaler Sessions und eine teilweise Wiederherstellung. Der eigene alte
Baselinelauf verwendete ebenfalls den ungeschützten Stand. Eine lückenlose
Rekonstruktion früherer Sessioninhalte ist nicht belegt. Ab Wiederaufnahme werden
Runtime-/Datenhashes verglichen; sensible Inhalte werden nicht ausgegeben.

### Architektur und wiederverwendete Strukturen

`python -m app` startet Uvicorn mit `app.main:create_app`. Der Loader bindet
WFS-Stand, Kuration, Betreiberangebote und getrennte Infrastruktur-Releases zu
einer validierten Runtime-Sicht. `QueryService` verwaltet Session und Dialog,
Preflight, Interpretation, Fachauswahl, optionale LLM-Auswahl und geerdete
Formulierung. Drei Providerstufen teilen das vorhandene monotone Wartebudget.
Antwort/Karten/Marker werden lokalisiert und an Session/TTS gebunden. FastAPI
protokolliert das finale Paar lokal. Aktualisierungs- und Review-CLIs bleiben
getrennte betriebliche Einstiegspunkte; kein Quellenabruf in der Nutzeranfrage.

Bestehende Komponenten werden weiterverwendet: `DialogueUI`, `SessionStore`,
`DialogState`, Providerfehlerklassen, vorhandene Pydantic-Validatoren,
`release_storage`, Pytest-Fixtures sowie bestehende Architekturdokumente.

## Dead-end analysis

| Gefahr | Evidenz / Auswirkung | Entscheidung / Prüfung |
|---|---|---|
| Tests als pauschaler Qualitätsbeleg | Statische Frontendtests suchen nur Textfragmente; Zustandsübergänge können trotzdem falsch sein | Kleine ausführbare Offline-JS-Regressionen ergänzen |
| Breiter Selbstbeschreibungs-Shortcut | Teilstring vor Interpreter und Safety-Dialog kann Risikoprüfung umgehen | Reproduktion, enges Matching und Schutz des offenen Safety-Dialogs |
| Aktive Daten als Duplikate löschen | Checkout, Paketbootstrap und Releases erfüllen verschiedene Verträge | Alle behalten; Manifest-/Hash- und Paketprüfung |
| Große Module blind aufteilen | `service.py` bündelt bewusst die Orchestrierung | Keine neuen Schichten; nur nachweislich tote interne Zweige reduzieren |
| Vollsuite erneut mit lokaler Runtime | Ursprünglicher Testfehler kann Forschungsdaten überschreiben | Isolation prüfen, nur temporäre Testzustände und Hashvergleich |
| Fremde Änderungen überschreiben | 212 gestagte und 27 ungestagte Claude-Änderungen | Baseline-Patches gesichert; keine Index-/History-Änderung |

## Cleanup inventory vor weiteren Löschungen

| Ort | Zweck / Evidenz / Referenzen | Risiko | Aktion |
|---|---|---|---|
| `.claude/worktrees/agent-*` | Vier identische, nicht registrierte Altbäume; alle 212 Inhalte im kanonischen Git-Verlauf nachgewiesen; keine Paket-/Startreferenzen | niedrig | Claudes bereits gestagte Löschung beibehalten |
| Fünf gelöschte Definitionen und 17 Imports | Claudes Diff, aktuelle Referenz-/Exportprüfung | niedrig nach Prüfung | Vorhandene Änderungen beurteilen und erhalten |
| `service.py` nach Interpreterfehler-Rückgabe | `interpreter_failed` ist dort stets falsch; nachgelagerter Legacy-Fallback unerreichbar | niedrig nach Callsiteprüfung | Nur interne tote Bedingungen entfernen; öffentliche Legacy-Verträge erhalten |
| Caches und `dist/*0.1.0*` | Generiert, ignoriert, bereits von Claude entfernt | niedrig | Keine Wiederherstellung; neue Prüfausgaben außerhalb Checkout |
| `lena_code3.egg-info/` | Metadaten der editierbaren Installation, Version wird daraus gelesen | mittel | Behalten |
| `app/retrieval.py`, Env-Aliase | Dokumentierte Hilfs-/Kompatibilitätsverträge, Tests und Aufrufer | mittel | Behalten |
| `runtime/**`, `data/**`, Bootstrap, Fixtures und historische Pläne | Betrieb, Forschung, Migration, Paketversorgung und Entscheidungen | hoch | Behalten |

## Recommended approach und File impact

| Datei/Bereich | Geplante Änderung | Grund / Risiko |
|---|---|---|
| `app/static/app.js`, `dialogue.js`; Frontendtests | Request- und Dialogbusy-Zustand korrigieren | Reproduzierbarer Bedienfehler; kleiner Zustandsfix |
| `app/service.py`, `dialogue_flow.py`; Safety-/Dialogtests | Verifizierte Shortcut-/Faktenfehler beheben, tote interne Fehlerzweige entfernen | Safety-Vertrag und korrigierte explizite Angaben erhalten |
| Daten-/Speech-/Sessionmodule und zugehörige Tests | Nur zusätzlich reproduzierte Grenzfehler, vor Edit im Fortschritt konkretisieren | Keine spekulative Validierung oder Vertragsänderung |
| `README.md`, `docs/architecture.md`, `docs/data-flow.md`, aktuelle Betriebsdocs | Abläufe/Diagramme und widersprüchliche Beschreibungen korrigieren | Dokumentationsänderung |
| `docs/reviews/quality-review-2026-09.md` | Nachweisbericht einschließlich Datei-/Prüfinventar | Eigene und fremde Evidenz getrennt |

Abgelehnt: Framework-/Dependencywechsel, generische neue Abstraktionen,
Löschung dokumentierter Legacyfunktionen, fachliche Neubeurteilung kuratierter
Angebote oder pauschales Umformatieren.

## Milestones und Validation plan

1. Review abschließen: drei rein lesende Teilreviews plus lokale Integration,
   Claude-Diff und bestehende Dokumente prüfen.
2. Kleine Fehlergruppen umsetzen, jeweils mit Regression, die vor dem Fix
   fehlschlägt. Relevante Tests nach jeder Gruppe ausführen.
3. `code-documentation` auf finalen Code anwenden; deutsche Dokumentation und
   Mermaid-Abläufe aktualisieren, Pfade und Aussagen abgleichen.
4. `python -m compileall -q app tests`, JS-Syntax und Offline-JS-Tests,
   `python -m pip check`, `git diff --check`, Paketbuild/-inventar und fokussierte
   betroffene Pytests. Vorhandene vollständige 754-Test-Evidenz wiederverwenden;
   keinen vollständigen Nachtest behaupten.
5. Finalen Diff gegen Ausgangsstand und Claude-Zwischenstand prüfen; Runtime,
   Daten, Konfiguration, Paketressourcen und Index unverändert nachweisen.

## Rollback and recovery

Eigene Änderungen bleiben ungestagt und sind anhand des Abschlussberichts von
Claudes Änderungen abgrenzbar. Die übernommenen Patches und SHA-256-Inventare
liegen temporär unter `lena-quality-audit-20260915-0s9xv94c`. Kein pauschales
`git restore`, kein Entfernen lokaler Forschungsevidenz. Einzelne eigene Hunks
können rückgängig gemacht werden; keine Migration erforderlich.

## Progress log / Discoveries

- Zusätzliches Bereinigungsinventar vor Löschung: `tests/test_frontend_runtime.js`
  ist eine unversionierte Zwischenfassung dieses Reviews. Alle fünf Fälle sind
  in `tests/frontend.test.cjs` abgedeckt, dort zusätzlich TTS. Keine Start-,
  Paket- oder Dokumentationsreferenz; niedrige Gefahr. Zwischenfassung entfernen.
- Betriebsreview: Der historische Live-Evaluationsrunner wertet den technischen
  Fallback noch als kartenlos aus und setzt die deklarierte Fehler-Injection
  nicht um. Seine E2E-Aufrufzählung erfolgt nachträglich. Diese Forschungsevidenz
  wird erhalten; Berichte sind kein Nachweis aktueller vollständiger Live-Gates.
- Aktualisierte Nutzerpriorität: Qualitätsprüfung und Fertigstellung vor neuen
  Mermaid-Diagrammen; Diagrammerweiterung ausdrücklich zurückgestellt. Vorhandene
  Diagramme bleiben erhalten, erkannte falsche Versionsangaben werden korrigiert.
- TTS-Zusatzbefund: Unterbrechung pausierte Audio ohne Freigabe der Blob-URL oder
  Abschluss des Wiedergabe-Promises. Der bestehende Unterbrechungspfad ruft jetzt
  dieselbe lokale Bereinigung wie das normale Audioende auf; Verhaltenstest prüft
  Sessionpayload, Unterbrechung und URL-Freigabe ohne Browser-/Provideraufruf.
- 2026-09-16: Der Nutzer hat die bisherigen Änderungen inzwischen in `8e7b204`
  und `3433c7a` committet. Der eigene Implementierungsvergleich beginnt deshalb
  beim sauberen `3433c7a`; diese Commits werden nicht verändert.
- Bestätigte Ergänzungen zum File impact: `sessions.py` behandelt ungültiges
  UTF-8 und zeitzonenlose persistierte Zeitstempel bislang nicht durchgehend
  als beschädigten Zustand. Vorhandene Quarantäne-/Record-Verwerfung erweitern,
  Bytes erhalten und valide Nachbarsessions mit Regressionen schützen.
- Weitere reproduzierte Grenzen: getauschte Kurations-Quell-IDs, datasetweiter
  Hash im Toiletten-Record-Diff, verkürzte CSV-Zeilen, defekte Grenzpolygone,
  falsche Legacy-Übersetzungsstrukturen, ungültige Speech-/LLM-Antwortwurzeln.
  Korrektur in den bestehenden Validatoren und Fehlerpfaden, keine neuen Layer.
- `candidates.py`: Mehrfachbedarf wählt bisher zufällig aus einem Set zwischen
  Hilfebus-Essens- und Beratungszeit. Primärbedarf muss deterministisch seine
  belegte Zeitregel verwenden; bestehende Kandidatentests um Regression ergänzen.
- 2026-09-16: Bericht und Claude-Diff gelesen; eigene alte Baseline wiedergewonnen;
  alle 212 Kopien mit historischen kanonischen Blobs abgeglichen.
- 2026-09-16: VS Codes vorhandene Electron-Node-Laufzeit (`ELECTRON_RUN_AS_NODE=1`)
  liefert Node 24.18.0; ausführbare Frontendtests ohne Projektabhängigkeit möglich.
- 2026-09-16: Plan vor eigenen Implementierungsänderungen geschrieben.

## Final verification summary

629 unterschiedliche betroffene Python-Tests und sechs ausführbare JS-Tests
bestanden; zehn STT-Tests nach abschließender Testcodebereinigung nochmals grün.
Syntax, Abhängigkeiten, CLI, Paketbau und Offline-Factory/Lifespan aus einem
außerhalb des Checkouts installierten Wheel geprüft. Alle 90 Appdateien im
94-Dateien-Wheel sind vollständig und bytegleich zum Checkout. Alle 224
geschützten Dateien sind unverändert, keine neuen Daten-/Runtime-Dateien.
Die abschließende rekursive Entfernung regenerierter Test-/Pythoncaches wurde
automatisch mit `blocked by policy` abgelehnt, ohne genauere Begründung. Die
ignorierten Caches bleiben erhalten; keine Umgehung der Sperre.

Der [Abschlussbericht](../reviews/quality-review-2026-09.md) enthält Befunde,
Prüfbefehle, Inventar, Restgrenzen und die dateiweise Übersicht. Historische
Sessionverluste sind nicht vollständig rekonstruierbar. Produktive
Providerqualität, echte Browser-/Screenreaderprüfung, Remote-CI und die
abweichenden Live-Evaluationsmetriken werden nicht als erfolgreich verifiziert
ausgegeben. Zusätzliche Diagramme bleiben entsprechend Nutzerpriorität vertagt.
