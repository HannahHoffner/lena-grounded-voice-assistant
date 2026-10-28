# Repository-Audit und konservative Bereinigung

## Status

- State: Complete
- Verantwortlich: Repository-Wartung
- Erstellt / aktualisiert: 2026-10-28
- Ausgangsstände: Code `5eebb72`, Thesis `acf0e01`; beide Worktrees sauber.

## Objective und Acceptance contract

- [x] Aktive Komponenten, Referenzen, Abhängigkeiten und Artefakte prüfen.
- [x] Nur belegte technische Redundanzen bereinigen; unsichere Kandidaten erhalten.
- [x] Keine Funktionen, wissenschaftlichen Inhalte, Daten oder Herkunftsnachweise verlieren.
- [x] Präsentationen vollständig schützen; keine Git-Historie ändern, nichts committen/pushen.
- [x] Verifikation und konkrete Restunsicherheiten im Abschlussbericht dokumentieren.

## Scope

Aktive Repositories `code/` und `../thesis/`. Workspacearchive werden nur zur
Referenz-/Herkunftsprüfung gelesen. Ausgeschlossen: `../presentations/`, alle
weiteren Präsentationsdateien samt Begleitmaterial; lokale Secrets, Sessions,
Interaktionslogs und Forschungsrohdaten bleiben erhalten. Keine Inhaltsredaktion
der Thesis, keine spekulativen Updates oder funktionalen Neuentwicklungen.

## Repository review

### Current behavior und Architektur

FastAPI-Einstieg `app/__main__.py` / `app/main.py`, Orchestrierung `app/service.py`;
kuratierte, hashgebundene Bootstrapdaten, deterministische Kandidaten-/Faktenprüfung,
explizite externe Sprachdienste, dateibasierte Sessions. Statisches Frontend und
vendortes Leaflet ohne npm-Build. Setuptools-Wheel/sdist, Python-Constraints für
3.11/3.12 sowie hashgebundene Linux-3.12-Locks; mehrstufiger Docker-Build.
Thesis: `thesis.tex`, Classicthesis, Biblatex, eingeschlossene Kapitel, lokale
Abbildungen und versionierte Evaluationsnachweise; `6Resultsneu` ist indirekt
in `5Solutionneu` eingebunden. Thesis-`docs/` ist bewusst privat/ignoriert.

### Reuse, Tests und Worktree

Bestehende `docs/exec-plans/`, `docs/reviews/`, Setup-/Test-/Reproduktionsdokumentation
weiterverwenden. Frühere Audits sind historische Nachweise, keine aktuellen
Löschbelege. Keine AGENTS-Dateien in den aktiven Repositories oder Eltern gefunden.
Pytest inklusive Packagingtests, Node-Verhaltenstests, compileall, pip check,
Python-Build, Docker-Test-/Runtimeziele und LaTeX-CI vorhanden. Kein konfigurierter
Linter, Formatter oder Typechecker. Keine bestehenden Nutzeränderungen überschreiben.

## Kandidatenliste vor Änderungen / Dead-end analysis

| Kandidat | Referenzbefund / Risiko | Entscheidung und Nachprüfung |
|---|---|---|
| Python-/Pytest-Caches, build/dist | generiert; erst nach erfolgreicher Reproduktion entbehrlich | nur eng begrenzte regenerierbare Pfade, mit Einzelinventar und Sicherung |
| `lena_code3.egg-info/` | Versions-/Editable-Vertrag laut altem Audit | erhalten, Installation prüfen |
| Bootstrap-/Checkout-Datenkopien | verschiedene Paket-/Wartungsrollen; Hashbindung | nicht deduplizieren; Bytes und Paketierung prüfen |
| Historische Renderer, Retrieval, Loader, Tests | Tests, indirekte Imports und Vergleichsverträge | erhalten; fehlender HTTP-Aufruf beweist keine Entbehrlichkeit |
| Thesis-Templatekapitel, ältere Abbildungen, Archive | Ursprung, Kommentare, Git- und Forschungsnachweise möglich | Referenzen prüfen, bei Unsicherheit erhalten |
| Thesis-Hilfsdateien/PDF | Buildreproduktion noch zu prüfen; PDF bewusst nutzbar | isolierten Build durchführen; Originale zunächst erhalten |
| Toolnamen in Wartungsplan-Ownerfeldern | reine Arbeitsmetadaten | neutralisieren, keine falschen Autorenschaften |
| KI-Bewertungen / Modellnamen / wissenschaftliche Offenlegung | methodisch relevante Herkunft | unverändert erhalten |
| bisherige toolspezifische Worktree-Ignore | verhindert versehentliche Aufnahme lokaler Arbeitskopien | Schutz durch allgemeine Regel erhalten |
| README „noch uncommittiert“ | Worktree sauber, Änderung in `5eebb72` vorhanden | auf tatsächlichen Commitstand korrigieren |

## Recommended approach / Alternatives rejected

