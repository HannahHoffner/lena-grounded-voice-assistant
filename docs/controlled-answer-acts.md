# Kontrollierte Antwortakte – Stand 27.10.2026

## Aktueller produktiver Textvertrag 7 (ersetzt den folgenden Planpfad)

Der Formulator formuliert den sichtbaren Text wieder selbst. `formulator_prose.py`
definiert den strikten Textvertrag 7 und hängt sein tatsächliches JSON-Schema an
Prompt 26 an; Evidencevertrag 5, Validator 8. Der Prompt verlangt einfache Duzform, ein bis drei kurze Sätze,
konkrete Fragebeantwortung und ausschließlich Fakten des ausgewählten Evidence-
Pakets. Zahlen, Bedingungen und Angebotszuordnung dürfen nicht verändert werden.
Interne Capability-Codes werden dem Formulator nicht als Ausgabetext angeboten.

`providers/llm.py` akzeptiert produktiv ausschließlich diesen Textvertrag.
`grounding.validate_formulation` prüft Modelltext atomar gegen die Fakten desselben
Angebots. Seit der Fachentscheidung nach dem Ablationstest verwirft die
claimtypunabhängige Inhaltswortabdeckung keine Antworten mehr; ebenso wenig
lexikalisches NOT_CHECKED/UNDECIDABLE der Leistungsprüfung. Das historische
Diagnosemodul bleibt für Reproduktion und Charakterisierung erhalten.
Literal-, Referenz-, Namens-, Zielgruppen-, Alters-, Zeit-/Preiszuordnungs-,
Entgelt-, Aufnahme-, Eignungs- und Echtzeitprüfungen bleiben aktiv, ebenso
explizite Leistungsnegationen. Diese endliche Prüfung ist keine vollständige
semantische Entailment-Prüfung und erkennt keine datengetreuen Fehler.
Gültiger Modelltext wird nur in seinen Leerzeichen normalisiert und mit
`provider: "blablador"` ausgegeben. Bei Parser-, Grounding-, Provider- oder
Budgetfehlern bleibt der bestehende Retry-/Templatepfad aktiv. Keine Änderung
an strukturierten Rückfragen, Safety-/Zielgruppendialogen oder Notfallrouting.

Regressionen: `tests/test_formulator_prose.py`, `tests/test_formulation.py`,
`tests/test_grounding_*.py`. Die folgenden Planbeschreibungen und Messungen
beziehen sich ausschließlich auf den historischen Vertrag 6; sein Renderer
ist kein erfolgreicher produktiver Antwortpfad mehr und auch nicht der
Template-Fallback. Dieser verwendet weiterhin `providers/template.py`.

Für medizinische Antworten wird `medical_emergency` aus `policy_facts.py`
gebunden bereitgestellt. Prompt 26 verlangt den zusätzlichen Notruf nur bei
sehr starken Beschwerden oder Gefahr; der Akutgefahrpfad bleibt unverändert.
`max_answer_chars` reserviert bei Ausschlussantworten Platz für den
deterministischen Hilfebuszusatz. Keine Telefonnummern öffentlicher Toiletten
in Evidence/Prosa, Prüfstatus der Brunnen nur intern. Quellangaben wie „nach
Bedarf“ sind keine Zusage; Postadresse als Leistung erklären.

`hilfebus.py` ergänzt vor der Session-/TTS-Persistenz den lokalisierten
Kontaktsatz bei allgemeiner/ungelöster Hilfe, keinem Treffer, Fachfremdheit und
technischem Rückfall, sofern Hilfebus nicht bereits im Text steht. Telefon und
Zeiten stammen aus der Runtime-Kuration. Jede Antwort mit Kacheln erhält eine
Hilfebuskachel; sie ist kein zusätzlicher fachlicher Treffer. Nur bei einem
tatsächlichen Sonntagsstand-Ergebnis werden Ort und Marker gezeigt. Die
Büroanschrift fehlt in allen Hilfebusprojektionen; Team Konsum/Wohnen behalten
ihre Büroanschrift. Mitarbeitertelefon nur auf der Kachel, Einsatztelefon in
Evidence, Kontaktprosa und Hilfebus-Vorlesetext. Copy 10 ist sprachlich nicht
menschlich freigegeben. Der neue Kurationshash verwirft alte Sessions.

