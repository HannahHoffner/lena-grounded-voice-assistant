# Prüfung lokaler und GitHub-Protokolle – 30.10.2026

## Ergebnis

In den tatsächlich gelesenen Dateien wurde weder der vorhandene lokale
API-Schlüssel noch ein Treffer der geprüften Secret-Muster gefunden.
Die sieben nicht mehr verfügbaren GitHub-Jobprotokolle bleiben ungeprüft.
Das Ergebnis ist eine begrenzte Protokollsichtung, keine allgemeine Zusicherung
von Secret-, Personen- oder Fehlerfreiheit.

Das Code-Repository ist privat. Die Sichtung änderte weder Sichtbarkeit noch
Berechtigungen und löste keine Workflows aus. App-/Datenbasis ist 5962d6c,
Version 0.2.0; eine öffentliche Datenfreigabe folgt daraus nicht. Die
Weitergaberechte des Trinkbrunnenbestands bleiben ungeklärt.

## Lokaler Umfang

| Bereich | Gelesene Dateien |
|---|---:|
| `code/runtime/` | 270 |
| Textbelege im getrennten Thesis-Repository unter `Evaluation/` | 122 |
| Lokales Fixture-Protokoll und aktuelles Docker-Buildprotokoll | 2 |
| Gesamt | 394 |

Geprüft wurden vorhandene LOG-, TXT-, JSON-, JSONL-, CSV-, XML- und TMP-Dateien;
die JSON-/JSONL-Dateien wurden zusätzlich nach Interaktionstexten und
Sitzungskennungen inventarisiert. Bild- und Audiodateien wurden in dieser
Textprüfung nicht auf ihren dargestellten oder gesprochenen Inhalt bewertet.
Es gab keine Lesefehler.

35 Dateien enthalten strukturierte Interaktionstexte, neun Dateien enthalten
Sitzungskennungen. Dazu gehören die Git-ignorierten lokalen Dateien
`runtime/sessions.json` und `runtime/logs/interactions.jsonl`; weitere Kennungen
stehen in früheren technischen Forschungsbelegen des getrennten Thesis-Repositorys.
Diese Bestände werden nicht pauschal als anonym eingestuft. Zwei Dateien enthalten
lokale Maschinenpfade: das ignorierte `fixture-S-12.log` und das historische
`technische-evaluation-2026-10-28/reviewed/native.log` im Thesis-Repository.
Quellen, ursprüngliche Protokolle und Nachweise wurden nicht geändert.

Die Sichtung vergleicht intern den einen vorhandenen lokalen Credentialwert
und prüft Muster für private Schlüssel, GitHub-/Provider-/AWS-Zugänge und
verdächtige Zuweisungen von Zugangsdaten. Werte, Rohfragen, Sitzungskennungen
und vollständige Maschinenpfade werden in diesem Bericht nicht wiedergegeben.
Unbekannte Secret-Formate und allein aus dem Kontext erkennbare persönliche
Informationen sind damit nicht vollständig ausgeschlossen.

## GitHub Actions

Repository: `HannahHoffner/lena-grounded-voice-assistant`. Die vollständige
zugängliche Lauf-, Job- und Artefaktliste wurde seitenweise und ausschließlich
lesend über die vorhandene authentifizierte GitHub-CLI abgefragt. Der Connector
kann die vollständige Push-/PR-Laufhistorie nicht auflisten. Jeder der 31 Läufe
hat einen Versuch; insgesamt wurden 34 Jobs erfasst.

| Prüfgegenstand | Ergebnis |
|---|---|
| Ereignisse | Push und Pull Request |
| Laufstatus | 10 erfolgreich, 21 fehlgeschlagen |
| Jobstatus | 13 erfolgreich, 21 fehlgeschlagen |
| Abrufbare, gelesene Jobprotokolle | 27 |
| Nicht verfügbare Jobprotokolle | 7, jeweils HTTP 410 |
| Aufgelistete Workflow-Artefakte | 0 |
| Treffer für die geprüften Secrets/Muster | 0 in den gelesenen Protokollen |

