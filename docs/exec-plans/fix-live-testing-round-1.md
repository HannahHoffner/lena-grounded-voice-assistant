# Fixes aus der ersten manuellen Live-Testrunde

## Status

- State: Complete
- Owner: Claude
- Created: 2026-08-04
- Last updated: 2026-08-04

## Kontext

Erste manuelle Testrunde der laufenden Anwendung gegen den real konfigurierten
Provider (`LENA_REWRITE_PROVIDER=blablador`) durch den Nutzer im Browser.
Ergänzt `fix-interpreter-prompt-missing-schema.md` (erster gefundener Bug in
derselben Runde) um alle weiteren Funde. Kein Punkt dieser Liste war zuvor
durch die (ausschließlich Test-Double-basierte) Suite abgedeckt.

## Befunde und Fixes

### 0. Dieselbe Prompt-Schema-Lücke auch bei Selector und Formulator

Nach dem Fund bei „Diese Angebote passen zu deiner Frage: ..." (statischer
Fallback statt LLM-Formulierung) ergab die Live-Nachverfolgung: `SELECTOR_SYSTEM_PROMPT`
und `FORMULATOR_SYSTEM_PROMPT` hatten dieselbe Lücke wie zuvor der Interpreter
— beide nennen zwar die erwarteten Top-Level-Schlüssel, aber nie den exakten
`contract_version`-Literalwert, und der Formulator-Prompt beschrieb
`sentences` nie als Objekt-Array mit `text`/`claim_type`/`offer_id`/
`fact_ids`/`policy_ids`, sondern nur als vages "one to three short sentences".
Live-Reproduktion zeigte das Modell frei erfundene `contract_version: "1"`
statt `"2"` und `sentences` als Liste bloßer Strings statt Objekten — beides
schlug an der strikten Pydantic-Validierung fehl (`formulator_schema_error`).
Beide Prompts um denselben expliziten Schema-Abschnitt wie beim Interpreter
ergänzt (`app/llm_selection.py`, `app/formulation.py`), `contract_version`
jetzt per f-string aus der Konstante statt hartkodiert. `SELECTOR_PROMPT_VERSION`
1→2, `FORMULATOR_PROMPT_VERSION` 5→6. Neue Regressionstests
(`test_formulator_prompt_names_every_contract_field_and_exact_contract_version`,
`test_selector_prompt_names_every_contract_field_and_exact_contract_version`)
verhindern, dass ein künftiger Vertragswechsel dieselbe Lücke erneut öffnet.

### 1. Interpreter-Antwort wurde bei Kategorie-Klicks abgeschnitten

`min(self.max_tokens, 700)` in `app/providers/llm.py` war zu knapp: Der vom
Blablador-Router gelegentlich ausgewählte Backend (`GPT-OSS-120b`,
Reasoning-Modell) verbraucht 1500–3300 Tokens für internes Reasoning, bevor es
den eigentlichen JSON-Inhalt schreibt — bei 700/1200 Tokens brach die Antwort
mitten im JSON ab (`interpreter_invalid_json`). Angehoben auf `min(self.max_tokens, 4096)`.
Live-Nachtest: Erfolgsrate bei Kategorie-Klicks von ca. 50 % auf 93–95 %
verbessert; ein Rest-Risiko bleibt, da der Router gelegentlich einen noch
größeren Reasoning-Umfang wählen kann — außerhalb der Kontrolle von LENA.
Zusätzlich `uncertain_hints`-Wortlaut im Prompt auf "wenige Worte, nie ein
ganzer Satz" begrenzt, um unnötig lange Modellantworten von vornherein zu
vermeiden.

### 2. `selected_need_hint` war dem Interpreter unbekannt

Kein funktionaler Bug (Kategorie-Klicks klassifizierten bei korrektem
Payload-Aufbau bereits korrekt), aber bei der Diagnose festgestellt: Das Feld
wird an das Modell gesendet, aber im Systemprompt nirgends erklärt — bislang
ohne beobachtbaren Schaden, da der tatsächliche Query-Text bereits den
Kategorienamen enthält (`service.py` ersetzt eine leere Anfrage durch
`payload.category.value`). Keine Änderung nötig; als Beobachtung dokumentiert.

### 3. Toilettenkarten: zu viele Felder, „Luftlinie“ genannt

`app/static/app.js`: Felder „Operator“, „Phone“ und „Air distance“ aus der
Toilettenkarte entfernt (Trinkbrunnenkarte unverändert, dort nicht bemängelt).
Die API liefert diese Felder weiterhin (keine Vertragsänderung), nur die
UI-Darstellung wurde reduziert.

### 4. „Luftlinie“/Distanzmethode nicht mehr in Antworttexten

Statische Vorlagen `fallback.toilet_primary`/`fallback.water_primary` (alle 5
Sprachen) umformuliert: nennen jetzt nur noch die nächstgelegenen Ziele
(gerankt nach Entfernung), ohne die Berechnungsmethode zu erklären.
Formulator-Systemprompt-Anweisung ergänzt: Entfernung darf zum Ranking/zur
Formulierung „am nächsten“ verwendet werden, die Messmethode darf nicht
genannt werden. Fact-Strings in `app/formulation.py` von „m Luftlinie vom
Leipzig Hauptbahnhof“ auf „m Entfernung vom Leipzig Hauptbahnhof“ geändert.
Die tatsächliche Berechnung (Haversine-Luftlinie) ändert sich nicht — nur der
Wortlaut gegenüber Endnutzer:innen. `FORMULATOR_PROMPT_VERSION` 4→5.

### 5. Toiletten-Facilities/Gebühr/Öffnungszeiten nur auf Deutsch

