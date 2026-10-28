# Execution Plan: Sichere Repository-Bereinigung

## Status

- State: Complete
- Arbeitsbereich: Repository-Wartung
- Created: 2026-07-31
- Last updated: 2026-07-31

## Objective

Das kanonische LENA-Repository wird ausschließlich um nachweislich generierte,
obsolete oder bereits historisch entfernte lokale Restartefakte bereinigt. Alle
Anwendungs-, Test-, Paketierungs-, Daten-, Frontend-, WFS-, Session- und
Forschungsverträge bleiben funktional unverändert.

## Acceptance contract

- [x] Der Repository-Root ist `C:/Users/User/OneDrive/Dokumente/MA Projekt/code`;
  der frühere Ordner `Code3` wird nicht verwendet.
- [x] Git-Zustand, Branches, Upstream, Remote, Historie und offene Git-Operationen
  wurden vor Änderungen geprüft.
- [x] GitHub bestätigt `HannahHoffner/lena-grounded-voice-assistant` als `PRIVATE`.
- [x] Der zuvor unversionierte aktive WFS-Stand wurde vor der Bereinigung im
  Sicherungscommit `de6ff13` erfasst.
- [x] Nur Kandidaten der Gruppe A werden entfernt.
- [x] Anwendung, Tests, Build, Paketierung, Installation, Start, KB, Frontend,
  Karten, Retrieval, Sessions, Logging und WFS-Verträge bleiben unverändert.
- [x] Vorher-/Nachher-Evidenz und finaler Git-Status werden dokumentiert.

## Scope

### In scope

- lokale Python-/Pytest-Caches und reproduzierbare Buildmetadaten;
- alte lokale Wheel-Smoke-Umgebung und abgeschlossene Modernisierungsoutputs;
- vollständig leere Altordner, deren frühere Inhalte bereits bewusst aus Git
  entfernt wurden und die von keinem aktuellen Pfad vorausgesetzt werden;
- Dokumentation von Analyse, Entscheidungen und Verifikation.

### Out of scope

- funktionale Änderungen, Refactorings, Abhängigkeitsupdates oder API-Änderungen;
- Löschung irgendeines versionierten Anwendungsteils;
- aktive oder Bootstrap-WFS-Daten, aktive Pointer, Manifeste und Snapshots;
- Sessions, Interaktionsprotokolle oder andere mögliche Forschungsevidenz;
- Promotion oder Löschung des validen Pending-WFS-Releases;
- Änderungen an `.env`, `.env.local` oder fachlichen Daten;
- Push, Force-Push oder Änderung der Git-Historie.

## Repository review

### Git-Ausgangszustand

- Ausgangsbranch: `modernization/packaging-versioning`, Commit `cadec30`, synchron
  mit `origin/modernization/packaging-versioning`.
- Ursprünglich unversioniert: `data/wfs/active_release.json` und
  `data/wfs/releases/legacy-3b72f95a88f9/`.
- Keine offenen Merge-, Rebase-, Cherry-pick-, Revert- oder Bisect-Operationen.
- Arbeitsbranch: `maintenance/repository-cleanup`.
- Sicherungscommit: `de6ff13 chore: snapshot repository before cleanup`.
- Remote: `origin`, `https://github.com/HannahHoffner/lena-grounded-voice-assistant.git`;
  GitHub-API/CLI: `visibility=PRIVATE`, `isPrivate=true`.

### Bestandsaufnahme

