# Repository-Audit und konservative Bereinigung vom 28.10.2026

## Ergebnis und Prüfgrenze

Die geprüften Anwendungs-, Paketierungs-, Container- und Thesis-Buildpfade sind
technisch konsistent. Die Bereinigung entfernt ausschließlich gesicherte,
ignorierte technische Zwischenprodukte. Anwendungscode, Schnittstellen,
Testszenarien, Daten, wissenschaftliche Quellen und bestehende Messwerte wurden
nicht funktional verändert. Vollständig eingefrorene, bitidentische Reproduktion
aller Umgebungen und externer Modellantworten wird nicht behauptet.

Ausgangsstände: Code `5eebb72`, Thesis `acf0e01`, beide Worktrees sauber.
Der gemeinsame Workspace selbst ist kein Git-Repository. Keine Commits,
Tags, Pushes, History-Rewrites oder destruktiven Git-Befehle ausgeführt.
Der reguläre Stagingbereich bleibt leer. Änderungen sind zur Prüfung vorbereitet.

## Inventar und Schutz

| Bereich | Bestand / Rolle | Behandlung |
|---|---|---|
| `code/` | 248 versionierte Dateien, darunter 131 Pythondateien, 56 Markdown-Dateien, statisches Frontend und vendortes Leaflet | vollständig inventarisiert; Imports, Ressourcen, Paketierung, Konfiguration und Tests geprüft |
| `thesis/` | 92 versionierte Dateien, darunter 25 TeX-Dateien, Bibliographie, drei Abbildungen und Evaluationsnachweise | Quellen und aktive Include-Kette geprüft; isoliert gebaut |
| `presentations/` | 39 Materialdateien außerhalb der Git-Metadaten | ausschließlich schreibgeschützt inventarisiert; alle 39 Originalhashes unverändert |
| Lokale Konfiguration / Laufzeit / private Thesisnotizen | Schutzmomentaufnahme von 345 Dateien in `code/runtime/`, `.env`, `.env.local`, `lena_code3.egg-info/`, `thesis/docs/` | Konfiguration, Forschungsruntime und private Notizen unverändert; nur generierte `egg-info/PKG-INFO` und `SOURCES.txt` durch den finalen Build an README/Manifest angepasst |
| Workspacearchive | u. a. `Code3-archive-pre-git-20260717/`, `legacy_review_backup/`, `migration_quarantine/`, frühere Audits und Thesisvarianten | Herkunfts- und Referenzkontext; keine Löschungen oder Umzüge |

Keine anwendbaren AGENTS-Dateien in aktiven Repositories oder Eltern gefunden.
Außerhalb von `presentations/` wurden in den aktiven versionierten Beständen
keine zusätzlichen Präsentationsdateien anhand der Pfad-/Endungsprüfung erkannt.
Es erfolgten keinerlei Schreiboperationen durch diese Prüfung in `presentations/`.
Die mitinventarisierte Datei `presentations/.git/FETCH_HEAD` hat sich während des
Audits verändert; keine ausgeführte Auditoperation schreibt diesen Pfad oder führt
Git-Befehle in diesem Repository aus. Die externe Ursache ist nicht abschließend
zugeordnet; die Metadatei wurde bewusst nicht zurückgesetzt. Präsentationsmaterialien
selbst sind unverändert.

## Architektur, Referenzen und Abhängigkeiten

`app/__main__.py` startet FastAPI; `app/service.py` orchestriert kuratierte Daten,
deterministische Kandidatenregeln, explizite Sprachdienste und Grounding.
Releasepointer, Manifeste, Rohstände und Übersetzungsprovenienz gehören zum
Reproduktionsvertrag. Statisches JavaScript benötigt keinen npm-Build.
Keine JavaScript-Paketdefinition, kein Lockfile dieses Ökosystems, keine Notebooks,
Makefiles oder zusätzlichen Deploy-Anwendungen im aktiven versionierten Bestand.