## Historischer Planvertrag 6

Der bestehende Ablauf bleibt: Interpreter → Fachregeln/Kandidaten → Selector →
Formulator → Prüfung/Renderer. Es gibt keinen zusätzlichen LLM-Prüfer. Geändert
ist die Verantwortung des Formulators: Er wählt aus freigegebenen Fakten und
geschlossenen Antwortakten, statt sichtbare Faktensätze frei zu schreiben.

## Vertrag und Datenfluss

`app/formulation.py` definiert Evidence 4 und Prompt 24. Evidence enthält nur
die final ausgewählten Angebote und deren freigegebene Fakten. Die aktuelle
Frage ist untrusted Relevanzkontext, keine zusätzliche Wissensquelle.
`app/providers/llm.py` parst ausschließlich `FormulatorPlan`, Vertrag 6
(`app/answer_plan.py`). Ein Plan enthält Sprache, ein bis drei Akte und höchstens
vier Kartenkennungen. Freie `text`- oder `claim_type`-Felder sind verboten.
Der Systemprompt enthält das aus dem Parser erzeugte JSON-Schema. Die
Modell-Evidence bietet nur darstellbare Faktenkennungen an; Capability-/Typcodes
bleiben interne Metadaten. Der Validator prüft weiterhin gegen das Originalpaket.

| Akt | Zulässige Information | Sichtbare Ausgabe |
|---|---|---|
| `facts` | Angebot und bis zu sechs Faktenkennungen desselben Angebots | Vollständige Sätze aus festen Vorlagen und Quellwerten; notwendige Bedingungen werden ergänzt |
| `contact` | Angebot | Feste Bitte, dort nachzufragen |
| `unknown` | Angebot und Grund `fee`, `hours`, `access`, `availability`, `detail` | Begrenzte Nicht-Zusage, keine erfundene Leistung und keine globale Abwesenheitsbehauptung |
| `boundary` | Passende geschlossene Policy | Vorhandener lokalisierter Systemgrenzentext |

`render_answer_plan` prüft Kennungen, Angebotsbindung, Aktfelder, bekannte
Gegenbelege zu Unbekanntheitsgründen, primäres Infrastrukturangebot und Länge.
Bei Leistungen/Beschreibungen/Kosten werden die vorhandenen Zugangs-, Alters-,
Zielgruppen-, Leistungszeit- und Hinweisfakten mitgeführt. Reine Zeitangaben
führen Leistungszeitbedingungen mit, behaupten aber keine persönliche Eignung.
`app/answer_sentences.py` (Renderer 1) formuliert Fakten in vollständigen Sätzen
in DE/EN/PL/RO/RU und fasst Angaben desselben Typs zusammen. Äußere Markdown-
Zitat-/Listenmarker werden für die Ausgabe entfernt; Zahlen, Negationen,
Bedingungen und Faktenreferenzen bleiben erhalten. Mehrdeutige führende
Vergleichszeichen vor Zahlen bleiben stehen. Unstrukturierte Hinweise werden
in einem festen vollständigen Hinweissatz zitiert, nicht semantisch umgeschrieben.
Quellwerte und Evidence werden nicht verändert. Die Vorlagen sind keine
zertifizierte Leichte Sprache; unabhängiges Sprachreview bleibt offen.

