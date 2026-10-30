# Execution Plan: README, Release-Checkliste und Protokollprüfung

## Status
Complete; 30.10.2026. Dokumentation aktualisiert, erreichbare Protokolle geprüft und Restgrenzen dokumentiert.

## Objective und Acceptance contract
- README und Release-Checkliste beschreiben den aktuellen Prototyp und die durchgeführte manuelle Finalprüfung mit 32 Fällen.
- Reale erfolgreiche STT-/TTS-Funktionstests bleiben als ergänzende Funktionsnachweise sichtbar; keine neue Messung behaupten.
- Weitergaberechte des Trinkbrunnenbestands bleiben ungeklärt; Daten unverändert. Vorgesehen ist eingeschränkter Zugang für Betreuende, keine öffentliche Freigabe.
- Danach lokale Protokolle und zugängliche GitHub-Actions-Protokolle auf Secrets und veröffentlichungskritische Inhalte prüfen und den Umfang nachvollziehbar dokumentieren.
- Keine Änderungen an Anwendung, Daten, Prompts, Tests, Konfiguration oder Thesis. Keine Commits, Tags, Pushes, Einladungen oder Änderung der Repositorysichtbarkeit.

## Repository review
Code-Repository sauber auf 5962d6c, Version 0.2.0. Keine AGENTS-Dateien im Workspace gefunden. README (über 600 Zeilen) und Release-Checkliste mischen aktuelle Betriebsanweisungen mit überholten Entwicklungsständen und offenen Erstprüfungen. Technische Details stehen bereits in docs/setup.md, configuration.md, reproducibility.md und IMPLEMENTATION_REPORT.md und werden wiederverwendet. Der Docker-Start aus einem frischen Git-Export wurde im vorausgehenden Review erfolgreich geprüft; ohne LLM-Zugang erscheint erwartungsgemäß technical_fallback. Eine erneute Testsuite ist für reine Dokumentationsänderungen nicht erforderlich.

Die Finalprüfung liegt im getrennten Thesis-Repository unter Evaluation/manual_final_20261029/: F-01 bis F-32, sechs Kriterien, 48 Screenshots, Fallurteile 21/9/2; F-03/F-25 erfüllen den Schlafhilfeweg bei technischem Rückfall nicht. Weitere Teilbefunde zu medizinischen Verweisen, Kartenfeldern, Priorisierung und Sprache bleiben sichtbar. Die technischen Regressionen und historischen Live-Läufe haben eigene Stände und werden nicht als neue Messungen ausgegeben.

## Dead-end analysis
| Risiko | Mitigation | Verification |
|---|---|---|
| Alte Schritte nur als erledigt markieren würde neue oder unabhängige Prüfungen vortäuschen | Aktuelle Checkliste aus belegten Nachweisen erstellen, Historie im vorhandenen Implementierungsbericht belassen | Abgleich mit Finalmatrix und Prüfberichten |
| Links in ein benachbartes Thesis-Verzeichnis wären im einzelnen Code-Checkout defekt | Getrennten Belegort erklären, keine nicht mitgelieferten lokalen Links setzen | Dokumentationslinkprüfung |
| Secrets beim Lesen von Logs im Chat offenlegen | Rohlogs intern auswerten, nur redigierte Kategorien und Fundstellen ausgeben | Kein vollständiger Log-/Credential-Dump |
| GitHub-Connector findet nur PR-Läufe, obwohl Push-Läufe existieren | Verfügbare Actions-Werkzeuge prüfen; nötigenfalls vollständige lesende CLI/API-Abfrage | Abfrageumfang/Paginierung im Bericht festhalten |
| Fehlende Logs als unauffällig werten | Nicht erreichbare/abgelaufene Protokolle gesondert kennzeichnen | Befundbericht mit Prüfgrenzen |

## File impact
| Pfad | Aktion |
|---|---|
| README.md | Aktueller Stand, kurzer Docker-Einstieg, Finalprüfung und aktuelle Grenzen |
| RELEASE_REVIEW_CHECKLIST.md | Aktuelle belegte Prüfung, echte offene Punkte, ungeklärte Datenrechte |
| docs/reviews/protokollpruefung-2026-10-30.md | Redigierter Bericht zu tatsächlich geprüften Protokollen |
| docs/exec-plans/readme-release-protokolle-2026-10-30.md | Dieser Arbeitsplan |

