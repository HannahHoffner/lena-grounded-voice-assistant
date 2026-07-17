# Execution Plan: Offene Baseline-Lücken schließen

## Status

- State: Complete
- Owner: Codex
- Created: 2026-07-17
- Last updated: 2026-07-17

## Objective

Die lokale Git-/CI-Baseline wird zu einem reproduzierbar installierbaren und
remote reviewbaren Stand: exakt fixierte Entwicklungsabhängigkeiten, ein
vollständiges Wheel, ein eindeutiger kanonischer Checkout sowie ein Draft-PR
mit tatsächlich ausgeführter GitHub-CI.

## Acceptance contract

- [x] Eine versionierte Constraints-Datei fixiert direkte und transitive
      Installationsabhängigkeiten für Python 3.11.
- [x] Ein aus dem Checkout gebautes Wheel enthält Frontend und erforderliche
      fachliche Daten und besteht einen Clean-Install-/Start-Smoke-Test.
- [x] Der ältere unversionierte Ordner `Code3` ist nach Inhalts- und
      Secret-Prüfung eindeutig als Archiv stillgelegt, ohne ihn zu löschen.
- [x] Der bestehende Branch wird ohne History-Rewrite gepusht und als Draft-PR
      gegen den Remote-Default-Branch geöffnet.
- [x] GitHub Actions läuft für den veröffentlichten Stand tatsächlich
      erfolgreich; ein lokaler Strukturcheck wird nicht als Remote-CI gezählt.
- [x] Bestehendes Laufzeit-, API- und Datenverhalten bleibt erhalten.

## Scope

### In scope

- Packaging-Konfiguration und eng erforderliche Pfadauflösung
- Constraints-Datei und Verwendung in lokaler/Remote-Installation
- Packaging- und Clean-Install-Regressionstest
- vorhandene GitHub-Workflow- und Entwicklerdokumentation
- kontrollierte Archivierung des benachbarten unversionierten `Code3`
- Commit, Push, Draft-PR und Beobachtung der Remote-CI

### Out of scope

- Dependency-Upgrades über die aktuell aufgelösten kompatiblen Versionen hinaus
- neue Linter, Type-Checker, Security-Scanner oder Deployment-Schritte
- Merge des Pull Requests oder Änderung des Default-Branches
- Löschung des alten `Code3`-Ordners
- allgemeine Pfad-, Daten- oder Anwendungsarchitektur-Refactorings

## Repository review

### Current behavior

Der saubere Branch `modernization/code3-baseline` enthält zwei lokale Commits
auf Basis von `c20a38a`; `origin` verweist eindeutig auf GitHub. Der Workflow
installiert `.[dev]` ohne Constraints und wurde noch nicht remote ausgeführt.
Setuptools findet nur `app*`; deshalb fehlen dem Wheel die JSON-/GeoJSON-Daten.
Ohne explizite Package-Data-Konfiguration fehlen außerdem `app/static/` und die
vendorten Leaflet-Dateien. Der benachbarte Ordner `Code3` ist weiterhin eine
unversionierte Vorläuferkopie.

### Relevant architecture and data flow

`app.main:create_app()` lädt statische Dateien relativ zum installierten
`app`-Paket. `app.config:load_settings()` setzt `app_root` aktuell auf das
Elternverzeichnis des Pakets und leitet davon Wissensbasis-, WFS- und i18n-Pfade
ab. Im Checkout ist das korrekt; bei einer Wheel-Installation liegen über
Setuptools `data-files` installierte Fachdateien unter dem Umgebungspräfix.
Die Pfadauflösung muss daher den Checkout bevorzugen und nur im installierten
Fall auf das Präfix mit nachweislich vorhandenen Daten ausweichen.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Setuptools-Build | `pyproject.toml` | um Package-Data/Data-Files ergänzen |
| zentrale Settings | `app/config.py:load_settings` | eine kanonische Root-Auflösung erweitern |
| API-/KB-Tests | `tests/test_api.py`, `tests/test_kb_loader.py` | unverändert als Regression verwenden |
| GitHub-Workflow | `.github/workflows/test.yml` | Constraints und Wheel-Smoke ergänzen |
| deutsche Betriebsdokumentation | `README.md`, `docs/setup.md`, `docs/testing.md` | aktualisieren, keine Paralleldoku |

### Existing tests and commands

- `python -m pytest` — zuletzt 81 bestanden.
- `python -m compileall -q app` — zuletzt erfolgreich.
- `python -m pip wheel . --no-deps` — baut formal, Artefakt bisher unvollständig.
- Zusätzlicher Nachweis: Wheel-Inhalt prüfen, in frische virtuelle Umgebung
  installieren und App/Health aus einem fremden Arbeitsverzeichnis starten.