Interne Capability-/Typcodes werden nicht als Prosa ausgegeben. Name, Kontakte,
Zahlen und Quelltext bleiben an das Angebot gebunden. Pflichtkarten und die
deterministische Reihenfolge werden wiederhergestellt. Vor der Darstellung
werden alle Akte vollständig validiert. Innerhalb von 600 Zeichen reserviert der
Renderer Platz für jeden Akt und übernimmt nur ganze Fakten einschließlich ihrer
Bedingungen. Nicht passende Fakten werden ausgelassen, niemals abgeschnitten.
Passt keine Gruppe, bleibt ein Kontaktauftrag ohne Leistungszusage. Für
Unbekanntheitsakte gibt es feste Kurzformen. `length_limited` im Referenzassessment
kennzeichnet diese Auswahl; `emitted_fact_ids` enthält nur tatsächlich ausgegebene
Fakten. Ein ungültiger späterer Akt wird dadurch nicht verdeckt.

Bei fehlendem typisierten Preis-/Zeit-/Zugangsfeld kann eine Angabe trotzdem
in einem Freitextfeld stehen. Deshalb behauptet `unknown` nicht, dass die ganze
Wissensbasis nichts weiß. Explizite bekannte Felder verbieten den entsprechenden
Unbekanntheitsakt. Aktuelle Kapazität wird aus statischen Daten nie garantiert.

Der gemeinsame Aufrufpfad behält Budget, höchstens einen begrenzten
Vertrags-/Groundingretry und atomaren Templatefallback. Es gibt keinen
Konfigurationsschalter zum alten freien Ausgabeformat. Externe Dienste und
`.env.example` ändern sich durch diese Überarbeitung nicht.

Die Einordnung kuratierter Namen verwendet Interpreterprompt 12. Eine reine,
vollständig erkannte Namenssuche wird nach der Safety-Entscheidung als
domänenzugehörig behandelt, auch wenn das Modell sie als fachfremd einordnet.
Das ergänzt keinen Leistungsbedarf und keine Eignungsdaten. Zusätzliche Wörter,
unbekannte Namen und akute/ungeklärte Gefahren passen nicht auf diesen begrenzten
Lookup. Die Kandidatenstufe hält mehrdeutige Namen bis zur Bezirks-/Bedarfsklärung
offen und erhält explizite Leistungen im Dialog. Bereits kuratierte konkrete
Kontaktdienste behalten Vorrang vor einem allgemeinen Kontaktlookup.

## Grenzen und historische Artefakte

Der Renderer sichert Treue zum vorgelegten Faktenpaket, keine Wahrheit der
Quellen oder Vollständigkeit der Antwort. Falsche Interpretation, unpassende
Auswahl und veraltete Daten bleiben möglich. Die Ausgabe ist weniger frei und
teilweise aufzählend. Lange unstrukturierte Hinweise können die Ausgabe auf
einen Kontaktauftrag begrenzen; dies ist keine vollständige Beantwortung aller
Fragedetails. Quellsprachige Felder werden nicht beliebig übersetzt; feste Akte,
kuratierte Enumwerte und bekannte Infrastrukturwerte sind in fünf Sprachen
hinterlegt (`app/answer_act_texts.py`), noch ohne unabhängiges Sprachreview.

Vertrag 5, Prompt 22 und der lexikalische Validator bleiben als Forschungsstand
erhalten. `app/prompt_comparison.py` verwendet dafür einen ausdrücklich
historischen Adapter; dieser hat keine produktive Route. Vier gespeicherte
Providerreplays prüfen weiter diesen alten Pfad. Neue produktive Provider- und
API-Tests prüfen Vertrag 6 einschließlich Ablehnung alter oder eingeschleuster
Freitextantworten. Das bekannte strikte XFAIL betrifft den historischen
Wortvalidator, nicht den neuen Renderer.

## Nachweise zum Blockerstand vom 26.10.2026

Der obige Aufbau ist im endgültigen Export `source-final/` geprüft. Vertrag/
Schema: `formulator_plan_prompt` und `planner_evidence_payload` in
`app/answer_plan.py`; Längenauswahl: `_fit_facts` / `_fit_answer` nach vollständiger
Validierung. Regression: `tests/test_answer_plan.py:97,121,163,182,200,212`.
Namenssuche: `app/interpreter.py:334`; Sicherheitsgegenproben in
`tests/test_interpreter.py:755,769,777`; Kontakt-/Dialogregression in
`tests/test_candidates.py:240` und `tests/test_dialogue.py:79,104,344`.