| Kategorie | Bestand und Entscheidung |
|---|---|
| Produktiver Anwendungscode | 20 Pythonmodule unter `app/` plus Providerpaket; alle über App, CLI, relative Imports oder Tests angebunden; erhalten |
| Tests und Fixtures | 13 Testmodule und `tests/fixtures/wissensbasis_hilfsangebote_leipzig.md`; 158 Tests; erhalten |
| Statische Ressourcen | `index.html`, `app.js`, `styles.css`, vendortes Leaflet und fünf von Leaflet/CSS referenzierte Bilder; im Wheel-Inventartest gefordert; erhalten |
| Bootstrap-/Laufzeitdaten | kanonische Angebote, Übersetzungen, Overrides, WFS-Rohdaten und Report unter `app/resources/bootstrap/`; paketiert und getestet; erhalten |
| Generierte/temporäre Artefakte | `.pytest_cache/`, `__pycache__/`, `build/`, `dist/`, alte `runtime/wheel-smoke/`; Gruppe A. `lena_code3.egg-info/` bleibt nach isoliert fehlgeschlagener Entfernung erhalten. |
| Laufzeitprotokolle/Sessions | `runtime/sessions.json` und `runtime/logs/interactions.jsonl` vom 2026-07-29; unversioniert, möglicherweise Forschungsevidenz; Gruppe C |
| Dokumentation | README, Architektur-, Setup-, Konfigurations-, Datenfluss-, Test- und ExecPlan-Dokumente; im sdist enthalten; erhalten |
| Möglicherweise veraltet | `runtime/dependency-report.json` und `runtime/pr-body.md` vom 2026-07-17; abgeschlossenes Baseline-Arbeitspaket, null Referenzen; Gruppe A |
| Leere Verzeichnisse | `scripts/`, `app/scraper/`, `data/evals/`, `data/maintenance/`, `data/prompts/`, `data/scraper_sources/`, `data/published/index/`, `data/published/pages/`; Gruppe A |
| Unklar/operativ | valider Pending-Release `runtime/wfs/pending/20260729T055851Z-3b72f95a88f9-02ade2e6`; Gruppe B |

### Current behavior

`python -m app` startet Uvicorn mit `app.main:create_app`. Die FastAPI-App lädt
über den atomaren Active-Pointer genau einen WFS-Release, stellt das vollständig
paketierte Frontend bereit, führt deterministisches Retrieval aus und verwendet
optionale LLM-/Speech-Provider mit kontrollierten Fallbacks. Sessions werden
atomar in `runtime/sessions.json`, vollständige Forschungsinteraktionen getrennt
in `runtime/logs/interactions.jsonl` geschrieben. WFS-Checks erzeugen zuerst
unveränderliche Pending-Releases; Promotion und Rollback wechseln den Pointer
erst nach Manifest- und Hashvalidierung.

### Relevant architecture and data flow

1. `app/__main__.py` → Uvicorn → `app.main:create_app`.
2. `app.main` → Konfiguration, aktive KB, QueryService, Speech, Sessions und
   InteractionWriter; Routen `/`, `/api/health`, `/api/speech/*`, `/api/query`.
3. `app.kb_loader` → `app.wfs_releases.load_active_release` oder Bootstrap-KB.
4. `app.service` → Retrieval, Zeitregeln, Übersetzungen, Karten, optionaler
   Blablador-Router/Formulator, Sessionabschluss und kontrollierte Fallbacks.
5. `app.wfs_sync`/`app.wfs_releases` → Download/Validierung, Pending-Release,
   Promotion/Rollback, atomarer Pointer.
6. `app.static/index.html` referenziert Styles, vendortes Leaflet und `app.js`;
   `app.js` konsumiert die vier API-Pfade und rendert Karten über Leaflet.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Runtime-Selbsterzeugung | `app/sessions.py`, `app/interactions.py`, `app/wfs_releases.py` | unverändert erhalten und nach leerer Temp-Runtime prüfen |
| Bootstrap-Auflösung | `app/resources.py`, `app/resources/bootstrap/` | unverändert erhalten und Clean-Install prüfen |
| Paketierungsvertrag | `pyproject.toml`, `MANIFEST.in`, `tests/test_packaging.py` | unverändert wiederverwenden |
| Ignore-Regeln | `.gitignore` | deckt alle Gruppe-A-Artefakte bereits ab; keine Erweiterung geplant |
| WFS-Verifikation | `python -m app.wfs_sync --verify/--list` | read-only zur Evidenz verwenden |

### Existing tests and baseline commands

| Check | Befehl | Baseline-Ergebnis |
|---|---|---|
| Python | `python --version` | 3.14.3; CI/Constraints zielen auf 3.11 |
| Vollständige Suite | `python -m pytest` | 158 passed, 0 skipped, 0 failed in 38.25s |
| Syntax/Import | `python -m compileall -q app` | erfolgreich |
| Build | `python -m build` | Wheel und sdist erfolgreich |
| CLI | `python -m app --version` | `0.1.0` |
| WFS Pending | `python -m app.wfs_sync --verify 20260729T055851Z-3b72f95a88f9-02ade2e6` | Schema 1, 30 Records, gültige Hashes |
| WFS Liste | `python -m app.wfs_sync --list` | aktiv `legacy-3b72f95a88f9`, ein valider Pending-Release |
| Echter Backend-Smoke | `python -m app --host 127.0.0.1 --port 8765` mit isolierter Runtime | Health, `/`, `app.js` HTTP 200; 30 Angebote; aktiver Release geladen |
| E2E Query | zwei HTTP-POSTs an `/api/query` | `ok`, Template, 4 Karten/4 Kartenziele, Folgefrage in gleicher Session |
| Runtime-Erzeugung | isolierte Runtime des Backend-Smokes | 1 Sessiondatei/Session, 1 JSONL-Datei mit 2 Zeilen |
| Clean-Install | neues venv, Wheel installieren, TestClient außerhalb Checkout | Version, Bootstrap, Health, Frontend, Asset, Query, Karten, externe Session/JSONL erfolgreich |

