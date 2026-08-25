# Safety- und Fehlerpolitik

## Geltungsbereich

Diese Policy beschreibt den implementierten Prototypstand von WP9A. Sie dient
der stabilen Begrenzung bei möglicher unmittelbarer Gefahr. Sie ist keine
medizinische oder psychologische Diagnose, keine Krisenberatung und keine
Produktivfreigabe. LENA alarmiert niemanden, übermittelt keinen Standort und
löst keinen Anruf aus.

Als einziger freigegebener Notruffakt wird `112` verwendet. Die Nummer ist in
`app/policy_facts.py` mit Notruffakt-Policyversion 1 und zwei Referenzen
gebunden. Die darauf aufbauende Anwendungspolitik trägt Safety-Policyversion 2:

- Bundesamt für Bevölkerungsschutz und Katastrophenhilfe: Erste Hilfe und Notruf
- Europäische Kommission: einheitliche europäische Notrufnummer 112

WP9A ergänzt bewusst keine weiteren Notfall-, Krisen- oder Beratungskontakte.

## Kontrollreihenfolge

```text
Requestgrenzen
→ enger deterministischer Preflight
→ LLM-Interpreter und strikte Vertragsvalidierung
→ deterministische Safety-Policy
→ erst danach Scope, Fachdialog, Kandidaten, Formulator und Karten
```

Safety hat Vorrang vor Out-of-Scope, offenen Fachdialogen, Hilfebus,
Sozialangeboten, Toiletten und Trinkbrunnen. Der Preflight in `app/safety.py`
ist ein versionierter Defense-in-Depth-Mechanismus. Er erkennt nur vollständige,
explizite Sätze mit Person, Handlung und unmittelbarem Zeitbezug in den fünf
unterstützten Sprachen. Einzelwörter, negative Stimmung, historische,
metaphorische oder verneinte Aussagen reichen in aller Regel nicht; da der
Preflight eine reine Wortfolgen-Übereinstimmung ohne Zitat- oder Berichtskontext
ist, kann ein exakt wortgleiches Zitat dennoch fälschlich auslösen. Seit
Safety-Policyversion 2 führt ein Treffer ohne Modellaufruf direkt zum
kontrollierten lokalisierten 112-Text. Diese bewusste fail-closed Entscheidung
verkürzt den Pfad bei den eng formulierten eindeutigen Akutsätzen; sie nimmt
für exakt passende Zitate einen möglichen unnötigen Stopp in Kauf. Alle nicht
exakt passenden Formulierungen gehen weiterhin an den LLM-Interpreter.

## Drei Risikostatus

| Status | Quelle | Bedeutung | Systementscheidung |
|---|---|---|---|
| `detected` | enger Preflight oder Interpreter | konkrete unmittelbare oder unmittelbar bevorstehende Gefahr | sofortiger lokalisierter 112-Text; keine weiteren Provider, Angebote, Karten oder Marker |
| `uncertain` | Interpreter | unmittelbare Gefahr ist möglich, aber nicht sicher auflösbar | strukturierter Dialog `acute_risk_confirmation` |
| `not_detected` | Interpreter | aktueller Kontext lässt keine Akutgefahr erkennen | regulärer Pfad, sofern kein offener Safety-Dialog eine ausdrückliche Verneinung verlangt |

Ein Preflight-Treffer öffnet keinen Dialog und erzeugt keinen künstlichen
Bedarfs- oder Faktenzustand. Er beendet den fachlichen Pfad unmittelbar. Nur
ein strikt validierter Interpreterstatus `uncertain` öffnet den nachfolgenden
Safety-Dialog.

Der Interpreter erzeugt weder Notrufnummer noch Safety-Text, Diagnose,
Risikobegründung oder Score. `QueryService` entscheidet nach Vertragsvalidierung
deterministisch über den sichtbaren Pfad.

## Safety-Dialog für unklare Interpreterergebnisse

Der Safety-Dialog nutzt den einzigen vorhandenen Session- und Dialogstore. Er
ist an Session, Runtime-Wissensbasisfingerabdruck und Ablaufzeit gebunden und
wird atomar beansprucht. Die stabilen Werte sind:

- `immediate_danger_yes`: führt ohne weiteren Modellaufruf zum 112-Text;
- `immediate_danger_unsure`: führt konservativ zum 112-Text;
- `immediate_danger_no`: öffnet den strukturierten ursprünglichen Bedarf wieder.

Freie Text- und Spracheingabe laufen durch den Interpreter. Ein Modellstatus
allein darf den Safety-Zustand nicht aufheben: Zusätzlich muss die Antwort eine
eng definierte ausdrückliche Verneinung der geschlossenen Frage sein. Eine neue
Fachfrage oder ein Themenwechsel bleibt blockiert. Nach höchstens einem
unverständlichen Wiederholungsversuch folgt konservativ der 112-Hinweis.
Ein Sprachwechsel erhält den Dialog bei identischem Fingerabdruck.

