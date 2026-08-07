# Fix: Formulator-Fallback ("Diese Angebote passen zu deiner Frage: ...") trat weiterhin häufig auf

## Status

- State: Complete (Root Cause 1 & 2); Residualverhalten dokumentiert, nicht behoben
- Owner: Claude
- Created: 2026-08-05
- Last updated: 2026-08-05

## Befund

Live-Test: „Es passiert noch immer ständig, dass das LLM nicht die Antwort
generiert, sondern Fallback: 'Diese Angebote passen zu deiner Frage:..'
kommt." — trotz der bereits behobenen Token-Limit- und Prompt-Schema-Bugs
aus `fix-live-testing-round-1.md`.

`runtime/logs/interactions.jsonl` zeigte für Formulator-Läufe mit
`formulator_used=true` weiterhin regelmäßig `formulator_fallback_used=true`
mit den Fehlercodes `formulator_contract_violation`,
`formulator_ungrounded_claim`, `formulator_invalid_fact`. Da
`validate_formulation()` **atomar** ist (ein einziger Verstoß verwirft die
gesamte Antwort), reicht ein einziger falsch-positiver Grounding-Check, um
jede sonst korrekte Formulierung auf das statische Template
(`fallback.found`) zurückfallen zu lassen.

Zur Ursachenanalyse wurde ein Reproduktionsskript gegen die echte
Blablador-API (reales Modell `alias-fast`, das aktuell laut `.env.local`
tatsächlich verwendete Modell — `.env` selbst konfiguriert `alias-large`,
wird aber durch `.env.local`s `BLABLADOR_MODEL=alias-fast` überschrieben,
analog zum bereits dokumentierten `BLABLADOR_MAX_TOKENS`-Vorrang aus
`fix-live-testing-round-1.md`) gefahren, mit `validate_formulation`
instrumentiert, um die rohe Modellantwort und den exakten Verstoßort bei
jedem Fehlschlag zu protokollieren.

## Root Cause 1: Fehlende „du"-Anweisung im Formulator-Prompt

