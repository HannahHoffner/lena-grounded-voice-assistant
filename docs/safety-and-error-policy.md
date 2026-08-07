# Safety- und Fehlerpolitik

## Geltungsbereich

Diese Policy beschreibt den implementierten Prototypstand von WP9A. Sie dient
der stabilen Begrenzung bei möglicher unmittelbarer Gefahr. Sie ist keine
medizinische oder psychologische Diagnose, keine Krisenberatung und keine
Produktivfreigabe. LENA alarmiert niemanden, übermittelt keinen Standort und
löst keinen Anruf aus.

Als einziger freigegebener Notruffakt wird `112` verwendet. Die Nummer ist in
`app/policy_facts.py` mit Policyversion 1 und zwei Referenzen gebunden:

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
ist, kann ein exakt wortgleiches Zitat dennoch fälschlich auslösen. Deshalb
führt ein Preflight-Treffer nicht zu einem sofortigen Stopp, sondern öffnet
denselben bestätigenden Safety-Dialog wie ein vom Interpreter gemeldetes
unsicheres Risiko (siehe unten). Der LLM-Interpreter bleibt die primäre
sprachliche Klassifikation und ist die einzige Quelle für einen sofortigen
Stopp ohne Rückfrage.

## Drei Risikostatus

| Status | Quelle | Bedeutung | Systementscheidung |
|---|---|---|---|
| `detected` | Interpreter | konkrete unmittelbare oder unmittelbar bevorstehende Gefahr | sofortiger lokalisierter 112-Text; keine weiteren Provider, Angebote, Karten oder Marker |
| `uncertain` | Interpreter oder Preflight | unmittelbare Gefahr ist möglich, aber nicht sicher auflösbar (Interpreter), oder ein enger Wortlauttreffer ohne Kontextprüfung (Preflight) | strukturierter Dialog `acute_risk_confirmation` |
| `not_detected` | Interpreter | aktueller Kontext lässt keine Akutgefahr erkennen | regulärer Pfad, sofern kein offener Safety-Dialog eine ausdrückliche Verneinung verlangt |

Ein Preflight-Treffer öffnet den Dialog ohne Kenntnis des eigentlichen Bedarfs
(`originating_need` ist der generische Platzhalter `general_help`, nicht der
vom Interpreter erkannte Bedarf). Eine Bestätigung oder Unsicherheit stoppt
konservativ ohne weiteren Provideraufruf. Eine Verneinung führt zu einer
allgemeinen Bedarfsklärung (`general_need`), da vor dem Preflight noch kein
Bedarf interpretiert wurde.

Der Interpreter erzeugt weder Notrufnummer noch Safety-Text, Diagnose,
Risikobegründung oder Score. `QueryService` entscheidet nach Vertragsvalidierung
deterministisch über den sichtbaren Pfad.

## Safety-Dialog

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
- keine Angebote, Karten, Marker oder Hilfebus-Ergänzung;
- lokalisierter technischer Text mit der bedingten Aussage, bei unmittelbarer
  Gefahr 112 zu rufen.

Ein Fehler behauptet nicht, dass Gefahr erkannt wurde. Die Nummer und alle
sichtbaren Safety-Texte stammen aus zentralen versionierten Ressourcen.

## API, Frontend, TTS und Datenminimierung

`POST /api/query` kennzeichnet die Pfade als `acute_risk`,
`acute_risk_clarification` oder `technical_fallback`. Safety-Antworten enthalten
leere Karten-, Karten-ID- und Markerlisten. Das Frontend leert bestehende Layer,
zeigt eine textliche Safety-Überschrift und ein zusätzliches Symbol, verwendet
native Dialogbuttons und genau einen Alert-Ausgabekanal. Es erzeugt keinen
`tel:`-Link.

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