- Nativ und im neuen netzlosen Container: **1476 Python-Tests bestanden,
  ein bekannter strikter historischer XFAIL**, 0 Fehler; je **19/19 JavaScript**.
  Beide Python-Läufe melden dieselbe bekannte TestClient-DeprecationWarning.
- Sauberer No-Cache-Testbuild erfolgreich beim dritten Versuch; vorher zweimal
  externer Ubuntu-Snapshotfehler. Runtime aus derselben frischen Buildkette.
- Echte HTTP-Runtimeprüfung: Health, Loopback-Port, Start ohne Schlüssel,
  Blablador-Textantwort und korrekte Kübel-/Grünau-Verweisung nach Neustart und
  Containerwechsel. Ergänzende gezielte E2E-Diagnose: `e_mobile` in drei
  unabhängigen Sitzungen korrekt; dies ist kein vollständiger E2E-Lauf.
- **Zehn direkte Formulatorfälle: neun gültige Pläne, eine korrekte Ablehnung,
  null Schemafehler.** Ein RU-Injection-Plan enthielt eine unzulässige Boundary-
  Policy. Je ein direkter Versuch, keine reguläre Stufe 2 und keine repräsentative
  Erfolgsquote; [Einzelfälle](live-provider-evaluation.md#zehn-fälle-stichprobe-vom-26102026).

Archiv: `C:/Users/User/AppData/Local/LENA/verification/2026-10-25-blockers/`,
insbesondere `final-source-manifest.json`, `native-pytest.xml`,
`docker-final-tests.log`, `verified/results.json`, `verified/calls.json`,
`runtime-final-results.json` und `final-checks.json`. SHA-256 des Manifests:
`a393b01071b7c70f0dd1a6a0c6db523bae811006a742ad22853314377aab6917`.
Vollständige Build-/Imageidentität: [Bericht 11](../IMPLEMENTATION_REPORT.md#11-technisch-geprüfter-stand-für-den-manuellen-release-review-26102026).

Die folgende historische Vierstufenreihe bleibt unverändert negativ bei
Selector/Formulator, E2E und Stabilität. Beim Abschluss der Blockerprüfung lag
noch kein neuer vollständiger Lauf vor; anschließend am Commit 2462e7d erhoben
(siehe Ergänzung unten). Sichtbarer Browser-/Mikrofon-/Karten-/Hörnachweis,
menschliches Sprach-/Datenreview und manuelle Fachevaluation bleiben offen;
auch N-03-Logging und Datenrechte sind unverändert. Kein neuer TTS-/STT-Lauf
bei der finalen Blockerprüfung. Diese Dokumentationsfortschreibung führt keine
Tests oder externen Anfragen aus und erteilt keine uneingeschränkte Abgabe-
oder Veröffentlichungsempfehlung. Nächste Schritte:
[Release-Review-Checkliste](../RELEASE_REVIEW_CHECKLIST.md).

## Historische Prüfung vom 25.10.2026 (vor der Blockerkorrektur)

Geprüfter isolierter Snapshot: `e8b5181e5d913d55b4fd36dde9f056c7aadced7c`,
aus dem damaligen Arbeitsbaum auf Basis `15a912f`. Die folgenden Zahlen
gelten für diesen älteren Snapshot, nicht für die Blockerkorrektur vom 26.10. Keine Thesisänderung, kein Commit im kanonischen Repository.

- Native Python-Suite: **1419 bestanden, 1 bekannter XFAIL**, 408,24 Sekunden.
- Sauberer Docker-Testbuild mit `--pull --no-cache`; vollständige Suite im
  Container mit `--network none`: **1419 bestanden, 1 XFAIL, 19 JS bestanden**;
  außerdem Compileall, Dependencycheck und JS-Syntaxprüfung erfolgreich.
- Native JS-Suite: **19 bestanden**, beide JS-Syntaxprüfungen erfolgreich.
- Runtime: Healthcheck, Loopback-Port, schreibgeschütztes Dateisystem mit
  Runtimevolume, Sessionerhalt nach Neustart und Containerwechsel bestanden.
  Ohne Zugangsdaten technischer Hilfepfad; deaktiviertes TTS 503 statt 404.
- Drei HTTP-Anfragen mit echtem Blablador: zwei belegte Blablador-Ergebnisse,
  eine Toilettenantwort über Template. Edge-TTS lieferte HTTP 200 und
  147888 Byte MPEG-Audio; fremder Text wurde mit 409 abgelehnt.

Die unveränderten Live-Gates sind **nicht insgesamt bestanden**:

| Stufe | Anfragen | Provideraufrufe | Fehlerfälle | Inhaltsabweichungen | Gates |
|---|---:|---:|---:|---:|---|
| Interpreter | 15 | 15 | 0 | 0 | bestanden |
| Selector/Formulator | 16 | 21 | 4 | 0 | nicht bestanden |
| E2E | 34 | 59 | 6 | 1 | nicht bestanden |
| Stabilität | 18 | 40 | 8 | 0 | nicht bestanden |

Fehlerfälle können auch nach Retry erholte Fehler enthalten und sind keine
Halluzinationsquote. Stufe 2 enthält Schemafehler sowie eine Vertragsverletzung;
ohne gespeicherten Rohtext ist die genaue Ursache eines Schemafehlers offen.
Im E2E-Fall `e_mobile` wurde zweimal `out_of_scope` statt des erwarteten
Hauptresultats ausgegeben. Alle sechs Antworttypen waren in den dreifachen
Stabilitätswiederholungen stabil; das belegt keine vollständige Inhaltsstabilität.
54 E2E- und 51 Stabilitätskriterien sind ungeprüft; Sprachreview bleibt ausstehend.
Modellalias: `alias-fast`, vom Dienst als GPT-OSS-120b bestätigt. Stufen wurden
trotz negativer Gates anschließend nur diagnostisch erhoben, ohne Tuning oder
Wiederholung auf Grün.

Lokale Rohbelege außerhalb des Repositories:
`%LOCALAPPDATA%/LENA/verification/2026-10-25-answer-acts/` mit Quellsnapshot,
Manifest, Build-/Testlogs, Live-JSONL und `runtime-smoke.json`. Diese sind ein
lokales Evidenzarchiv und noch kein veröffentlichtes wissenschaftliches Paket.
Browserbedienung, Mikrofon, tatsächliches Anhören, Kartenkacheln und ein neuer
STT-Lauf wurden nicht geprüft. Keine menschliche Evaluation oder Abgabefreigabe.

## Vollständiger Live-Nachweis am Commit 2462e7d

26.10.2026, unveränderte Implementierung: 83 Anfragen/122 Provideraufrufe.
Selector/Formulator besteht beide Gates nach zwei erfolgreichen regulären
Formulatorretrys (zehn Fälle/zwölf Aufrufe); Interpreter Inhaltsgate wegen einer
Scopeabweichung negativ. E2E/Stabilität bleiben wegen 2/1 erholten Fehlern
negativ. Wassererstpläne missachteten den Primärvertrag, ein Toilettenplan das
Schema; alle drei final über regulären Retry erholt. Keine terminale
Längenverwerfung; fünf Assessments `length_limited`. Null katalogseitig kritische
Fehler, keine allgemeine Fakten-/Safetygarantie. Alle sechs Antworttypen innerhalb
Stabilitätsreihe stabil; Detailtexte variieren. 54/51 Kriterien und menschliche
Bewertung offen. [Bericht 12](../IMPLEMENTATION_REPORT.md#12-abschließende-vierstufige-live-messung-am-commit-2462e7d)
enthält Rohbelege, genaue Zählgrenzen und Empfehlung für formative Evaluation.
Die frühere Zehn-Fälle-Stichprobe bleibt ein separater Nachweis.