Vorhandene Warnung: Die manuelle Clean-Installation meldet eine
`StarletteDeprecationWarning` zur späteren Umstellung von `httpx` auf `httpx2`.
Sie bestand vor der Bereinigung und ist kein Cleanup-Fehler. Buildmeldungen zu
ausgeschlossenen `data/`, `runtime/`, `.env*` und Caches entsprechen dem
beabsichtigten Distributionsvertrag.

### Working tree considerations

- `.env` und `.env.local` sind ignorierte lokale Geheimniskonfiguration und
  werden weder gelesen ausgegeben noch verändert.
- `runtime/sessions.json` und `runtime/logs/interactions.jsonl` können sensible
  Freitexte beziehungsweise wissenschaftliche Evidenz enthalten und bleiben.
- Der aktive WFS-Release ist seit `de6ff13` versioniert und darf nicht verändert
  werden.
- Ignorierte Bereinigungen erscheinen nicht im Git-Diff; ihre exakten Pfade und
  Metadaten werden deshalb im Abschlussbericht dokumentiert.

## Kandidaten

### A. Sicher löschbar

| Kandidat | Zweck/Alter | Belege für Nichtverwendung | Risiko | Nachprüfung |
|---|---|---|---|---|
| `.pytest_cache/` | Pytest-Cache, 6 Dateien/15,883 Bytes | `.gitignore`, Pytest regeneriert ihn, nicht paketiert | sehr niedrig | volle Suite |
| `app/**/__pycache__/`, `tests/__pycache__/` | Bytecode, 35 Dateien/ca. 820 KB | `.gitignore`, `compileall` regeneriert ihn | sehr niedrig | compileall + Suite |
| `build/` | Setuptools-Buildbaum, 28 Dateien/428,811 Bytes | `.gitignore`, `python -m build` regeneriert ihn | sehr niedrig | Build wiederholen |
| `dist/` | Wheel/sdist, 2 Dateien/496,902 Bytes | `.gitignore`, Baseline-Build erfolgreich reproduziert | sehr niedrig | Build wiederholen, danach final erneut räumen |
| `runtime/wheel-smoke/` | alte lokale venv vom 2026-07-17, 2,189 Dateien/36,760,220 Bytes | null Referenzen; aktuelle Packagingtests nutzen `tmp_path`; nicht paketiert | niedrig | volle Suite + neue Clean-Installation |
| `runtime/dependency-report.json` | pip-inspect-artiges Abhängigkeitsinventar vom 2026-07-17, 525,970 Bytes | null Referenzen; Constraints/Build sind kanonisch; reproduzierbar | niedrig | Installation mit Constraints |
| `runtime/pr-body.md` | Text für den bereits gemergten PR #1, 1,715 Bytes | null Referenzen; GitHub bestätigt PR #1 als merged | sehr niedrig | keine Runtimewirkung; Git-/Dokureview |
| leere Altordner `scripts/`, `app/scraper/`, `data/evals/`, `data/maintenance/`, `data/prompts/`, `data/scraper_sources/`, `data/published/` samt `index/` und `pages/` | Restverzeichnisse früherer v1/v2-Pfade | null aktuelle Referenzen; frühere Inhalte in Commit `43b88bc` bewusst gelöscht; keine `mkdir`-/Packaging-/Runtime-Abhängigkeit | niedrig | Suite, Build, Start, Clean-Install |

### B. Wahrscheinlich löschbar, aber weitere Prüfung nötig

| Kandidat | Warum nicht Gruppe A |
|---|---|
| `runtime/wfs/pending/20260729T055851Z-3b72f95a88f9-02ade2e6/` | Der Inhaltshash entspricht dem aktiven Datenstand und könnte redundant sein; der Release ist aber gültig, operativ noch pending und kann Prüf-/Promotionsevidenz darstellen. Ohne fachliche Entscheidung nicht löschen. |

