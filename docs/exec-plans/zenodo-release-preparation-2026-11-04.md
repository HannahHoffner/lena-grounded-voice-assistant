# Execution Plan: Zenodo-Vorbereitung des Thesis-Codes

## Status

- State: Verified
- Owner: Codex
- Created: 2026-11-04
- Last updated: 2026-11-04

## Objective und acceptance contract

Das von der Nutzerin ausgewählte Entwicklungsrepository
`HannahHoffner/lena-grounded-voice-assistant` für eine prüfbare wissenschaftliche
Archivierung vorbereiten.

- [x] Versionierte Dateien, lokale sensible Dateien und erreichbare Git-Historie prüfen.
- [x] Vorhandene Lizenz und Dokumentation bewahren; fehlende Start-/Compose-Hilfe ergänzen.
- [x] CITATION.cff validieren; keine DOI oder Veröffentlichung erfinden.
- [x] Exakte Codebasis für den Archivcommit festlegen; Commit-SHA im getrennten Prüfmanifest führen.
- [x] Prüfungen, Grenzen und konkrete Veröffentlichungshindernisse dokumentieren.
- [x] Anwendung, Tests, Datenbytes und historische Evaluation unverändert lassen.

## Scope

In scope: lokale Vorbereitung, Metadaten, Compose, Archivprüfung und Nachweis.
Out of scope: Push, Tag, GitHub-Release, öffentliche Sichtbarkeit, Zenodo-Publish,
Datenlizenzvergabe, Umschreiben der Git-Historie, Änderungen am Thesis-Repository
oder am getrennten Repository `lena-final`.

## Repository review

### Current behavior und Architektur

Sauberes Arbeitsverzeichnis auf `105c0b19fd91a8d1c71b9eda259f0380a947cf9c`.
FastAPI wird über `python -m app` gestartet. Dockerfile enthält Build-, Test-
und Runtime-Ziel, nicht privilegierte UID 10001 und flüchtige `/tmp`-Daten.
Provider, Quellenabruf und Interaktionslogging sind standardmäßig deaktiviert.
Eigener Code ist bereits GPL-3.0-only; LICENSE enthält den vollständigen Text.
CITATION.cff nennt Hannah Hoffner und Version 0.2.0, noch kein Releasedatum/DOI.
Keine Compose-Datei. README ist ausführlich; nativer Pfad `cd code` passt nur
zum lokalen Workspace, nicht zum dokumentierten Clone-Namen.

Die Thesis auf `28ca468` bindet ihre Finalprüfung an
`5962d6c172d6f6eeddf6bc65c8644b833838b671`. Zwischen diesem Commit und HEAD sind
nur vier Dokumentationsdateien geändert. Bootstrap und Wartungsdaten enthalten
öffentlich beschriebene Einrichtungen und Kontakte; die Weitergaberechte des
Trinkbrunnenbestands sind ausdrücklich ungeklärt. GitHub meldet das Repository
am 04.11.2026 als privat. Die Nutzerin wählte dieses Repository ausdrücklich.

### Existing structures to reuse

| Struktur | Pfad | Entscheidung |
|---|---|---|
| Betriebsanleitung | README.md, docs/setup.md | gezielt ergänzen |
| Release-Anleitung | docs/release.md | präzisieren und Audit verlinken |
| Lizenz und Datenherkunft | LICENSE, THIRD_PARTY_NOTICES.md | erhalten |
| Zitiermetadaten | CITATION.cff | einzige Metadatenquelle, validieren |
| Verpackung | Dockerfile, MANIFEST.in, .dockerignore, .gitattributes | vorhandene Ausschlüsse verwenden |
| Prüfungen | tests/test_packaging.py, tests/test_configuration_profiles.py | gezielte Regression |

### Tests und working tree

Python 3.14.3, pytest, build, PyYAML verfügbar. Docker-CLI vorhanden, Engine
anfangs nicht erreichbar. Keine neuen Laufzeitabhängigkeiten erforderlich.
Lokale `.env`, `.env.local`, `runtime/` und `fixture-S-12.log` sind ignoriert;
ihre Inhalte nicht in Ausgaben oder Dokumentation übernehmen und nicht löschen.

## Dead-end analysis

