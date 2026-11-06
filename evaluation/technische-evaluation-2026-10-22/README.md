# Technische Primärbelege des finalen MA-Stands

Software: `597e1f0216c72eedd01b7b9e6d49be67ca8150f9`, Version 0.2.0. Datum: 22.10.2026.

Die vier Live-Läufe und die native Pythonregression stammen aus der eingefrorenen Messreihe `20261022-validator3`. Ihre Dateien wurden bytegleich übernommen. `IMPORTNACHWEIS.json` bindet diese Quelldateien an ihre ursprünglichen SHA-256-Werte. `artifact-verification.json` ist der unveränderte Prüfbericht zum Zeitpunkt der Messung; dessen damaliges Feld `thesis_updated=false` beschreibt den Zeitpunkt vor der späteren Thesisübernahme.

| Stufe | Laufkennung | Anfragen / Provideraufrufe | Technische Befunde / Inhaltsabweichungen | Gates |
|---|---|---:|---:|---|
| Interpreter | `run_1977f38ae9474934b478bb4c5a83fa4c` | 15 / 15 | 0 / 0 | bestanden |
| Selector/Formulator | `run_ea2ce8564da94843895ada6e8cf2e04e` | 16 / 24 | 5 / 0 | nicht bestanden |
| E2E | `run_50d9cdb41a564aab909d737f0811546d` | 34 / 59 | 8 / 1 | nicht bestanden |
| Stabilität | `run_fced37b8811c44f382b4e2266146d78f` | 18 / 40 | 4 / 0 | nicht bestanden |

Je Lauf enthält `live-evaluations/<Laufkennung>/` Manifest, unveränderte Einzelresultate und Zusammenfassung. Alle geplanten Fälle wurden ausgeführt. Negative Gates bleiben negativ. Die nachfolgenden Stufen wurden als getrennte Diagnosen ausgeführt; eine bestandene Gesamtkette wird nicht behauptet. Technische Befunde im integrierten Pfad umfassen auch erfolgreiche Retrys. Keine automatisch registrierte Inhaltsabweichung bedeutet keine vollständige Inhaltsprüfung.

`regression.xml` dokumentiert nativ 1220 Fälle in 41 Modulen: 1219 bestanden, ein bekannter strict xfail. `container-regression.xml` dokumentiert dieselben Zahlen für den für die Thesisübernahme zusätzlich geprüften Linux/AMD64-Container. `docker-test.log` enthält dessen vollständigen Testlauf einschließlich 17 Frontendtests, Syntax- und Abhängigkeitsprüfungen; `container-verification.json` bindet die tatsächlich gebauten Images und beide Starts mit frischem temporärem Zustand. Beide Starts verwendeten kein Netzwerk und keinen Modellprovider. Die Healthantworten zeigen den geladenen gebundenen Paket-Bootstrap mit `runtime_kb_status=degraded` und `source_status=pointer_error`, weil kein lokaler Active-Pointer bereitgestellt wird; dies wird nicht als gesunder externer Quellenstand ausgegeben. Prozesshealth, Oberfläche und definierter technischer Query-Fallback wurden erfolgreich geprüft.

`additional-verification.json` und die nativen Prüflogs ergänzen Syntax-/Abhängigkeitsprüfungen und 17 bestandene native Frontendtests. `BEISPIELANTWORTEN.md` trennt ausgelieferte Antworten, verworfene Versuche, erfolgreiche Retrys und abschließende Vorlagen. `VERTRAGSPRUEFUNG.md` erläutert die Vertragsänderungen; `USER_CONFIRMATIONS.json` hält die gesonderte fachliche Bestätigung zum warmen Essen der Oase fest. Diese Bestätigung ändert weder Laufdaten noch Gates und ist keine manuelle Bewertung.

Die automatische Live-Katalogversion ist 3, mit SHA-256 `0b99cff95d403bd3fdd242ffb73c96e0f21f804ca40ecda4afdcbd46c6c43dbf`. Formulatorvertrag/Prompt: 5/22; Groundingvalidator: 3; Evidence: 4. Der Runtime-KB-Fingerprint lautet `9471e7051acb8d4e0fc62d59c1d74bb54f72cec1c28b6cffe291ac15499ec0d9`. Modellalias, Providerangabe und alle weiteren Versionen stehen in den Manifesten.

Der `SHA256.json`-Index bindet die Dateien dieses Belegverzeichnisses außer
sich selbst. Die aktuelle manuelle Ergebnisgrundlage dokumentiert ausschließlich
die [Finalprüfung vom 29.10.2026](../manual_final_20261029/README.md);
die zeitliche Zuordnung steht im [Evaluationsstand](../EVALUATIONSSTAND.md).
Die Messdaten dieses technischen Archivs beziehen sich auf den damaligen Stand.
