# Technische Voraussetzungen der manuellen Evaluation

Diese Checkliste beschreibt Voraussetzungen, keine durchgeführte Evaluation
und keine Freigabe für öffentliche Nutzung oder personenbezogene Testeingaben.

1. Den geprüften Code- und Datenstand festhalten. Der Live-Evaluations-CLI
   verlangt einen sauberen Git-Arbeitsbaum; Änderungen deshalb erst prüfen und
   durch die verantwortliche Person versionieren. Commit, Runtime-Fingerprint,
   Release-IDs, Kurationsstand, Prompt-/Vertragsversionen und Providerkonfiguration
   gemeinsam dokumentieren. Zeitabhängige Szenarien mit Datum, Uhrzeit und
   Zeitzone erfassen; ein allgemeiner Lauf ist nicht zeitunabhängig reproduzierbar.
2. Die verantwortliche Person hat den aktuellen Datenstand für diese Evaluation
   bestätigt (`4A`). `reviewed_for_prototype` bleibt dennoch keine institutionelle
   Freigabe: aus einer erfolgreichen Hashprüfung folgt keine Aktualität der
   Öffnungszeiten oder Erreichbarkeit. Kein Pending-Release ungeprüft aktivieren.
3. Lokal und mit einem Prozess starten (`python -m app`). Keine öffentliche
   Bindung, keine Mehrprozess-Worker. `.env.local` kann Prozesswerte übersteuern;
   für ein vollständig explizites Profil `LENA_ENV_FILE_MODE=disabled` verwenden.
   WFS-/Toiletten-/Brunnen-Synchronisation für einen eingefrorenen Teststand
   deaktivieren. Ohne LLM-Interpreter gibt es nur den technischen Hilfepfad,
   keine normale Bedarfsauswahl. Health-Status belegt Konfiguration und lokale
   Ladefähigkeit, nicht Erreichbarkeit oder Qualität externer Provider.
4. Runtimepfad außerhalb von Cloud-Synchronisation wählen. Volltextlogging
   bewusst ein- oder ausschalten (`INTERACTION_LOGGING_ENABLED`); auch ohne
   Interaktionslog speichert die Sitzung nicht-akute Fragen und Antworten.
   Nur synthetische, nicht personenbezogene Eingaben verwenden. Aufbewahrung,
   Zugriff und anschließende Löschung sind organisatorisch festzulegen.
5. Jeden unabhängigen Fall mit Start bzw. frischer Sitzung beginnen. Start und
   der 180-Sekunden-Frontend-Inaktivitätsreset löschen sichtbare Inhalte,
   verwerfen die Browser-Sitzungskennung und stoppen/entwerten ausstehende
   Requests, Mikrofon-Callbacks und Wiedergabe. Sie löschen keine Serverlogs
   oder bereits gespeicherten Sitzungsdateien; laufende Serververarbeitung
   kann noch enden. Server-TTL-Bereinigung erfolgt bei Zugriff, nicht als
   garantierter zeitgesteuerter Löschdienst. Sprachwechsel erhält die Sitzung.
6. Netzwerkpfade separat berücksichtigen: LLM, Browser-Spracherkennung,
   serverseitiges STT, standardmäßiges Edge-TTS und OSM-Kacheln sind nicht
   vollständig lokal. Texterfassung bleibt bei fehlender Sprachfunktion möglich.
   Ein erneuter Klick auf die aktive Vorleseschaltfläche stoppt die Ausgabe.
7. Bekannte Grenzen protokollieren: maschinelle, nicht vollständig sprachlich
   geprüfte Übersetzungen; keine reale Akustik-/WCAG-/Screenreader-Validierung;
   heuristische Grounding-Prüfung; kein Nachweis aktueller Aufnahmekapazitäten;
   Luftlinien statt Routen; keine automatische vollständige Standortverlagerung.

## Beschlossener Zeit- und Vermittlungsvertrag

Für diese Evaluation gilt: Ohne ausdrückliche Zeitangabe prüft LENA die aktuelle
Europe/Berlin-Zeit strikt bei Essen und Trinkwasser. Medizinische und allgemeine
Vermittlungspfade folgen nur ihren jeweils dokumentierten Regeln; es gibt keinen
universellen Öffnungszeitenfilter. Der Hilfebus darf jederzeit als
Telefon-/Vermittlungshinweis erscheinen, zeigt dabei die dokumentierten täglichen
Einsatzzeiten 18:00--23:00 und behauptet keine aktuelle Erreichbarkeit. Außerhalb
des belegten Sonntag-20:00--21:00-Standfensters für Essen/Trinkwasser ist er
keine direkte Leistung und hat keinen Marker. Dieser Vertrag ersetzt die hiervon
abweichende Thesis-Formulierung erst nach einer separaten Thesis-Korrektur; die
Thesisdateien wurden nicht geändert.

## Evaluationsreihenfolge

1. **5A:** Manuelle technische Prüfung mit synthetischen Eingaben und
   Test-Doubles, ohne produktive Provider. Diese Phase kann nach einer lokalen,
   dokumentierten Konfiguration erfolgen.
2. **5B:** Kontrollierter Live-Provider-Lauf ausschließlich mit synthetischen
   Eingaben. Vorher sauberen Commit, eingefrorene Daten-/Konfigurationsidentität,
   explizite Live-Freigabe und Providerverfügbarkeit bestätigen. Dieser Schritt
   erzeugt einen neuen Laufreport; bisherige Tests sind kein Live-Ergebnis.
3. **5C:** Reale Eingaben/Provider erst danach und erst nach eigener
   Datenschutz-, Aufbewahrungs-, Zugriffsschutz- und Betriebsfreigabe. Diese
   Freigabe wird durch 4A oder einen technischen Test nicht ersetzt.

## Sichere technische Prüfungen

`python -m pytest`, `python -m compileall -q app tests`, `python -m pip check`,
`node --test tests/frontend.test.cjs`, `node --check app/static/app.js` und
`node --check app/static/dialogue.js` prüfen automatisierte technische Pfade.
Die Packaging-Tests bauen Wheel und sdist, installieren isoliert und starten
außerhalb des Checkouts. Paketinstallation kann Paketindizes benötigen, macht
aber keine produktiven LLM-/Speech-/Quelldatenaufrufe.

Die JavaScript-Tests führen die echten Skripte mit DOM-/Transport-Doubles aus,
einschließlich Reset-Rennen und verspäteter Mikrofonfreigabe. Sie ersetzen
keine echten Browser-, Touch-, Assistenztechnik- oder Akustiktests.
`live-dry-run` ist providerfreie Vorbereitung; das `--dry-run` der
Übersetzungswartung bedeutet dagegen nur, dass kein Store geschrieben wird:
es kann echte Provideraufrufe ausführen. Nicht als Offline-Test verwenden.