| Sackgasse | Evidenz / Auswirkung | Gegenmaßnahme / Verifikation |
|---|---|---|
| Gesamten lokalen Ordner zippen | ignorierte Secrets und Sessions vorhanden | ausschließlich Commit mit git archive exportieren und Inventar prüfen |
| Vorhandene Daten als durch GPL freigegeben behandeln | THIRD_PARTY_NOTICES nennt fehlende Brunnenlizenz | ausdrückliches Veröffentlichungshindernis erhalten, keine Daten verändern |
| Neuen Evaluationsstand behaupten | nur Dokumentation geändert | Git-Objekte gegen 5962d6c vergleichen, historische Prüfung unverändert zuordnen |
| Heutiges Datum als Veröffentlichung ausgeben | noch kein Release/DOI vorhanden | Releasedatum erst bei tatsächlichem Release setzen |
| Compose lädt still persönliche Konfiguration | Checkout enthält .env-Dateien | separate ausdrücklich benannte externe Datei, Standard ohne env_file |
| Private GitHub-Quelle automatisch archivieren wollen | aktuelle Sichtbarkeit privat | manuellen Weg dokumentieren; Sichtbarkeit nicht ändern |

## Recommended approach und verworfene Alternativen

Vorhandene GPL, README und CITATION weiterverwenden. Compose bildet den
dokumentierten Docker-Start ab; Zugangsdaten werden nur ausdrücklich über eine
externe Datei eingebunden. Ein lokales Audit dokumentiert Befunde ohne Werte
aus Secrets. Kein Entfernen der Brunnenressourcen: dies würde den in der Thesis
evaluierten Gegenstand und vorhandene Manifeste verändern. Keine zusätzliche
.zenodo.json, da sie die vorhandenen CFF-Metadaten verdrängen würde.

## File impact

| Datei | Änderung | Risiko |
|---|---|---|
| README.md, docs/setup.md | Compose, Clone-Pfad und Zitation | gering |
| compose.yaml, compose.provider.yaml | lokaler Start / explizite externe Konfiguration | Konfiguration gezielt prüfen |
| MANIFEST.in, .dockerignore | Compose in Source Distribution und Build-Kontext aufnehmen | Inventar prüfen |
| CITATION.cff | ggf. vorbereitende Hinweise | kein erfundenes Datum |
| docs/release.md | Standwahl, tatsächliches Release und Hindernisse | kein öffentlicher Vorgang |
| docs/reviews/zenodo-preflight-2026-11-04.md | Prüfbefunde | ohne Secrets |
| dieser Plan | Fortschritt und Entscheidungen | export-ignore |

## Milestones

1. [x] Repositoryreview, Nutzerinnenauswahl und Plan.
2. [x] Bestands-/Historienprüfung und Commitabgleich.
3. [x] Kleine Dokumentations-/Compose-Ergänzungen.
4. [x] CFF, Compose, Archiv und relevante Tests prüfen; abschließendes Diffreview.
5. [x] code-documentation auf finalen Änderungen anwenden; Commitentscheidung dokumentieren.

## Validation plan

| Prüfung | Methode | Erwartung |
|---|---|---|
| Secrets | lokaler redigierter Scanner, aktuelle Dateien und erreichbare Historie | Kandidaten ohne Werte berichten und einordnen |
| Personen-/Lokaldaten | Inventar, E-Mail-/Kontakt-/Dateipfad-Kandidaten manuell einordnen | öffentliche Angebotskontakte von privaten Angaben trennen |
| Prüfstand | Git-Tree-Objekte app, data, tests, requirements und Dockerfile gegen 5962d6c | identisch |
| CFF | cffconvert/schema und Metadatenabgleich | gültig, GPL-3.0-only/0.2.0/Hannah Hoffner |
| Compose | docker compose config --quiet, isolierte Interpolation mit Testdatei | gültig, localhost, read-only, kein Standard-env_file |
| Regression | gezielte Packaging-/Konfigurationsprüfungen, JS-Suite | bestanden bzw. bestehende Einschränkung dokumentiert |
| Archiv | git archive des ausgewählten Commits, Inventar/SHA-256 | keine lokalen Secrets/Logs/Sessions |
| Review | git diff --check, finale Diff-/Linkkontrolle | nur beabsichtigte Änderungen |

## Rollback und recovery

