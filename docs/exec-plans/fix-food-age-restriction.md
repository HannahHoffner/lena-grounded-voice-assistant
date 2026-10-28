# Fix: Essensausgabe darf nicht altersbeschränkt sein

## Status

- State: Complete
- Arbeitsbereich: Repository-Wartung
- Created: 2026-08-04
- Last updated: 2026-08-04

## Befund

Live-Test: Die Essensausgabe der Streetwork-Teams am Schwanenteich (Angebot
14, Diakonisches Werk, dienstags 17–18 Uhr) wurde bei einer Essensfrage nie
genannt, auch nicht auf explizite Nachfrage. Ursache: Angebot 14 trägt
`minimum_age: 18` (vom gesamten „Streetwork Erwachsene"-Angebotstyp geerbt,
der auch Beratung umfasst) — ohne bekanntes Alter landete es in
`conditional_candidates` statt `selectable_candidates`, und es existiert
weder ein Alias „Schwanenteich" noch ein Dialogmechanismus, der bei einer
reinen Essensfrage nach dem Alter fragt.

## Fachliche Klärung (Nutzer)

„Die Altersgrenze ist so gemeint, dass nur Leute bis einschließlich 26 das
Angebot des Jugendstreetworks annehmen dürfen. Essensausgaben sind aber für
alle, und die Leute dort würden auch jungen Personen helfen oder sie weiter
verweisen." Die Alters-/Zielgruppengrenzen (`minimum_age`, `maximum_age`)
gelten für die institutionelle Zuständigkeit (Beratung, Fallzuordnung), nicht
für die Essens-/Kleiderausgabe selbst.

## Fix

`app/candidates.py`: Für `need == Need.FOOD` werden die
`minimum_age`/`maximum_age`-Prüfungen vollständig übersprungen (kein
`AGE_NOT_ESTABLISHED`, kein `AGE_OUTSIDE_RANGE`); alle anderen
Eignungsregeln (Geschlecht, expliziter Drogenkonsum, Zeitfenster usw.)
bleiben unverändert. Neuer `RuleCode.FOOD_AGE_UNRESTRICTED` dokumentiert die
Ausnahme in `applied_rules` für Nachvollziehbarkeit. Betrifft alle Angebote
mit `food`-Bedarf und Altersgrenze (7, 8, 11, 12, 14, 18, 23) — für
`Need.ADVICE`/`Need.SLEEP`/etc. bleibt die Altersprüfung unverändert
bestehen.

`Need.DRINKING_WATER` wurde bewusst **nicht** mit einbezogen, da die
Klärung des Nutzers sich ausdrücklich nur auf „Essensausgaben" bezog.

## Verification

- Live: Angebot 14 erscheint jetzt für eine Essensfrage (dienstags, vor
  18 Uhr) direkt in `selectable_candidates`, nicht mehr `conditional`.
- Angebot 11 bleibt weiterhin `conditional` — aus einem anderen, unveränderten
  Grund (`requires_explicit_drug_use`), bestätigt die gezielte statt
  pauschale Wirkung des Fixes.
- Neuer Regressionstest `test_food_need_ignores_age_restriction_even_when_offer_requires_adults`
  (`tests/test_candidates.py`): Angebot 14 ist für `Need.FOOD` sofort
  auswählbar, für `Need.ADVICE` bleibt es unverändert altersbedingt
  `conditional`.
- Ein bestehender Test (`test_service_passes_only_validated_food_selection_to_formulator`)
  musste angepasst werden: Die Reihenfolge im Formulator-Ergebnis folgt der
  kanonischen Prioritäts-/ID-Sortierung (`order_social_results`), nicht der
  vom Test-Double absichtlich umgekehrten Selector-Reihenfolge — das war
  schon vor diesem Fix so, wurde aber erst durch das neu hinzukommende,
  gleich priorisierte Angebot 18 sichtbar.
- Volle Testsuite: grün (siehe Bericht). `compileall`: OK.

## Offen

Die separate Rückfrage zu unübersetzten „Opening hours"/„Notes"-Feldern bei
Sozialangeboten (dokumentierte, bewusste Design-Entscheidung laut
`docs/data-flow.md`) ist noch unbeantwortet.
