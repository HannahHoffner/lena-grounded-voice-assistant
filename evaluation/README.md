# Evaluation von LENA

Die maßgebliche Ablage der Evaluationsunterlagen ist seit dem 06.11.2026
`evaluation/` in diesem Anwendungsrepository. Übernommen wurde der vollständige
Bestand aus `Evaluation/` des Thesiscommits `26cfa71441800639ab3311faa8c1de8be810740a`
(Repository `HannahHoffner/Chatbot-MA`). Alle Originalbelege und
`pruefe_evidenz.py` wurden bytegleich verschoben. Im README der manuellen
Finalprüfung wurden ausschließlich die Quellverweise angepasst.
Historische Pfad- und Commitangaben in diesen Originalen beschreiben weiterhin
den Erhebungsstand.
Die Ablageänderung ist kein neuer Prüflauf.

Das bereits veröffentlichte Zenodo-Softwarearchiv v0.2.0 enthält diese
vollständigen Evaluationsoriginale noch nicht. Der erweiterte Gitstand
und dieses bestehende Archiv sind unterschiedliche Artefakte.

Die [manuelle Finalprüfung vom 29.10.2026](manual_final_20261029/README.md)
ist die einzige manuelle Evaluation in diesem Repository. Sie dokumentiert
32 fortlaufende Fälle F-01 bis F-32 auf dem finalen App- und Datenstand,
sechs Kriterien und gesonderte Fallurteile. Durchführung und Bewertung erfolgten
durch eine Prüferin. Ergänzende manuelle Funktionstests der Sprachpfade wurden
nicht protokolliert und gehören nicht zu den 32 kriterienbewerteten Fällen.
Maßgeblich sind [Testplan](manual_final_20261029/testplan.md),
[Ergebnisse](manual_final_20261029/results.md) und die zugehörigen Originalbelege.
Die zeitliche Zuordnung aller Nachweise steht im [Evaluationsstand](EVALUATIONSSTAND.md).

## Ergänzende technische und formative Nachweise

- [Finale technische Prüfung vom 28.10.](technische-evaluation-2026-10-28/README.md):
  Regression nach Kartentextkorrektur und Quellabgleich zum Wartungsstand.
- [Historische Live-Messreihe vom 27.10.](technische-evaluation-2026-10-27/README.md):
  Stand 557a487/Copy 10, ursprüngliche Gates und getrennte nachträgliche Einordnung.
- Formative Validatorentwicklung [26.10.](validatorentwicklung-2026-10-26/README.md)
  und [27.10.](validatorentwicklung-2026-10-27/README.md).
- Historische technische Archive [22.10.](technische-evaluation-2026-10-22/README.md)
  und [26.10.](technische-evaluation-2026-10-26/README.md).
- [Synthetischer Kurztest](speech-integration-2026-10-27/README.md):
  fünf synthetische Sprachfälle auf 209edfa und getrennte Firefox-Bedienbestätigung.

Diese Nachweise werden entsprechend ihrem jeweiligen Stand eingeordnet und
nicht als manuelle Ergebnisse der Finalprüfung gezählt.

## Providerfreie Konsistenzprüfung

Aus der Anwendungswurzel, mit Python >= 3.11, ohne Netzwerk oder Zusatzpakete:

```text
python evaluation/pruefe_evidenz.py
```

Das Skript prüft die 32 Fallkennungen, die ausgefüllte Kriterienmatrix und
ihre Auszählung, die Fallurteile im Testplan sowie die Belegverknüpfungen.
Zusätzlich prüft es SHA-256-Indizes der technischen und formativen Archive,
beide Erstversuchstabellen, JUnit-Zahlen und die Summe der Live-Provideraufrufe.
Die Prüfung bewertet keine Antwort fachlich oder sprachlich neu.
`.gitattributes` schützt die Originalbelege vor Zeilenendekonvertierung.

Ein korrekter technischer Rückfall erfüllt nicht automatisch den ursprünglichen
Informationsbedarf. Die Finalmatrix hält beide Aspekte getrennt fest;
die Reichweite der Befunde erläutert Abschnitt 6.8 der Masterarbeit.
