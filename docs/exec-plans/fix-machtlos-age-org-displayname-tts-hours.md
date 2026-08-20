# Fix: MachtLos-Altersscope, rohe Organisations-Namen, TTS-Uhrzeitspannen

## Status

- State: Complete
- Owner: Claude
- Created: 2026-08-14
- Last updated: 2026-08-14

## Befund 1 – MachtLos e. V. für altersunbekannte Hunger-Anfragen

Live gemeldet: "ich habe Hunger" ohne Altersangabe empfahl u. a. MachtLos e. V.,
ein Jugendstreetwork-Angebot ("unter 27", `maximum_age: 26`). Ursache:
[`app/candidates.py`](../../app/candidates.py) überspringt für `need ==
Need.FOOD` die komplette Alters-Eignungsprüfung (`RuleCode
.FOOD_AGE_UNRESTRICTED`), begründet in
[fix-food-age-restriction.md](fix-food-age-restriction.md) (04.08.2026):
"Essensausgaben sind aber für alle […] die Alters-/Zielgruppengrenzen gelten
für die institutionelle Zuständigkeit, nicht für die Essens-/Kleiderausgabe
selbst." Dieser frühere Fix listete Angebot 18 (MachtLos) explizit als
betroffen.

## Fachliche Klärung (Nutzer, 14.08.2026)

Die frühere Klärung gilt weiterhin für Erwachsenen-Angebote mit
`minimum_age` (Diakonie/Schwanenteich u. a.), nicht aber für MachtLos: ein
Jugendangebot (Obergrenze `maximum_age`) darf nicht an altersunbekannte
allgemeine Anfragen ausgespielt werden.

## Fix 1

`app/candidates.py`: Die `FOOD_AGE_UNRESTRICTED`-Ausnahme gilt jetzt nur noch
für `minimum_age` (unverändert für Angebote 11/12/14). `maximum_age` wird für
**jeden** Bedarf inklusive `FOOD` normal geprüft — bei unbekanntem Alter wird
das Angebot `conditional_candidate` statt automatisch auswählbar. `Need.FOOD`
kennt keinen Klärungsdialog (`choose_dialog()` in `app/dialogue_flow.py`), das
Angebot verschwindet also still aus der Auswahl statt eine Rückfrage
auszulösen. Regressionstest ergänzt/angepasst in `tests/test_llm_selection.py`
(kanonische `order_social_results`-Reihenfolge statt der zufällig
übereinstimmenden `selectable_candidates`-Reihenfolge, durch die veränderte
Kandidatenmenge sichtbar geworden).

## Befund 2 – rohe Organisations-Rechtsnamen statt kuratierter Kurznamen

Live gemeldet: "Caritasverband Leipzig e. V. Ökumenische Bahnhofsmission"
statt "Bahnhofsmission Leipzig". Ursache:
[`app/curation.py`](../../app/curation.py)`::project_runtime_offers()`
verwendete ausschließlich den offer-eigenen `display_name` (nur 5 von 30
Angeboten gesetzt); der kuratierte `display_name` der Organisation (alle 16
Organisationen haben einen) wurde nirgends in der Runtime gelesen — 25 von 30
Angeboten zeigten daher den vollen WFS-Rechtsnamen.

## Fix 2

`project_runtime_offers()` fällt jetzt auf `organizations[offer.
organization_id].display_name` zurück, wenn das Angebot selbst keinen
eigenen `display_name` hat. Zusätzlich bekam Angebot 21 (SZL Suchtzentrum,
`place_type: help_bus`) einen eigenen `display_name: "Hilfebus"` in
`app/resources/bootstrap/curation/social_offers.json` — der reine
Organisationsname "SZL Suchtzentrum" hätte sonst den in Dialogtexten und
Priority-Rules durchgängig verwendeten Begriff "Hilfebus" verdeckt.

**Nebenwirkung:** `operational_facts_hash` (`app/i18n.py`) bindet
`display_name` ein; jede Änderung an `social_offers.json` ändert außerdem
`catalog_content_hash` (SHA-256 der gesamten Datei) und invalidiert dadurch
den **kompletten** Übersetzungsbestand (26 Angebote × 4 Sprachen), nicht nur
die 25 direkt betroffenen. Übersetzungsstore wurde live neu erzeugt:
`python -m app.translate_offers generate --provider blablador`. Mit dem
Standardmodell (`BLABLADOR_MODEL=alias-large`, `translate_offers.py` liest
anders als Interpreter/Selector/Formulator keine Stufenmodell-Overrides)
blieb der Lauf nach >30 Minuten ohne jede Ausgabe hängen — konsistent mit dem
bereits dokumentierten alias-large-Problem (siehe `.env.example`). Mit
`BLABLADOR_MODEL=alias-fast` (nur für diesen einen Lauf per Env-Override,
`.env`/`.env.local` unverändert) liefen alle 104 Kombinationen in wenigen
Minuten durch: `{"generated": 104, "failed": 0}`. Der neu erzeugte
Übersetzungsbestand wurde von `data/i18n/offer_translations.json` nach
`app/resources/bootstrap/i18n/offer_translations.json` gespiegelt (von
`test_schema_two_migration_is_idempotent_and_packaged_copy_matches_checkout`
als Invariante geprüft).

## Befund 3 – TTS liest Uhrzeitspannen ziffernweise

Live gemeldet: "12-13:30 Uhr" wird als "eins zwei bis eins drei dreißig Uhr"
statt als Uhrzeit vorgelesen (Edge-Neural-Stimmen).

