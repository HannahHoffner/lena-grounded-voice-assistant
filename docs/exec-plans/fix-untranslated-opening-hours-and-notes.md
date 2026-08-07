# Fix: „Opening hours"/„Notes" bei Sozialangeboten blieben unübersetzt

## Status

- State: Complete
- Owner: Claude
- Created: 2026-08-05
- Last updated: 2026-08-05

## Befund

Live-Test: Eine englischsprachige Karte zu UVO (Angebot 23, Kategorie
medical help) zeigte die Abschnitte „Opening hours" und „Important notes"
vollständig auf Deutsch, während `short_description`/`services` bereits
übersetzt waren. Ursache: `opening_hours_raw`/`notes` waren laut
`docs/data-flow.md` bewusst **nicht** Teil von `TRANSLATABLE_FIELDS` —
begründet mit der höheren Freitext-Varianz gegenüber den Toiletten-Feldern.
Bei genauerer Betrachtung überwiegt der Schaden (offensichtlich
unvollständig übersetzte Karte) den ursprünglichen Grund, zumal der
Angebotskatalog klein und stabil ist (26 Angebote).

## Fachliche Klärung (Nutzer)

„Das ist eine Karte zu medical help. auf englisch. Das ist nicht in
Ordnung. Finde die beste Lösung. Da die Angebote begrenzt sind, wäre es
auch in Ordnung, für jede Sprache feste Übersetzungen der Karten zu haben."
— explizite Freigabe, `opening_hours_raw`/`notes` in das bestehende
LLM-Übersetzungssystem (WP7) aufzunehmen statt eine neue Sonderlösung zu
bauen, da das System bereits genau für „feste Übersetzungen pro
Angebot/Sprache" ausgelegt ist (`TranslationRecord`, `provider=blablador`,
`status=machine`).

## Fix

### Schema (`app/translation_contract.py`)

- `TRANSLATION_STORE_VERSION` `"2"` → `"3"`, `TRANSLATION_PROMPT_VERSION`
  `"3"` → `"4"`.
- `TRANSLATABLE_FIELDS` erweitert um `opening_hours_raw`, `notes`.
- `TranslationFields` bekommt `opening_hours_raw: list[str]`,
  `notes: list[str]` (analog zu `services`, Listen-Feld).
- `ReviewPackageItem` bekommt die passenden
  `source_opening_hours_raw`/`source_notes`/`translated_opening_hours_raw`/
  `translated_notes`-Felder für den menschlichen Review-Export.

### Hash-Komposition (`app/i18n.py`)

- `source_translation_hash()` hasht jetzt alle vier übersetzbaren Felder.
- `operational_facts_hash()` hasht die beiden Felder **nicht mehr** (sie
  sind kein unveränderlicher Fakt mehr, sondern übersetzbarer Inhalt).
- `validate_translation_fields()` um Längen-Konsistenzprüfungen für die
  beiden neuen Listenfelder erweitert.

### Migration (`app/i18n.py::migrate_schema_two_store`)

Neue Funktion nach dem Vorbild der bestehenden `migrate_legacy_store`
(Schema 1→2): alle 104 bestehenden Records (26 Angebote × 4 Sprachen)
werden auf Schema 3 gehoben, dabei `opening_hours_raw=[]`/`notes=[]`
gesetzt (keine Vorübersetzung vorhanden) und der Record hart auf
`STALE`/„nicht human-reviewed" gesetzt — bewusst keine automatische
Review-Freigabe erfunden. `load_translation_catalog()` erkennt
`stored_schema_version == "2"` und ruft die neue Migration auf.

### Platzhalterschutz (`app/translation_tokens.py`)

`mask_translation_fields()`/`restore_translation_fields()` waren fest auf
`services` als einziges Listenfeld verdrahtet. Verallgemeinert auf
`_LIST_FIELDS = ("services", "opening_hours_raw", "notes")`, damit
Telefonnummern/Uhrzeiten/Preise auch in den neuen Feldern vor der
LLM-Übersetzung geschützt und danach unverändert wiederhergestellt werden
— exakt der bereits etablierte Mechanismus, nur auf mehr Felder angewandt.

### Übersetzungs-CLI (`app/translate_offers.py`)

- `translation_system_prompt()` nennt jetzt alle vier Felder mit exakter
  JSON-Form.
- `_copy_fields()` (Test-Provider `copy`) kopiert alle vier Felder.
- `export_review()`/`import_review()` um die neuen Felder erweitert;
  `visible_operational_facts` verliert den Schlüssel `opening_hours`, da er
  jetzt editierbarer Übersetzungsinhalt statt reiner Kontext ist.
