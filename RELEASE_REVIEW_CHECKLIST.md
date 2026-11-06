# Prüfstand und Release-Checkliste – LENA

Stand: 30.10.2026. Anwendungsversion 0.2.0, geprüfte App-/Datenbasis 5962d6c.
Die Liste unterscheidet belegte Prüfungen und tatsächlich offene Aufgaben.
Die technischen und formativen Entwicklungsstände bleiben im
[Implementierungsbericht](IMPLEMENTATION_REPORT.md) dokumentiert.

## Belegte Prüfungen

- [x] Finale Kartenkorrektur vom 28.10. enthalten: Anwendungstexte 11,
  lokalisierte bekannte Telefon- und Standzeitzusätze bei geschützten
  Namen, Anschriften, Telefonnummern und Zeiten.
- [x] Vollständige Regression nach dieser Korrektur: nativ und im netzlosen
  Container jeweils 1695 bestandene Pythonfälle, ein bekannter strikter XFAIL
  und 19 bestandene JavaScriptfälle; Packaging und Runtime/Persistenz geprüft.
  Der spätere Wartungsstand ist über App-/Datenidentität zugeordnet,
  nicht durch einen zusätzlich behaupteten Volltestlauf.
- [x] Manuelle Finalprüfung am 29.10.2026 durchgeführt und bewertet:
  32 Fälle F-01 bis F-32, sechs Kriterien und gesonderte Fallurteile.
  Durchführung und Bewertung erfolgten durch eine Prüferin.
- [x] Vollständiger manueller Testplan, Kriterienmatrix, sichtbare Texte,
  Rohdaten und 48 Screenshots unter
  [`evaluation/manual_final_20261029/`](evaluation/manual_final_20261029/README.md)
  dokumentiert (am 06.11.2026 aus dem Thesisrepository übernommen).
- [x] Reale Spracherkennung und hörbare Sprachausgabe von der Prüferin
  wiederholt erfolgreich funktional getestet. Keine systematische Sprach-
  oder Akustikvollprüfung daraus abgeleitet.
- [x] Verbleibende Befunde erhalten: F-03/F-25 erfüllen den Schlafhilfeweg bei
  technischem Rückfall nicht; weitere Teilbefunde betreffen medizinische
  Verweise, Kartenfelder, Priorisierung und Sprache. Ein sicherer Rückfall
  gilt nicht automatisch als erfüllter Informationsbedarf.
- [x] Letzte vierstufige Live-Reihe auf 557a487 als historisch eingeordnet;
  negative Rohgates, technische Fehler und ungeprüfte Kriterien bleiben
  sichtbar. Die Finalprüfung ersetzt keinen neuen vollständigen Live-Lauf.
- [x] Docker-Runtime aus frischem Git-Export am 30.10.2026 auf Linux/AMD64
  gebaut und ohne Zugangsdaten gestartet: Oberfläche, geladene Daten und
  erwarteter technischer Hilfepfad geprüft. Keine erneute Vollsuite oder
  externe LLM-/STT-/TTS-Prüfung in diesem Kurztest.

## Eingeschränkte Weitergabe an Betreuende

- [x] README auf aktuellen Prüfstand und Docker-Einstieg aktualisiert.
  Normale Suchanfragen erfordern einen eigenen LLM-Zugang; STT/TTS besitzen
  gesonderte Dienstprofile. Keine Zugangsdaten mitliefern.
- [x] Trinkbrunnenrechte ausdrücklich als **ungeklärt** belassen
  (`not_explicitly_specified`). Öffentliche Erreichbarkeit, Forschungszweck
  und eine ausstehende Antwort werden nicht als Datenfreigabe dokumentiert.
  Daten, Quellen und Abrufnachweise bleiben unverändert erhalten.
- [x] Repositorysichtbarkeit lesend bestätigt: privat. Keine Sichtbarkeitsänderung.
- [ ] Betreuenden den vorgesehenen gezielten Zugriff auf das private
  Repository einrichten; eine öffentliche Sichtbarkeit ist dafür nicht nötig.
- [ ] Zielrechner prüfen; Docker ist auf Linux/AMD64 erprobt, ein nativer
  ARM64-/Apple-Silicon-Lauf wurde hier nicht zusätzlich nachgewiesen.

## Protokolle und sensible Dateien

- [x] 394 lokale Protokoll-/Belegdateien auf den vorhandenen lokalen API-Schlüssel
  und typische Secret-Muster geprüft; keine Treffer oder Lesefehler. Dateien
  mit Interaktionstexten, Sitzungskennungen und lokalen Pfaden gesondert benannt.
  Keine pauschale Anonymisierung oder allgemeine Inhaltsfreigabe behauptet.
- [x] Vollständige zugängliche Actions-Inventur einschließlich Push-/PR-Läufen:
  31 Läufe, 34 Jobs; 27 Jobprotokolle geprüft, keine Secret-Treffer.
  Sieben Protokolle sind abgelaufen (HTTP 410) und ausdrücklich ungeprüft.
  Keine aufgelisteten Workflow-Artefakte vorhanden.
- [x] Aktuellen Remote-Nachweis auf 5962d6c geprüft: Jobs `test` und `container`
  erfolgreich; ihre Protokolle waren abrufbar. Historische fehlgeschlagene
  Läufe bleiben als solche erhalten, keine erneuten Läufe ausgelöst.
- [x] Ergebnisse im [Protokollprüfbericht](docs/reviews/protokollpruefung-2026-10-30.md)
  festgehalten; Rohprotokolle nicht in den Code-Quellbaum übernommen.

## Vor einer späteren öffentlichen Veröffentlichung

- [ ] Weitergabeberechtigung für Trinkbrunnen-KML und abgeleitete Daten sowie
  weitere offene Fremddatenrechte klären. Die GPL des Codes ersetzt keine
  Datenlizenz; siehe [Lizenz und Herkunft](THIRD_PARTY_NOTICES.md).
- [ ] Tatsächlich vorgesehenen Versionsstand, Diff, Paket-/Archivinventar,
  Secrets und öffentlich sichtbare GitHub-Protokolle abschließend prüfen.
  Die sieben abgelaufenen Protokolle sind durch diese Sichtung nicht abgedeckt;
  vor einer Veröffentlichung diese verbleibende Prüfgrenze ausdrücklich bewerten.
- [ ] Bei Änderungen an Anwendung, Daten oder Providerkonfiguration die
  betroffenen technischen und manuellen Prüfungen erneut durchführen.
  Eine reine Dokumentationsänderung erzeugt keinen neuen Messstand.
- [ ] Erst für eine tatsächlich beschlossene Veröffentlichung Version, Tag
  und Zitiermetadaten konsistent festlegen; siehe [Release](docs/release.md).

Für personenbezogene Nutzung und öffentlichen Betrieb bleiben fachliche,
sprachliche, Datenschutz- und Betriebsfragen gesondert zu bearbeiten.
Sessions und Rohlogs gehören nicht ins Softwarepaket. Die Nachweise dieser
Checkliste sind keine Produktionsfreigabe.