Alle lokalen Python-Modulimporte sind auflösbar. Der Importgraph umfasst auch
Tests und Wartungsmodule. Das einzige Paket ohne direkten Importverbraucher ist
`app.providers` selbst: seine Untermodule benötigen den Paketcontainer.
Einfach vorkommende Symbole sind insbesondere Pydantic-Validatoren,
FastAPI-Handler und durch Pytest entdeckte Tests; sie sind keine Löschkandidaten.
Die acht statisch erfassten HTML-/CSS-/JS-Ressourcenbezüge sind vorhanden;
Packagingtests prüfen zusätzlich die ausgelieferten Frontenddateien.
Alle aktiven lokalen TeX-Includes, Bibliographie- und Abbildungsbezüge lösen auf.
`Chapters/6Resultsneu.tex` und `ErgebnisSpezifikation.tex` sind indirekt eingebunden.

| Abhängigkeit | Verwendungsbeleg | Entscheidung |
|---|---|---|
| `av` | Audio-Normalisierung in `app/speech.py` und Transkriptionstests | erhalten |
| `fastapi` | API, Routing und TestClient | erhalten |
| `edge-tts` | explizites optionales TTS-Profil in `app/speech.py` | erhalten |
| `httpx` | Provider, Quellsynchronisierung, Sprachdienste und Tests | erhalten |
| `pydantic` | API-, Daten-, Interpretations-, Release- und Groundingverträge | erhalten |
| `tzdata` | `zoneinfo` / `Europe/Berlin`, insbesondere plattformabhängiger Fallback | erhalten |
| `uvicorn` | nativer Servereinstieg | erhalten |
| `build`, `pytest`, `setuptools` | dokumentierte Entwicklungsbefehle, CI, Buildbackend und Packagingtests | erhalten |
| transitive Constraints und Hashlocks | 3.12-Locks stimmen mit den entsprechenden Constraints und allen direkten Versionsbereichen überein | erhalten |
| `colorama` | Windowsabhängigkeit im Constraintsbestand; im Linux-Lock nicht erforderlich | erhalten |

**Keine Abhängigkeit entfernt, ergänzt oder aktualisiert.** Kein belastbarer
Entbehrlichkeitsbeleg; installierte Auflösung und getestete Containerauflösung
sind konsistent. Die Locks sind ausdrücklich Linux/CPython 3.12 zugeordnet,
die 3.11-Constraints bleiben der CI zugeordnet. Keine spekulativen Versionswechsel.

## Konkrete Änderungen

### Wiederhergestellte Exportierbarkeit wissenschaftlicher Belege

Lokal passten vor Änderungen alle 47 indizierten Originaldateien. Ein frischer
Git-Export enthielt jedoch fünf Logs nicht; elf weitere Belege hatten durch
Zeilenendenkonvertierung andere Gitblob-Bytes als die hashgebundenen lokalen
Originale (`core.autocrlf=true`). Folgende minimale Korrekturen beheben dies:

- `thesis/.gitattributes` ergänzt: keine Textkonvertierung in den beiden
  gebundenen technischen Evaluationsverzeichnissen.
- `thesis/.gitignore` ergänzt: Attribute-Datei sichtbar machen und genau die
  fünf bereits indizierten Logs ausnehmen:
  `docker-test.log`, `native-frontend.log`, `native-js-dialogue.log`,
  `native-js-main.log`, `native-pip-check.log`, jeweils unter
  `Evaluation/technische-evaluation-2026-10-22/`.
- `Evaluation/technische-evaluation-2026-10-22/TESTERGEBNIS.md` aus dem
  ursprünglichen Messarchiv bytegleich ergänzt. Damit löst der vorhandene Link
  in `VERTRAGSPRUEFUNG.md` wieder auf. SHA-256:
  `db520bc41fcd27a6c7f5194c640b79982e10b388e09e4d3723664002db94c0fc`.
- Dortigen `SHA256.json` um genau diesen Bericht erweitert; alle 31 vorherigen
  Einträge und sämtliche zuvor indizierten Dateibytes unverändert erhalten.
