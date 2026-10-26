# Diagnostischer Vergleich der Formulator-Prompts

Der Vergleich untersucht, ob ein engerer Formulierungsauftrag hilfreichere,
belegte Modellantworten erzeugt. Er ist eine gesonderte synthetische Studie,
keine neue bestandene Vier-Stufen-Evaluation und keine menschliche Fachprüfung.
Diese Studie gehört zum historischen Freitextvertrag 5. Seit 25.10.2026
verwendet der reguläre API-Pfad den [geschlossenen Antwortplan](controlled-answer-acts.md).

## Reproduktion

Voraussetzungen: installierte LENA-Pythonumgebung und explizit eingerichteter
Blablador-Zugang (`REWRITE_PROVIDER=blablador`, `BLABLADOR_BASE_URL`,
`BLABLADOR_API_KEY`). Der Vergleich fixiert für beide Arme `alias-fast`,
4096 Tokens und 30 Sekunden Formulator-Timeout. Kein STT, TTS oder Kartendienst.
Der Alias muss am gewählten Endpunkt existieren. Prozesswerte haben Vorrang
vor `.env.local` und `.env`; Zugangsdaten nie in Befehlszeilen schreiben.

Beispiel in PowerShell, Ergebnisverzeichnis außerhalb des Repositorys und
außerhalb von Cloudsync (muss bei `prepare` noch fehlen):

```powershell
$study = Join-Path $env:LOCALAPPDATA 'LENA/verification/mein-promptvergleich'
python -m app.prompt_comparison prepare $study
python -m app.prompt_comparison run $study --split development
python -m app.prompt_comparison review-packets $study
# Entwicklungsantworten prüfen; eingefrorene Prompts unverändert lassen.
python -m app.prompt_comparison run $study --split holdout
python -m app.prompt_comparison review-packets $study
```

`prepare` ruft keinen Provider auf. Es speichert Manifest, beide vollständigen
Prompts und 60 vollständige Fragen-/Belegpakete einschließlich vorab festgelegter
Referenzbedingungen. Das Manifest enthält HEAD **und Dirty-Status**, App-Quellhashes,
Paket-/Prompthashes, Parameter und fünf Wiederholungsfälle. Der Dirty-Status
wird nicht als sauber ausgegeben: das Werkzeug ist selbst Teil der uncommittierten
Änderung; die Quellhashes ergänzen die Commitkennung.

`run` führt die vorab registrierten Aufrufe aus (80 Entwicklung, 50 Abschluss
einschließlich Wiederholungen). Pro Fall beide Arme nacheinander, wechselnder
erster Arm, höchstens zwei parallele Fälle. Kein Retry. Eine vorhandene
Ergebnisdatei wird nicht überschrieben; geänderte Quellen, Fälle oder Prompts
führen zum Abbruch. Unvollständige Läufe sind keine vollständigen Ergebnisse.
Bei Fehlern werden geschlossene Fehlercodes statt freier Exceptiontexte ausgegeben.

Zum Messzeitpunkt ersetzte die Evaluations-Unterklasse ausschließlich den
Systemprompt am vorhandenen Providertransport. Nach der produktiven Umstellung
auf Vertrag 6 verwendet sie ausdrücklich den historischen Parser für Vertrag 5
und den alten Wortvalidator. Der Transport bleibt gemeinsam; das ist kein Test
des neuen produktiven Renderers. Sie sichert die rohe Modellantwort. Das Werkzeug
ist ein ausdrücklich aufgerufener CLI ohne API-Route; es wird beim Anwendungsstart
nicht ausgeführt. Rohtexte bleiben lokal und werden nicht in technische Logs geschrieben.

## Einzelbewertung

`review-packets` gibt Pakete mit Frage, Fakten, vorab fixierten Kriterien und
Modellentwurf aus; Arm und Gateurteil sind in dieser Ansicht ausgeblendet.
Das allein macht eine anschließende Codex-Bewertung nicht zu einer unabhängigen
oder verblindeten menschlichen Studie.

In `reviews.json` wird pro `sample_id` ein begründetes Urteil hinterlegt:

```json
{
  "beispiel_sample_id": {
    "supported": true,
    "answers_question": true,
    "major_error": false,
    "reviewer": "codex",
    "reason": "Belegt die genannte Leistung und ergänzt keine Bedingungen."
  }
}
```

