# Fix: Interpreter-Systemprompt spezifizierte kein JSON-Schema

## Status

- State: Complete
- Owner: Claude
- Created: 2026-08-04
- Last updated: 2026-08-04

## Befund

Beim ersten manuellen Test der laufenden Anwendung durch den Nutzer gegen den
real konfigurierten Provider (`LENA_REWRITE_PROVIDER=blablador`, Modell
`alias-fast`) scheiterte **jede** Anfrage mit der technischen Fallback-Antwort
("Ich kann deine Anfrage gerade nicht sicher prüfen..."). Die lokalen
Interaktionsprotokolle zeigten `interpreter_error_code: "interpreter_schema_error"`
für jede einzelne Anfrage — auch für Einträge vom 2026-08-03, also bereits vor
dieser Session.

## Ursache

`INTERPRETER_SYSTEM_PROMPT` (`app/interpreter.py`) beschreibt die
Klassifikationsregeln ausführlich in Prosa, spezifiziert aber an keiner Stelle
die exakte JSON-Struktur des erwarteten Vertrags (`QueryInterpretation`,
Contract-Version 3): Weder das Feld `input_language` noch der verschachtelte
Container `explicit_facts` wurden im Prompt namentlich erwähnt. Da der Request
nur `response_format: {"type": "json_object"}` setzt (kein strukturprüfendes
`json_schema`), musste das Modell die Struktur allein aus der Prosa erraten —
und produzierte plausible, aber falsche flache Felder (`age`, `gender`,
`district` usw. direkt auf oberster Ebene statt unter `explicit_facts`),
zusätzlich ohne die drei Pflichtfelder `input_language`, `uncertain_hints`,
`clarification_may_be_needed`. Der strikte Pydantic-Vertrag (`extra="forbid"`)
wies das deshalb bei jedem einzelnen Aufruf zurück — deterministisch
reproduzierbar, keine Modell-Flakiness.

Reproduziert per Direktaufruf gegen den echten Provider (siehe Diagnoseskript,
nicht Teil des Repositorys). Die gesamte bisherige Testsuite hatte diesen
Fehler nie aufgedeckt, weil ausnahmslos alle Tests Test-Doubles verwenden, die
bereits korrekt strukturierte `QueryInterpretation`-Objekte zurückgeben —
niemals den realen Provider durchlaufen. Der bereits vorbereitete WP9B-Live-Smoke-Test
war ebenfalls nie tatsächlich ausgeführt worden (`prepared_not_executed`).
Das ist der exakte Risikofall, den AP12 selbst benennt: "Behaupte keine
allgemeine Modellzuverlässigkeit allein aufgrund bestandener Mocktests."

## Fix

`INTERPRETER_SYSTEM_PROMPT` um einen expliziten Abschnitt ergänzt, der jedes
Top-Level-Feld, den verschachtelten `explicit_facts`-Container und alle
erlaubten Enum-Werte benennt, mit der ausdrücklichen Anweisung, `explicit_facts`
niemals auf die oberste Ebene zu flachen. `INTERPRETER_PROMPT_VERSION` von
`"4"` auf `"5"` erhöht (alle Verwendungsstellen referenzieren die Konstante
symbolisch, keine Hardcodierung).

## Verifikation

- Direkter Live-Aufruf gegen den echten Provider für 5 unterschiedliche,
  reale Anfragen (Schlafplatz mit Alter/Stadtteil, Toilette EN, Essen,
  Out-of-Scope, Akutgefahr) — alle 5 validieren jetzt fehlerfrei gegen
  `QueryInterpretation`.
- `tests/test_interpreter.py` (nutzt `INTERPRETER_SYSTEM_PROMPT` symbolisch,
  keine hartkodierte Prompt-Erwartung): grün.
- Volle Testsuite: grün (siehe Bericht).
- `python -m compileall -q app`: COMPILE_OK.

## Bezug zu AP12

Dieser Fund unterstreicht unmittelbar die AP12-Anforderung nach einem
tatsächlich ausgeführten Live-Smoke-Test des real konfigurierten Modells,
nicht nur bestandenen Mocktests — genau diese Lücke (Live-Runner existiert
bislang nur für die Stufe `interpreter`) wurde beim AP12-Bestandsaudit parallel
als offener Punkt identifiziert.