- `thesis/README.md` um tatsächlich ausgeführten Buildbefehl, Grenzen,
  Byteschutz und transparente Herkunft der Ergänzung erweitert. Die eingefrorene
  README des Belegverzeichnisses bleibt unverändert.

Die elf vorhandenen Dateien mit nun sichtbaren reinen Git-Zeilenendekorrekturen
sind im Verzeichnis vom 22.10.:
`additional-verification.json`, `artifact-verification.json`,
`BEISPIELANTWORTEN.md`, `container-verification.json`, `IMPORTNACHWEIS.json`,
`pdf-verification.json`, `thesis-verification.json`, `VERTRAGSPRUEFUNG.md`;
im Verzeichnis vom 26.10.:
`measurement-profile.json`, `measurement-summary.json`, `source-manifest.json`.
Ihre lokalen Inhalte wurden nicht geändert. Nur die Dateistatistik wurde
aktualisiert, damit Git die erforderliche Speicherung der Originalbytes erkennt.
Bei `git diff --ignore-space-at-eol` verschwinden diese elf Diffs vollständig.

Ein Export mit separatem temporärem Index enthält alle nun 48 gebundenen Dateien
mit korrekten Hashes. Der Hash des regulären Git-Index blieb dabei unverändert.
Diese Bytes und die fünf bislang ignorierten Logs müssen beim nächsten regulären
Commit mit aufgenommen werden; es wurde nichts automatisch gestaged oder committet.

### Wartungsdokumentation und neutrale Arbeitsmetadaten

- `code/README.md`: „noch uncommittiert“ auf Commit `5eebb72` korrigiert;
  aktuellen Teststand 1695 / Validator 10 / Copy 11 korrekt zugeordnet,
  passenden Nachweis verlinkt und älteren Ablationsstand als historisch bezeichnet.
- Aktuelle Kopfstatus in `IMPLEMENTATION_REPORT.md`, `THESIS_UPDATE_NOTES.md`
  und `THESIS_CODE_TRACEABILITY.md` ebenfalls auf `5eebb72` berichtigt.
  Historische Aussagen über damals uncommittierte Messstände bleiben erhalten.
- `MANIFEST.in` und `.dockerignore`: die sieben öffentlich versionierten,
  mehrfach referenzierten Dateien `IMPLEMENTATION_REPORT.md`,
  `RELEASE_REVIEW_CHECKLIST.md`, `THESIS_CODE_TRACEABILITY.md`,
  `THESIS_UPDATE_NOTES.md`, `AUDIT_REPORT.md`, `REPRODUCIBILITY_MATRIX.md`,
  `REPOSITORY_CLEANUP_PLAN.md` aufnehmen. Zuvor fehlten direkt/indirekt
  referenzierte Berichte in der sdist und im
  Docker-Quellkontext; 34 lokale Markdownlinks waren dadurch in der anfänglich
  gebauten sdist nicht auflösbar, einschließlich eines ausgeschlossenen Plans.
- `docs/validator-ablation-decisions.md`: Methoden-/Ergebnislink auf den
  öffentlichen Ablationsbericht umstellen; den ursprünglichen internen Plan
  weiter als nur im Entwicklungscheckout verfügbaren Herkunftspfad benennen.
  Interne Pläne bleiben aus der Distribution ausgeschlossen.
- `docs/architecture.md`: vorhandenen Fragmentlink an die tatsächliche
  Überschrift „Prompt 18 und begrenztes Korrekturfeedback“ anpassen.
- `code/.gitignore`: toolspezifische Worktree-Regel durch die allgemeine
  Regel `/.*/worktrees/` ersetzt. Beide Schutzbeispiele wurden mit
  `git check-ignore` geprüft; lokale Arbeitskopien bleiben geschützt.
- `code/IMPLEMENTATION_REPORT.md` und `RELEASE_REVIEW_CHECKLIST.md`:
  drei rein prozedurale Toolnennungen in damaligen Commitbeschränkungen neutralisiert.
  Keine wissenschaftliche Bewertung oder deren Urheberschaft verändert.