### Working tree considerations

Der kanonische Checkout war vor dieser Plan-Datei sauber. Lokale Runtime-Daten,
`.env*`, Caches und Builds bleiben ignoriert. Der alte Ordner `Code3` wird nicht
inhaltlich überschrieben und nur nach geprüftem absoluten Quell-/Zielpfad
verschoben. Remote-Push und PR sind ausdrücklich Teil des Ziels; Merge bleibt
ausgeschlossen.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| nur `MANIFEST.in` ergänzen | Wheel nutzt Package-/Data-Files, nicht bloß sdist-Manifest | Wheel bleibt unvollständig | Setuptools-Konfiguration direkt prüfen | Wheel-Dateiliste und Clean-Install |
| Daten nur bundlen, Root nicht auflösen | `config.py` erwartet `app_root/data` | installierte App findet KB nicht | Checkout-first, Präfix-Fallback bei vorhandenen Daten | Start aus fremdem CWD |
| nur direkte Pins erzeugen | transitive Auflösung bleibt veränderlich | CI nicht reproduzierbar | vollständige Constraints aus sauberer Resolver-Ausgabe | Fresh install mit `-c` |
| Lockdatei plattformblind behaupten | Python-Wheels können plattformspezifisch sein | falsche Reproduzierbarkeitszusage | Constraints für Python 3.11 dokumentieren und Linux-CI prüfen | Windows clean install + GitHub Linux CI |
| `Code3` ungeprüft löschen | unversionierte Herkunft | möglicher Datenverlust | Secret-/Dateivergleich, anschließend nur umbenennen | Archivpfad und Hashvergleich |
| PR vor lokalem Wheel-Nachweis öffnen | CI-Schleifen mit bekannt defektem Artefakt | unnötige Remote-Iteration | lokal vollständig verifizieren, dann commit/push | lokale Checks vor Push |
| lokalen Workflow als CI-Erfolg melden | bisheriger Zustand | falsche Abnahme | GitHub-Check bis Abschluss beobachten | PR-Checks/Run-URL |

## Recommended approach

Setuptools bündelt statische Paketdateien und die bereits versionierten aktiven
Daten. Eine kleine zentrale Root-Auflösung erhält den Checkout-Pfad und erkennt
den Wheel-Fall. Ein Integrationstest baut und installiert das reale Artefakt.
Danach werden Constraints, Workflow und bestehende Dokumentation abgeglichen.
Erst nach vollständigem lokalen Nachweis wird der bestehende Branch als Draft-PR
veröffentlicht und die Remote-CI bis zum Endstatus geprüft.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Daten nach `app/` duplizieren | erzeugt zwei fachliche Wahrheiten |
| alle Daten in Python-Module verschieben | unnötige Datenarchitekturänderung |
| neue Locking-Tool-Abhängigkeit | für diesen begrenzten Baseline-Schritt nicht erforderlich |
| alten Ordner sofort entfernen | nicht reversibel und ohne Herkunftsnachweis riskant |
| PR direkt als review-ready öffnen | menschliches Review ist noch nicht erfolgt; Draft ist ehrlich |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `pyproject.toml` | Modify | statische und fachliche Wheel-Inhalte | klein, mittel |
| `app/config.py` | Modify | installierten Daten-Root auflösen | klein, mittel |
| `requirements/constraints-py311.txt` | Create | reproduzierbare Auflösung | klein, niedrig |
| `tests/test_packaging.py` | Create | reales Wheel/Clean-Install prüfen | mittel, niedrig |
| `.github/workflows/test.yml` | Modify | Constraints und Packaging-Gate | klein, niedrig |
| `README.md`, `docs/setup.md`, `docs/testing.md` | Modify | tatsächlichen Install-/CI-Stand dokumentieren | klein, niedrig |
| `docs/exec-plans/codebase-modernization.md` | Modify | Lückenstatus und Nachweise aktualisieren | klein, niedrig |
| `Code3` (außerhalb Git) | Rename to archive | kanonischen Checkout eindeutig machen | reversibel, mittel |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: sauberer Branch, GitHub-Remote, Setuptools-/Pfadpfad und bestehende
Tests wurden am 2026-07-17 geprüft.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run integration/build checks.
- [x] Verify packaging, data discovery and installed startup.
- [x] Review final diff and secrets.
- [x] Push, open Draft-PR and observe Remote-CI.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Constraints | clean `pip install -c requirements/constraints-py311.txt -e ".[dev]"` | installierbar ohne Resolverabweichung |
| Regression | `python -m pytest` | alle Tests bestanden |
| Syntax | `python -m compileall -q app` | Exit 0 |
| Wheel | `python -m pip wheel . --no-deps` + Archivprüfung | statische und aktive Daten enthalten |
| Clean install | frische venv, Wheel-Installation, Health/Root-Smoke aus Temp-CWD | App lädt KB und Frontend |
| Git | `git diff --check`, Index-/Secret-/Großdateiprüfung | keine unbeabsichtigten Inhalte |
| Remote | GitHub Draft-PR und Actions-Check | tatsächlicher erfolgreicher Lauf |