Erst Inventar mit Hashes und Referenzanalyse, dann kleinste belegte Korrekturen,
danach unabhängige Regression/Installation/Buildprüfung. Keine großflächigen
Refactorings, Umzüge, Auflösung historischer Tests oder Datenkonsolidierung:
sie erhöhen Risiken ohne belastbaren Entbehrlichkeitsnachweis.

## File impact

| Pfad | Aktion | Begründung / Risiko |
|---|---|---|
| dieser Plan | anlegen/fortschreiben | persistenter Reviewnachweis, niedrig |
| `docs/reviews/repository-audit-2026-10-28.md` | anlegen | vollständiger Abschlussnachweis, niedrig |
| `README.md` | Statuskorrektur nach Prüfung | reproduzierbare Commitzuordnung, niedrig |
| bestehende Wartungspläne | reine Owner-Metadaten neutralisieren | keine Bewertung oder wissenschaftliche Attribution ändern |
| `IMPLEMENTATION_REPORT.md`, `RELEASE_REVIEW_CHECKLIST.md` | drei rein prozedurale Toolnennungen neutralisieren | wissenschaftliche Bewertungen und Attributionen bleiben erhalten |
| `tests/test_packaging.py` | falsche Versionsbehauptung im Kommentar entfernen | behauptete Version 0.3.0 widerspricht tatsächlicher 0.2.0; keine Testlogik ändern |
| `MANIFEST.in`, `.dockerignore` | sieben direkt/indirekt referenzierte öffentliche Markdownberichte mitnehmen | bisher fehlen zahlreiche verlinkte Belege in sdist und Container-Quellkontext |
| `docs/architecture.md` | veralteten Fragmentlink Prompt 17 auf vorhandene Überschrift Prompt 18 korrigieren | tatsächliche Abschnittsüberschrift geprüft |
| `docs/validator-ablation-decisions.md` | auf öffentlichen Ergebnisbericht statt aus Release ausgeschlossenem Arbeitsplan verlinken | Methoden-/Ergebnisverweis in Distribution auflösbar machen, internen Plan unverändert erhalten |
| `THESIS_UPDATE_NOTES.md`, `THESIS_CODE_TRACEABILITY.md`, `IMPLEMENTATION_REPORT.md` | nur aktuellen Kopfstatus auf Commit `5eebb72` berichtigen | historische uncommittierte Messstände ausdrücklich nicht umschreiben |
| bestätigte generierte Ausgaben | ggf. lokal entfernen | erst nach Inventar, Sicherung und Reproduktion |
| `../thesis/.gitignore` | fünf genaue Logausnahmen | bereits hashgebundene wissenschaftliche Belege im Checkout erhalten |
| `../thesis/.gitattributes` | anlegen | Zeilenendekonvertierung der beiden gebundenen Evidenzverzeichnisse verhindern |
| `../thesis/Evaluation/technische-evaluation-2026-10-22/TESTERGEBNIS.md` | Original bytegleich ergänzen | vorhandener Link zeigt ins Leere; Primärdatei außerhalb des Repositorys gefunden |
| dortiger `SHA256.json`, `../thesis/README.md` | Index um wiederhergestellten Bericht ergänzen, Herkunft und Build erläutern | alle bisherigen Hashwerte und Primärdateien unverändert erhalten |

## Milestones und Validation plan

- [x] Initiales Review, Schutzgrenzen und Ausgangsstatus prüfen.
- [x] Datei-/Import-/Referenz-/Duplikat-/Manifestprüfung abschließen.
- [x] Belegte Minimaländerungen durchführen.
- [x] `python -m pytest`, `python -m compileall -q app tests`, `python -m pip check`.
- [x] Node-Tests und Syntaxprüfung; Wheel/sdist und isolierte Installation.
- [x] Docker-Testimage, netzlose Suite und Runtime-Smoke.
- [x] Thesis aus separater Quellkopie mit `latexmk -pdf` bauen; Log prüfen.
- [x] Lokale Links, Ressourcen, Datenhashes, Präsentationsschutz, Git-Diff prüfen.
- [x] `code-documentation` auf finalen Diff, Bericht und tatsächliche Befehle anwenden.

## Rollback and recovery

Alle vorhandenen versionierten Inhalte bleiben über die Ausgangscommits verfügbar.
Kein Reset, Clean, History-Rewrite oder pauschales Löschen. Vor lokaler Entfernung
generierter Dateien Einzelpfade/Hashes und Sicherung außerhalb der Repositories
anlegen. Kein fremder Worktree wird überschrieben. Auditbelege liegen unter
`../repository-audit-2026-10-28/`; sie sind keine Anwendungseingaben.

## Progress / Discoveries / Decision log

- 2026-10-28: Workspace selbst ist kein Git-Repository; `code` und `thesis` sind
  die aktiven Komponenten. Präsentationen sind separat geschützt.