Die fehlgeschlagenen historischen Läufe enthalten Testfehler; sie werden weder
gelöscht noch durch den späteren Erfolg nachträglich als bestanden gewertet.
Keine neuen CI-, Modell- oder Sprachläufe wurden ausgelöst.

### Aktueller vorhandener Remote-Nachweis

Der [Lauf 40693191060 vom 28.10.2026](https://github.com/HannahHoffner/lena-grounded-voice-assistant/actions/runs/40693191060)
gehört zu 5962d6c. Die beiden Jobs
[`test`](https://github.com/HannahHoffner/lena-grounded-voice-assistant/actions/runs/40693191060/job/122833011057)
und [`container`](https://github.com/HannahHoffner/lena-grounded-voice-assistant/actions/runs/40693191060/job/122833011167)
sind erfolgreich; beide Protokolle waren abrufbar und dokumentieren jeweils
1695 bestandene Pythonfälle, einen XFAIL und eine Warnung. Dies ist ein
vorhandener Remote-Nachweis für die App-/Datenbasis, kein neuer CI-Lauf für die
anschließenden Dokumentationsänderungen.

### Nicht verfügbare Protokolle

Die folgenden Protokolle konnten nicht inhaltlich geprüft werden:

| Lauf | Job | Abruf |
|---|---|---|
| [30633712461](https://github.com/HannahHoffner/lena-grounded-voice-assistant/actions/runs/30633712461) | 91165955682 | HTTP 410 |
| [29748492669](https://github.com/HannahHoffner/lena-grounded-voice-assistant/actions/runs/29748492669) | 88372480975 | HTTP 410 |
| [29568551398](https://github.com/HannahHoffner/lena-grounded-voice-assistant/actions/runs/29568551398) | 87846679808 | HTTP 410 |
| [29568300389](https://github.com/HannahHoffner/lena-grounded-voice-assistant/actions/runs/29568300389) | 87845883491 | HTTP 410 |
| [29568298056](https://github.com/HannahHoffner/lena-grounded-voice-assistant/actions/runs/29568298056) | 87845876413 | HTTP 410 |
| [29568219430](https://github.com/HannahHoffner/lena-grounded-voice-assistant/actions/runs/29568219430) | 87845625491 | HTTP 410 |
| [29568197722](https://github.com/HannahHoffner/lena-grounded-voice-assistant/actions/runs/29568197722) | 87845559007 | HTTP 410 |

HTTP 410 bedeutet hier, dass der Log-Endpunkt den Inhalt nicht mehr bereitstellt.
Erhaltene Jobmetadaten ersetzen diese Inhalte nicht. Nicht mehr aufgelistete
oder bereits entfernte Läufe und Artefakte können ebenfalls nicht geprüft werden.

## Umgang mit den Befunden

- Lokale Sessions, Zugangsdaten und unbereinigte Rohlogs bleiben außerhalb der
  Versionskontrolle; `.gitignore` und die Docker-Kontext-Positivliste bleiben erhalten.
- Die Forschungsbelege im getrennten Thesis-Repository bleiben unverändert.
  Bei einer späteren öffentlichen Weitergabe müssen dort enthaltene
  Interaktionstexte, Kennungen und Maschinenpfade gesondert beurteilt werden.
- Sieben abgelaufene Jobprotokolle gelten ausdrücklich als ungeprüft.
  Für den vorgesehenen eingeschränkten Betreuendenzugriff wird keine
  öffentliche Veröffentlichungsfreigabe behauptet.
- Dieser Bericht enthält ausschließlich Prüfumfang, redigierte Befundarten
  und nachvollziehbare GitHub-Verweise. Neue Rohlogkopien wurden nicht im
  Code-Repository abgelegt.