### C. Nicht löschen

| Kandidat | Erhaltungsgrund |
|---|---|
| sämtliche 20 Pythonmodule und `app/providers/` | alle importiert, per CLI ausführbar oder getestet; dynamische Provider-/Startup-Pfade vorhanden |
| `app/static/` vollständig | Frontend-/Leaflet-/CSS-Referenzen und Wheel-Inventartests |
| `tests/` und Fixture | 158 Regressionstests, Markdownimport und Paketierungsverträge |
| `app/resources/bootstrap/`, `data/canonical/`, `data/i18n/`, bestehende `data/wfs/` | Wissensbasis, Clean-Install, Übersetzungen, aktiver Release, Pointer, Manifeste, Snapshot und Reproduzierbarkeit |
| `runtime/sessions.json` | Inhalt vom 2026-07-29; möglicherweise reale oder wissenschaftlich relevante Sessionevidenz; nicht vollständig reproduzierbar |
| `runtime/logs/interactions.jsonl` | Inhalt vom 2026-07-29; laut Dokumentation explizit für Evaluation/Masterarbeit; nicht löschen ohne Aufbewahrungsentscheidung |
| `runtime/wfs/state.json` | aktueller lokaler Sync-/Zeitstatus; Laufzeitvertrag |
| `runtime/wfs/pending/...` | bis zur fachlichen Entscheidung geschützt (Gruppe B) |
| `.env`, `.env.local` | lokale Secrets/Konfiguration; keine Bereinigungsartefakte |
| `lena_code3.egg-info/` | die isolierte Entfernung änderte `python -m app --version` von `0.1.0` auf `0+unknown` und ließ 1/7 Packagingtests scheitern; über den vorgesehenen Editable-Installationsweg wiederhergestellt |
| README, `docs/`, `.github/workflows/test.yml`, Constraints, `pyproject.toml`, `MANIFEST.in`, `.gitignore`, `.env.example` | Setup, CI, Build, Installation und Dokumentation |

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Active/Pending-WFS als „alte Daten“ löschen | Pointer und Manifest werden aktiv geladen; Pending ist gültig | KB-/Promotionverlust | aktive Daten Gruppe C, Pending Gruppe B | Health, WFS verify/list, E2E |
| Sessions/JSONL pauschal nach Datum löschen | Dokumentation nennt sie Evaluationsevidenz | irreversibler Forschungsdatenverlust | vollständig erhalten | finaler Pfad-/Metadatencheck |
| leere Runtime-Zielordner entfernen | Writer erzeugen Eltern zwar selbst, vorhandene Inhalte sind aber relevant | Datenverlust/Startprobleme | nur historisch tote leere Altordner entfernen | Temp-Runtime-Smoke |
| unreferenziertes Modul anhand einer Textsuche löschen | CLI, relative Imports und dynamische Pfade | stiller Funktionsverlust | Import-, CLI-, Test-, Packaging- und Laufzeitprüfung kombiniert; kein Code wird gelöscht | Suite, Build, Start, E2E |
| nur Tests statt echter Installation prüfen | lokale Restdateien könnten Fehler verdecken | scheinbar grüne, nicht installierbare App | Clean-Wheel-Installation außerhalb Checkout | manueller Clean-Install-Smoke |
| Buildartefakte vor finalem Status wieder liegen lassen | Verifikation regeneriert sie | Repository bleibt lokal unaufgeräumt | nach finaler Build-/Installprüfung generierte Gruppe-A-Ausgaben nochmals entfernen | finaler Filesystem-Audit |

## Recommended approach

