# Execution Plan: Evaluation beim Anwendungsrepository bündeln

## Status

- State: Complete
- Owner: Codex
- Created: 2026-11-06
- Last updated: 2026-11-06

## Objective

`code/evaluation/` wird die einzige aktive Ablage der bislang unter
`thesis/Evaluation/` gepflegten Evaluationsunterlagen. Die Thesis verweist auf
einen festen lokalen Codecommit dieses Gesamtstands und bleibt eigenständig baubar.

## Acceptance contract

- [x] Alle 209 vorhandenen Evaluationsdateien übertragen; Originalbelege bytegleich.
- [x] Evidenzprüfung aus der Anwendungswurzel ohne Netzwerk erfolgreich.
- [x] Keine parallel gepflegte Evaluationskopie im Thesisrepository.
- [x] Aktuelle Dokumentationsverweise, Gitattribute und Ignore-Regeln angepasst.
- [x] Thesisabbildung F-01 als gekennzeichnete Abbildungskopie erhalten.
- [x] Bestehende Kapiteländerungen und wissenschaftliche Ergebnisse erhalten.
- [x] Git-Export enthält alle Belege; Docker-/Python-Laufzeit bleibt unverändert.
- [x] Lokaler Codecommit ermöglicht feste Verweise; keine Remote-Veröffentlichung.

## Scope

### In scope

Verschieben der Evaluation, Dokumentations- und Pfadanpassungen in beiden Repos,
Integritätsnachweis, lokaler Codecommit und eigenständiger Thesis-Build.

### Out of scope

Neue Evaluation, Änderung historischer Messwerte/Primärbelege, Änderungen an
Anwendung, Daten, Abhängigkeiten oder Providerkonfiguration; Release, Tag, Push,
Zenodo-Upload; Bearbeitung anderer Checkouts wie `lena-final/` oder Arbeitsarchive.

## Repository review

### Current behavior

`code/` ist das aktive Anwendungsrepo (origin lena-grounded-voice-assistant,
Branch main, HEAD 2d212a8). Werkzeuge liegen bereits in `app/live_evaluation*`.
209 versionierte Dateien (54.599.234 Bytes) liegen in `thesis/Evaluation/`.
`pruefe_evidenz.py` verwendet seinen eigenen Ordner als ROOT; der Verschiebeweg
benötigt keine neue Implementierung. Die Ausgangsprüfung besteht: 32 Fälle,
48 Screenshots, E/T/N/B 21/9/2/0, 144 technische/formative Belege,
1696 historische JUnitfälle in 54 Modulen und 126 historische Provideraufrufe.

### Relevant architecture and data flow

Thesis-README und Reproduzierbarkeitspaket verlinken bisher lokale Belege.
`Chapters/5Solutionneu.tex` verwendet F-01.png zweimal als zugeschnittene Grafik.
Die Thesis-CI baut nur das Thesisrepo. `.dockerignore` ist eine Allowlist;
`evaluation/` bleibt außerhalb des Dockerkontexts. Setuptools paketiert nur app.
`code/.gitignore` ignoriert u. a. runtime/, *.log, *.mp3 und *.ogg, die als
archivierte Belege ausdrücklich ausgenommen werden müssen. Vorhandene
SHA-256-Indizes und historische Commitzuordnungen bleiben unverändert.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Evidenzprüfung | `thesis/Evaluation/pruefe_evidenz.py` | vollständig übernehmen |
| Zeitschnitt und Ergebnisindex | `Evaluation/EVALUATIONSSTAND.md` | Ablagehinweise anpassen |
| Originalschutz | `thesis/.gitattributes` | auf code/evaluation übertragen |
| Abbildungen | `thesis/Figures/` | reine Abbildungskopie F-01 ergänzen |
| Reproduktionsdokumentation | `code/docs/reproducibility.md` | Prüfkommando ergänzen |

### Existing tests and commands

- `python Evaluation/pruefe_evidenz.py` (vorher, erfolgreich).
- `python evaluation/pruefe_evidenz.py` (nachher).
- `tests/test_packaging.py` und Git-Exportprüfung für Archivgrenzen.
- `latexmk -pdf -interaction=nonstopmode -halt-on-error thesis.tex` in separater Kopie.

### Working tree considerations

