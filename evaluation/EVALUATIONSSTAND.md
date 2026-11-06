# Evaluationsstand von LENA

Stand der wissenschaftlichen Zuordnung: 30.10.2026.
Ablage seit 06.11.2026: `evaluation/` im Anwendungsrepository; die
historischen Prüfstände und Ergebnisse bleiben unverändert. Die aktuelle manuelle Ergebnisgrundlage ist die
[Finalprüfung vom 29.10.2026](manual_final_20261029/README.md). Sie untersucht
den abschließenden App- und Datenstand nach der Kartentextkorrektur. Sie ist die einzige manuelle Evaluation im Repository.
Technische und formative Nachweise werden ihrem jeweiligen Stand zugeordnet.

## Aktueller Anwendungs- und Datenstand

- Anwendungsversion `0.2.0`, Code-Wartungscommit
  `5962d6c172d6f6eeddf6bc65c8644b833838b671`.
- Laufzeitstand nach Kartentextkorrektur auf `5eebb72` (Anwendungstexte 11).
  Der [Byteabgleich](technische-evaluation-2026-10-28/zuordnung-finaler-code.json)
  bindet alle 122 erfassten App-/Datendateien an den Wartungsstand.
- Finales manuelles Paket: [Testplan](manual_final_20261029/testplan.md),
  [Ergebnismatrix](manual_final_20261029/results.md),
  [sichtbare Texte](manual_final_20261029/evidence/sichtbare-ausgaben.txt),
  [Rohdaten](manual_final_20261029/evidence/rohdaten.json) und 48 Screenshots.
- Kuration `prototype-2026-10-27-validator-ablation`, 28 aktive soziale Angebote;
  Toilettenrelease `20260802T055552Z-fce215d4e7bd` mit 21 Datensätzen, 20 auswählbar;
  Brunnenrelease `20260802T122318Z-58d55e2ab090` mit 35 Quellpunkten,
  21 freigegebenen festen Leipziger Brunnen.
- Während der Finalprüfung wurde kein Wechsel des aktiven Bestands beobachtet.
  Es wurden keine Fehlerfixtures, Daten- oder Konfigurationsänderungen eingesetzt.

## Manuelle Finalprüfung

Durchführung und Bewertung durch eine Prüferin am 29.10.2026,
12:39:56–12:56:39 Uhr (Europe/Berlin). Technische Aufzeichnung über die echte
Browseroberfläche mit Chromium/Playwright. Ein Probelauf von F-03 um 12:39:45 Uhr
ist separat gekennzeichnet und ersetzt nicht den Hauptlauf.

32 Fälle: F-01 bis F-32. Die Kriterien sind Hilfeweg, Angebotsauswahl,
Fakten, Zeit-/Ortsbezug, Sprache und Bedienung; hinzu kommt ein Fallurteil.
Die reinen Bedienfälle F-28/F-29 enthalten jeweils fünf als nicht einschlägig
markierte Felder. Es gibt keine fehlenden oder als nicht beurteilbar kodierten
Felder. Die fachlichen Präzisierungen zu F-08/F-13/F-21 vom 30.10. sind im Paket
dokumentiert; sie sind keine Änderungen des Anwendungsstands.

| Kriterium | Erfüllt | Teilweise | Nicht erfüllt | Nicht einschlägig | Einschlägige Fälle |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hilfeweg | 26 | 2 | 2 | 2 | 30 |
| Angebotsauswahl | 27 | 3 | 0 | 2 | 30 |
| Fakten | 28 | 2 | 0 | 2 | 30 |
| Zeit-/Ortsbezug | 26 | 4 | 0 | 2 | 30 |
| Sprache | 27 | 3 | 0 | 2 | 30 |
| Bedienung | 32 | 0 | 0 | 0 | 32 |

Die gesonderten Fallurteile lauten 21 erfüllt, neun teilweise erfüllt und zwei
nicht erfüllt; keine Gesamtquote. F-03/F-25 zeigen sichere technische Rückfälle
bei unerfülltem Schlafhilfeweg. F-04/F-05/F-07 erfüllen die Frauen-/Jugendpfade.
Verbleibende Teilbefunde betreffen Helene-Kartenzeiten (F-09), medizinische
Hinweise (F-10–F-12), Sprache/Kartenfelder (F-13/F-14/F-18), Priorisierung (F-21)
und Zugangskommunikation (F-22). F-16 zeigt korrigierte rumänische Telefon- und
Standzeitdarstellung. Interne Ursachen neuer Rückfälle werden nicht aus älteren
Schemafehlern abgeleitet.

Die protokollierten Sprachurteile enthalten keinen gesonderten Kompetenznachweis
für EN/PL/RO/RU und sind keine muttersprachliche Freigabe. Die Finalprüfung
belegt weder klinische Safety noch reale Verständlichkeit, Zugänglichkeit,
Zielgruppennutzen oder Betriebsreife. Ergänzende manuelle Funktionstests der
Sprachpfade durch die Autorin wurden nicht protokolliert. Sie sind als
Funktionsbeobachtungen außerhalb der 32 kriterienbewerteten Fälle einzuordnen;
eine reproduzierbare Bewertung oder systematische Qualitätsprüfung von
Erkennung, Hörverständlichkeit und Akustik ergibt sich daraus nicht.

## Ergänzende technische und historische Nachweise

- [Technische Regression vom 28.10.](technische-evaluation-2026-10-28/README.md):
  nativ und im Container je 1695 bestandene Pytestfälle, ein strikter XFAIL,
  54 Module, sieben eingeschlossene Packagingfälle und je 19 JavaScriptfälle.
  Vollständige Läufe auf dem später gespeicherten Übersetzungspatch, keine neue
  Vollsuite auf dem Wartungscommit; Quellidentität separat geprüft.
- [Letzte vierstufige Live-Messung vom 27.10.](technische-evaluation-2026-10-27/README.md):
  historischer Stand `557a487` vor der Kartenkorrektur, 83 Anfragen und
  126 Provideraufrufe; nur Interpretergates bestanden. Rohgates und technische
  Fehler bleiben unverändert. Die damaligen 53/51 ungeprüften Kriterien werden
  nicht durch die neue Browserprüfung nachträglich als bestanden gewertet.
- Die formative Validatorentwicklung vom [26.10.](validatorentwicklung-2026-10-26/README.md)
  und [27.10.](validatorentwicklung-2026-10-27/README.md) bleibt ein eigener
  Entwicklungsnachweis und wird nicht mit der Finalprüfung zusammengezählt.
- [Synthetischer Kurztest](speech-integration-2026-10-27/README.md) auf `209edfa`:
  früherer fünfsprachiger Integrationsnachweis mit eigener Bedienbestätigung.
  Ergänzende manuelle Funktionstests der Autorin wurden nicht protokolliert.
  Die frühere Bedienbestätigung ersetzt kein Versuchsprotokoll dieser Tests.

Das frühere Live-Modellprofil wird nicht als Modellidentität der finalen
Oberflächenerhebung übernommen. Zeitabhängige Provideraliase begrenzen die
Wiederholbarkeit. Ein sicherer technischer Rückfall erfüllt nicht automatisch
den ursprünglichen Informationsbedarf.

Providerfreie Konsistenzprüfung der Finalprüfung und der ergänzenden Originalbelege:
`python evaluation/pruefe_evidenz.py` aus der Anwendungswurzel.
Separater Thesis-Build aus der Thesiswurzel: `latexmk -pdf -interaction=nonstopmode -halt-on-error thesis.tex`.
Ein vollständig fixiertes TeX-Image fehlt.