## Fix 3

`app/speech.py::normalize_tts_text()` löst kompakte Zahl-Trennzeichen-Zahl-
Muster vor der Synthese in Zahl + gesprochenes Trennwort + Zahl auf ("12 bis
13:30 Uhr"), analog zur bestehenden Notrufnummer-Normalisierung.
Sprachabhängiges Trennwort (`bis`/`to`/`do`/`până la`/`до`). Adressen mit
Wort-Bindestrichen (z. B. "Willy-Brandt-Platz") bleiben unberührt, da nur
Ziffer-Trennzeichen-Ziffer matcht. Keine akustische Hörprüfung durchgeführt
(wie bei der Notrufnummer bereits dokumentiert).

**Nachtrag (14.08.2026, live erneut gemeldet als weiterhin falsch):** Die
erste Fassung matchte nur den ASCII-Bindestrich (U+002D) und griff dadurch
beim häufigsten Fall -- Formulator-Antworten -- nie: der Formulator schreibt
Zeitspannen live reproduziert mit geschütztem Halbgeviertstrich (U+2011,
z. B. "09:00‑10:00"), einzelne Quelldaten nutzen einen Halbgeviertstrich
(U+2013, "06:00 – 22:00"). Zeichenklasse um alle gängigen Bindestrich-/
Gedankenstrich-Varianten erweitert (U+002D, U+2010–U+2014, U+2212). Mit dem
tatsächlichen, live erzeugten Formulatortext (`Willy‑Brandt‑Platz`,
`09:00‑18:00` usw., aus dem LLM-Antwort-Check weiter oben) verifiziert:
alle Zeitspannen werden jetzt aufgelöst, Adressen mit Wort-Halbgeviertstrich
("Willy‑Brandt‑Platz") bleiben unveraendert, da nur Ziffer-Trennzeichen-
Ziffer matcht.

## Verification

- Manuelle Prüfung: MachtLos erscheint nicht mehr in `selectable_candidates`
  bei altersunbekannter FOOD-Anfrage (`conditional_candidates`), Diakonie
  (Angebot 14, `minimum_age`) bleibt unverändert sofort auswählbar.
- Manuelle Prüfung: `offer.display_name` für alle vormals betroffenen
  Angebote (22, 18, 24, 9, 10, 21, …) zeigt jetzt den kuratierten Kurznamen.
- Manuelle Prüfung: `normalize_tts_text()` löst mehrere reale
  Uhrzeit-/Adressbeispiele korrekt auf (Adresse bleibt unverändert).
- Volle Testsuite: 697/697 grün. `compileall`: OK.

## Nachtrag – STT lieferte HTTP 503, Statusmeldung blitzte nur kurz auf

Live gemeldet (14.08.2026): Sprachaufnahme zeigte kurz "Ich verarbeite deine
Sprache." und dann nichts mehr.

**Ursache 1 (Backend):** `SPEECH_TRANSCRIPTION_MODEL` stand standardmäßig auf
`whisper-large-v3` ([config.py](../../app/config.py),
[.env.example](../../.env.example),
[docs/configuration.md](../configuration.md)) — kein registriertes Modell bei
Blablador (`404 {"error":"No backend for model whisper-large-v3"}`, live
geprüft). `GET /v1/models` listet stattdessen `faster-whisper-large-v3`.
Default korrigiert; mit synthetischem Audio 200 OK und valides (leeres, da
kein Sprachinhalt) Transkript live bestätigt.

**Ursache 2 (Frontend, unabhängig davon und vermutlich bereits vorher
bestehend):** In [app.js](../../app/static/app.js) setzten drei
Fehlerpfade (`recognition.onerror`, der `catch`-Block von
`transcribeRecordedAudio`, der `catch`-Block von `startServerRecording`) die
Statusmeldung (z. B. "Versuch es noch mal.") und riefen danach sofort
`updateVoiceStatusReady()` auf, nachdem sie zuvor `state
.keepRecognizedStatus = false` gesetzt hatten. Da `updateVoiceStatusReady()`
den Statustext nur dann *nicht* überschreibt, wenn `keepRecognizedStatus`
`true` ist, wurde die gerade gesetzte Fehlermeldung im selben synchronen
Zug wieder durch den generischen "bereit"-Text ersetzt — sichtbar nur als
kurzes Aufblitzen. Alle drei Stellen auf `true` korrigiert (wie im
Erfolgsfall, der das schon richtig macht); die vier bestehenden
Reset-Stellen (`resetView`, `backToSearch`, Sprachwechsel, Aufnahmestart)
bleiben unverändert bei `false`.

Volle Testsuite weiterhin 697/697 grün (`node --check` in dieser Umgebung
nicht verfügbar).

## Offen

- `translate_offers.py` verwendet für alle vier Sprachen weiterhin das
  gemeinsame `BLABLADOR_MODEL` (`alias-large` in `.env`), nicht die für
  Interpreter/Selector/Formulator bereits umgestellten `alias-fast`-Stufen-
  Overrides. Der heutige Lauf zeigt dasselbe Zuverlässigkeitsproblem wie
  bereits für den Formulator dokumentiert. Noch nicht entschieden: soll
  `translate_offers.py` einen eigenen Modell-Override bekommen (z. B.
  `BLABLADOR_TRANSLATION_MODEL`) oder `BLABLADOR_MODEL` selbst auf
  `alias-fast` umgestellt werden?