Code war sauber. Thesis hat Nutzeränderungen in Chapters/4Approachneu.tex,
Chapters/6Resultsneu.tex und Chapters/7Discussion.tex. Nur notwendige Hinweise
auf die Belegablage werden im Ergebnis-Kapitel angepasst; alle vorbestehenden
Änderungen werden separat gesichert. Keine AGENTS-Dateien in den Repos oder
übergeordneten Verzeichnissen gefunden. Keine Beitrags-/Plan-Sonderregeln gefunden.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Falsches Checkout | zusätzlich lena-final und viele Archive | zweite aktive Ablage | nur code/ und thesis/ bearbeiten | Remotes/Status prüfen |
| Ignore-Regeln verlieren Belege | runtime/, Audio, Logs ignoriert | unvollständiger Gitstand | eng begrenzte Ausnahmen für evaluation | vollständiger Pfadvergleich und Git-Export |
| Git normalisiert Originalbytes | code: text=auto eol=lf | kaputte SHA-Indizes | -text für alle acht Belegordner | Hashvergleich vor/nach und nach Git-Export |
| Thesis hängt von Nachbarcheckout ab | Grafikpfad zeigt in Evaluation | CI-Build kaputt | F-01 als deklarierte Grafik nach Figures | unabhängiger Thesis-Build |
| Alte DOI als neues Gesamtarchiv ausgeben | Zenodo v0.2.0 ohne Originale | falsche Archivbehauptung | bestehendes Archiv klar von erweitertem Gitstand trennen | Dokumentationsreview |
| Alte Prüfstände pauschal aktualisieren | historische Codestände in Belegen | Evidenzverfälschung | acht Originalordner unangetastet | Gesamtinventar/Hashvergleich |

## Recommended approach

Vorherinventar und Nutzeränderungen außerhalb beider Repos sichern, vollständigen
Evaluationsordner nach Prüfung der absoluten Quell-/Zielpfade verschieben,
nur Top-Level-Indexdokumente aktualisieren, Gitregeln übertragen, aktuelle
Verweise anpassen. Die Abbildungskopie ist ausdrücklich keine zweite Belegablage.
Nach Validierung ausschließlich die Codeänderungen lokal committen, anschließend
Thesisverweise an diesen Commit binden. Nutzeränderungen der Thesis nicht committen.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Beide Belegbestände pflegen | widerspricht einer maßgeblichen Ablage |
| Nur manuelle Ergebnisse umziehen | zerreißt Zeitschnitt und historische Integritätsprüfung |
| Thesis-CI klont vollständige Software | unnötige Build-/Netzwerkabhängigkeit für eine Abbildung |
| Historische Belegdokumente umschreiben | verletzt Byteidentität und historische Aussage |
| Bestehendes Zenodoarchiv überschreiben | nicht Teil des lokalen Umzugs |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `thesis/Evaluation/**` -> `code/evaluation/**` | Move | gemeinsame Ablage | 209 Dateien; bytegenau prüfen |
| `code/evaluation/README.md`, `EVALUATIONSSTAND.md` | Modify | neue Wurzel und Provenienz | klein |
| `code/.gitignore`, `.gitattributes` | Modify | Vollständigkeit und Originalbytes | gezielt |
| `code/README.md`, `RELEASE_REVIEW_CHECKLIST.md`, `docs/reproducibility.md` | Modify | aktuelle Fundstellen | klein |
| aktuelle weitere Belegpfade in code-Dokumentation | Modify | gebrochene Querverweise verhindern | nur Fundstellen |
| `thesis/README.md`, `Reproduzierbarkeit/*`, `Chapters/*.tex` | Modify | externe feste Fundstelle | nur Ablagehinweise |
| `thesis/Figures/lena-final-F-01.png`, `Figures/README.md` | Create | eigenständiger Grafikbuild | Originalbild unverändert |
| `thesis/.gitignore`, `.gitattributes` | Modify | obsolete Regeln entfernen | gezielt |

## Milestones

### Milestone 1: Review and design

- [x] Anweisungen, Status, Diffs und relevante Pfade geprüft.
- [x] Evidenzprüfung vor Umzug erfolgreich.
- [x] Wiederverwendung und Risiken bewertet.

### Milestone 2: Implementation

- [x] Vollständige Übertragung und Dokumentationsanpassung im Anwendungsrepo.
- [x] Lokalen Gesamtstand fixieren und Thesisverweise binden.

### Milestone 3: Verification

- [x] Inventar/Hashwerte, Ignore-Regeln und Git-Export prüfen.
- [x] Evidenzprüfung am Ziel und aus sauberem Export ausführen.
- [x] Thesis unabhängig bauen; vorbestehende Änderungen erhalten.
- [x] Relevante Packagingchecks und Diffprüfung im Anwendungsrepo.

### Milestone 4: Documentation

- [x] code-documentation gelesen und für bestehende Dokumentation angewandt.
- [x] Dokumentationslinks, Kommandos und historische Abgrenzung abschließend prüfen.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Originale | SHA-256-Inventar aller 209 Dateien vor/nach | nur beide redaktionellen Indexdateien geändert |
| Evidenz | `python evaluation/pruefe_evidenz.py` | unveränderte Zahlen, 144 Belege bytegleich |
| Gittransport | staged paths / git archive / erneute Prüfung | alle 209 übertragenen Dateien enthalten |
| Packaging | vorhandene tests/test_packaging.py | keine Belege im Laufzeitpaket |
| Thesis | latexmk in eigener Kopie ohne code/ | PDF erfolgreich gebaut |
| Nutzeränderungen | Vorherkopien und selektiver Diff | vorhandene Änderungen vollständig erhalten |

## Rollback and recovery