- `code/tests/test_packaging.py`: unbelegte Versionsangabe „seit 0.3.0“ aus
  einem Kommentar im eingebetteten Smoke-Skript entfernt; tatsächliche Version
  bleibt 0.2.0, Testcode und Assertions unverändert.
- 15 Wartungspläne: ausschließlich Toolnamen aus Owner-/Statusmetadaten entfernt
  oder durch den sachlichen Arbeitsbereich ersetzt. Keine Person als Autor eingesetzt.

Betroffene Dateien unter `code/docs/exec-plans/`:

```text
audio-activation.md
card-translation-completeness.md
codebase-modernization.md
complete-synthetic-evaluation.md
curate-timmitohelp-thursday-route.md
final-technical-quality-gate.md
fix-food-age-restriction.md
fix-formulator-fallback-sie-and-menschen-collision.md
fix-shower-sleep-firefox.md
quality-review-2026-09.md
repository-cleanup.md
validator-final-false-positives.md
work-package-7-multilingual-quality-assurance.md
work-package-8b-drinking-fountains.md
work-package-9b-controlled-live-provider-evaluation.md
```

Wissenschaftliche KI-Offenlegung in `FrontBackmatter/Declaration.tex`,
Modellkennungen, diagnostische KI-Reviews, Reviewer-Verträge und
Übersetzungsprovenienz bleiben bewusst erhalten. Deren Neutralisierung würde
die Bewertungsmethode oder Herkunft verschleiern. Lizenzen, Copyright,
Attributionen, Paketautor und Git-Historie bleiben unverändert.

Neu: dieser Bericht und `docs/exec-plans/repository-audit-2026-10-28.md`.
Die bestehenden Ausschlüsse für Wartungspläne/-reviews aus Software-Releases
bleiben erhalten. Private Thesisnotizen werden weiterhin nicht exportiert.

### Gelöschte Dateien und Verzeichnisse

**Keine versionierte Datei gelöscht. Keine vorhandene Datei verschoben,
umbenannt oder zusammengeführt.** Lokal entfernt: **219 ignorierte generierte
Dateien, 9.218.852 Bytes**, vollständig vorab gesichert.

| Bereich | Anzahl | Belastbarer Entbehrlichkeitsbeleg |
|---|---:|---|
| `code/app/__pycache__/`, `code/app/providers/__pycache__/`, `code/tests/__pycache__/`, `code/.pytest_cache/` | 191 Dateien | Python-/Pytest-Cacheformate, keine getrackte Datei, keine Quell-/Konfigurationsreferenz oder eigener Bytecodelader; vollständige Suite, Compile und Builds erfolgreich |
| ignorierte LaTeX-Zwischenprodukte in `thesis/` | 28 Dateien | erfolgreicher Clean-Build aus ausschließlich versionierten Quellen; Biblatex-Steuerdatei ausdrücklich regenerierbar, keine wissenschaftlichen Primärbelege oder PDFs betroffen |

Zusätzlich die sechs anschließend leeren Verzeichnisse entfernt:
`code/app/__pycache__/`, `code/app/providers/__pycache__/`,
`code/tests/__pycache__/`, `code/.pytest_cache/v/cache/`,
`code/.pytest_cache/v/`, `code/.pytest_cache/`.
OneDrive schützte zunächst ein leeres Cacheverzeichnis per Read-only-Attribut;
nach Prüfung des exakten erlaubten Pfads wurde nur dieses technische
Verzeichnisattribut zur vollständigen Entfernung der leeren Caches freigegeben.

Die LaTeX-Dateien im Einzelnen:

