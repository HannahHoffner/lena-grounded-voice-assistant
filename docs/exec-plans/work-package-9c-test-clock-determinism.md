# Arbeitspaket 9C: Zeitunabhängigkeit der Testsuite

## Status

- State: Complete
- Owner: Claude
- Created: 2026-08-04
- Last updated: 2026-08-04

## Objective

Ein Teil der Testsuite band bislang die reale Systemuhr (`datetime.now()`)
statt einer festen `QueryService.clock`. Dadurch hing das Ergebnis mehrerer
Tests von der Tageszeit ab, zu der die Suite lief: Angebote mit
Öffnungszeitenbindung (z. B. `Need.FOOD`) wurden je nach realer Uhrzeit
gefunden oder nicht. Das ist ein reines Testinfrastrukturproblem, kein
fachlicher Fehler — siehe Klarstellung unten. WP9C macht die betroffenen
Tests deterministisch, ohne Anwendungsverhalten zu ändern.

## Klarstellung (vom Nutzer bestätigt, keine erfundene Regel)

Es ist ausdrücklich zulässiges, gewolltes Verhalten, wenn zu einer Anfrage
gerade kein Angebot geöffnet hat und LENA stattdessen allgemein auf die
Öffnungszeiten hinweist (z. B. „montags bis freitags, dann und dann
geöffnet") oder auf zeitlich gebundene Angebote wie den Hilfebus
(Einsatzzeiten), die Standzeit Sonntag am Hauptbahnhof oder die
SAFE-Team-Präsenz dienstags am Schwanenteich verweist. WP9C ändert daher
**nichts** an `CandidateSelector`, Öffnungszeitenlogik oder Formulierung —
das ist korrektes fachliches Verhalten und bleibt unverändert. Der Fehler
liegt ausschließlich darin, dass Tests keine feste Uhrzeit injiziert haben
und deshalb bei unterschiedlicher realer Tageszeit unterschiedliche
Ergebnisse erwarteten.

## Scope

### In scope

- Die sechs identifizierten, real-uhrzeitabhängigen Tests erhalten eine
  eingefrorene `service.clock` (Montag, 10:00 Uhr Europe/Berlin — dieselbe
  Konvention wie bereits in `tests/test_safety.py` verwendet), sodass die
  betroffenen Angebote unabhängig von der realen Ausführungszeit im
  erwarteten Zustand (geöffnet) vorgefunden werden.
- Keine Änderung an `app/`-Code; reine Testdeterminismus-Korrektur.

### Out of scope

- Jede Änderung an Öffnungszeiten-, Kandidaten- oder Formulierungslogik.
- Eine systematische Suite-weite Umstellung auf einen global injizierten
  Clock-Fixture (nur die konkret betroffenen Tests werden korrigiert, um das
  Risiko auf ein Minimum zu begrenzen).
- AP9 (räumliche Auswahl), AP10–12.

## Betroffene Tests

| Datei | Test | Ursache |
|---|---|---|
| `tests/test_api.py` | `test_template_answer_uses_selected_language` | `category="food"`, Template-Antwort setzt geöffnetes Angebot voraus |
| `tests/test_curation.py` | `test_alternative_i_day_need_without_drug_fact_stays_conditional` | Karte `11` nur bei geöffnetem Zustand erwartet |
| `tests/test_formulation.py` | `test_exhausted_request_budget_skips_formulator_and_uses_template` | `Need.FOOD`-Interpretation, Budget-Fallback über Template |
| `tests/test_formulation.py` | `test_tts_rejects_an_older_answer_after_a_new_session_turn` | erster Turn nutzt `Need.FOOD`; siehe zusätzliche Korrektur unten |
| `tests/test_llm_selection.py` | `test_service_passes_only_validated_food_selection_to_formulator` | `Need.FOOD`-Selektion |
| `tests/test_observability.py` | `test_llm_formulator_path_stores_visible_answer_and_sources` | `Need.FOOD`-Interpretation |
| `tests/test_provider_timeouts.py` | `test_formulator_timeout_uses_existing_template_fallback` | `_interpretation_payload()` Default `need="food"` |

Alle sechs Fälle wurden durch direkten Vergleich (eingefrorene vs. reale
Uhrzeit) reproduziert und bestätigt; ein vollständiger Suitelauf mit nur
diesen sechs Tests abgewählt war zu jedem Zeitpunkt grün, was eine
unabhängige, real-uhrzeitbedingte Ursache belegt statt einer Kopplung an
andere Änderungen dieser Session.

## Implementation

Für Tests mit lokal erzeugter `app`-Instanz wird `app.state.service.clock`
direkt vor Testausführung gesetzt (kein Wiederherstellen nötig, da die
Instanz nicht mit anderen Tests geteilt wird). Für den einzigen Fall mit
modulweit geteilter `app`-Fixture (`tests/test_formulation.py`) wird der
ursprüngliche Clock gesichert und in einem `finally`-Block wiederhergestellt,
analog zum bereits bestehenden Muster für `service.blablador`.

## Verification

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Gezielte betroffene Tests (7 Testfunktionen, davon 5 parametrisiert = 15 Fälle) | `python -m pytest tests/test_api.py::test_template_answer_uses_selected_language tests/test_curation.py::test_alternative_i_day_need_without_drug_fact_stays_conditional tests/test_formulation.py::test_exhausted_request_budget_skips_formulator_and_uses_template tests/test_formulation.py::test_tts_rejects_an_older_answer_after_a_new_session_turn tests/test_llm_selection.py::test_service_passes_only_validated_food_selection_to_formulator tests/test_observability.py::test_llm_formulator_path_stores_visible_answer_and_sources tests/test_provider_timeouts.py::test_formulator_timeout_uses_existing_template_fallback -q` | 15/15 bestanden |
| Volle Suite, ohne Deselektion | `python -m pytest -q` | 100 % grün, keine Deselektion mehr nötig |
| Compile | `python -m compileall -q app tests` | COMPILE_OK |

## Notes

Diese Korrektur betrifft ausschließlich die sechs oben genannten Tests. Falls
künftig weitere Tests mit Angeboten arbeiten, die eine Öffnungszeitenbindung
haben, ohne die Uhr einzufrieren, gilt dieselbe Ursache und derselbe
Lösungsweg.

### Zusätzlich gefundene, nicht uhrzeitbedingte Ursache in einem der sechs Tests

Beim Einfrieren der Uhr blieb `test_tts_rejects_an_older_answer_after_a_new_session_turn`
weiterhin rot. Ursache war nicht die Uhrzeit, sondern zwei voneinander
unabhängige Effekte, die beide erst durch die genauere Prüfung sichtbar
wurden:

1. Der ursprüngliche erste Turn-Text „Ich bringe mich jetzt um." ist ein
   vollständiger Satz mit Person, Handlung und unmittelbarem Zeitbezug und
   löst seit der Umstellung „auf bestätigenden Dialog" (WP9A-Folgeänderung
   in `app/service.py`) den Preflight-Safety-Dialog aus, statt wie zuvor vom
   Test-Double als `Need.FOOD` interpretiert zu werden. Das ist korrektes
   Safety-Verhalten (Safety hat Vorrang), aber der Testtext kollidierte
   ungewollt mit der Safety-Schicht. Behoben durch einen fachlich neutralen
   Ersatztext („Ich habe Hunger.") ohne Personen-/Handlungs-/Zeitbezug.
2. Unabhängig davon liefern `Need.FOOD` und `Need.ADVICE` im aktuellen
   Katalog dieselbe Mehrfachtreffer-Vorlage mit identischer Organisations-
   aufzählung (Caritasverband, Bahnhofsmission, Diakonisches Werk, Leipziger
   Oase), wodurch beide Turns denselben Antworttext erhielten und die
   eigentliche Testaussage (unterschiedliche Antworten je Turn) nicht mehr
   geprüft wurde. Behoben durch Wechsel des zweiten Turns auf `Need.SLEEP`,
   dessen Vorlage nachweislich abweicht.

Beide Korrekturen ändern ausschließlich Testtexte/-bedarfe, keine
Anwendungslogik.