- Ein vorbestehender Bug beim `migrate`-Subcommand behoben: `"to_schema"`
  im Log war hart auf `"2"` kodiert statt die tatsächliche
  `catalog.store.schema_version` zu verwenden.

### Formulator-Konsistenz (`app/formulation.py`, `app/service.py`)

Zusätzlich entdeckter, vorbestehender Bug: `_facts_for_offer()` (die Fakten,
die dem Formulator als Beleg für die Kartenangaben übergeben werden) las
`short_description`/`services`/`opening_hours_raw`/`notes` immer aus dem
**deutschen Original-Angebot**, nicht aus der bereits lokalisierten Karte —
auch für `short_description`/`services`, die schon vor diesem Fix übersetzt
wurden. Das bedeutet, der Formulator hat bislang immer auf deutschen
Fakten formuliert, selbst wenn die angezeigte Karte englisch war (nur durch
die Grounding-Validierung gegen die übersetzte Karte nicht aufgefallen).

Fix: `_facts_for_offer`/`_facts_for_answer_type` nehmen optional eine
bereits lokalisierte `OfferCard` entgegen und lesen alle vier Felder
daraus, falls vorhanden. `build_formulator_evidence()` bekommt
`translation_catalog`/`translation_policy` und ruft intern
`localize_offer_card()` pro Angebot auf. `service.py` reicht die im
`LenaService` bereits vorhandenen `self.translation_catalog`/
`self.translation_policy` durch.

### Reale Migration + Neugenerierung

Die Feld-Verschiebung ändert `source_translation_hash` für **alle** 104
bestehenden Records, wodurch das bestehende Alles-oder-nichts-Fallback
(fehlt eines der Felder, fällt die ganze Karte auf Deutsch zurück) sofort
alle Karten wieder auf Deutsch zurückgeworfen hätte. Deshalb nicht nur
migriert, sondern real neu generiert:

```
python -m app.translate_offers migrate
python -m app.translate_offers generate --provider blablador --force
```

104 reale LLM-Aufrufe, 0 Fehler. `data/i18n/offer_translations.json` neu
geschrieben; `app/resources/bootstrap/i18n/offer_translations.json`
(gepackte Kopie) byte-identisch synchronisiert.

## Verification

- `python -m pytest tests/test_translation_quality.py
  tests/test_translation_tokens.py tests/test_curation.py -q` — grün nach
  Anpassung an das neue Schema:
  - `tests/test_translation_tokens.py`: `TranslationFields(...)`-Konstruktionen
    um `opening_hours_raw=`/`notes=` ergänzt.
  - `tests/test_translation_quality.py`: Feldmengen-Assertions erweitert;
    `test_all_runtime_cards_preserve_names_and_operational_facts` prüft nur
    noch Längen-Erhalt statt exakter Gleichheit (die Felder sind jetzt
    übersetzt); erwartete `schema_version` von „2" auf „3" korrigiert;
    `test_regenerated_records_remain_machine_without_human_review_metadata`
    komplett neu geschrieben (alte Version hing an einer historischen,
    jetzt bedeutungslosen Momentaufnahme von 14 spezifischen
    Offer/Sprache-Kombinationen aus einer früheren Repair-Aktion).
  - `tests/test_curation.py`:
    `test_scharni_runtime_override_preserves_immutable_wfs_address` an
    tatsächlichen (verifizierten) LLM-Wortlaut angepasst.
    `test_card_translation_cannot_override_curated_operational_facts`
    umbenannt zu `test_card_translation_cannot_override_curated_identity_facts`
    und umgeschrieben: `address`/`phone_numbers`/`standzeiten_raw` bleiben
    exakt erhalten (unveränderliche Fakten); `opening_hours_raw` ist jetzt
    absichtlich übersetzt (Länge erhalten, Inhalt anders), alle
    `HH:MM`-Zeitangaben aus dem deutschen Original müssen aber wortgleich
    in der Übersetzung wiederzufinden sein.
- Volle Testsuite (`python -m pytest -q`): grün, keine Fehler.
- `python -m compileall -q app tests`: OK.
- `git diff --check`: keine echten Whitespace-Fehler (nur harmlose
  CRLF/LF-Hinweise durch bestehende `.gitattributes`-Konfiguration).
- Live-Verifikation ausstehend beim Nutzer: erneuter Aufruf der UVO-Karte
  auf Englisch sollte jetzt übersetzte „Opening hours"/„Important notes"
  zeigen.

## Offen

Keine offenen fachlichen Fragen zu diesem Fix. Bei zukünftigen
Datenänderungen an `opening_hours_raw`/`notes` (z. B. WFS-Sync) werden die
betroffenen Records automatisch `STALE` (bestehender Mechanismus über
`source_translation_hash`) und müssen erneut mit
`python -m app.translate_offers generate --provider blablador` übersetzt
werden.