- `supported`: Jede sichtbare inhaltliche Aussage ist durch Fakten/Policies
  oder eine korrekt eingegrenzte fehlende Information gedeckt. Ein fehlender
  Entwurf oder eine nicht verständlich bewertbare Ausgabe erhält kein positives Urteil.
- `answers_question`: Die konkrete Frage wird ausreichend beantwortet;
  auch „nicht dokumentiert“ kann eine richtige Antwort sein. Eine bloße
  allgemeine Angebotsbeschreibung kann trotz korrekter Fakten unzureichend sein.
- `major_error`: Unbelegte/kontradiktorische Leistung, Zugang, Preis,
  aktuelle Verfügbarkeit oder falsche Zuordnung zu einer Einrichtung.
- Formale Schemafehler werden **zusätzlich** ausgewiesen; ein verständlicher
  richtiger Text in einem ungültigen Vertrag ist keine verwendbare API-Antwort.
- Unbekanntes ist nicht gleich falsch; „keine Information über Reparaturen“
  belegt weder eine Reparaturleistung noch deren tatsächliche Nichtexistenz.

```powershell
python -m app.prompt_comparison summarize $study
```

Die Zusammenfassung verlangt vollständige Labels und Reviewerangaben, erzeugt
aber selbst keine semantischen Urteile. `reviewer=human` darf nur bei tatsächlich
erfolgter menschlicher Prüfung gesetzt werden. `supported_but_rejected` ist eine
diagnostische Differenz zwischen Codex-Urteil und Gate, keine automatisch
bewiesene Fehlablehnungsquote. Die Sprach- und Fachbewertung durch externe
Menschen bleibt separat erforderlich.

## Reichweite

Die Fälle verwenden erfundene Einrichtungen und kleine, gezielt schwierige
Belegpakete in DE/EN/PL/RO/RU. Sie messen das Formulierungsmodul, keine reale
Quellenaktualität, vollständige Kandidatenauswahl, reguläre Dialogfolge oder
Browserbedienung. Einzelne Fälle können im normalen Service bereits vor einer
freien Formulierung durch Fachregeln/Dialogsätze abgeschlossen werden.
Entwicklungs- und Abschlussteil bleiben klein; externe Modellaliase und
Dienstausfälle schränken Wiederholbarkeit ein. Laufzeiten bei Parallelität sind
kein isolierter Performancebenchmark. Ein negatives Gate ist keine
Halluzinationsquote, ein positives Gate keine Garantie sachlicher Vollständigkeit.

## Ergebnis der Erhebung vom 24.10.2026

### Erhebung und Ergebnis

Ausgangscommit `15a912f657a3e47e2c0d96a6a9201a693ea134db`, produktiver Prompt
22 / Vertrag 5 / Validator 4. Die zwei neuen Evaluationsmodule waren uncommittiert;
das Manifest kennzeichnet den Arbeitsbaum deshalb korrekt als dirty und bindet
alle App-Pythondateien per SHA-256. Keine produktive Prompt-/Gateänderung.
Fragen/Fakten/Kriterien: SHA256
`d0cfe65dee9b18c64777674238cbb42fed4fc004c5f8064f346f019f1d55d48d`.
Baselineprompt `d41ec4353b3f1052d3d636354881a2892449ec4dd51b0326f1d8c1e327dca536`,
Kandidat `6438cd667b381bfc214933f90f4fc7b1432342206eb353559a7206ae8f4b5b04`.
Beobachtete Modellkennung: `01 - GPT-OSS-120b - an open model released by OpenAI in August 2025`.

**Die folgende Semantikbewertung stammt von Codex, nicht von unabhängigen
menschlichen Fach-/Sprachprüfenden.** Alle Einzelurteile mit Begründung liegen
vor. Sprachstil und fachliche Akzeptanz müssen Menschen gesondert prüfen.

| Teil / Arm | Aufrufe | Entwürfe | Nach Codex belegt und hilfreich | Vom bestehenden Gate akzeptiert | Belegte Entwürfe vom Grounding verworfen | Schemafehler | Providerfehler |
|---|---:|---:|---:|---:|---:|---:|---:|
| Entwicklung / bisher | 40 | 25 | 25 | 10 | 12 | 3 | 15 |
| Entwicklung / Kandidat | 40 | 25 | 25 | 12 | 12 | 1 | 15 |
| Abschluss inkl. Wiederholungen / bisher | 25 | 25 | 23 | 3 | 16 | 5 | 0 |
| Abschluss inkl. Wiederholungen / Kandidat | 25 | 25 | 25 | 10 | 10 | 5 | 0 |