- Python 3.14.3 und Docker verfügbar; Node nicht im PATH, frühere lokale Kopie
  vorhanden. MiKTeX-Werkzeuge vorhanden, tatsächlicher Build noch offen.
- Wissenschaftliche KI-Bewertungen in Evaluationsberichten sind methodische
  Herkunft und werden bewusst erhalten.
- Die beiden Thesis-Hashindizes stimmen lokal für alle 47 Dateien. Fünf gebundene
  Logs sind jedoch ignoriert; elf weitere gebundene Dateien besitzen im Gitblob
  andere Bytes als lokal (`core.autocrlf=true`). Eine frische Quellarchiv-Ausgabe
  ist damit unvollständig bzw. hashinkonsistent. Gezielte Attribute und Logausnahmen
  beheben die Ursache; vorhandene wissenschaftliche Bytes werden nicht verändert.
- Der fehlende verlinkte `TESTERGEBNIS.md` liegt im Original unter
  `C:/Users/User/AppData/Local/LENA/evaluations/20261022-validator3/` vor. Nur dieser
  Bericht wird ergänzt, keine neuen Messergebnisse erzeugt.
- Native Regression: 1695 passed, 1 bekannter XFAIL, 1 bestehende Warnung;
  Node 24.22.0: 19/19, beide Syntaxprüfungen erfolgreich. Build Wheel/sdist,
  compileall und pip check erfolgreich.
- Isolierter Clean-Build aller versionierten Thesisquellen: 187 Seiten,
  keine abschließend undefinierten Zitate/Referenzen. Bestehende Layoutwarnungen
  und zwei BibTeX-Längenwarnungen bleiben ohne inhaltliche Redaktion erhalten.
- Bestätigte Löschfreigabe: ausschließlich `code/{app,app/providers,tests}/__pycache__/`,
  `code/.pytest_cache/` sowie ignorierte Thesis-Zwischenprodukte `thesis.{aux,bbl,blg,
  fdb_latexmk,fls,lof,log,lot,run.xml,synctex.gz,tdo,toc}`, `thesis-blx.bib` und
  vorhandene `.aux` unter `Chapters/` und `FrontBackmatter/`. Keine Quell-/Runtime-
  Referenz auf Cachedateien; LaTeX-Build erzeugt die Hilfsprodukte aus Quellen,
  Biblatex kennzeichnet seine Steuerdatei ausdrücklich als regenerierbar.
  Jede konkrete Datei wird vor Löschung per Hash in ZIP gesichert; getrackte,
  verlinkte oder außerhalb der erlaubten Wurzeln liegende Dateien werden abgewiesen.
  Das vorhandene `thesis.pdf` und sämtliche Evaluationslogs bleiben erhalten.

## Final verification summary

- Python vollständig: nativ und netzlos Linux/AMD64 jeweils 1695 passed,
  1 bekannter XFAIL, 1 bestehende TestClient-Warnung. Frontend jeweils 19/19.
- Finaler Packagingstand: 7/7 nativ und 7/7 im netzlosen Container; Wheel/sdist,
  sdist-Rebuild, Clean-Installation, CLI/API/Bootstrap bestanden. Sieben direkt
  und indirekt verlinkte öffentliche Berichte jetzt enthalten; keine fehlenden
  Datei-/Überschriftenziele in Checkout oder finaler sdist.
- Finale Docker-Test-/Runtimeziele gebaut; zweimaliger netzloser, read-only
  Runtime-Smoke mit frischem tmpfs erfolgreich. App-, Daten- und Lockbytes unverändert.
- Thesis aus sauberer Quellkopie: 187 Seiten; bestehende Layout- und zwei
  BibTeX-Längenwarnungen erhalten, keine abschließend undefinierten Zitate/Referenzen.
- 48 hashgebundene wissenschaftliche Belege auch im tatsächlichen Git-Export
  bestätigt; temporärer Prüfindex, regulärer Index unverändert und nicht gestaged.
- 219 unterschiedliche generierte Dateipfade entfernt und vollständig gesichert;
  65 durch die Packagingnachprüfung regenerierte Caches zusätzlich gesichert/geräumt.
- 39 Präsentationsmaterialdateien bytegleich; keine Schreiboperation in diesem
  Repository. Externe Änderung von `.git/FETCH_HEAD` beobachtet und nicht zurückgesetzt.
- Lokale Konfiguration, Forschungsruntime, private Thesisnotizen unverändert;
  ausschließlich generierte Editable-Metadaten vom finalen Build aktualisiert.
- Finaler Diff anhand der Review-Checkliste geprüft: keine funktionale Codeänderung,
  keine Testassertion geändert, keine wissenschaftliche Quelle/Attribution verändert,
  keine unnötige Architektur-/Abhängigkeitsmigration. `code-documentation` angewendet.
- Verbleibende Grenzen und exakte Einzelinventare siehe
  `docs/reviews/repository-audit-2026-10-28.md` sowie lokales Audit-Verzeichnis.