Der Thesis-HEAD erhält die alte Belegablage; alle Dateien vor dem Umzug werden
zusätzlich per SHA-256 inventarisiert. Vorbestehende Nutzeränderungen und betroffene
Dokumente werden außerhalb beider Repos gesichert. Bei Fehlern Ordner auf den
geprüften alten Pfad zurückverschieben und ausschließlich eigene Textänderungen
rückgängig machen; kein Reset des Nutzerarbeitsbaums. Keine alten Historien ändern.

## Progress log

- 2026-11-06 — Review und erfolgreiche Ausgangsprüfung; Plan erstellt.

## Decision log

- Ziel ist code/evaluation/ im aktiven Softwarecheckout. Andere Checkouts bleiben erhalten.
- Originalbelege bleiben bytegleich; neue Provenienz auf Indexebene. Nur die
  Quellverweise im README der manuellen Finalprüfung werden angepasst.
- Lokaler Codecommit dient als feste Fundstelle; Veröffentlichung ist gesondert.

## Discoveries

- Zwei TeX-Grafiken verwenden dieselbe F-01-Datei, daher genügt eine Abbildungskopie.
- Der Evidenzprüfer ist bereits ortsunabhängig innerhalb des gesamten Belegordners.
- README der manuellen Finalprüfung hatte Querverweise außerhalb des
  Belegordners. Die App-Verweise zeigen nun innerhalb des Anwendungsrepos; der
  Thesisanhang und ein exportierter Entwicklungsplan sind an ihre ursprünglichen
  Repositorycommits gebunden. Sonst bleiben
  alle Inhalte der acht datierten Belegordner unverändert.
- Move-Item hat die Dateien erfolgreich übertragen, konnte aber schreibgeschützte
  leere OneDrive-Verzeichnisse am alten Ort nicht entfernen. Die automatische
  Befehlsprüfung hat das Entfernen dieser leeren Verzeichnisse abgelehnt.
  Es verbleiben dort keine Dateien und keine zweite aktive Evaluationsablage;
  leere Verzeichnisse sind kein Bestandteil des Gitbestands.
- Inventarvergleich: 209 Dateien übertragen, davon 206 bytegleich; Änderungen
  ausschließlich README.md, EVALUATIONSSTAND.md und Quellverweise in
  manual_final_20261029/README.md. Alle 144 bestehenden Hashbindungen bestehen.
- Packaging: `python -m pytest tests/test_packaging.py` erfolgreich, 7 passed
  in 81,27 Sekunden. Wheel und sdist enthalten keinen evaluation/-Belegbestand.
- Sauberer Gitexport enthält alle 209 übertragenen Dateien; 206 davon sind
  auch nach dem Gittransport bytegleich zum Ausgangsinventar. Die providerfreie
  Evidenzprüfung besteht unabhängig von einem Nachbarcheckout.
- `git diff --cached --check` besteht. Anwendung, Daten, Tests, Dockerfile,
  MANIFEST.in und pyproject.toml bleiben unverändert.

## Final verification summary

- Acceptance requirements: alle erfüllt. Alle 209 Dateien übertragen, 206
  bytegleich; drei README-/Indexdokumente redaktionell angepasst. Keine neuen
  Messungen oder Ergebnisänderungen. Historische Source-Commitbindungen bleiben.
- Tests: providerfreie Evidenzprüfung im Checkout und separaten Gitexport
  erfolgreich; 144 Hashbindungen intakt. Sieben Packagingtests erfolgreich;
  Wheel und sdist ohne zusätzlichen Evaluationsbestand.
- Build: unabhängige Thesisquellenkopie ohne Anwendungs- oder Evaluationsordner
  mit latexmk erfolgreich gebaut, 161 Seiten. Der Build meldet zwei ungelöste
  acro:wfs-Hyperverweise im bereits vorher bearbeiteten Tabellenverzeichnis.
  Diese Abkürzungswarnungen betreffen keinen durch den Umzug geänderten Pfad.
- Manual verification: alle drei zuvor bearbeiteten Kapitel anhand gesicherter
  Arbeitsbaumkopien geprüft; einzig die notwendigen Ablagehinweise in Kapitel 4
  und 6 ergänzt, Kapitel 7 bytegleich erhalten. Beide Grafikverwendungen zeigen
  auf eine bytegleiche, ausdrücklich gekennzeichnete Abbildungskopie von F-01.
- Documentation: code-documentation angewandt, bestehende README, Release-
  Checkliste und Reproduktionsdokumentation aktualisiert, Thesispfade und
  Archivierungsabgrenzung aktualisiert. 102 lokale Markdownlinks und 13 feste
  Gitreferenzen gegen vorhandene Gitobjekte geprüft. Diffprüfungen bestanden.
- Residual risks: der Codecommit ist lokal; GitHub-Permalinks benötigen dessen
  spätere Übertragung. Das bestehende Zenodoarchiv enthält keine nachträglich
  verschobenen Originale. Keine Veröffentlichung oder neue Releasezuordnung.
  Leere schreibgeschützte OneDrive-Ordner bleiben am alten Ort; ihr Entfernen
  wurde automatisch blockiert. Die Thesisänderungen bleiben wegen vorhandener
  Nutzeränderungen als prüfbarer Arbeitsstand ohne Commit erhalten.
