# Exec-Plan: Fachentscheidungen nach Validator-Ablation

## Auftrag, Stand und Grenzen
27.10.2026; Basis `02a3612`. Umsetzung der sechs Fachentscheidungen der
Nutzerin. Kein Commit/Tag/Push, keine Änderungen unter `../thesis`, an
Rohdaten/Releases/Manifesten/Snapshots oder Safety-Preflight/Akutgefahr.
Unversionierte vorhandene Exec-Pläne bleiben erhalten. Keine vierstufige
Live-Evaluation. Neuer Messstand ist mangels Commitfreigabe ein per Hash
identifizierter Arbeitsbaum auf 02a3612, kein erfundener neuer Commit.

## Review und Architektur
Gelesen: Ablation/grounded-model-prose, controlled-answer-acts, Berichts- und
Traceabilityvertrag R-01–42/FR-01–13 sowie betroffene Anwendungsmodule und
Kurations-/Textressourcen. Pipeline: Interpreter → deterministische Kandidaten
→ Selector → Evidence → Formulator/atomarer Validator → Service/Karten/Session.
Vorhandene Literal-, Relations-, Zielgruppen-, Garantie- und Safetytests sind
der Regression-Contract. Wiederverwenden: BindingPolicy/policy_facts,
application_texts, service_schedules, _card, offer_stand_destinations,
Session-speakable_texts. Fremdsprachiges Review bleibt ehrlich pending.

## Risiken, Dead Ends und Entscheidungen
| Risiko / Beleg | Folge | Behandlung / Prüfung |
|---|---|---|
| Wortabdeckung verwirft richtige Prosa (86/98) | unnötiger Templatepfad | Gate aus Laufzeit entfernen; frühere Negativtests als Charakterisierung erhalten |
| wound_care nur bei A1 | falsches no_result | Capability-Unterart erweitern; Drogen-/Altersschranken unverändert testen |
| Hilfebus-Büro in Evidence; _card blendet Adresse bereits aus | datengetreuer Fehler bleibt validierbar | kuratierter Override plus gezielte Evidence-/Anzeigeprojektion; Teams 12/13 behalten Büro |
| Hilfebus überall als Kandidat | würde Fach-/Selectorregeln ändern | ergänzende Kachel erst bei Ausgabe; Sonntagessen dagegen verbindlich auswählen |
| Anhängen nach 600 Zeichen / nach Sessionpersistenz | Länge/TTS inkonsistent | Modellbudget für betroffene Fälle reservieren, deterministischer Zusatz vor Persistenz |
| Namenänderungen invalidieren Übersetzungen/Sessions | erwarteter Fingerprintwechsel | Integrität bewahren, Fallback statt fingiertem Review, Aliasse testen |
| neuer Commit ausdrücklich verboten | Messung kann keinen neuen Commit nennen | unveränderten Runner mit Arbeitsbaumhash/Manifest ausführen, Differenz offen ausweisen |

Teamnamen sind in `bootstrap/wfs/current.geojson` eindeutig Team Konsum und
Team Wohnen; keine Rückfrage nötig. Keine zweite Wahrheit für Telefon/Zeiten:
aus kuratiertem Hilfebus und daily_18_23 ableiten. Keine neue Konfiguration.
Abgelehnt: Validator komplett abschalten, Datenquellen umschreiben, LLM-Judge,
Hilfebus im Akutgefahrpfad, willkürliche Übersetzungsfreigabe.

## Dateiauswirkung
| Dateien | Zweck / Risiko |
|---|---|
| grounding.py, grounding_content.py | nur zwei lexikalische Ablehnungen entfernen, Version; sonst Regression |
| candidates.py | wound_care-Unterart; Sonntag-Hilfebus verbindlich erhalten |
| formulation.py, formulator_prose.py | Evidence/Promptversion, medizinische Policy, Darstellungsfilter |
| service.py, ergänzendes kohäsives Hilfebusmodul | deterministische Ausgabe vor Persistenz, Orts-/Kontaktrollen |
| application_texts.py, bootstrap/i18n/application_texts.json | lokalisierte Copy, Version/Reviewstatus |
| bootstrap/curation/social_offers.json | Namen, Aliasse, Hilfebusprojektion, protokollierte Entscheidungen |
| tests/ betroffene Module und neue Regressionen | Charakterisierung plus erhaltener Contract |
| IMPLEMENTATION_REPORT, THESIS_UPDATE_NOTES, TRACEABILITY, README, docs | tatsächliche Versionen, Prüfungen, Grenzen |