Die kleinste sichere Änderung entfernt ausschließlich Gruppe A in getrennten
Kategorien. Nach jeder Kategorie werden Pfade, Git-Diff und die engsten
relevanten Checks kontrolliert. Versionierter Code wird nicht gelöscht. Nach der
Gesamtbereinigung wird die vollständige Baseline wiederholt; anschließend werden
dabei neu erzeugte Gruppe-A-Artefakte nochmals entfernt und ein read-only finaler
Audit durchgeführt.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| vollständige Runtime löschen | Sessions, Forschungslogs und valider Pending-WFS wären gefährdet |
| WFS-Pending wegen gleichem Inhaltshash löschen | operativer Status und wissenschaftliche Evidenz sind nicht geklärt |
| vermeintlich ungenutzte Pythonmodule entfernen | keine Datei besteht die geforderte doppelte Nichtverwendungsprüfung |
| `.gitignore` erweitern | alle eindeutigen generierten Kandidaten sind bereits abgedeckt; weitere Regeln könnten Fachdaten verstecken |
| allgemeines Refactoring großer Dateien | nicht Teil der Bereinigung und würde Funktionsgleichheit gefährden |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `docs/exec-plans/repository-cleanup.md` | Create/Update | persistenter Plan und Evidenz | niedrig |
| Gruppe-A-Pfade laut Kandidatentabelle | Delete locally | nachweislich generiert/obsolet/leer | niedrig; meist ignoriert |
| `docs/reviews/repository-cleanup-report.md` | Create | Abschlussnachweis | niedrig |
| `.gitignore` | Preserve | Regeln sind bereits vollständig | kein Risiko |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Git-/Remoteprüfung, 77 versionierte Dateien inventarisiert, Imports,
Routen, Frontend- und Paketressourcen verfolgt, 158 Tests und echte Laufzeitpfade
geprüft, Historie `43b88bc` für leere Altordner ausgewertet.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

Evidence: sichere Cache-/Buildausgaben, 2.189 Dateien der alten Wheel-Smoke-venv,
zwei obsolete Runtime-Dokumente und neun leere Altordner entfernt. Keine
versionierte Quellcodedatei geändert oder gelöscht. Die testweise Entfernung von
`lena_code3.egg-info/` wurde wegen sichtbarer Versionsregression sofort durch den
dokumentierten Editable-Installationsweg rückgängig gemacht; anschließend
bestanden alle 7 Packagingtests wieder.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run integration/build checks where relevant.
- [x] Verify registration, imports, routes, configuration, and packaging.
- [x] Review final diff.

Evidence: vollständige Suite erneut mit 158/158 bestanden; 39/39 fokussierte
Persistenz-, Logging- und WFS-Vertragstests bestanden; Compile, Build, CLI,
WFS-Verify/List, echter Uvicorn-E2E-Smoke und korrigierter Clean-Wheel-Smoke aus
einem fremden Arbeitsverzeichnis erfolgreich. Alle durch die Verifikation erneut
erzeugten Gruppe-A-Artefakte wurden anschließend erneut entfernt.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: `code-documentation` vollständig gelesen und für Genauigkeits-, Pfad-,
Versions- und Konsistenzprüfung von Plan und Abschlussbericht angewendet. Alle
dokumentierten geschützten Pfade und Version 0.1.0 wurden erneut geprüft;
`git diff --check` und ein bytecodefreier Import waren erfolgreich.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Full regression | `python -m pytest` | exakt 158 passed, 0 skipped/failed |
| Static import/syntax | `python -m compileall -q app` | exit 0 |
| Distribution | `python -m build` | Wheel + sdist erfolgreich, Inventar unverändert |
| Focused runtime contracts | Observability, session, WFS, packaging, provider timeout tests | alle erfolgreich |
| Backend/API/UI | echter Uvicorn-Start mit isolierter Runtime, Health/Root/Asset/Query/Follow-up | Baselinewerte und HTTP 200 |
| Active/Pending WFS | `app.wfs_sync --list/--verify` | aktiver und Pending-Release unverändert/gültig |
| Clean install | neues Temp-venv aus finalem Wheel außerhalb Checkout | Bootstrap, UI, Query, Karten, externe Runtime erfolgreich |
| Runtime recovery | Tests für TTL, Limit, Quarantäne, atomare Writes plus frische Runtime | unverändert erfolgreich |
| Final cleanliness | `git status`, `git diff --check`, Filesystem-Audit | nur geplante Dokumentation/Commits; keine Gruppe-A-Reste |

## Rollback and recovery

- Der vollständige funktionsfähige Ausgangszustand einschließlich aktivem WFS
  ist in `de6ff13` wiederherstellbar.
- Versionierte Dokumentationsänderungen können über normale Revert-Commits
  rückgängig gemacht werden; kein History-Rewrite ist nötig.
- Gruppe-A-Builds/Caches sind durch die dokumentierten Befehle reproduzierbar.
- Die historisch leeren Verzeichnisse können bei Bedarf ohne Inhalt neu angelegt
  werden; keine Anwendung setzt sie voraus.
- Gruppe-B/C-Inhalte werden nicht verändert und benötigen daher keine Recovery.

## Progress log

- 2026-07-31 — Repository-/Remote-/Git-Sicherheitsprüfung abgeschlossen; Remote
  nachweislich privat.
