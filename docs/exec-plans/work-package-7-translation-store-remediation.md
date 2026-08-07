# Arbeitspaket 7: Begrenzte Reparatur ungültiger Angebotsübersetzungen

## Status

- State: Completed with one bounded residual failure
- Owner: Codex
- Created: 2026-08-02
- Last updated: 2026-08-02

## Objective

Die 15 aktuell faktisch ungültigen Sprachdatensätze des aktiven
26-Angebote-Bestands werden ausschließlich mit dem bestehenden
Übersetzungsprompt und dem konfigurierten Blablador-Modell neu erzeugt. Jeder
Datensatz wird einzeln vor der atomaren Storeübernahme geprüft. Alle übrigen
Übersetzungen, UI-Ressourcen, dynamischen LLM-Stufen, Nutzer-/Sessiondaten,
WFS- und Kurationsdaten bleiben unverändert.

## Acceptance contract

- [x] Vorstatus und 15 Zielpaare sind read-only inventarisiert; 17 Fehler sind
  gegen die beabsichtigten Schutzregeln auf False Positives geprüft.
- [x] Der strukturell identische Checkout-/Paketstore ist vor dem ersten Schreibzugriff
  unter seinem SHA-256 versioniert gesichert.
- [x] Nur die 15 bestätigten aktiven `machine`-Datensätze werden angefragt;
  IDs 1–4, valide, `reviewed`/`rejected` und statische Sprachressourcen bleiben
  unberührt.
- [x] Je Zielpaar höchstens zwei Provideraufrufe; ungültige Antworten werden
  vollständig verworfen und erzeugen keine Teilübernahme.
- [x] Erfolgreiche Datensätze bleiben `machine`, werden `valid` und erhalten
  aktuelle Identität, Promptversion 2, Provider, Modell und Erstellungszeit;
  keine menschlichen Reviewmetadaten werden gesetzt.
- [ ] Checkout- und paketierter Bootstrapstore sind nach Erfolg identisch;
  104/104 aktive Sprachdatensätze sind valide, 0 reviewed, 104 machine.
- [x] Vollständige technische und begrenzte visuelle Plausibilitätsprüfung,
  Regression, Build, sdist→Wheel, Clean-Install, Template-Smoke und Diffprüfung
  bestehen; kein dynamischer Live-Smoke wird ausgeführt.

## Scope

### In scope

- `data/i18n/offer_translations.json` und paketierter Spiegel.
- Kleinste Testanpassung vom bekannten Altfehler- zum bereinigten Inventar.
- Versionierte lokale Sicherung unter `runtime/i18n/backups/`.
- Dieser Ausführungsplan und Abschlussnachweis.

### Out of scope

- UI-/Dialog-/Fallbackübersetzungen und menschliche Reviewstatus.
- Interpreter-, Selector-, Formulator- oder Szenario-Live-Aufrufe.
- Prompt-, Vertrags-, Kurations-, WFS-, Thesis- oder Präsentationsänderungen.
- Linguistische, professionelle oder SAFE-Freigabe.

## Repository review

### Current behavior and data flow

`python -m app.translate_offers generate` lädt ausschließlich die kuratierte
Runtime-KB, baut den Providerpayload aus Zielsprache, `short_description`,
`services` und geschützten Tokens und validiert die JSON-Antwort vor einer
atomaren Gesamtspeicherung. Mit exakt einer Sprache und einer Angebots-ID kann
der vorhandene Pfad ein einzelnes Zielpaar reparieren; ein neuer paralleler
Reparaturloader ist nicht erforderlich.

Die 15 Zielpaare sind `7/en`, `8/en|pl|ro|ru`,
`19.1|19.2|19.3` jeweils `pl|ro|ru` sowie `23/en`. Alle sind `machine` und
faktisch `invalid`. Die übrigen 89 aktiven Maschinenfassungen sind valide.

### Error review

| Ursache | Paare | Fehlercodes | Bewertung |
|---|---:|---:|---|
| Preise `5,00`/`2,50` wurden mit Punkt wiedergegeben | 7/en, 23/en | 4 | echter Verstoß gegen exakte Preise/Tokens |
| Scharni-Serviceumfang 3 Quelle versus 7 Übersetzung | 8 in vier Sprachen | 4 | echte Listen-/Quellabweichung |
| geschützter Organisationsalias `Mobile` verändert | 19.1–19.3 in PL/RO/RU | 9 | echter Eigennamenverstoß |

### Existing structures to reuse

- `_provider_payload()`, `_translate_with_provider()` und `generate()` in
  `app/translate_offers.py`.
- `validate_translation_fields()` und `write_json()` in `app/i18n.py`.
- Schema-2-Modelle in `app/translation_contract.py`.
- Bestehende Policy-/Karten-/Packagingtests.

### Dead-end analysis