## Meilensteine und Validierung
- [x] Review, bestehende Änderungen prüfen, Plan anlegen.
- [x] 1: Validator abladieren; gezielte Groundingtests, betroffene Tests einzeln protokollieren.
- [x] 2: Wundkandidaten; fünf Sprachen, FR-04 und bestehende Kandidatentests.
- [x] 3: Kuration/Namen und Hilfebusprojektion; Aliasse, Fingerprint, Übersetzungsintegrität.
- [x] 4: Prompt/Policy/Copy und deterministische Ausgabe; alle fünf Sprachen, 600 Zeichen, TTS, Sonntagessen, Akutgefahr.
- [x] 5: `python -m pytest`, `node --test tests/frontend.test.cjs`; bestehende Architekturchecks.
- [ ] 6: sauberer Export; `docker build --pull --no-cache --target test`, netzloser Testlauf, Runtime/Health/ohne Schlüssel/Persistenz.
- [x] 7: unveränderte externe run.py/queries.json in neuem Verzeichnis; 120 Anfragen, technische Auswertung, blindes Paket ohne eigene Richtigkeitsbewertung.
- [x] 8: Dokumentation mit code-documentation, Selbstreview/Diff/Quellschutz prüfen.

Gezielte Prüfungen nach jedem Schritt; Rohlogs außerhalb Cloudsync unter
`%LOCALAPPDATA%/LENA/verification/2026-10-27-validator-implementation/`.
Rollback: nur eigene Diff-Hunks reversieren; Quelldaten und frühere Belege
bleiben unverändert. Kein Schema-/Datenmigrationsschritt.

## Fortschritt / Entdeckungen
- 27.10.: HEAD bestätigt, drei unversionierte Nutzerpläne erhalten; Plan angelegt.
- Validator 8, Prompt 26/Evidence 5, Copy 10 und Kuration umgesetzt; getrennte gezielte Zwischenprüfungen, anschließend vollständig 1585 bestanden + historischer XFAIL, 19 JS. Einzelne abladierte Testfälle in Bericht 14.2 gelistet.
- Übersetzungsfelder/Reviewstatus bleiben byteinhaltlich unverändert; nur validierte Identitätsmetadaten neu gebunden. SZL/Suchtzentrum als Organisationsalias erhält Mehrdeutigkeit; neue Anzeigenamen ebenfalls explizite Aliasse.
- Ablation 120/120, App-Hash unverändert im Lauf; 21/120 statt 83/120 Templates. Alle fünf Wundfälle grounded_result; 120 Hilfebuskacheln, kein Hilfebus-Büro in Evidence/Anzeige. Blindpaket 134 Texte mit 82 maschinellen Hilfsübersetzungen und separaten 120 Anzeigeprüfungen, keine eigenen Ratings.
- Native HTTP-Runtime ohne Schlüssel und Sessionpersistenz nach Prozessneustart bestanden.
- Docker blockiert vor dem Anwendungsbuild beim Builderstart; auch Pull/Load/Containerliste hängen. Desktopstatus widersprüchlich; Neustartfreigabe angefragt. Noch kein erfolgreicher Docker-Neubau, netzloser Testlauf oder neues Runtimeimage behauptet.
- Nutzerin hat den Docker-Desktop-Neustart ausdrücklich freigegeben. Fortsetzung nur der offenen Containerprüfungen; abgeschlossene Ablation und native Suite bleiben unverändert.
- Docker-Engine nach freigegebenem gezieltem Neustart wieder betriebsbereit. Drei saubere Buildversuche scheitern danach vor Anwendungscode an HTTP 502/503 des festgelegten Ubuntu-Snapshotservers, auch direkt vom Host reproduziert. Keine Änderung an Dockerfile/Locks. Separater Build mit vorhandenen Basis-Layern erfolgreich; 161 App-/Testdateien im Container stimmen per SHA-256 mit dem nativ geprüften Export und aktuellen Arbeitsstand überein.
- Meilenstein 6 teilweise abgeschlossen: netzloser vollständiger Testlauf im separaten Build mit Basis-Cache 1585 bestanden + historischer XFAIL, 19 JS, compileall/pip check/Syntaxchecks bestanden. Runtime aus derselben Buildkette healthy, ohne Schlüssel, read-only/Loopback und Persistenz nach Neustart und Containerersatz bestanden (`docker-completion-cached.json`, `runtime-smoke-cached.json`). Prüfcontainer/-volume entfernt. No-Cache-Neubau bleibt wegen externer Paketquelle offen, daher Meilenstein bewusst nicht abgehakt.

## Abschließendes Review / Evidenz
Code-/Test-/Dokumentationsreview und Secret-/Quelldatenschutz bestanden
(`final-audit.json`, `git diff --check`). App-Hash entspricht dem Live-Lauf.
Offene technische Prüfung: sauberer No-Cache-Neubau nach Erholung des externen Ubuntu-Snapshotservers.
Offene Fachentscheidung: Hilfebus bei acute_risk wird nicht ergänzt. Fachliche
Bewertung des neuen Blindpakets erfolgt durch die Nutzerin.