`GERMAN_FORMAL_RE` (`app/grounding.py`) lehnt jede deutsche Sie-Form
(„Sie", „Ihnen", „Ihr" usw.) als `formulator_contract_violation` ab — LENA
soll durchgängig informell duzen. Der Formulator-Prompt verlangte bislang
nur „simple informal language", ohne die Anrede selbst zu benennen. Reale
Modellantworten enthielten deshalb regelmäßig „Rufen Sie...",
„Kontaktieren Sie..." und scheiterten atomar an genau dieser Prüfung.

**Fix**: `FORMULATOR_SYSTEM_PROMPT` (`app/formulation.py`) um eine
explizite Zeile ergänzt: „For German specifically, always address the
reader as 'du'/'dich'/'dir'/'dein'; never use the formal 'Sie'/'Ihnen'/
'Ihr' register in any form." `FORMULATOR_PROMPT_VERSION` 6→7.

## Root Cause 2: `TARGET_ASSERTION_RE` verwechselt „men" mit „Menschen"

`TARGET_ASSERTION_RE` (`app/grounding.py`) erkennt Zielgruppen-Behauptungen
im Antworttext (z. B. „für Männer", „for men") und verlangt dafür einen
zitierten `target_group`/`minimum_age`/`maximum_age`/`eligible_gender`/
`access`-Fact. Das Muster nutzte für alle Alternativen ein `\w*`-Suffix
(`\b(?:...|man|men|...)\w*\b`), wodurch das englische Stichwort „men" auch
als *Präfix* innerhalb beliebiger Wörter zündete — insbesondere im
deutschen Wort **„Menschen"** (Personen, keine Geschlechtsangabe).

Live reproduziert: Angebot 25 heißt amtlich „UVO - Umfeldnahe Versorgung
**von Menschen** ohne festen Wohnsitz". Jede Formulierung, die diesen
zitierten Namen (wie vom Prompt gefordert: „Keep proper names ... exactly
as supplied") wortwörtlich wiedergab, löste fälschlich eine unbelegte
Zielgruppenbehauptung aus — unabhängig davon, ob überhaupt etwas über die
Zielgruppe ausgesagt wurde.

Weiterer, bei der Fehlersuche entdeckter Kollisionsfall: dieselbe
`\w*`-Suffix-Regel ließ auch das bare Stichwort **„man"** zünden — im
Deutschen das unpersönliche Pronomen („man kann sich melden…"), keine
Geschlechtsbehauptung. Da die Prüfung sprachunabhängig auf dem
Ausgabetext läuft, hätte jede deutsche Formulierung mit diesem sehr
gebräuchlichen Pronomen ebenfalls grundlos scheitern können.

**Fix**: `mann`/`men` aus der `\w*`-Suffix-Hauptgruppe herausgelöst und als
exakte Wortgrenzen-Alternative behandelt (`\b(?:mann|men)\b`, kein
Präfix-Matching mehr); das bare `man` komplett aus der Regel entfernt (das
englische „men" im Plural bleibt als Geschlechtssignal ausreichend). Alle
anderen, längeren Stämme (`frau`, `frauen`, `männer`, `minderjähr`,
`erwachsen`, `jugendlich`, `woman`, `women`, `minor`, `adult`, `young`
sowie die polnischen/rumänischen/russischen Stämme) bleiben unverändert mit
Suffix-Erweiterung, da sie kollisionsarm sind.

## Nebenfund (gleicher Reproduktionslauf, kleinerer, korrigierter Bug)

Der `_validate_operational_tokens`-Adressencheck verglich bisher, ob die
*offizielle* `ADDRESS`-Fact-Adresse des Angebots im Text vorkommt, statt zu
prüfen, ob die im Text gefundene Adress-artige Zeichenkette selbst in den
zitierten Fakten vorkommt. Dadurch wären Adressen, die legitim aus einem
zitierten `notes`/`opening_hours_raw`-Fact stammen (z. B. „im Tagestreff
OASE, Nürnberger Straße 31" innerhalb von UVOs eigenen Sprechstunden-Notizen
— seit der Übersetzungserweiterung dieser Session zitierfähig, siehe
`fix-untranslated-opening-hours-and-notes.md`), grundlos abgelehnt worden,
sobald der Satz keinen separaten `ADDRESS`-Fact zitierte. Fix: Prüfung
vergleicht jetzt die im Text gefundene Adress-Zeichenkette direkt gegen
alle zitierten Fakten (`_address not in cited`), nicht nur gegen
`ADDRESS`-Typ-Fakten.

## Verifikation

Reproduktionsskript (echte Blablador-API, Modell `alias-fast`, 7 reale
Anfragen über DE/EN/RU, `interaction_logging_enabled=False`):

| Vorher (vor beiden Fixes) | Nachher |
|---|---|
| 2 von 5 Testanfragen erfolgreich | 3 von 7 Testanfragen erfolgreich (erweiterter Satz) |
| „Ich brauche ärztliche Hilfe" (de): `formulator_contract_violation` (Sie-Form) | OK |
| „I need medical help" (en): `formulator_ungrounded_claim` (Menschen-Kollision) | OK |

Neue Regressionstests (`tests/test_formulation.py`):
- `test_prompt_instructs_informal_du_address_for_german`
- `test_offer_name_containing_menschen_is_not_treated_as_target_assertion`
- `test_target_assertion_still_rejects_real_gender_and_age_claims`
  (Sicherstellung, dass „für Männer"/„nur für Erwachsene" weiterhin korrekt
  als unbelegt abgelehnt werden)
- `test_impersonal_pronoun_man_does_not_trigger_target_assertion`

`tests/test_formulation.py::test_versions_prompt_and_health_are_observable`
angepasst: `FORMULATOR_PROMPT_VERSION` „6"→„7".

Volle Testsuite: grün (siehe Ausführungsbericht).

## Residuales, nicht behobenes Verhalten

Im selben Reproduktionslauf traten weitere, seltenere Fallbacks auf, deren
Ursache **keine Regel-/Prompt-Lücke**, sondern eine Zitierdisziplin-Schwäche
des Modells `alias-fast` ist: Das Modell paraphrasiert gelegentlich einen
Fakt (Zielgruppen-Beschreibung, Angebotsname), ohne die zugehörige
`fact_id` in `fact_ids` mitzuführen — genau das verlangt der atomare
Grounding-Validator aber zwingend, um jede Aussage auf einen konkreten,
geprüften Fakt zurückführen zu können. Beispiel: „...bietet Sozialberatung
für Erwachsene..." ohne den zitierten `target_group`-Fact „adults".

Das ist eine bewusste Sicherheitseigenschaft des Systems (lieber ein
korrektes Template als eine unbelegte Behauptung in einem
Referral-System für eine vulnerable Zielgruppe) und keine Regel-Lücke wie
Root Cause 1/2 — eine Lockerung der Zitierpflicht wäre ein bewusster
fachlicher Kompromiss zwischen Antwortquote und Beleg-Strenge und wurde
hier **nicht** vorgenommen. Ebenfalls beobachtet, aber unverändert: eine
„duschen"-Anfrage wird über die `toilet`-Bedarfskategorie beantwortet (es
gibt keine eigene „shower"-Bedarfskategorie); das Modell erkannte korrekt,
dass öffentliche Toiletten keine Duschen sind, und wich auf eine
Kein-Ergebnis-Aussage aus, was der `toilet`-spezifische Struktur-Check
ablehnte. Das ist eine separate, vorbestehende Bedarfs-Modellierungsfrage
und nicht Teil dieses Fixes.

## Offen

Keine neue fachliche Rückfrage. Die Restrate an Fallbacks durch
Zitierdisziplin-Lücken lässt sich nur durch (a) ein leistungsfähigeres
Modell (Kompromiss: höhere Latenz — `alias-large` wurde in dieser Sitzung
gegengetestet und schlug in der Stichprobe sogar häufiger fehl, vermutlich
Timeout-bedingt bei 90s-Zeitlimit) oder (b) eine bewusste Lockerung der
Grounding-Strenge reduzieren; beides sind fachliche Entscheidungen, keine
Bugs.