| Dead end | Impact | Mitigation |
|---|---|---|
| Ein kombinierter Angebots-/Sprachlauf | würde valide Sprachen desselben Angebots überschreiben | genau ein Paar je CLI-Lauf |
| Validierung lockern | Preise/Aliase könnten unbemerkt driften | Regeln unverändert lassen; Texte neu erzeugen |
| 80-Szenarien-Smoke verwenden | überträgt synthetische Nutzeranfragen außerhalb der Freigabe | ausschließlich Übersetzungs-CLI |
| Store pro Antwort manuell editieren | umgeht Schema, Identität und Atomizität | bestehenden Generator verwenden |
| Unbegrenzter Retry | unkontrollierte Provideraufrufe | orchestriert maximal zwei Versuche je Paar |

## File impact

| File | Action | Reason |
|---|---|---|
| `data/i18n/offer_translations.json` | Modify | 15 gezielt validierte Maschinenfassungen |
| `app/resources/bootstrap/i18n/offer_translations.json` | Modify | identischer Clean-Install-Bootstrap |
| `tests/test_translation_quality.py` | Modify | Zielzustand 104/104 statt bekannter Altfehler |
| dieses Planfile | Create/Update | Audit, Aufrufzahlen und Verifikation |
| `runtime/i18n/backups/<sha>.json` | Create, ignored | exakte lokale Vorher-Sicherung |

## Validation plan

1. SHA-/Backupprüfung und exakte Zielpaarinventur.
2. Maximal zwei Einzelaufrufe pro Zielpaar; Resultat und Versuchszahl nur
   redigiert erfassen.
3. `status`, `validate`, 104er-Inventar, fünf Sprachen und Kartenprüfung.
4. Technische Sichtprüfung nur der neu erzeugten Felder.
5. Fokussierte I18n-/Runtime-/Formulator-/Dialog-/API-/Speechtests.
6. Vollständige Suite, `compileall`, Wheel/sdist, sdist→Wheel, Clean-Install,
   providerfreier Template-Smoke und `git diff --check`.

## Rollback and recovery

Vor dem ersten Generatorlauf werden Checkout- und Paketstore auf Bytegleichheit
und SHA-256 geprüft. Der Checkoutstore wird unter diesem Hash atomar nach
`runtime/i18n/backups/` kopiert und zurückgelesen. Jeder Generatorlauf schreibt
erst nach vollständiger Einzelvalidierung den gesamten Store atomar; ungültige
Antworten verändern ihn nicht. Der Paketspiegel wird erst nach abschließender
Storevalidierung aus demselben validierten Objekt atomar aktualisiert. Die
Sicherung ermöglicht die exakte Wiederherstellung ohne WFS-/Kurationsänderung.

## Progress log

- 2026-08-02 — Review-First-Skill vollständig gelesen; Branch, Commit,
  Arbeitsbaum, Status, Validate, Providerkonfiguration und aktive Pfade geprüft.
- 2026-08-02 — 15 Zielpaare und 17 Fehlercodes feld-/tokenbezogen analysiert;
  keine fehlerhafte Schutzregel festgestellt.
- 2026-08-02 — Ausgangsstore strukturell gleich, aber wegen CRLF/LF nicht
  bytegleich; Checkout-SHA `140d2219…1d55` und Paket-SHA `225a17e4…befe`
  separat atomar gesichert und rückgelesen.
- 2026-08-02 — 17 Provideraufrufe mit `alias-fast`: 15 Erstversuche und zwei
  Zweitversuche. 14 Paare valide übernommen; `23/en` blieb nach zwei
  `translation_integrity_error` unverändert.
- 2026-08-02 — Nur die 14 erwarteten Sprachdatensätze und `generated_at`
  änderten sich; IDs 1–4 und alle übrigen 90 Sprachdatensätze blieben
  unverändert. Checkout-/Paketspiegel anschließend bytegleich unter SHA
  `79d75e37…12a7` atomar gespeichert.
- 2026-08-02 — 438 Tests, Python-Syntax, Wheel/sdist, sdist→Wheel,
  Clean-Install, Template-Smoke und `git diff --check` bestanden.

## Decisions

- Decision: Bestehenden Einzelpaar-Generator orchestrieren, keinen zweiten
  Reparaturpfad implementieren.
- Decision: Preis-, Listen- und Aliasprüfungen bleiben unverändert.
- Decision: Erfolgreiche technische Neugenerierung bleibt immer `machine`.

## Final verification summary

- Store SHA/backup: beide Ausgangsfassungen separat SHA-geprüft gesichert;
  Endspiegel bytegleich.
- Provider calls/retries: 17 insgesamt, 15 Erst- und zwei Zweitversuche;
  keine weiteren Aufrufe.
- Active integrity: 104 active/machine/reviewed=0; 103 valid, 1 invalid
  (`23/en` mit zwei Preis-Tokenfehlern), stale=0.
- Technical plausibility: 14 neue Fassungen mit plausibler Zielschrift,
  identischer Listenstruktur, geschützten Eigennamen und ohne sichtbare
  interne IDs; keine linguistische Freigabe.
- Tests/build/clean install: 438 Tests und alle angeforderten lokalen
  Artefakt-/Smoke-/Diffprüfungen erfolgreich.
- Human language review: nicht durchgeführt und nicht Gegenstand dieses Pakets
