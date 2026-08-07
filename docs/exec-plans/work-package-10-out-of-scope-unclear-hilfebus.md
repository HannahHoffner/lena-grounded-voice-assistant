# Arbeitspaket 10 (Methodikkapitel-Nummerierung): Out-of-Scope, Unklarheit und Hilfebus

## Status

- State: Complete
- Owner: Claude
- Created: 2026-08-04
- Last updated: 2026-08-04

## Einordnung

Nicht zu verwechseln mit den Codex-eigenen WP9A/9B/9C-Dateien. Dieses Dokument
setzt das inhaltliche „Arbeitspaket 10: Out-of-Scope, Unklarheit und Hilfebus"
aus dem ursprünglichen Methodikkapitel-Auftrag um:

> Bei klar fachfremder Anfrage: keine freie Weltwissensantwort geben, die
> geschlossene Domäne knapp erklären, die unterstützten Hilfebereiche nennen.
> [...] Bei unklarer, aber möglicherweise fachlich relevanter Anfrage:
> höchstens eine gezielte Rückfrage stellen, in einfacher Sprache, Antwort
> über Text/Sprache/Button ermöglichen, bei weiterhin unklarer Zuständigkeit
> auf den Hilfebus verweisen. Hilfebusdaten müssen aus dem freigegebenen
> Datensatz stammen; Telefonnummer, Einsatzzeiten und Funktion dürfen nicht
> im Prompt dupliziert oder frei ergänzt werden.

## Audit-Ergebnis (vor dieser Änderung)

Ein Read-only-Audit ergab vier separat prüfbare Anforderungen:

1. **Keine freie Weltwissensantwort bei Out-of-Scope** — vollständig erfüllt.
   `ScopeStatus.OUT_OF_SCOPE` erzwingt `need=unknown` (Vertragsvalidierung),
   jede LLM-Formulierung durchläuft Grounding-Zwang (feste Ablehnungsformel +
   ≥3 von 6 Domänenbegriffen, `app/grounding.py::_validate_policy_answer`).
   **Content-Lücke gefunden:** der statische Fallback-Text nannte nur 4 von 6
   Bereichen (Wasser und öffentliche Toiletten fehlten).
2. **Höchstens eine Rückfrage bei unklarer Anfrage** — teilweise erfüllt. Für
   `need=general_help` (und `sleep`/Organisations-Alias) sauber umgesetzt
   (`DialogType.GENERAL_NEED`, `max_attempts=1`). **Lücke gefunden:** für
   `need=unknown` mit `scope_status=unclear` — laut Interpreter-Prompt genau
   der Fall „unverständlich/unklar" — löste `choose_dialog()` keinen Dialog
   aus; die Anfrage landete in der generischen No-Results-Antwort ohne
   Rückfrage.
3. **Hilfebus-Verweis bei fortbestehender Unklarheit** — überwiegend erfüllt.
   Ein dedizierter, testabgesicherter Eskalationspfad existiert
   (`_hilfebus_response`, `AnswerType.AMBIGUOUS_HELP_FALLBACK`). Gleiche
   Lücke wie Punkt 2: für `need=unknown` ohne Alias nie erreichbar, da an
   einen bereits offenen Dialog gebunden.
4. **Keine Prompt-Duplikation der Hilfebus-Fakten** — vollständig erfüllt.
   Telefon/Zeiten laufen ausschließlich als strukturierte, faktentyp-
   beschränkte Evidence durch zeichengenaues Grounding.

Der Nutzer hat entschieden: Bucket-A-Fund (Content-Lücke) direkt beheben,
Bucket-B-Fund (Trigger-Lücke) durch Erweiterung der bestehenden, bereits
getesteten Infrastruktur schließen (keine neue Dialoglogik nötig).

## Acceptance contract

- [x] `fallback.out_of_scope` nennt in allen 5 Sprachen (DE/EN/PL/RO/RU) alle
  6 unterstützten Bereiche (Essen, Wasser, Schlafen, Medizin, Beratung,
  öffentliche Toiletten).
- [x] `choose_dialog()` öffnet den bestehenden `general_need`-Dialog jetzt
  auch für `need=unknown` (bislang nur `need=general_help`), mit
  `originating_need=general_help` normalisiert — reuse der bestehenden,
  bereits getesteten Ein-Frage- und Hilfebus-Eskalationslogik ohne neue
  Dialoglogik.
- [x] `ScopeStatus.OUT_OF_SCOPE` bleibt unverändert vorrangig (früherer
  Return in `app/service.py` vor `choose_dialog()`); die Erweiterung betrifft
  ausschließlich Fälle, die diesen Check bereits passiert haben.
- [x] Freitext-Antworten auf den neuen Dialog, die weiterhin unklar bleiben,
  landen wie beim bestehenden `general_help`-Fall beim Hilfebus statt in
  einer erneuten Rückfrage oder einem Loop.
- [x] Bestehende Tests, die `need=unknown` mit `OUT_OF_SCOPE`- oder
  Akutrisiko-Status oder mit Organisations-Alias verwenden, bleiben
  unverändert grün (diese Zweige liegen vor bzw. neben dem geänderten Code).

## Implementation

**Bucket A** (`app/resources/bootstrap/i18n/application_texts.json`):
`fallback.out_of_scope` in allen 5 Sprachen um die fehlenden Domänen ergänzt,
Wortwahl an den bereits vorhandenen `SUPPORTED_DOMAIN_STEMS` in
`app/grounding.py` ausgerichtet.

**Bucket B** (`app/dialogue_flow.py::choose_dialog`): letzte Bedingung von
`if interpretation.need == Need.GENERAL_HELP` auf
`if interpretation.need in {Need.GENERAL_HELP, Need.UNKNOWN}` erweitert;
`new_dialog(..., need=Need.GENERAL_HELP, ...)` bleibt unverändert (Need.UNKNOWN
wird auf denselben Platzhalter-Originating-Need normalisiert, den auch
`is_clear_topic_change()` und `merge_dialog_facts()` bereits für beide Werte
identisch behandeln — keine neue Sonderbehandlung nötig). Kein Eingriff in
`app/service.py`: der bestehende `if dialog:`-Block (Rückfrage öffnen) und die
bestehende `still_unclear`-Hilfebus-Eskalation (bereits `{Need.UNKNOWN,
Need.GENERAL_HELP}`-übergreifend) griffen bereits korrekt, sobald
`choose_dialog()` ein `DialogState`-Objekt zurückgibt.

## Verification

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Gezielte neue/angepasste Tests | `tests/test_dialogue.py`, `tests/test_formulation.py::test_out_of_scope_fallback_text_names_all_six_supported_domains` | grün |
| Volle Suite | `python -m pytest -q` | siehe Bericht |
| Compile | `python -m compileall -q app tests` | COMPILE_OK |
