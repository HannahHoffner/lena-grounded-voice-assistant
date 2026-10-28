# Exec-Plan: Vierstufenmessung auf 557a487

## Auftrag und Status

27.10.2026, abgeschlossen. Nutzerin: „es ist committed. dann nochmal eine
Live-Messung“. Die vorherige ausdrückliche Freigabe umfasst alle vier Stufen
und diagnostische Fortsetzung trotz negativer Gates. Keine Codeänderung.

Der Plan wurde **vor** Ausführung extern unter
`%LOCALAPPDATA%/LENA/verification/2026-10-27-validator10-live/PLAN.md`
persistiert. Diese Repositoryfassung entstand erst nach allen vier Stufen,
damit deren unveränderter Clean-Worktree-Vertrag erfüllt bleibt.

## Review und Scope

Sauberer Commit `557a487a43d0edc3cac57f4bbc80670673ddc066`, Validator 10,
Prompt 27/Evidence 5/Copy 10. Offizieller `app.multilingual_review live-smoke`,
unveränderter Katalog 3/Assessment 3. Wiederverwendung der externen
Supervisor-/Archivierungsskripte des vorigen Laufs; keine zweite
Evaluationsimplementierung. Alle 167 App-/Testdateien sind bytegleich zum
vollständig geprüften Validator-10-Export (`regression-link.json`).

Risiken: stochastische neue Modelltexte erlauben keine kausale Zuweisung jeder
Zähleränderung zum Patch; bekannte Szenarien sind kein Holdout. Überholte
Marker-/Kachelannahmen dürfen die aktuelle Auswertung nicht bestimmen.
Deshalb unveränderte Rohberichte plus getrennte, reproduzierbare Ableitung;
`marker_set_valid` und das normale out_of_scope-Kartenverbot ausnehmen,
Akutgefahrverbote erhalten. Ungeprüfte Kriterien bleiben ungeprüft.

## Schritte und Belege

- [x] Commit/Dateihashes und Git-Archiv vorab sichern; providerfreier Dry-Run.
- [x] Vier Stufen je einmal mit bisherigen exakten Limits/Timeouts ausführen:
  83 Requests, maximal 249 Provideraufrufe; tatsächlich 126, separat ein
  Modellinventar-GET. Keine nachträgliche Wiederholung.
- [x] Originalreports, Diagnosecodes und Gates erhalten; aktuelle Ableitung
  und Vergleich mit 482f1f9 sichern. Source während aller Stufen unverändert.
- [x] Manuelles 16-Einheiten-Paket neu an Commit und aktuellen Referenzlauf
  binden; Eingaben/Erwartungen/Kriterien/Skalen unverändert, CSVs bytegleich.
  Keine manuellen Antworten oder Urteile erzeugt.
- [x] code-documentation: Bericht 20, Thesisnotizen P, README, Traceability,
  Test-/Live-Dokumentation, Entscheidungen und Checkliste fortschreiben.

| Dateien | Wirkung |
|---|---|
| Bericht, Thesisnotizen, README, Traceability | Neue Messung und Aussagegrenzen, historische Belege weiter standgebunden |
| docs/testing.md, docs/live-provider-evaluation.md | Aktuellen Nachweis verlinken, alte Gates nicht umschreiben |
| Entscheidungen, Review-Checkliste | Finalen Commit und noch offene manuelle Erhebung zuordnen |
| App, Tests, Kataloge, Daten, .env, Thesis | Keine Änderung |

## Ergebnis und Review

Interpreter 0, Selector/Formulator 4, E2E 3, Stabilität 2 technische Fehlerfälle.
Nur Interpreter besteht beide Rohgates. Aktuell anwendbare Inhaltsabweichungen
E2E/Stabilität 0/0, ungeprüfte Metrikvorkommen 53/51. Antworttypfolgen 6/6
stabil, keine vollständige Textgleichheit behauptet. Keine automatisch als
kritisch klassifizierte Safetyabweichung, keine allgemeine Nullfehleraussage.

Extern: `live/measurement-summary.json`, `current-assessment.json`,
`audit.json`, `regression-link.json`, unveränderte Primärreports. Vollständige
1665er-/Dockerprüfung war bereits am bytegleichen App-/Teststand durchgeführt;
wegen reiner neuer Messung nicht nochmals wiederholt. Keine Tests geändert.
Nach Messung ausschließlich Markdown im Repository geändert, keine Secrets,
kein Commit/Tag/Push. Die Thesis bleibt unverändert.

Wiederherstellung bei Ausführungsfehlern: Teilberichte bewahren, Fehler melden,
keine stille Wiederholung oder Anpassung von Provider, Limits oder Gates.
Nicht benötigt: alle vier Stufen regulär abgeschlossen. Offen bleiben die
manuelle 16-Einheiten-Erhebung und Abgleich ihrer tatsächlichen Instanz;
der normale Server 8002 wurde für die CLI-Messung nicht neu gestartet.
