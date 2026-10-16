# Execution Plan: Vollständige Ausweisung der End-to-End-Prüfgrenzen

## Status

- State: Complete
- Owner: Codex
- Created: 2026-10-15
- Last updated: 2026-10-15

## Objective

Jede deklarierte End-to-End-Erwartung wird geprüft oder ausdrücklich als nicht
automatisch prüfbar ausgewiesen. Der Bericht trennt Gate-Ergebnis und
Prüfvollständigkeit. Anschließend beschreibt die Masterarbeit das implementierte
Kurationsdatenmodell als Endzustand, ohne Entwicklungschronik.

## Acceptance contract

- [x] `requested_language` mit `QueryResponse.language` vergleichen, ohne damit die
  tatsächliche Natürlichkeit oder Sprache jedes Antwortsatzes zu behaupten.
- [x] Numerisch verbotene Angebots-IDs auf allen strukturierten Ausgabeflächen prüfen.
- [x] `need`, nicht operationalisierte Verbote und unbekannte required/allowed-
  Erwartungen explizit als `None`/`unverified_metrics` ausweisen.
- [x] Eine bekannte Verletzung bleibt `False`, auch wenn andere Verbote ungeprüft sind.
- [x] Prüfgrenzen in E2E- und Stabilitätszusammenfassungen ausweisen und die
  Auswertungsversion im Manifest binden.
- [x] Modell, Prompt, Daten, Anwendungspfad, Budgets, Abbruch- und Gatekriterien
  unverändert lassen. Keine Live-Aufrufe, Installation, Commits oder Veröffentlichung.
- [x] Positive und negative Regressionen sowie den realen Runner mit Testdoubles prüfen.
- [x] Freigegebene Tabellen und Datenmodellabbildung in Approach/Solution ergänzen;
  feste P-/Z-/A-Aussagen und rote Platzhalter unverändert lassen.

## Scope

In scope: geschlossene Auswertungslogik, lokaler Bericht, Regressionstests,
bestehende Evaluationsdokumentation und das freigegebene Thesis-Datenmodellpaket.
Out of scope: neue Laufzeitmetadaten, neue fachliche Inferenz aus Antworttext,
Gate-Lockerung, historische Ergebnisdateien, finale Messungen und globaler Textumbau.

## Repository review

### Current behavior and architecture

Ausgangspunkt: Code `329994f`, Branch `maintenance/repository-cleanup`, Thesis
`fd7a29f`, Branch `master`; beide Arbeitsstände sauber. Keine anwendbaren AGENTS-
Dateien gefunden. FastAPI/Pydantic, Python >=3.11, setuptools und pytest sind
vorhanden; keine Abhängigkeitsänderung erforderlich.

`_run_e2e_scenario` ruft den echten `QueryService.query` auf und übergibt die letzte
`QueryResponse` an `_evaluate_e2e`. E2E und Stabilität verwenden diesen Pfad.
`need`, `requested_language` und `forbidden_results_absent` fehlen in den Checks.
Unbekannte Schlüssel verschwinden ebenfalls. Nur numerische Verbote werden gegen
`card_ids`/`interaction.source_ids` geprüft. Die Antwort enthält Sprache, aber keinen
abschließend aufgelösten Bedarf. Ein Schluss aus Angebots-IDs oder dem letzten
Interpreteraufruf wäre besonders bei Dialogfortsetzungen nicht verlässlich.

### Existing structures to reuse

| Structure | Path | Reuse decision |
| --- | --- | --- |
| E2E-Auswertung und Safety-Semantik | `app/live_evaluation_runner.py::_evaluate_e2e` | Kohäsiv extrahieren; Runner importiert dieselbe Funktion |
| Rückgabevertrag bool/None, mismatches, unverified | derselbe Pfad | Beibehalten und vervollständigen |
| Manifest und Stufenzusammenfassungen | `app/live_evaluation_plan.py`, `app/live_evaluation_runner.py` | Additive Prüfversions-/Abdeckungsfelder |
| Isolierte Dienste und Testprovider | `tests/test_live_evaluation.py`, `tests/conftest.py` | Bestehende Integrationsregressionen verwenden |
| Kurationsschema und Projektion | `app/curation.py`, `app/models.py` | Quelle für Thesis-Diagramm, Typen und Namensauflösung |

### Tests and working tree

`tests/conftest.py` sperrt externe HTTP-/Socket-Verbindungen und lenkt Runtime-
Schreibzugriffe in temporäre Verzeichnisse. Bytecode, Pytest-Cache und zusätzliche
Plugins werden beim Testaufruf deaktiviert. Tests benötigen temporäre Dateien;
diese werden ausschließlich im temporären Testbereich erzeugt, nicht als
Ergebnisartefakte im Repository. Historische Live-Läufe bleiben unangetastet.

## Dead-end analysis