## Milestones
1. [x] Quellen und bestehende Dokumentationsstruktur lesen.
2. [x] Vorherkopie/Hashinventar sichern; README und Checkliste aktualisieren.
3. [x] Danach lokale und verfügbare GitHub-Protokolle prüfen; Reichweite dokumentieren.
4. [x] Nach code-documentation Links, Kommandos und Befundzuordnung prüfen; Diff und Schutzinventar kontrollieren.

## Validation und Recovery
Vorherkopien und maschinenlesbare Prüfergebnisse außerhalb des Repositorys unter ../code-dokumentation-protokolle-20261030/. Alle vorbestehenden Dateien außer den zwei ausdrücklich bearbeiteten Markdown-Dateien anhand SHA-256 schützen; Thesis und lokale Konfiguration ebenfalls schützen. Narrow checks: Markdownlinks/Anker, Versionsangaben, Quellenabgleich, git diff --check. Bekannte lokale Credentialwerte nur intern vergleichen, niemals ausgeben. Bei Fehlern eigene Änderungen aus Kopien korrigieren; kein Git-Reset.

## Final verification summary
- README und Release-Checkliste beziehen sich jetzt auf die durchgeführte Finalprüfung mit 32 Fällen; offene Erstprüfungen und Entwurfsrollen stehen nicht mehr als aktuelle Aufgaben darin. Historische technische Messungen bleiben im Implementierungsbericht zugeordnet.
- Trinkbrunnenrechte bleiben ungeklärt; alle Daten-/Lizenzdateien unverändert. Privaten Repositorystatus über den GitHub-Connector bestätigt; keine Sichtbarkeit oder Zugriffsrechte geändert.
- 394 lokale Protokoll-/Belegdateien gelesen: 270 unter code/runtime, 122 Textbelege unter thesis/Evaluation, zwei weitere Logs. Keine Lesefehler oder Treffer für den vorhandenen lokalen API-Schlüssel bzw. die geprüften Secret-Muster. 35 Dateien mit Interaktionstexten, neun mit Sitzungskennungen und zwei mit lokalen Maschinenpfaden ausgewiesen; keine pauschale Inhalts-/Anonymitätsfreigabe.
- Vollständige zugängliche Actions-Inventur seitenweise gelesen: 31 Push-/PR-Läufe, 31 Versuche, 34 Jobs, keine aufgelisteten Artefakte. 27 Joblogs gelesen, keine Secret-Treffer; sieben Logs liefern HTTP 410 und bleiben ungeprüft. Keine alten Läufe gelöscht oder neu gestartet.
- Vorhandener Remote-Lauf 40693191060 auf 5962d6c: test und container erfolgreich, Logs abrufbar; beide zeigen 1695 passed, 1 xfailed, 1 warning. README und Checkliste behaupten keinen neuen Lauf für Dokumentationsänderungen.
- Finale Selbstprüfung nach code-documentation: Quellenzuordnung, Dockerbefehle, Sprachfunktionstests, offene Rechte und Protokollgrenzen konsistent; 30 lokale Links einschließlich Markdownanker gültig. Der redigierte Bericht enthält keine Rohfragen, Schlüssel, Sitzungskennungen oder vollständigen privaten Maschinenpfade.
- 500 geschützte Dateien bytegleich, darunter übrige Codequellen, Tests, Prompts, Konfiguration, Daten, die gesamte vorbestehende Thesis und lokale .env-Dateien. Fünf exemplarische lokale Konfigurations-/Runtimepfade weiterhin Git-ignoriert. git diff --check erfolgreich.
- Keine neue Testsuite oder Docker-Vollprüfung für diese reinen Markdownänderungen erforderlich; enger Dokumentations- und Schutzabgleich erfolgreich. Kein Commit, Tag, Push, Provideraufruf oder Workflowstart.

## Discoveries
- Der GitHub-Connector kann nur PR-bezogene Laufteilmengen auflisten. Für die vollständige Push-/PR-Historie und alle Seiten wurde daher die bereits authentifizierte GitHub-CLI ausschließlich mit GET-Abfragen verwendet.
- Die bisherige README-Aussage, der Containerjob sei noch nicht remote ausgeführt, war veraltet: der vorhandene Lauf vom 28.10. belegt beide Jobs auf der finalen App-/Datenbasis.
- Sieben ältere Logs sind nicht mehr verfügbar. Diese Einschränkung wurde separat dokumentiert, statt fehlende Inhalte als unauffällig zu werten.
