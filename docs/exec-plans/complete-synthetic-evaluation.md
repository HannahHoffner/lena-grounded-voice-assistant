# Execution Plan: Vollständige synthetische Evaluationsläufe

## Status
In progress; 2026-10-22. Nutzerauftrag: alle Szenarien ausführen, kein Abbruch nach wenigen bewerteten Fehlern; anschließend Messung und Thesis auf neuestem Commit.

## Review and acceptance contract
Die bestehende CLI und alle Runner verlangen exakt die versionierten Kataloglimits. Gewöhnliche Fehler stoppen per AtomicRunCounter.record_failure; E2E/Stabilität haben zusätzlich separate Schwellen für kritische synthetische Befunde. E2E erlaubt nur einen Formulatorcall pro Anfrage im Maximalbudget, obwohl der Anwendungspfad einen Retry haben kann. Deshalb reicht ein CLI-Override nicht.

- [ ] Alle geplanten Szenarien/Wiederholungen auch bei gewöhnlichen und kritischen synthetischen Befunden ausführen.
- [ ] Jeder Fehler bleibt gezählt; fehlgeschlagene Gates bleiben negativ.
- [ ] Endliche Request-, Provider-, Laufzeit- und Identitätsgrenzen sowie Reportfehlerbehandlung bleiben wirksam.
- [ ] Formulatorbudgets berücksichtigen zwei Versuche je Anfrage.
- [ ] Kein Eingriff in produktive Antwort-, Safety-, Modell-, Prompt- oder Groundinglogik.
- [ ] Katalogversion, Tests, Dokumentation, neue Messung und Thesis konsistent.

## Reuse / architecture / tests
app/live_evaluation.py, app/resources/bootstrap/evaluation/live_scenarios.json, app/live_evaluation_runner.py, tests/test_live_evaluation.py und docs/live-provider-evaluation.md. Bestehende Runner, Counter, Provider-Doubles und Reportstore wiederverwenden. Das umfangreiche Runner-/Testmodul bleibt gezielt geändert; eine Extraktion wäre sachfremder Umbau und erschwerte den Vergleich.

## Dead ends and decisions
| Sackgasse | Folge | Lösung / Nachweis |
|---|---|---|
| Nur max_failures in Shell erhöhen | CLI/Runner verweigern unverbindliche Limits | Katalogversion 3, neuer sauberer Commit |
| Nur gewöhnliche Fehlergrenze erhöhen | kritische Schwelle stoppt dennoch früh | synthetische kritische Befunde vollständig erfassen; negative Gates erhalten |
| Formulatorbudget unverändert | Retrys verbrauchen Budget vor letztem Szenario | E2E 68, Stabilität 36 Formulatorcalls; Gesamtsummen 136/72 |
| Gate lockern | falscher Erfolgsnachweis | Gatebedingungen unverändert, Regression mit Fehlern/critical prüft negative Gates |
| Alte Ergebnisse auf neuen Commit umetikettieren | falsche Artefaktbindung | neue Messreihe in eigenem externem Verzeichnis |

## Scope / file impact
Nur Evaluationsrunner, Katalog, gezielte Tests, Dokumentation und dieser Plan. Keine produktive Anwendungsänderung. Szenariowortlaute/Erwartungen unverändert. Anschließende Thesisänderungen im separaten Thesisrepo.

## Implementation and validation
1. Fehlerschwellen im Katalog höher als maximal mögliche Fehlerzahl setzen, Katalogversion erhöhen; harte Ressourcenlimits endlich halten.
2. Separate kritische Stopps aus dem synthetischen Runner entfernen, kritische Befunde weiterhin zählen und ausweisen.
3. Bestehende Fehler-/Diagnosetests auf vollständigen Umfang aktualisieren; vollständige Traversierung bei gewöhnlichen und kritischen Fehlern sowie Retrybudgets testen.
4. Fokussierte Tests und Diffcheck; Softwareänderung versionieren, damit die erneute Messung auf sauberem Commit läuft.
5. Vollständige native/Containerprüfung und alle vier Live-Stufen einmal auf neuem Commit; Ergebnisse, manuelle Baseline und Thesis aktualisieren.

## Recovery
Keine bisherigen Reports überschreiben. Änderungen per gezieltem Git-Revert rücknehmbar. Bei Ressourcen-, Identitäts- oder Schreibfehlern kontrollierten Abbruch als solchen dokumentieren; keine stillen Wiederholungen.

## Progress
2026-10-22: Review abgeschlossen, Umsetzung noch offen. Ausgangscommit f795cb7 sauber; vorherige Messung extern 20261022-f795cb7. Code-documentation-Skill gelesen. Neue Messidentität erst nach Commit bestimmen.

Implementation verified: targeted evaluation suite (109 cases) passed. Scenarios, expectations and metrics unchanged. Catalog 3 covers failure counts and formulation retries. Full native/container regression and live remeasurement follow on the clean committed revision; results are recorded in the separate thesis plan and external report directory. code-documentation used to update current execution semantics and CLI limits.

Full-regression discovery: five dependent test expectations still described the old three-error stop or used CLI limit 3. Updated tests/test_interpreter_diagnostics.py, test_provider_isolation.py and test_translation_quality.py to the versioned complete-sample profile. The 69 dependent tests passed; production and evaluation implementations did not change in this correction. Intermediate bd69c76 provider run was explicitly interrupted and archived, not silently counted as final evidence. Final clean-commit full regressions precede provider measurement.