| Potential dead end | Evidence / impact | Mitigation / verification |
| --- | --- | --- |
| Bedarf aus Karten oder Provider ableiten | Kein finaler Bedarf in Response; Dialog kann Bedarf auflösen | Explizites `None`; Regression für diesen Fall |
| Symbolische Verbote als ID oder Textsubstring auswerten | Tokens wie `invented_offer` sind keine operationalisierten Prüfer | Ungeprüfte Tokens einzeln ausweisen; keine semantische Scheingenauigkeit |
| Unbekannte Bedingungen still ignorieren | Dictionaries erlauben zusätzliche Erwartungsschlüssel | Required/allowed vollständig nachführen; Negativtest mit künftigem Schlüssel |
| Grünes Gate als vollständige Inhaltsbewertung lesen | Bestehendes Gate prüft nur beobachtete Abweichungen | Separate Abdeckungsfelder und Dokumentation; Gateformel unverändert |
| Überlangen Runner weiter aufblähen | Runner >1000 Zeilen | Kohäsive Checkfunktion in `live_evaluation_checks.py`; kein paralleler Pfad |
| Altbefunde nachträglich aktualisieren | Gemessen mit anderem Code/Auswerter | Keine historischen Reports oder Testergebnisse umschreiben |

## Recommended approach and rejected alternatives

Auswertung als kleine, unabhängig testbare Einheit extrahieren und über den
vorhandenen Runner aufrufen. Die bestehende Safety-Interpretation bleibt identisch.
Neue Runtime-API-Felder, ein LLM als Bewerter, Textheuristiken für Bedeutungsprüfung
und eine Änderung der Gatekriterien sind für diese begrenzte Korrektur nicht nötig.

## File impact

| File | Action / reason | Risk |
| --- | --- | --- |
| `app/live_evaluation_checks.py` | Kanonische Auswertung mit expliziten Prüfgrenzen | Mittel: Safety-Verhalten erhalten |
| `app/live_evaluation_runner.py` | Import; Abdeckungszähler in E2E/Stabilität | Klein, keine Providerlogik |
| `app/live_evaluation_plan.py` | Prüfversion im Manifest | Klein, additives Feld |
| `tests/test_live_evaluation_checks.py` | Direkte Regressionen | Klein |
| `tests/test_live_evaluation.py` | Berichtsintegration prüfen | Klein |
| `docs/live-provider-evaluation.md` | Finale Auswertungssemantik dokumentieren | Klein |
| `../thesis/Chapters/4Approachneu.tex` | Qualitätsbegriffe und Bezeichnungsarten | Klein, freigegebener Abschnitt |
| `../thesis/Chapters/5Solutionneu.tex` | Schema, Kardinalitäten, Feldtypen und Projektion | Mittel, LaTeX-Layout |

## Milestones

1. [x] Anweisungen, Aufrufpfad, Verträge, Tests und Risiken prüfen.
2. [x] Auswertung und Regressionen implementieren; rote Regression vor Korrektur nachweisen.
3. [x] Gezielte und breitere providerfreie Tests, Syntax und Diff prüfen.
4. [x] `code-documentation` auf finalen Diff anwenden; Evaluationsdokumentation ergänzen.
5. [x] Thesis-Datenmodellpaket ergänzen und LaTeX isoliert prüfen.
6. [x] Enddiff und Git-Status gegen Scope prüfen; Restgrenzen berichten.

## Validation plan

| Check | Method | Expected result |
| --- | --- | --- |
| Regression vor Fix | `python -B -m pytest -p no:cacheprovider tests/test_live_evaluation_checks.py` | Neue Fälle belegen bislang fehlende Checks |
| Runner und Auswertung | Gleiches Kommando mit beiden Evaluations-Testdateien | Alle nicht als bekannte Grenze markierten Fälle bestanden |
| Breitere Regression | `python -B -m pytest -p no:cacheprovider` | Keine neuen Fehler; bekannten strict xfail separat berichten |
| Nebenwirkungen | Deaktivierte Env-Datei/Live-Flag, Netzwerk-Sperrfixture, temporäre Tests | Keine produktiven Aufrufe/Runtimeänderungen |
| Syntax / Diff | AST-Parse ohne Imports; `git diff --check` | Erfolgreich |
| Thesis | LaTeX-Build mit Ausgabe außerhalb Thesis und deaktivierter Paketinstallation | Neue Tabellen/Abbildung ohne Fehler; Layout visuell prüfen |

## Rollback and recovery

Keine Migration, Löschung, Umbenennung oder Abhängigkeitsänderung. Änderungen
liegen uncommitted als begrenzter Diff vor und können einzeln geprüft werden.
Kein automatischer Rollback oder Zurücksetzen fremder Änderungen.

## Progress log

- 2026-10-15 — Plan nach Review und vor Quellcodeänderung angelegt.
- 2026-10-15 — 13 neue Regressionen am ursprünglichen Auswerter fehlgeschlagen;
  nach Implementierung und zwei zusätzlichen Grenzfällen bestehen alle 84
  Evaluationsprüfungen (20,15 s). Laufzeit-/Providerkonfiguration unverändert.