```text
Chapters/1Introductionneu.aux
Chapters/2Preliminariesneu.aux
Chapters/3RelatedWork.aux
Chapters/4Approachneu.aux
Chapters/5Solutionneu.aux
Chapters/6Resultsneu.aux
Chapters/7Discussion.aux
Chapters/AppendixLenaDesign.aux
FrontBackmatter/Acknowledgments.aux
FrontBackmatter/Bibliography.aux
FrontBackmatter/Contents.aux
FrontBackmatter/Declaration.aux
FrontBackmatter/Summary.aux
FrontBackmatter/Titleback.aux
FrontBackmatter/Titlepage.aux
thesis-blx.bib
thesis.aux
thesis.bbl
thesis.blg
thesis.fdb_latexmk
thesis.fls
thesis.lof
thesis.log
thesis.lot
thesis.run.xml
thesis.synctex.gz
thesis.tdo
thesis.toc
```

Das vollständige **Einzelinventar sämtlicher 219 Dateien** einschließlich Größe,
Hash und Grund steht in
[`removed-files.json`](../../../repository-audit-2026-10-28/removed-files.json),
die Verzeichnisse in
[`removed-directories.json`](../../../repository-audit-2026-10-28/removed-directories.json).
Reversible Sicherung:
[`removed-generated-files.zip`](../../../repository-audit-2026-10-28/removed-generated-files.zip).
ZIP-Integrität und jeder enthaltene Dateihash wurden vor Löschung geprüft.
Die zusätzliche Packagingprüfung erzeugte 65 Cachedateien erneut, sämtlich auf
bereits erfassten Pfaden. Sie wurden abschließend ebenfalls inventarisiert,
gesichert und entfernt; die Anzahl unterschiedlicher entfernter Dateipfade bleibt
219. Zweiter Nachweis:
[`removed-validation-files.json`](../../../repository-audit-2026-10-28/removed-validation-files.json),
Sicherung:
[`removed-validation-generated-files.zip`](../../../repository-audit-2026-10-28/removed-validation-generated-files.zip).
Das vorhandene `thesis/thesis.pdf` bleibt erhalten. Audit-Ausgaben, separate
Buildkopien und Sicherungen liegen gesammelt außerhalb der beiden Repositories
unter `repository-audit-2026-10-28/`; keine Laufzeiteingaben wurden dort eingeführt.

## Validierungen

| Prüfung | Ergebnis / Evidenz |
|---|---|
| `python -m pytest -ra` auf Python 3.14.3 | 1695 passed, 1 bekannter strict XFAIL, 1 bestehende Warnung; 527,64 s; `pytest.log` |
| `python -m compileall -q app tests` | erfolgreich |
| `python -m pip check` | keine defekten Abhängigkeiten |
| Node 24.22.0 `--test tests/frontend.test.cjs` | 19/19; `frontend.log`; vorhandene lokale Node-Kopie verwendet, da Node nicht im PATH |
| Node `--check app/static/app.js` und `dialogue.js` | beide erfolgreich |
| `python -m build --outdir ../repository-audit-2026-10-28/dist` | Wheel und sdist gebaut; `build.log` |
| Packagingtests der vollständigen Suite | frische Wheelinstallation außerhalb Checkout, CLI/API/Bootstrap, sdist→Wheel und Paketressourcen bestanden |
| abschließende Packagingtests nach Manifeständerung | nativ 7/7 in 96,81 s; finaler netzloser Container 7/7 in 20,24 s; `final-packaging-tests.log`, `final-container-packaging.log` |
| abschließender Build und Paketdokumentation | Wheel/sdist mit sieben ergänzten Berichten gebaut; 181 Checkout- und 143 sdist-Markdownlinks einschließlich Überschriftenzielen ohne fehlendes Ziel; `final-build.log`, `final-link-verification.json` |
| `docker build --target test -t lena-repository-audit-test:20261028 .` | erfolgreich; vorhandene Basis-Layer, neue hashgeprüfte Abhängigkeitsinstallation und Offline-Paketierung; `docker-build-test.log` |
| `docker run --rm --network none lena-repository-audit-test:20261028` | Linux/AMD64, CPython 3.12: 1695 passed, 1 bekannter XFAIL, 1 Warnung; 346,02 s; danach compileall, pip check, 19/19 JS und beide Syntaxchecks erfolgreich; `docker-test.log` |
| `docker build --target runtime -t lena-repository-audit-runtime:20261028 .` | erfolgreich; `docker-build-runtime.log` |
| zwei echte Runtime-Starts | ohne Netzwerk, read-only, frisches tmpfs, kein Hostport: Health, KB, Oberfläche, JS-Assets und HTTP-Query-Fallback bestanden; `runtime-smoke.json`; nur eigene Testcontainer danach beendet/entfernt |
| `latexmk -pdf -interaction=nonstopmode -halt-on-error thesis.tex` | separate saubere Kopie der 92 versionierten Thesisdateien: 187 Seiten, 2.693.649 Bytes; keine abschließend undefinierten Zitate/Referenzen; `thesis-build.log` |
| aktive lokale TeX-/Markdown-/Assetreferenzen | fehlender Ergebnisbericht wiederhergestellt; abschließende Pfadprüfung ohne fehlende lokale Markdownziele oder aktive TeX-/Assetziele |
| Hash- und Git-Exportprüfung | alle 48 gebundenen Dateien passen auch im Quell-ZIP; `export-verification.json`; regulärer Index unverändert |
| Python-Semantikvergleich | 130 Datei-ASTs unverändert; beim Packagingtest auch der AST des eingebetteten Python-Skripts unverändert; ausschließlich Kommentar geändert; `semantic-preservation.json` |
| Anwendung, Daten, Constraints/Locks | alle ursprünglichen Bytes unter `app/`, `data/`, `requirements/` unverändert |
| Diff-/Schutzkontrolle | `git diff --check` in beiden Repositories erfolgreich; keine wissenschaftliche Quelldatei, Präsentation, Lizenz oder bestehende Testassertion geändert |