## Technische Fehler

Timeout, HTTP-Fehler, ungültiges JSON, Schema- oder Vertragsfehler,
Budgeterschöpfung und ein nicht verfügbarer Interpreter fallen geschlossen aus:

- kein CandidateSelector, Selector oder Formulator;
- keine lexikalische Fachklassifikation;
- keine themenbezogenen Angebote oder Kartenergebnisse;
- lokalisierter technischer Text mit der bedingten Aussage, bei unmittelbarer
  Gefahr 112 zu rufen.

Ein Fehler behauptet nicht, dass Gefahr erkannt wurde. Die Nummer und alle
sichtbaren Safety-Texte stammen aus zentralen versionierten Ressourcen.

Seit Version 0.3.0 ist dieser Text kein Sackgassentext mehr: Ist in der
Wissensbasis ein Hilfebus-Kontakt hinterlegt (`priority_rules` enthält
`general_help_referral_first`, siehe `_general_help_contact()` in
`app/service.py`), enthält der Text zusätzlich dessen Telefonnummer und
Einsatzzeiten (`safety.technical_hilfebus`) sowie eine zugehörige
Angebotskarte und einen Kartenmarker -- ausschließlich aus bereits geladenen,
deterministischen Wissensbasisdaten, ohne jeden weiteren Providerkontakt. Der
bedingte 112-Hinweis bleibt dabei unverändert Teil des Texts (weiterhin genau
einmal, zentral geprüft), weil der vorgelagerte Preflight bewusst eng gefasst
ist und nicht jede tatsächliche Akutgefahr abfängt. Ist kein Hilfebus-Kontakt
in der Wissensbasis vorhanden -- oder ist gar keine Wissensbasis geladen
(`POST /api/query` ohne aktiven `QueryService`, siehe `app/main.py`) --, bleibt
es beim bisherigen reinen 112-Text (`safety.technical`) ohne Karte oder
Marker. Der Sofortstopp bei erkannter oder unsicherer Akutgefahr
(`acute_risk`/`acute_risk_clarification`) ist von dieser Änderung nicht
betroffen und bleibt weiterhin ohne Karten, Karten-IDs oder Marker.

## API, Frontend, TTS und Datenminimierung

`POST /api/query` kennzeichnet die Pfade als `acute_risk`,
`acute_risk_clarification` oder `technical_fallback`. `acute_risk` und
`acute_risk_clarification` enthalten weiterhin leere Karten-, Karten-ID- und
Markerlisten. `technical_fallback` enthält seit Version 0.3.0 die
Hilfebus-Karte und einen Kartenmarker, sofern die Wissensbasis den Kontakt
liefert (siehe oben); das Frontend rendert diese Karte und Markierung wie bei
jeder anderen Antwort. Das Frontend leert in jedem Fall zunächst bestehende
Layer, zeigt eine textliche Safety-Überschrift und ein zusätzliches Symbol,
verwendet native Dialogbuttons und genau einen Alert-Ausgabekanal. Es erzeugt
keinen `tel:`-Link.

TTS akzeptiert weiterhin nur den letzten sichtbaren Antworttext derselben
Session und Sprache. Technische Normalisierung spricht 112 ziffernweise; eine
menschliche Hörprüfung wird nicht behauptet.

Session- und Interaktionsspeicherung redigieren Safety-Eingaben. Zulässig sind
nur Risikostatus, Safety-Pfad, Dialognutzung/-ergebnis, Fallbackstatus,
redigierter Interpreterfehler und Antwortsprache. Nicht gespeichert werden
Modellrohausgabe, Begründung, Diagnose, Score oder detaillierte
Gefahrenbeschreibung.

## Mehrsprachigkeit und verbleibende Grenzen

Safety-Texte und Dialoglabels liegen zentral für Deutsch, Englisch, Polnisch,
Rumänisch und Russisch vor. Die Nummer 112 wird erst aus dem zentralen
Policyfakt eingesetzt und muss in jedem Safety-Text genau einmal vorkommen.
Deutsch ist `review_pending`; die vier Übersetzungen sind `machine`. Keine
Fassung ist dadurch muttersprachlich, professionell, fachlich institutionell
oder akustisch freigegeben.

Der paketierte synthetische Katalog `app/resources/bootstrap/safety/scenarios.json`
deckt 19 Gruppenfälle in allen fünf Sprachen ab. Test-Doubles belegen Vertrag
und Kontrollfluss, nicht die reale linguistische Modellgüte. Falsch positive und
falsch negative Modellklassifikationen bleiben möglich. Reale Provider- und
Hörtests sowie ein produktives Krisen-, Datenschutz- und Betriebskonzept liegen
außerhalb von WP9A.