Im ursprünglichen Abschlussteil ohne die fünf Wiederholungen waren 3/20
Baseline- und 7/20 Kandidatenantworten akzeptiert. Wiederholungen sind keine
weiteren unabhängigen Szenarien. Es wurde kein systematischer Nachweis stabiler
Überlegenheit oder einer repräsentativen Fehlerrate erbracht.

Im Entwicklungsteil fehlten durch 30 Transport-/Providerfehler sämtliche
Entwürfe der drei Familien Angebotszuordnung, Negation und Prompt-Injection.
Die ursprünglichen Fehlversuche bleiben in den Zahlen. Nach Abschluss der
ursprünglichen Reihe wurde deshalb **ein zusätzlicher Durchgang** mit genau
diesen 15 Paketen und beiden unveränderten Prompts vorab registriert
(`supplement-plan.json`): 30 weitere Aufrufe, sequenzielle Paare, kein Retry.
Das ist eine nachträglich beschlossene Diagnose, kein unabhängiger Abschlussteil
und kein Ersatz der fehlgeschlagenen ursprünglichen Messungen.

| Ergänzungsdurchgang | Aufrufe / Entwürfe | Nach Codex belegt und hilfreich | Gate akzeptiert | Grounding verworfen | Schemafehler |
|---|---:|---:|---:|---:|---:|
| Bisher | 15 / 15 | 14 | 5 | 5 | 5 |
| Kandidat | 15 / 15 | 15 | 5 | 6 | 4 |

Insgesamt 160 Studienaufrufe: 130 ursprünglich registriert plus 30 ergänzend.
Hinzu kamen ein Modellinventar-GET und eine minimale Completion als getrennte
Verfügbarkeitsdiagnose. Der Inventar-GET und die Diagnose-Completion waren
HTTP 200. Ein zusätzlicher, archivierter Beobachter erfasste im Abschlussteil
ausschließlich HTTP-Statuswerte, ohne Anfragen/Antworten/Timing zu verändern:
50/50 HTTP 200. Die ursprünglichen 30 Providerfehler besitzen keinen
gesicherten Upstream-Status; sie dürfen nicht als bewiesenes Rate-Limit,
Authproblem oder Promptfehler bezeichnet werden.

### Einzelbefunde

- `unknown_fee_de`: Beide Prompts erklären korrekt, dass der Duschpreis nicht
  dokumentiert ist. Ablehnung unter anderem `service_fact_missing`.
- 14 ursprüngliche Schemafehler haben denselben Grund:
  `non-offer sentence requires policy`. Die Modelle formulieren eine inhaltlich
  richtige fehlende Information, liefern dafür aber einen Block ohne Angebots-
  oder Policybindung. Der aktuelle Vertrag hat keine ausdrückliche Policy für
  fehlende Angebotsfakten. Das ist ein konkreter Vertrags-/Aufgabenabgleich;
  Schemafehler nicht einfach zulassen.
- `service_time_*`: Die korrekte Einschränkung „Mahlzeiten nur Freitag
  18:00–19:00, nicht 09:00“ wird in beiden Armen verworfen. Diese synthetische
  `service_condition` ist freie Formulierung und nicht das kanonische Format
  des Runtime-Builders (`service_condition_text` / `condition_capability`).
  Daraus folgt **kein** Beweis, dass alle entsprechenden echten Hilfebuspakete
  scheitern. Für den Promptvergleich ist dasselbe verständliche Belegpaket
  beiden Armen gegeben; eine zusätzliche Builder-/Parserprüfung ist getrennt nötig.
- Ergänzungsfall `negation_*`: Die ausdrücklich belegte fehlende
  Übernachtungsmöglichkeit wird von beiden Modellen erhalten, aber vom
  Grounding verworfen (`service_fact_missing`). Baseline-EN ergänzt „only
  provide social advice“; diese zusätzliche Vollständigkeitsbehauptung wurde
  als unbelegt bewertet. Die anderen neun Entwürfe enthalten diesen Zusatz nicht.