Logs und maschinenlesbare Einzelbefunde befinden sich im
[`Audit-Verzeichnis`](../../../repository-audit-2026-10-28/).
Die abschließenden README-/Wartungsdokumentationsänderungen, Paketdefinitionen
und der reine Testkommentar ändern die vollständig geprüften Laufzeitbytes nicht.
Der finale Containerbau und die gesonderten Packagingtests prüfen die veränderte
Distribution zusätzlich. Die vollständigen funktionalen Suiten wurden deshalb
nicht allein wegen dieser Dokumentations-/Paketkorrekturen wiederholt.

Nicht vorhanden: konfigurierte Linter-, Formatter- oder Typprüfungswerkzeuge.
Deshalb keine neuen Werkzeuge/Regeln eingeführt und keinen solchen Check als
bestanden ausgegeben. Python 3.11 und ARM64 wurden in diesem Audit nicht
zusätzlich ausgeführt; die vorhandenen CI-/Lockdefinitionen bleiben erhalten.

Ein erster LaTeX-Aufruf scheiterte bereits bei der Argumentauswertung von
`-outdir=.` unter PowerShell, bevor Quellen verarbeitet wurden. Der korrigierte
Aufruf im separaten Buildverzeichnis bestand vollständig. Das Fehlerlog bleibt
als `thesis-build-initial-error.log` dokumentiert; keine Quellen wurden dadurch verändert.

## Bewusst erhaltene Kandidaten und konkrete Restpunkte

1. Vier bytegleiche Datengruppen bleiben wegen verschiedener Rollen erhalten:
   `canonical/offers.json`, `i18n/offer_translations.json`, `wfs/current.geojson`,
   `wfs/last_change_report.json` unter `data/` und Paket-Bootstrap. Keine
   Deduplizierung ohne Änderung des Lade-/Paketierungsvertrags.
2. Historische Retrieval-/Renderer-/Loaderwege einschließlich Fixture und
   Regressionstests bleiben erhalten: direkte/indirekte Imports, Testverträge,
   Vergleichbarkeit oder dokumentierte Kompatibilität. Kein öffentliches Symbol
   wurde aufgrund eines fehlenden HTTP-Verbrauchers gelöscht.