- 2026-07-31 — Aktiven WFS-Ausgangszustand in `de6ff13` gesichert und sauberen
  Wartungsbranch hergestellt.
- 2026-07-31 — Vollständige statische Bestandsaufnahme und historische Prüfung
  abgeschlossen.
- 2026-07-31 — Baseline mit 158 Tests, Build, echtem Backend-Smoke, WFS-Verify
  und Clean-Wheel-Installation erfolgreich.
- 2026-07-31 — Plan nach Review erstellt; Löschung noch nicht begonnen.
- 2026-07-31 — Caches/Buildausgaben entfernt; `lena_code3.egg-info/` nach
  isoliertem Versions-/Packagingfehler sofort wiederhergestellt und Gruppe C
  zugeordnet.
- 2026-07-31 — Alte Wheel-Smoke-venv, Dependency-Report, PR-Text und neun leere
  historische Altordner entfernt; geschützte Runtime-/WFS-Dateien bestätigt.
- 2026-07-31 — Nachher-Baseline mit 158/158 Tests, Compile, Build, echtem
  Backend/E2E, WFS-Verifikation und echter Wheel-Installation aus fremdem
  Arbeitsverzeichnis erfolgreich.
- 2026-07-31 — 39/39 fokussierte Session-, Logging- und WFS-Vertragstests
  erfolgreich; regenerierte Caches/Builds final erneut entfernt.
- 2026-07-31 — Abschlussbericht nach `code-documentation`-Prüfung erstellt;
  dokumentierte Pfade, Versionen, Kommandos und finaler Artefaktstatus verifiziert.

## Decision log

- Decision: Keine Anwendungscode-Datei löschen.
  - Context: Alle Module besitzen Imports, CLI-Nutzung oder Tests; der einfache
    Symbolheuristiklauf fand keine nur einmal definierte öffentliche Definition.
  - Choice: Nur Gruppe-A-Artefakte und leere historische Verzeichnisse entfernen.
  - Consequences: kleinere, aber nachweislich risikoarme Bereinigung.
- Decision: Sessions und Interaktionslogs vollständig behalten.
  - Context: Inhalte können Masterarbeits-/Evaluationsevidenz sein.
  - Choice: Gruppe C gemäß „im Zweifel nicht löschen“.
  - Consequences: Runtime bleibt teilweise befüllt, ohne funktionales Risiko.
- Decision: Pending-WFS nicht löschen oder promoten.
  - Context: gültig und inhaltlich redundant, aber operativer Status ungeklärt.
  - Choice: Gruppe B.
  - Consequences: offene fachliche Entscheidung bleibt sichtbar.

## Discoveries

- Die zunächst unversionierten WFS-Dateien sind kein Müll, sondern der aktive,
  valide Release; sie wurden deshalb vor jeder Bereinigung gesichert.
- Die leeren Scraper-/Prompt-/Evaluations-/Publishingordner sind Reste von in
  Commit `43b88bc` bewusst entfernten v1/v2-Inhalten.
- `runtime/pr-body.md` entspricht dem bereits gemergten GitHub-PR #1.
- Die aktuelle Test- und Clean-Install-Logik verwendet temporäre Verzeichnisse;
  `runtime/wheel-smoke/` wird nirgendwo mehr referenziert.
- `.gitignore` deckt alle sicheren generierten Artefakte bereits ab.
- `lena_code3.egg-info/` ist trotz generierter Herkunft im aktuell editable
  installierten Source-Checkout funktional relevant: ohne die Metadaten liefert
  die Anwendung `0+unknown` und der Versionsvertrag scheitert. Der Kandidat wurde
  deshalb nach isolierter Prüfung nicht endgültig gelöscht.

## Final verification summary

- Acceptance requirements: vollständig erfüllt.
- Tests: Baseline 158 passed; Nachher 158 passed; zusätzlich 39 fokussierte
  Vertragsprüfungen bestanden.
- Build: vorher und nachher erfolgreich; Wheel-/sdist-Inventar unverändert.
- Manual verification: vorher und nachher erfolgreich; Health, Frontend, Asset,
  Query, Karten, Folgefrage, Out-of-scope- und 422-Fehlerpfad geprüft.
- Documentation: Plan und Abschlussbericht aktualisiert, mit
  `code-documentation` geprüft und durch Pfad-/Versions-/Diff-Checks verifiziert.
- Residual risks: Pending-WFS und Aufbewahrung realer Forschungslogs bleiben
  absichtlich ungelöste fachliche Entscheidungen.