`app/infrastructure.py`: neue geschlossene Übersetzungstabelle
(`TOILET_FACILITY_TRANSLATIONS`, `TOILET_FEE_TRANSLATIONS`,
`TOILET_HOURS_TRANSLATIONS`, Helper `localize_toilet_text`) für den kleinen,
tatsächlich vorkommenden Wortschatz der amtlichen CSV (4 Facility-Werte, 2
Gebührenwerte, 2 Öffnungszeiten-Werte). Unbekannte Werte bleiben unverändert
deutsch statt eine falsche Übersetzung zu erfinden. Angewendet sowohl auf die
Karte (`toilet_card()`) als auch auf die dem Formulator übergebenen Fakten
(`build_public_toilet_evidence()`), damit LLM-formulierte und
Karten-/Template-Antworten sprachlich konsistent bleiben. Dabei einen echten
Folgefehler behoben: die deterministische Fallback-Antwort zitierte weiterhin
den unübersetzten `primary.fee_raw` statt des jetzt übersetzten Kartenwerts
(`primary_card.fee_raw`) — ohne diese Korrektur wären Karte und Antworttext
sprachlich auseinandergelaufen.

### 6. Schlaf-Altersfrage: „unter 18“-Option entfernt

Das Datenmodell (`AgeGroup`) kennt ohnehin nur zwei Stufen (`under_27`/
`not_under_27`) — die dritte, im Prompt genannte Option „unter 18“ war reine
Formulierung ohne eigene Logik dahinter. Auf Wunsch des Nutzers vereinfacht:
`dialogue.prompts.sleep_age` fragt jetzt nur noch zweigeteilt („18–26 oder
mindestens 27?“), da unter 27-Jährige ohnehin über die U27-Priorisierung an
Jugendstreetwork-Angebote verwiesen werden und die dritte Option keinen
zusätzlichen fachlichen Zweck erfüllte. Keine Änderung an
Eligibilitätslogik/`AgeGroup`-Auswertung.

### 7. AP12-Szenariokatalog: Stadtteilpriorität ausdrücklich ausgeschlossen

Nutzerentscheidung: Stadtteillogik bleibt draußen (konsistent mit der
AP9-Entscheidung) und wird auch nicht als eigene Evaluationskategorie
nachgebaut. Fließt in die AP12-Planung ein, sobald diese begonnen wird.

## Verification

| Prüfung | Ergebnis |
|---|---|
| Live-Wiederholungstest Interpreter (20 echte Kategorie-Aufrufe) | 19/20 |
| `tests/test_public_toilets.py`, `test_formulation.py`, `test_live_evaluation.py`, `test_api.py`, `test_interpreter.py`, `test_dialogue.py` | grün |
| Volle Suite | grün |
| `python -m compileall -q app tests` | COMPILE_OK |

## Nachtrag: `.env.local`-Präzedenz und ein weiterer echter Grounding-Bug

„Diese Angebote passen zu deiner Frage: ..." blieb nach Anhebung von
`LENA_LLM_MAX_TOKENS` in `.env` zunächst bestehen. Ursache: eine separate,
höher priorisierte lokale Datei `.env.local`
(„Local non-secret override for responsive answer generation") setzte
`BLABLADOR_MAX_TOKENS=800` — dieser Name hat in der Einstellungsauflösung
(`_optional_env("BLABLADOR_MAX_TOKENS", "LENA_LLM_MAX_TOKENS")`) Vorrang, und
`.env.local` wird nach `.env` mit `override=True` geladen. Der `.env`-Wert
wurde dadurch vollständig unwirksam. Mit Zustimmung des Nutzers
`BLABLADOR_MAX_TOKENS` in `.env.local` auf `6000` gesetzt.

Danach zeigte sich ein weiterer, unabhängiger echter Bug: `app/grounding.py`s
Satzbruch-Erkennung (`SENTENCE_BREAK_RE`, jetzt `_contains_sentence_break`)
behandelte die deutsche Vereinsform „e. V." fälschlich als Satzende (zwei
Sätze statt einem), da nur „Str." als Abkürzung ausgenommen war. 18 der
Angebote im Katalog enthalten „e. V." im Namen — jede Formulierung, die
diesen Namen zitierte, schlug an dieser Prüfung fehl. Die Erkennung geprüft
jetzt das Wort vor dem Satzzeichen gegen eine kleine feste Abkürzungsliste
(„str", „e", „v", „dr", „nr", „ca", „ggf", „bzw", „u", „a", „z", „b", „co")
sowie jedes auf „str" endende Wort (Straßennamen), statt eine dreistellige
Lookbehind-Zeichenkette zu prüfen. Neuer Regressionstest
`test_sentence_with_e_v_abbreviation_is_not_treated_as_multiple_sentences`.

**Live-Ergebnis nach allen Fixes:** Formulator-Erfolgsrate für die Medizin-
Testabfrage von 0/4 auf 2/4 verbessert; erfolgreiche Antworten entsprechen
inhaltlich genau dem gewünschten Stil („Du kannst die ärztliche Sprechstunde
am Donnerstag ab 15:00 Uhr in der Leipziger Oase, Nürnberger Str. 31, ...").
Die verbleibenden Fehlschläge sind andere `formulator_ungrounded_claim`-Fälle
(u. a. eine Zahlen-/Telefonnummern-Prüfung in
`_validate_operational_tokens`) — nicht weiter angepasst, da unklar ist, ob
das echte Halluzinationen abfängt (gewollt) oder ein weiteres
Formatierungs-Mismatch ist; das wäre ein separater Untersuchungsschritt, kein
unilateraler Fix an einer sicherheitsrelevanten Prüfung.