- 2026-10-15 — Breite Suite ohne Packaging: 1012 passed, 1 strict xfailed,
  1 vorhandene StarletteDeprecationWarning, 250,77 s. Syntax: 93 Pythondateien
  erfolgreich per AST geprüft. Frontend: 17 Node-Tests bestanden.
- 2026-10-15 — `code-documentation` auf finalen Diff angewendet: bestehende
  Evaluationsdokumentation ergänzt; Namen und Felder gegen Modelle und
  Manifest geprüft. Keine spekulativen Funktionen dokumentiert.
- 2026-10-15 — Notwendige Folgeanpassung im freigegebenen Solution-Text:
  pauschale Bindung aller Implementierungsbeschreibungen an `429ab1b` durch
  Softwareversion und neuen roten Platzhalter für die finale Commitbindung
  ersetzt. Sonst würde die Beschreibung des korrigierten Runners fälschlich
  diesen alten Commit belegen. Bestehende Ergebnisdateien, Messbefunde und
  bereits vorhandene rote Platzhalter bleiben unverändert.
- 2026-10-15 — Isolierter LaTeX-Build erfolgreich; die fünf Seiten der neuen
  Tabellen/Abbildung und die Seite mit der Artefaktbindung visuell geprüft.
  Neue Querverweise aufgelöst, keine Undefined-Reference-Warnungen und kein
  erneuter Label-Lauf angefordert. Bestehende Thesis-PDF nicht überschrieben.
- 2026-10-15 — Nach Dokumentationsprüfung erneut 84 Evaluationsprüfungen
  bestanden (20,67 s); Enddiff und `git diff --check` in beiden Repositories
  geprüft. Vorhandene rote Blöcke automatisiert mit HEAD verglichen: alle
  unverändert. Feste P-/Z-/A-Dateien und historische Messergebnisse unberührt.

## Decision log

- `need` bleibt ohne hinreichende Metadaten ausdrücklich ungeprüft. Keine Erfindung
  eines aus Karten abgeleiteten Bedarfs.
- Ungeprüft und verletzt sind getrennte Zustände. Bestehende Gates werden nicht
  umdefiniert; zusätzliche Vollständigkeitsfelder verhindern Überinterpretation.
- Thesis beschreibt finale Strukturen, keine Änderungen gegenüber Vorversionen.

## Discoveries

- Vorhandene Assertion `14 < 27 / 2` war unabhängig von dieser Korrektur falsch.
  Sie prüft nun exakt `27 // 2 + 1`, also den unveränderten Stopp beim ersten
  Fehlerstand oberhalb der Hälfte. Keine Änderung des Limits oder der Gates.
- Die Packagingtests bauen und installieren Pakete. Sie werden wegen der Vorgabe
  gegen Installationen/unnötige Artefakte beim breiteren Lauf ausgeschlossen;
  keine vollständige Packagingprüfung behaupten.
- LaTeX benötigt im isolierten Buildverzeichnis einen vorrangigen lokalen
  Suchpfad (`TEXINPUTS=.;<thesis>//;`), damit bestehende Aux-Dateien im
  Quellrepository nicht die neuen Querverweise verdecken. Das konfigurierte
  Bibliographiebackend ist BibTeX8; ein zunächst gestarteter, unpassender
  Biberprozess wurde beendet. BibTeX8 erzeugte die Bibliographie mit vier
  Größenwarnungen für den bestehenden Gemini-Eintrag. Die umfassende
  bibliographische und globale Layoutbereinigung ist nicht Teil dieses Pakets.

## Final verification summary

- Acceptance requirements: erfüllt; fehlende Evidenz wird sichtbar statt geraten.
- Tests: 84 gezielte Tests; 1012 bestanden und 1 bekannter strict xfail im
  breiten Lauf ohne Packaging; 17 Frontendtests; 93 Pythondateien syntaxgültig.
- Build: isolierter Gesamtlauf erfolgreich, neue Tabellen und Abbildung ohne
  Überlagerungen visuell geprüft; keine ungelösten Querverweise. Die gesamte
  Arbeit ist damit nicht als warnungsfrei oder abgabefertig bewertet.
- Documentation: bestehende Evaluationsdokumentation und freigegebene
  Approach-/Solution-Abschnitte gegen das implementierte Schema abgeglichen.
  Neue Texte beschreiben den Endzustand, nicht Unterschiede zu Vorversionen.
- Self-review: richtige kanonische Repositories, keine Anwendungs-/Datenänderung,
  kein doppelter Auswerter, Import und Aufrufpfad durch reale Runner-Tests
  nachgewiesen; additive Reportfelder, Gates und Safety-Semantik erhalten.
- Residual risks: kein finaler Commit eingefroren; keine neuen Live-Messungen;
  `need` und semantisch nicht operationalisierte Verbote bleiben ausdrücklich
  ungeprüft. Historische Befunde gelten ausschließlich für ihre gespeicherten
  Artefaktstände. Keine Packaging-, Installations- oder Produktivprüfung erfolgt.
