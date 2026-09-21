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

### Konkreter Ablauf für 5A

Die vorhandenen Test-Doubles sind in die Testsuite eingebunden. Es gibt keinen
allgemeinen Browser-Modus, der freie Eingaben durch einen Fake-Interpreter
versteht. Deshalb besteht 5A aus den automatisierten fachlichen Prüfungen mit
Doubles und einer anschließenden manuellen Prüfung des providerfreien
Browser-/Fehlerpfads. Die normale freie Bedarfssuche wird mit 5B geprüft.

Für die fachlichen Regeln im Verzeichnis `code` ausführen:

```powershell
$env:LENA_ENV_FILE_MODE = 'disabled'
$env:LENA_ALLOW_LIVE_SMOKE = 'false'
python -m pytest tests/test_candidates.py tests/test_dialogue.py tests/test_result_ordering.py tests/test_safety_policy.py tests/test_drinking_fountains.py -q
```

Für die manuelle lokale Prüfung in einer eigenen PowerShell starten (Fenster
danach schließen, damit die Testkonfiguration nicht für 5B bestehen bleibt):

```powershell
$env:LENA_ENV_FILE_MODE = 'disabled'
$env:REWRITE_PROVIDER = 'template'
$env:WFS_AUTO_SYNC = 'false'
$env:TOILET_AUTO_SYNC = 'false'
$env:DRINKING_FOUNTAIN_AUTO_SYNC = 'false'
$env:LENA_ALLOW_LIVE_SMOKE = 'false'
$env:INTERACTION_LOGGING_ENABLED = 'false'
$env:LENA_RUNTIME_DIR = Join-Path $env:LOCALAPPDATA 'LENA\evaluation-5a'
python -m app --host 127.0.0.1 --port 8002
```

Vor dem Öffnen die externe Netzwerkverbindung des Rechners trennen, während
Loopback verfügbar bleibt, und die Mikrofonberechtigung für die lokale Seite
blockieren. Damit sind auch externe Aufrufe durch Browser und Backend gesperrt.
Ein Browser-Filter für fremde Domains allein sperrt serverseitiges Edge-TTS
nicht; `template` allein deaktiviert außerdem die automatische Browser-
Spracherkennung nicht. Für diesen Text-Smoke keine Mikrofon-/Vorleseaktion
verwenden. Öffne `http://127.0.0.1:8002`.

| Fall | Eingabe/Aktion | Erwartung |
| --- | --- | --- |
| A01 | Jede der fünf Sprachen wählen | Bedienelemente in gewählter Sprache; Texteingabe nutzbar |
| A02 | „Ich brauche Essen.“ | Technischer Hinweis mit geladenem Hilfebus-Kontakt und dokumentierten Zeiten; keine reguläre Essenssuche, kein Marker |
| A03 | Start nach A02 | Eingabe, Antwort, Verlauf und Kartendaten entfernt; neue Browser-Sitzung |
| A04 | Nach A02 drei Minuten inaktiv bleiben | Rückkehr zur Sprachauswahl; vorherige Inhalte verborgen/geleert |
| A05 | Anfrage absenden und sofort Start | Späte Antwort stellt vorherigen Inhalt nicht wieder her |
| A06 | Sprache wechseln und erneut A02 | Neuer Hinweis in gewählter Sprache; keine fremdsprachige verspätete Antwort |

Pro Fall Datum/Uhrzeit, Browser, Sprache, Code-Commit plus lokale Änderungen,
Runtime-Fingerprint, Eingabe, sichtbares Ergebnis und bestanden/fehlgeschlagen
mit Begründung notieren. Diese Tabelle enthält Erwartungen, keine Ergebnisse.

### Übergang zu 5B und 5C

Für 5B ist deine Auswahl bereits festgehalten. Nach 5A die verbleibenden
Test-/Dokumentationsänderungen versionieren und in einer frischen Shell das
vorgesehene Providerprofil verwenden. Zuerst den vorhandenen providerfreien
Plan ausgeben:

```powershell
python -m app.multilingual_review live-dry-run --stage all
```

Modell-/Domainwerte und Grenzen mit dem gewünschten Profil vergleichen.
Anschließend die vorhandenen vier Stufen gemäß
[Live-Provider-Anleitung](live-provider-evaluation.md) nacheinander ausführen;
der Stufe-1-Befehl steht dort vollständig. Erst nach dem jeweiligen Gate zur
nächsten Stufe wechseln. Kein WFS-Abruf oder Datenupdate ist dafür notwendig.
Die Live-Stufen prüfen LLM-Verhalten; reale STT-/TTS- und Akustikprüfungen sind
damit noch nicht durchgeführt.

Bei anschließender manueller Bedarfssuche mit synthetischen Eingaben besonders
prüfen: Hilfebus-Verweis um 10:00/23:30 ohne Marker; explizit Sonntag20:30 für
Essen/Wasser mit belegtem Stand; Sonntag22:00 ohne diesen direkten Stand;
medizinische Anfrage ohne Zeit und mit widersprechendem Tag; Minderjährige,
unbekanntes Alter, unklare Aliase, Safety sowie Sprachwechsel/Reset. Für
zeitabhängige Fälle den tatsächlichen Zeitpunkt oder die explizite Eingabe
dokumentieren, nicht die Betriebssystemzeit verändern.

5C folgt nach den dokumentierten Ergebnissen von 5A/5B. Vor Eingaben mit
Personenbezug sind die bereits genannten Entscheidungen zu Verantwortlichkeit,
Logging/Aufbewahrung und Zugriffsschutz zu treffen.

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