Nur die aufgelisteten neuen Dateien und eigenen Diffabschnitte zurücknehmen;
keine lokalen Konfigurationen oder historischen Daten löschen. Kein Reset,
kein Force-Push, keine History-Neuschreibung. Ein lokaler Vorbereitungscommit
kann durch einen Folgecommit korrigiert werden.

## Progress log

- 2026-11-04: Skills review-first-coding und code-documentation gelesen und
  angewendet. Repositoryreview abgeschlossen, vor Änderungen Plan geschrieben.
- 2026-11-04: Gitleaks 8.30.1 im Baseline-Export und in allen 97 erreichbaren
  Commits ohne Funde. Ein bekannter lokaler Secretwert gegen 1481 eindeutige
  erreichbare Blobs ohne Treffer abgeglichen. Kontakte/Dateiinventar eingeordnet.
- 2026-11-04: Compose ergänzt und mit synthetischer externer Konfiguration
  geprüft. CFF durch cffconvert 2.0.0 gegen Schema 1.2.0 validiert. Keine
  .zenodo.json, keine erfundene DOI oder Datum.
- 2026-11-04: Docker-Testbuild erfolgreich. 24 gezielte Python- und 19
  JavaScripttests im netzlosen Container bestanden. Isolierter Runtime-Compose-
  Start mit Healthcheck, Oberfläche und geladenen Daten bestanden; aufgeräumt.
- 2026-11-04: Inventarprüfung fand fehlende Compose-Dateien im Docker-sdist;
  .dockerignore-Allowlist ergänzt. Neu gebaut und 7 Packagingtests bestanden;
  finales Source-Inventar mit Compose, CFF und Lizenz ohne lokale Daten geprüft.
- 2026-11-04: Nativer Erstlauf 23 bestanden/1 fehlgeschlagen (isolierte
  Wheelinstallation); direkte Wiederholung desselben Skripts und des einzelnen
  pytest-Falls bestanden. Ursache des Erstfehlers nicht belegt, nicht verschwiegen.
- 2026-11-04: code-documentation auf finales Diff angewendet: vorhandene README,
  Setup- und Releaseanleitung statt paralleler Anleitungen ergänzt; Pfade,
  Befehle, Voraussetzungen, Daten-/Provider-/Prototypgrenzen abgeglichen.
- 2026-11-04: Finalen Index auf genau 10 beabsichtigte Dateien geprüft;
  git diff --cached --check bestanden. Export des Index-Trees enthält 218
  Dateien, beide Compose-Dateien und keine lokalen Secrets/Logs/Sessions oder
  internen Plan-/Reviewdokumente. Gitleaks im finalen Export: 0 Funde.

## Decision log / offene Annahmen

- Bestätigt: Das Entwicklungsrepository ist Ziel dieser Aufgabe.
- Bestätigt: Datenrechte der Brunnen sind im Repository ungeklärt.
- Offen: tatsächliches öffentliches Veröffentlichungsdatum; nicht erfunden.
- Der vorbereitete Commit ist noch keine öffentliche Freigabe des Datenpakets.

## Final verification summary

- Akzeptanz: Prüfung und Vorbereitung umgesetzt; Index-Export und Secret-Scan
  bestanden. Die vollständige SHA des lokalen Archivcommits und ZIP-Prüfsumme
  werden unmittelbar nach Erstellung im getrennten Prüfmanifest festgehalten.
- Tests: 24 gezielte Python- und 19 JS-Prüfungen im netzlosen Container;
  anschließend 7 Packagingtests nach Allowlistkorrektur bestanden.
- Build: Testimage und Runtime-Compose erfolgreich, finale Source-Inventarprüfung
  bestanden. Keine Veränderung an Laufzeitcode, Daten oder ursprünglichen Tests.
- Self-review gemäß REVIEW_TEMPLATE: Scope, keine unbeabsichtigten Löschungen,
  bestehende Änderungen, Packagingpfade, Konfiguration, Lizenzabgrenzung und
  Geheimnisse geprüft. Neue Compose-Dateien sind dokumentiert und paketiert.
- Residual risks: ungeklärte Brunnenrechte; tatsächliches Releasedatum und DOI
  fehlen bis zum Release; privates GitHub-Repository; unerklärter nativer
  Erstfehler trotz erfolgreicher Wiederholungen. Kein neuer Vollsuite- oder
  Live-Provider-Nachweis behauptet.
