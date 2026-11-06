# LENA: manuelle Finalprüfung vom 29.10.2026

Dieses Paket enthält die Prüfung des aktuellen Prototyps (Abgabestand) mit
32 Fällen. Geprüft werden sichtbare Hilfewege, Fakten, Zeit-/Ortsbezug,
Sprachen und Bedienung des finalen Stands.
Durchführung am 29.10.2026, Ergebnisse und Belege in [results.md](results.md)
und `evidence/`; Ablauf unter [Durchführungsstand](#durchführungsstand).

## Bestand und Vorbereitung

Grundlage ist der am 29.10.2026 gelesene Checkout `code/` auf `5962d6c`, mit
aktueller Kuration, Laufzeitübersetzungen und den Anwendungstexten des
Abgabestands (nach der Kartentextkorrektur vom 28.10.2026). Die
Thesisquellen liegen auf `c1aa2e2`. Maßgeblich für Erwartungen sind aktueller
Code und freigegebene Laufzeitdaten; ältere Szenarioerwartungen sind keine
Vorgabe für abweichendes finales Verhalten.

Vorbereitungsplan: Repository und vorhandene Nachweise lesen; aktuelle Regeln
und offene Grenzen abgleichen; ausschließlich dieses getrennte Paket erstellen;
Fallabdeckung, Quellen, Leerformulare und unveränderte Bestandsdateien prüfen.
Die Struktur folgt dem vorhandenen Evaluationsort. Auf zusätzliche CSV-/JSON-
Kataloge wird verzichtet, damit kein zweiter zu pflegender Sollkatalog entsteht.

Gelesen wurden README, Anforderungskatalog R-01–R-42 und Fachregeln FR-01–FR-13,
Szenariokataloge, kanonische Daten samt Overrides, Infrastrukturreleases,
Übersetzungen, relevante Auswahl-/Dialog-/Safety-/Frontendregeln und Tests.
Die gespeicherten manuellen Ausgaben und Einzelbefunde, XLSX-Strukturen,
Screenshotdokumentation sowie Validator-, Live-, Kartentextkorrektur- und Speech-Nachweise
wurden als Risikoquellen herangezogen. Es wurden keine App-Anfragen ausgeführt,
keine Providerprüfungen gestartet und keine Konfigurationen geändert.
Die lokalen Leseendpunkte `GET /api/health` und `GET /api/speech/config`
wurden abgefragt. Die ausgelieferten Dateien `/static/app.js` und
`/static/dialogue.js` wurden gelesen und stimmen byteweise mit dem Checkout
überein; damit wurde kein manueller Testfall ausgeführt.

Die Instanz auf `http://127.0.0.1:8002` meldete dabei 28 soziale Angebote,
Kuration `prototype-2026-10-27-validator-ablation`, Anwendungstexte des
Abgabestands, 21 Toilettendatensätze
(20 auswählbar) und 21 freigegebene feste Leipziger Trinkbrunnen aus 35
Quelldatensätzen. Toilettenrelease: `20260802T055552Z-fce215d4e7bd`;
Brunnenrelease: `20260802T122318Z-58d55e2ab090`. STT und TTS waren konfiguriert.
Ergänzende manuelle Funktionstests beider Sprachpfade durch die Autorin wurden
nicht protokolliert (Einordnung unter [Manuelle Funktionstests der Sprachpfade](#manuelle-funktionstests-der-sprachpfade)). Die Health-Abfrage prüft nicht sämtliche geladenen
Backend-Dateibytes. WFS-Autoabgleich war aktiv, automatische Freischaltung aus;
eine Vorbereitungseinstellung wurde deshalb nicht stillschweigend verändert.

## Durchführung

1. Die tatsächlich geprüfte Instanz muss aus dem aktuellen `code/`-Checkout
   stammen. Keine alte Fixture-Instanz, archivierte Antwort oder Test-Double
   verwenden. Die bereits eingerichtete lokale Anwendung öffnen. Bei unklarer
   Herkunft den Lauf erst nach technischer Klärung beginnen, keine Altinstanz
   als final ausgeben. Es ist kein Commit, Tag oder Push erforderlich.
2. In [results.md](results.md) URL, Zeitpunkt in Europe/Berlin und Browser
   eintragen. Health- und Speech-Status nur lesen und den aktuellen
   Daten-/Sprachstand festhalten. Bei geändertem aktivem Datenstand Erwartungen
   vor Beginn neu abgleichen; keine Daten aktivieren oder Fehler durch
   Konfigurationsänderungen erzeugen. Ein gemeldeter Hintergrundabgleich allein
   ist keine Änderung des aktiven Bestands.
3. [testplan.md](testplan.md) der Reihe nach abarbeiten. Jeder Fall beginnt
   mit **Start** (Haussymbol) und der dort genannten Sprache; sonst Deutsch.
   Ausnahmen sind nur die ausdrücklich zusammengehörenden Schritte eines Falls.
   Folgeäußerungen innerhalb von 180 Sekunden eingeben. Die fünfsprachige
   Startauswahl öffnet man über die Sprachschaltfläche (Globus).
4. Eingaben wörtlich verwenden. Bei relativen Zeiten und bei „heute“ die reale
   Uhrzeit protokollieren; die Systemuhr nicht verändern. Eine benannte
   Wochentagsanfrage ist ein Planungsszenario, keine aktuelle Anwesenheitsabfrage.
5. Antwort vollständig lesen, alle sichtbaren Angebotskarten aufklappen und
   vorhandene Marker anklicken. Antwort, Karteninhalt und Markertafel auf
   dieselben wesentlichen Fakten prüfen. Die App darf mehr passende Orte als
   im Kurztext anzeigen. Fehlende Geometrie darf eine Kontaktkarte ohne Marker
   ergeben; unterschiedliche Listenlängen sind allein kein Fehler.
6. Pro Kriterium und Fall bewerten, Abweichungen mit sichtbarer Fundstelle
   notieren. Screenshots oder kurze Textbelege optional unter `evidence/`
   ablegen, z. B. `F-10.png`; bei mehreren Ansichten `F-10-01.png` usw.
   Keine Namen oder sonstigen personenbezogenen Prüferinnenangaben erfassen.

Normale Freitextsuche braucht den eingerichteten LLM-Interpreter. Bei fehlender
Technik keinen Sucherfolg simulieren. Ein im ausgeführten Textfall tatsächlich sichtbarer technischer Rückfall ist
hingegen ein beobachtetes Ergebnis, kein automatisch nicht beurteilbarer Fall.

## Ergebnisregeln

- **Erfüllt:** sichtbarer Hilfeweg, Auswahl, Fakten, Zeit-/Standortbezug und
  Sprache sind für den Fall stimmig; alle jeweils einschlägigen Kriterien passen.
- **Teilweise erfüllt:** keine erfundenen Fakten, aber eine relevante Bedingung,
  Übersetzung, Karte oder Priorisierung bleibt unzureichend.
- **Nicht erfüllt:** ein erwarteter sicherer oder fachlich plausibler Pfad
  bleibt aus, Fakten werden falsch kombiniert oder die Ausgabe kann fehlleiten.
- **Nicht beurteilbar:** ausschließlich technisch nicht ausführbar oder ohne
  ausreichende Sprachkompetenz nicht fundiert bewertbar. Sprachkompetenz wird
  nicht personenbezogen erfasst. Fundiert bewertbare andere Kriterien bleiben
  separat bewertbar; das Sprachurteil wird nicht aus Zahlen/Struktur abgeleitet.

In der Matrix stehen E/T/N/B für diese vier Urteile. Leere Felder bedeuten
„noch nicht geprüft“. Wo der Sollpfad keine Karte vorsieht, wird ihr korrektes
Ausbleiben beurteilt; das ist kein Grund für B. Keine Gesamtquote bilden.

**Technischen Rückfall und ursprüngliches Hilfeziel getrennt erfassen.**
Bei sichtbarem Fehlerhinweis nur den Fehlerpfad bewerten: lokalisierter Hinweis,
bedingter Notrufhinweis aus der Policy und geladener Hilfebuskontakt ohne
Büromarker; keine erfundene fachliche Ersatzsuche. Ein korrekt ausgegebener
Rückfall erfüllt eine ausgefallene Schlaf-/Essens-/Medizinsuche nicht. Gelingt
die fachliche Antwort über ein Template, zählt der sichtbare Inhalt; die
Entstehungsart muss ohne sichtbaren Beleg nicht geraten werden. Keine
unsichtbaren Retries oder Modellentscheidungen bewerten.

## Erwartete Grenzen des finalen Stands

- Keine Echtzeitdaten zu freien Plätzen, Aufnahme, tatsächlicher Anwesenheit,
  laufendem Brunnenbetrieb oder garantierter persönlicher Eignung.
- Essen und Trinkwasser ohne Zeitangabe verwenden aktuelle Berliner Zeit.
  Bei Essen können heute erst später beginnende, noch nicht beendete Angebote
  erscheinen. Das bedeutet nicht „jetzt geöffnet“. Zudem nutzt der Essensfilter
  teilweise die allgemeinen Öffnungszeiten: etwa Oase 08–16 Uhr, während die
  Quelle Frühstück 09–10 und Mittag 12–13:30 Uhr nennt. Keine universelle
  Öffnungszeiten- oder Feiertagslogik voraussetzen; F-02 erfasst diese Grenze.
- Medizin: UVO wird tageweise eingeschränkt; kein lückenloser Termin- oder
  Anmeldefilter. Oase kann mittwochs als medizinischer Treffer erscheinen,
  obwohl ihre eigene ärztliche Sprechstunde Donnerstag ab 15 Uhr lautet.
  Der normale medizinische Kartenpfad kann UVO an der Taubestr. 2 statt am
  Einsatzort zeigen; die Standprojektion existiert, wird aber nicht in jedem
  Pfad genutzt. F-10/F-11 beobachten diese **bekannten Grenzen**, verlangen
  keine unimplementierte Korrektur. Eine sichtbar irreführende Wegweisung bleibt
  nach den Ergebnisregeln zu bewerten und darf nicht als Erfolg gelten.
- Trinkbrunnen: Saison April bis Oktober nach aktuellem Kalendermonat,
  kein verifizierter Live-Betrieb; keine erfundenen Hausnummern. Im November
  bis März ist der soziale Trinkwasserpfad statt direkter Brunnen erwartbar.
- Entfernungen beziehen sich auf den Hauptbahnhof und sind Luftlinien.
  Stadtteilwörter allein verschieben diesen Ursprung nicht.
- Zielsprachen sind maschinell übersetzt. Namen, Adressen, Ortsbezeichnungen
  und operative Werte bleiben erhalten. Die feste Quellenfußzeile bleibt
  deutsch; dies als bekannte Oberflächengrenze notieren, nicht als neu
  fehlgeschlagene Übersetzung von Antwort/Karte behandeln.
- Die englische Form „minor injuries“ kann eine unnötige Ablehnung bzw. einen
  Rückfall auslösen. F-12 erfasst diese bekannte Grenze; kein bestimmter
  Wortlaut und kein interner Validatorstatus wird verlangt.
- Safety-Preflight ist eng und kann exakt passende Zitate fehlklassifizieren.
  Eine verlässlich reproduzierbare unklare Gefahr lässt sich ohne Modellkontrolle
  nicht erzwingen. F-30 prüft den belegten unmittelbaren Gefahrpfad, keinen
  simulierten Safety-Dialog. Die App ruft nicht selbst an.
- Start/Timeout löschen sichtbaren Kontext und verwerfen die Browser-Sitzung;
  sie sind keine Löschfunktion für gespeicherte Serverdaten.

## Manuelle Funktionstests der Sprachpfade

Die Autorin erprobte Spracherkennung (STT) und hörbare Sprachausgabe (TTS)
in der laufenden Anwendung und beobachtete funktionierende Ein- und Ausgabe.
Die Versuche wurden nicht protokolliert. Zeitpunkte, Anzahl, Sprachen sowie
Geräte-, Umgebungs- und Dienstkonfiguration liegen nicht als auswertbare
Versuchsdokumentation vor. Diese Funktionsbeobachtungen gehören nicht zu den
32 kriterienbewerteten Fällen. Ein reproduzierbarer Prüfbeleg oder eine
systematische Qualitätsprüfung von Erkennung, Hörverständlichkeit und Akustik
am vorgesehenen Einsatzort liegt damit nicht vor.

Diese Einordnung präzisiert am 04.11.2026 die frühere Erfolgsaussage auf Grundlage
der Angabe der Autorin, dass die manuellen Versuche nicht protokolliert wurden.
Die historische Firefox-Bedienbestätigung vom 27.10. ist kein Versuchsprotokoll
dieser ergänzenden Tests.

## Quellen und Ableitung

Die Links dienen der Nachvollziehbarkeit; der Testplan ist ohne ältere
Evaluationsdateien ausführbar. Die Erwartungen enthalten bewusst keine
internen Kennungs-, Hash-, Modell- oder Testnamensprüfungen.

| Aktuelle Quelle | Abgeleitete Fälle / Zweck |
| --- | --- |
| [README](../../README.md), [Anforderungen und Fachregeln](https://github.com/HannahHoffner/Chatbot-MA/blob/26cfa71441800639ab3311faa8c1de8be810740a/Chapters/AppendixLenaDesign.tex) | Umfang, Bedienung, Sprache, Ergebnisgrenzen |
| [Kanonische Daten](../../app/resources/bootstrap/canonical/offers.json), [Kuration und Overrides](../../app/resources/bootstrap/curation/social_offers.json), [offizielle Ergänzungen](../../app/resources/bootstrap/official/verified_offers.json) | F-01–F-17, F-20–F-22, F-32; Fakten und Zugang |
| [Kandidatenregeln](../../app/candidates.py), [Zeitregeln](../../app/result_time.py), [Kontext](../../app/candidate_context.py) | Auswahl, Zielgruppe, Essen ohne Mindestalter, Helene-Bedingung, Aliasbindung |
| [Dialogsteuerung](../../app/dialogue_flow.py), [Service](../../app/service.py), [Dialogtests](../../tests/test_dialogue.py) | F-03, F-07, F-13, F-21/F-22, F-25/F-26 |
| [Kartenorte](../../app/maps.py), [Ordnung](../../app/result_ordering.py), [Infrastrukturpfade](../../app/infrastructure_results.py) | Stand-/Bürotrennung, Wasser, Toiletten, Luftlinie |
| [Toilettenbestand](../../app/resources/bootstrap/toilets/releases/20260802T055552Z-fce215d4e7bd/records.json), [Brunnenbestand](../../app/resources/bootstrap/drinking_fountains/releases/20260802T122318Z-58d55e2ab090/records.json) | F-18/F-19: belegte Orte, Gebühren, Saison, Schließung |
| [Übersetzungen](../../data/i18n/offer_translations.json), [Anwendungstexte](../../app/resources/bootstrap/i18n/application_texts.json), [Kartenprosa](../../app/card_texts.py), [Kartenprüfungen](../../tests/test_card_translation_completeness.py) | Sprachfälle und korrigierte Telefon-/Standzeitzusätze |
| [Safety-Policy](../../docs/safety-and-error-policy.md), [Preflight](../../app/safety.py), [Frontend](../../app/static/app.js) | F-27–F-31, Rückfallregeln |
| [Aktuelle Implementierungsentscheidungen](../../docs/final-implementation-decisions.md), [Implementierungsbericht](../../IMPLEMENTATION_REPORT.md), [Korrektur Duschen/Schlafdialog](https://github.com/HannahHoffner/lena-grounded-voice-assistant/blob/2d212a8120e57af4b50710c436a6d35c33221e3d/docs/exec-plans/fix-shower-sleep-firefox.md) | F-07/F-12/F-25/F-31/F-32; aktuelle Schutzgrenzen statt alter Solltexte |
| [Live-Szenarien](../../app/resources/bootstrap/evaluation/live_scenarios.json), [mehrsprachige Szenarien](../../app/resources/bootstrap/i18n/dynamic_scenarios.json) | Eingaben und Risikoabdeckung; veraltete Solltypen nicht übernommen |
| [Live-Einordnung](../technische-evaluation-2026-10-27/current-assessment.json), [Validatorbefunde](../validatorentwicklung-2026-10-27/fehlablehnungen-30-befunde.json), [Belege Kartentextkorrektur](../technische-evaluation-2026-10-28/README.md) | Frauenpfad, UVO/Oase, Sprachwechsel, Telefon-/Standzeitübersetzung, Namen/Preise/Zielgruppen und technische Rückfälle gezielt erneut prüfen |

Interne Korruption, Releaseaktivierung und erzwungene Providerfehler werden nicht
manuell herbeigeführt: Dafür müssten Daten, Konfiguration oder Fixtures geändert
werden. Ihre sichtbaren Risiken werden über die regulären Fälle und eine
gesonderte Rückfallerfassung abgedeckt. Es gibt keinen solchen Browser-Testmodus.

Maßgeblich sind die im Paket dokumentierten Ausgaben und Urteile des finalen Stands.

## Durchführungsstand

- **Durchführung:** Durch die Prüferin am 29.10.2026, 12:39–12:56 Uhr
  (Europe/Berlin), über die echte Browseroberfläche der laufenden Instanz
  (Chromium/Playwright, technische Aufzeichnung mit dem
  Skript [`evidence/durchfuehrung_run_cases.py`](evidence/durchfuehrung_run_cases.py)).
  Jeder Fall wurde einmal ausgeführt; Start, Sprachwahl, Eingaben, Auswahl,
  Zurück, Kartenkacheln und Marker wie im Testplan bedient. Keine Daten-,
  Konfigurations- oder Codeänderung, keine Fixtures.
- **Bewertung:** Durch die Prüferin. Sprachurteile EN/PL/RO/RU ohne gesondert
  nachgewiesene Sprachkompetenz.
- **Fachliche Vorgaben der Autorin (30.10.2026):** Kostenfreiheit der
  Bahnhofsmission ist fachlich bekannt (F-13); die Hundebedingung muss vorerst
  nicht benannt werden, die Klärung erfolgt bei der Rücke (F-08); Jugend-
  Streetwork führt wegen der Nähe zum Hauptbahnhof zunächst zu Streetwork Mitte
  (F-21, Erwartung im Testplan angepasst).
- **Umfang:** 32 Fälle bewertet.