## Rollback and recovery

Packaging-, Constraints-, Test-, Workflow- und Dokumentationsänderungen werden
als eigener Commit auf dem bestehenden Branch gehalten und können per Revert
rückgenommen werden. Der alte Ordner wird nur umbenannt; die Rücknahme ist eine
geprüfte Umbenennung auf seinen ursprünglichen absoluten Pfad. Es gibt keinen
Force-Push, keinen Merge und keine Remote-/Default-Branch-Änderung.

## Progress log

- 2026-07-17 — Plan nach Repository-, Skill-, Packaging- und Git-Review erstellt.
- 2026-07-17 — Wheel um statische Dateien und aktive Daten ergänzt; zentrale
  Root-Auflösung und zwei Regressionstests implementiert.
- 2026-07-17 — 83 Tests, Compile-Check, Wheel-Inhalt und Clean-Install-Smoke auf
  Windows/Python 3.14 erfolgreich.
- 2026-07-17 — `Code3` enthielt außerhalb ignorierter Bereiche keine
  einzigartigen Dateien (43 identisch, 7 veraltet/abweichend). Lokale `.env`-
  und Runtime-Dateien wurden nicht gelesen und mit dem Ordner reversibel nach
  `Code3-archive-pre-git-20260717` verschoben.
- 2026-07-17 — `$code-documentation` auf bestehende README-, Setup-, Test- und
  Plan-Dokumentation angewendet.
- 2026-07-17 — GitHub-Veröffentlichung blockiert: `gh` ist nicht installiert;
  gemäß Publish-Workflow kein alternativer Push oder PR erzeugt.
- 2026-07-17 — GitHub CLI 2.96.0 installiert und als `HannahHoffner`
  authentifiziert; Commit `e96fa2a` erstellt und Branch ohne Force-Push nach
  `origin/modernization/code3-baseline` veröffentlicht.
- 2026-07-17 — Draft-PR #1 gegen `main` geöffnet. Push- und PR-Workflow liefen
  auf GitHub/Linux/Python 3.11 in 30 beziehungsweise 34 Sekunden erfolgreich.

## Decision log

- Decision: Constraints statt Einführung eines neuen Locking-Werkzeugs.
  - Context: vorhandenes Setuptools/pip-Projekt, keine Lock-Konvention.
  - Choice: vollständige Python-3.11-Constraints plus beide Plattformnachweise.
  - Consequences: reproduzierbare CI/Entwicklung; kein universeller Cross-Python-Lock behauptet.
- Decision: Draft-PR, kein Merge.
  - Context: Lücke verlangt Reviewbarkeit und Remote-CI, nicht Freigabe.
  - Choice: Branch pushen, Draft-PR öffnen, Checks beobachten.
  - Consequences: menschliches Review bleibt als bewusster nächster Schritt sichtbar.

## Discoveries

- Setuptools kodiert `data-files` im Wheel unter dessen `.data/data`-Bereich;
  nach Installation liegen sie korrekt unter dem Präfix der Umgebung.
- Auf dem Rechner ist ausschließlich CPython 3.14 installiert. GitHub Actions
  ergänzt den lokalen Nachweis durch Linux mit CPython 3.11.
- `Code3` besaß `.env`, `.env.local` und lokale Runtime-Zustände. Diese Inhalte
  wurden nicht gelesen oder vervielfältigt und dürfen nicht veröffentlicht
  werden.

## Final verification summary

- Acceptance requirements: erfüllt; der veröffentlichte Draft-PR ist technisch
  geprüft, bleibt aber bis zu einem menschlichen Review bewusst Draft.
- Tests: `python -m pytest` — 83 passed; Packagingtests — 2 passed.
- Build: Wheel erfolgreich; erwartete Dateien enthalten; Clean-Install-Smoke
  gegen `/` und `/api/health` erfolgreich.
- Manual verification: installierter Root und KB-Pfad liegen im Venv-Präfix;
  alter Quellpfad fehlt, Archivziel existiert.
- Documentation: `code-documentation` angewendet; README, Setup, Testing und
  beide ExecPlans aktualisiert.
- Remote verification: GitHub-Actions-Runs `29568197722` und `29568219430`
  erfolgreich; Draft-PR `#1` gegen `main` geöffnet.
- Residual risks: menschliches PR-Review ausstehend; Constraints enthalten keine
  Artefakthashes.