3. WFS-/Toiletten-/Brunnenreleases, Snapshots, Diffdateien, aktive Pointer,
   Kurationsmetadaten, Rohdaten, Evaluationen, negative Ergebnisse und
   Übersetzungsreviewstatus bleiben unverändert.
4. Nicht aktive Templatekapitel `BibTips`, `GitTips`, `LatexTips`, `PrintTips`,
   Frontmatter `Abstract`, `Dedication`, `Titleback` sowie die ältere Abbildung
   `Figures/lena-frontend-result-80950ba.png` bleiben wegen möglicher
   Template-/Historienfunktion erhalten. Fehlende aktive Einbindung allein ist
   kein Entbehrlichkeitsnachweis.
5. Workspace-Thesisvarianten, frühere Auditstände, `fixture-S-12.log`, lokale
   Sessions und Forschungslogs bleiben mangels belastbarer Entbehrlichkeit erhalten.
   `lena_code3.egg-info/` bleibt für Editable-Metadaten/Versionsauflösung erhalten.
6. Bestehender XFAIL: „minor injuries“ kann die Zielgruppenworterkennung
   übermäßig aktivieren. Keine funktionale Änderung im Bereinigungsauftrag.
7. Bestehende Starlette-TestClient-Warnung empfiehlt `httpx2`. `httpx` wird aber
   aktiv zur Laufzeit verwendet; eine Clientmigration wäre eine gesonderte
   API-/Kompatibilitätsänderung, keine belegte Abhängigkeitsbereinigung.
8. Thesis: 191 Overfull- und 510 Underfull-Meldungen im abschließenden Log,
   bestehende Templatewarnungen und zwei BibTeX-Längenwarnungen zum Eintrag
   `comaniciGemini25Pushing2025`. Kein fehlendes Zitat, kein Buildabbruch;
   Layout-/Bibliographieredaktion ist nicht Bestandteil dieses Audits.
9. 18 handgeschriebene Appmodule überschreiten 400 Zeilen, insbesondere
   `service.py` (1545), `live_evaluation_runner.py` (980), `formulation.py` (752).
   Eine Aufteilung wäre ein gesondertes, funktional abzusicherndes Refactoring.
10. Docker fixiert Basis, Ubuntu-Snapshot und Python-Locks; der tatsächlich
    ausgeführte Build verwendet Basis-Caches. Kein neuer No-Cache- oder
    ARM64-Nachweis und keine bitidentische Binärreproduktion behauptet.
    Native Buildisolation und TeX-/CI-Umgebung sind nicht vollständig eingefroren.
11. Live-Provider-, Audio-, fachliche und muttersprachliche Qualitätsprüfungen
    wurden nicht neu durchgeführt. Externe Dienste und Modellaliasauflösungen
    verhindern die Garantie identischer zukünftiger Antworten. Historische
    absolute Archivpfade bleiben als Herkunftsinformation erkennbar; nicht
    sämtliche außerhalb liegenden Forschungsarchive sind Teil eines Git-Checkouts.

## Dokumentation und abschließende Bewertung

`code-documentation` wurde zur Prüfung des finalen Diffs angewendet:
Setupbefehl tatsächlich ausgeführt, aktuelle Versions-/Messzuordnung berichtigt,
lokale Pfade und Links geprüft, historische Aussagen von aktuellen Nachweisen
getrennt und keine neuen öffentlichen APIs oder spekulativen Funktionen dokumentiert.
Vorhandene Dokumentation wurde ergänzt; keine parallele Projektstruktur eingeführt.

Das Repository ist im geprüften Umfang aufgeräumt und technisch konsistent.
Wissenschaftliche Belege sind nach Aufnahme der vorbereiteten Git-Änderungen
vollständiger und bytegetreu exportierbar. Reproduzierbare Installation und
Buildbarkeit wurden praktisch geprüft; vollständige externe, plattformübergreifende
oder bitidentische Reproduzierbarkeit bleibt ausdrücklich begrenzt wie oben beschrieben.