- Abschluss `unsupported_service_ro`, Baseline, Sample
  `9ee81844b0ba6459`: „Talpunkt … nu repară biciclete“ behauptet tatsächliche
  Nichtexistenz der Reparaturleistung. Belegt ist nur Kleiderausgabe.
  Codex bewertet das als wesentliche unbelegte Verneinung; das vorhandene Gate
  verwirft sie. Der Kandidat benennt stattdessen die fehlende Dokumentation.
- Abschluss `availability_pl`, Baseline, Sample `b4e1f2a085219649`:
  Dienst und Zeiten stimmen, aber die Frage nach garantierter Behandlung jetzt
  wird nicht beantwortet. Kandidat nennt die Grenze ausdrücklich.
- In den 65 tatsächlich zurückgegebenen Kandidatenentwürfen (inklusive
  Ergänzungsdurchgang) fand Codex keine unbelegte inhaltliche Aussage.
  Das ist ein kleiner diagnostischer Befund, keine Sicherheitsgarantie.
  Beispielsweise verwendet der Kandidat in einer deutschen Antwort dennoch
  „Sie“ und verändert in einer anderen den Namen durch Genitivflexion;
  vollständige Stil-/Identitätskonformität ist ebenfalls nicht nachgewiesen.

### Entscheidung und nächster struktureller Schritt

**Keinen produktiven Prompt und keine Faktenprüfung in diesem Auftrag ersetzen.**
Der eingefrorene Kandidat bleibt ein dokumentiertes Forschungsartefakt.
Er wurde in dieser Stichprobe häufiger akzeptiert (22 statt 13 von 65
ursprünglichen Aufrufen), aber auch bei ihm werden 22 nach Codex korrekte
Entwürfe vom Grounding verworfen und sechs weitere am Schema abgewiesen.
Ein Prompt allein behebt die belegten Fehlerklassen daher nicht. Die Ausfälle,
kleinen Szenariozahlen und fehlende unabhängige menschliche Bewertung erlauben
keine uneingeschränkte Freigabe. Bestehende Prompt-/Regressionsprüfungen werden
nicht umgeschrieben oder abgeschwächt, um einen experimentellen Kandidaten
als abgabereif auszugeben.

Die kleinste sachliche Fortsetzung ist ein ausdrücklich modellierter
**Antwortakt für fehlende Information** mit Angebots-/Themenbindung und einer
kontrollierten sprachlichen Ausgabe. Danach prüfen, welche belegten Aussagen
direkt aus Fakten ausgegeben werden können und wo freie Paraphrase eine
semantische Prüfung benötigt. Der Kandidatenprompt kann bei dieser
Vertragsüberarbeitung erneut als Ausgangspunkt dienen. Erst nach dieser
Entscheidung sind produktive Promptversion, zielgerichtete Regression und
neue relevante Live-Nachweise festzulegen. Ein vierter produktiver LLM-Schritt
ist durch diese Studie weder als erforderlich noch als überlegen nachgewiesen.

### Nachweise und technische Prüfung

Vollständiger lokaler Nachweis außerhalb Cloudsync:
`C:/Users/User/AppData/Local/LENA/verification/2026-10-24-formulator-prompts/`.
Enthalten: Manifest, beide Prompts, alle Belegpakete, originale JSONL-Zeilen,
begründete Einzelurteile, beide ergänzenden Beobachter-/Ausführungsskripte,
gesonderte Summaries, Schema-Diagnose und gehashte gemessene App-Pythonquellen.
`semantic-summary.json` zählt die ursprüngliche Reihe;
`complete-summary.json` führt den Ergänzungsdurchgang ausdrücklich separat.

Technisch: 12 neue Offline-Tests für Gleichheit der Belegpakete, Quellen-/
Prompthashes, Aufrufgrenzen, Überschreibschutz, Parser/Groundingintegration,
Fehlerredaktion und Bewertungsprovenienz. Vollständige native Suite:
**1355 bestanden, 1 bekannter XFAIL**, 4795,88 s, eine bekannte
Starlette-TestClient-Deprecationwarnung. JS **19/19**, Syntax beider Skripte
erfolgreich. Die ungewöhnlich lange Testlaufzeit ist protokolliert und wird
nicht als gemessene Anwendungs-/Providerlatenz interpretiert.

Produktive Anwendung, Daten, Konfiguration, Prompts und Gates sind unverändert.
Es wurde deshalb kein neuer Docker-/E2E-Freigabelauf behauptet. Die früheren
Docker- und vierstufigen Livebelege bleiben auf ihren jeweiligen Stand gebunden.
