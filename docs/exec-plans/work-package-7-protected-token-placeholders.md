# Arbeitspaket 7: Platzhalterschutz für operative Übersetzungstokens

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-02
- Last updated: 2026-08-02

## Objective

Der bestehende Angebotsübersetzungspfad maskiert alle bereits kanonisch
erkannten operativen Tokens vor dem Provideraufruf mit requestlokalen,
ID-freien Platzhaltern. Providerantworten werden nur nach vollständiger,
feldgebundener Platzhalterprüfung, exakter Wiederherstellung und unveränderter
Integritätsprüfung übernommen. Nach bestandenen lokalen Tests wird höchstens
ein realer Providerrequest ausschließlich für `23/en` ausgeführt.

## Acceptance contract

- [x] Eine kanonische Tokenklassifikation speist Validierung und Maskierung;
  die bestehende Integritätsprüfung wird nicht gelockert.
- [x] Jedes Tokenvorkommen erhält einen deterministischen, requestlokalen
  Platzhalter ohne Angebots-ID; Anzahl, Bekanntheit und Feldposition werden
  vor Wiederherstellung geprüft.
- [x] Fehlende, veränderte, doppelte oder unbekannte Platzhalter sowie
  Schema-, Listen- oder Restorationsfehler verwerfen die gesamte Antwort mit
  redigiertem Fehlercode.
- [x] Lokale Test-Doubles decken Preise, Kontakte, Zeiten, URLs, E-Mail,
  Eigennamen, Aliase, Adresse, Mehrfachvorkommen, Listen, die deutsche Quelle
  und alle vier Übersetzungszielsprachen
  ab; Dry-Run schreibt nichts.
- [x] Die vorhandenen 103 validen Datensätze bleiben vor dem Liveaufruf valide
  und werden nicht regeneriert.
- [x] Erst nach den lokalen Tests erfolgt höchstens ein Blablador-Aufruf für
  `23/en`; alle anderen Übersetzungen bleiben byteinhaltlich unverändert.
- [x] Bei Erfolg sind 104 aktive Datensätze technisch valide und weiter
  `machine`; bei Fehlschlag bleibt `23/en` unverändert im deutschen Fallback.
- [x] Vollsuite, Syntax, Packaging, Clean-Install, Template-Smoke und
  `git diff --check` bestehen; kein weiteres Arbeitspaket beginnt.

## Scope

### In scope

- Bestehende operative Tokeninventarisierung und Übersetzungsproviderpfad.
- Ein fokussiertes Platzhaltermodell mit Vor-/Nachverarbeitung.
- Lokale Unit-, Integrations-, Runtime- und Packagingtests.
- Bei lokalen grünen Tests genau ein möglicher Storeaustausch `23/en` und der
  identische paketierte Bootstrapspiegel.
- Bestehende Übersetzungsdokumentation und dieser Ausführungsplan.

### Out of scope

- Abschwächung der Tokenintegrität oder manuelle Reparatur des Textes.
- Änderungen an anderen Übersetzungen, UI-/Dialogressourcen oder Reviewstatus.
- Menschliche Sprachprüfung, dynamischer Live-Smoke und andere LLM-Stufen.
- Toiletten, Infrastruktur, geografische Auswahl, Thesis und Präsentation.

## Repository review

### Current behavior

`app.translate_offers.generate()` lädt die kuratierte Runtime-KB und ruft für
ein Zielpaar `_translate_with_provider()` auf. `_provider_payload()` sendet
aktuell deutsche Klartexte plus ein Klartextinventar geschützter Tokens. Erst
nach der Antwort erkennt `app.i18n.validate_translation_fields()` veränderte
Zahlen-/Preistokens, Eigennamen, Listenlängen, interne IDs und klare
Schriftsystemfehler. Deshalb bleibt `23/en` korrekt ungültig, aber der Provider
erhält keine technische Hilfe zur exakten Beibehaltung von `0,50`-Tokens.

### Relevant architecture and data flow

`OfferRecord` → kanonisches Tokeninventar in `app/i18n.py` → Providerpayload in
`app/translate_offers.py` → striktes `TranslationFields`-Schema →
Integritätsprüfung → `TranslationRecord(machine, valid)` → atomarer Store. Die
Runtime verwendet ungültige Records nicht und fällt auf deutsche Basisfelder
zurück.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Regex- und Eigennameninventar | `app/i18n.py` | In ein fokussiertes kanonisches Tokenmodul extrahieren und weiterverwenden |
| Providerpayload und Parser | `app/translate_offers.py` | Um Maskierung und Restore erweitern; keinen zweiten Providerpfad schaffen |
| Striktes Feldschema | `app/translation_contract.py` | Unverändert vor und nach Restore validieren |
| Atomarer Storewriter | `app/i18n.py::write_json` | Unverändert verwenden |
| Runtime-Fallback | `app/i18n.py::localize_offer_card` | Unverändert erhalten |

### Existing tests and commands

- `tests/test_translation_quality.py` prüft Positivlistenpayload, Dry-Run,
  Status, Karten und Storeidentität.
- `tests/test_provider_timeouts.py` prüft redigierte Providerfehler.
- `python -m app.translate_offers validate` meldet derzeit ausschließlich
  `23/en` mit zwei `protected_token_mismatch`-Fehlern.

### Working tree considerations

Der Arbeitsbaum enthält die freigegebenen, noch nicht committen Änderungen aus
Arbeitspaketen 1–7. Sie werden nicht zurückgesetzt, formatiert oder außerhalb
der oben genannten Dateien verändert. Checkout- und Bootstrapstore sind vor
diesem Paket identisch; die 103 validen Records sind Nutzerdaten des aktuellen
Arbeitsstands und bleiben erhalten.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Integritätsregex lockern | `0,50 → 0.50` wird korrekt erkannt | operative Fakten könnten driften | Endvalidierung unverändert lassen | Negativtest und Vollvalidierung |
| Klartexttokens zusätzlich mitsenden | aktueller Payload macht genau dies | Provider kann sie erneut normalisieren; unnötige Daten | nur maskierte Übersetzungsfelder senden | Payloadinventartest |
| Ein Platzhalter pro Tokenwert | gleiches Token kann mehrfach vorkommen | Duplikate/Verlust nicht eindeutig lokalisierbar | eindeutiger Platzhalter je Vorkommen | Mehrfachvorkommen-Test |
| Nur globale Anzahl prüfen | Provider könnte Tokens zwischen Services verschieben | Fakten-/Listenzuordnung driftet | erwarteten Feldpfad je Platzhalter prüfen | Reorder-/Feldtest |
| Zweite Tokenklassifikation | widersprüchliche Erkennung | Maskierung und Endvalidierung laufen auseinander | ein kanonisches Modul für beide Pfade | Import-/Inventartest |
| Store vor lokalen Tests ändern | Livefehler könnte Datenstand beeinflussen | nicht freigegebene Teiländerung | erst Test-Doubles, dann ein Einzelaufruf | SHA-/Diffinventar |

## Recommended approach

Die bestehenden Regex- und Eigennamenregeln werden in ein kleines,
verantwortungsspezifisches Tokenmodul verschoben. Es ermittelt pro Feld
überlappungsfrei die längsten geschützten Spannen und ersetzt jedes Vorkommen in
stabiler Feldreihenfolge durch `__LENA_P0000__`, `__LENA_P0001__` usw. Die
Mappingstruktur bleibt lokal und wird nicht an den Provider gesendet.
Nach dem strikten JSON-Parsing prüft der Restore alle bekannten, unbekannten,
veränderten und doppelten Platzhalter einschließlich ihres Feldpfads, setzt die
Originalwerte exakt ein und übergibt erst dann an die unveränderte
Integritätsprüfung.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Providerprompt ohne Maskierung weiter verschärfen | zwei reale Versuche haben die Grenze bereits gezeigt |
| Preise nachträglich normalisieren | wäre eine heuristische Datenänderung und schwächt Exaktheit |
| Nur `23/en` speziell behandeln | institutions-/datensatzspezifischer Workaround statt generischem Schutz |
| Platzhalter im persistenten Schema speichern | Mapping ist requestlokal und kein fachlicher Datensatz |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/translation_tokens.py` | Create | kanonische Erkennung, Maskierung und Restore | klein, sicherheitsrelevant |
| `app/i18n.py` | Modify | kanonische Tokenfunktionen importieren, Endvalidierung erhalten | kleine Extraktion |
| `app/translate_offers.py` | Modify | maskierter Payload und fail-safe Restore | mittlere Änderung |
| `app/translation_contract.py` | Modify | Promptversion für geänderten Vertrag | eine Konstante |
| `tests/test_translation_tokens.py` | Create | vollständige lokale Platzhalterfälle | fokussierte Tests |
| `tests/test_translation_quality.py` | Modify | Payload, Dry-Run, 103/104-Inventar und Runtime | kleine Anpassung |
| `data/i18n/offer_translations.json` | Conditional modify | nur validiertes `23/en` | genau ein Record |
| `app/resources/bootstrap/i18n/offer_translations.json` | Conditional modify | identischer Paketspiegel | genau ein Record |
| `docs/data-flow.md` | Modify | nicht offensichtlichen Schutzpfad dokumentieren | kurzer Abschnitt |
| dieses Planfile | Create/Update | Audit und Evidenz | gering |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Branch `maintenance/repository-cleanup`, Commit `9673668…`; keine
Repository-AGENTS-Datei; aktiver CLI-/Provider-/Runtimepfad und aktueller
`23/en`-Fallback nachvollzogen.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and assess existing files above 400 lines.
- [x] Update this plan with discoveries.

Evidence: `app/translation_tokens.py` ist die einzige kanonische Maskierungs-
und Restoreimplementierung. `app/i18n.py` verwendet daraus Regex und
Eigennameninventar für die unveränderte Endentscheidung;
`app/translate_offers.py` sendet ausschließlich maskierte Felder. Die schon
zuvor umfassenden Wartungsmodule liegen bei 433/406 Zeilen; eine weitere
fachfremde Aufspaltung wurde im begrenzten Paket bewusst vermieden. Das neue
Modul umfasst 147 Zeilen.

### Milestone 3: Verification

- [x] Run targeted tests before provider access.
- [x] Execute at most one authorized provider call.
- [x] Run integration/build checks and verify package resources.
- [x] Review final diff.

Evidence: Vor Livezugriff bestanden 47 fokussierte Tests und die vollständige
lokale Suite; beide Stores waren unverändert und bytegleich unter
`79d75e37…12a7`. Genau ein Blablador-Aufruf für `23/en` erzeugte einen vollständig
validen Record. Danach bestanden 48 fokussierte Tests, 452 Gesamttests,
`compileall`, Wheel/sdist, sdist→Wheel, externer Clean-Install,
providerfreier Template-Smoke und `git diff --check`.

### Milestone 4: Documentation

- [x] Invoke `code-documentation` against the final diff.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: Der Code-Documentation-Skill wurde vollständig gelesen und auf den
finalen Diff angewendet. `docs/data-flow.md` dokumentiert Maskierung,
requestlokales Mapping, Restore-Reihenfolge, Fehlerverhalten und die Grenze zur
menschlichen Sprachprüfung. Nach der Änderung bestanden fokussierte und volle
Suite erneut.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Placeholder units | `pytest tests/test_translation_tokens.py` | alle Positiv-/Negativfälle grün, keine Provider |
| Translation integration | fokussierte `test_translation_quality.py`/Timeouttests | maskierter Positivlistenpayload, Dry-Run unverändert |
| Pre-live store | lokale Storeinventur und `validate` | exakt 103 valide, nur `23/en` ungültig; kein anderer Record geändert |
| Authorized live repair | Einzelziel `23/en`, `en`, Limit 1 | höchstens ein Request; nur bei vollständiger Validierung gespeichert |
| Runtime regression | fokussierte Karten/I18n/Formulator/Dialog/API/Speechtests | keine Regression, bei Erfolg englische Helene-Karte |
| Full regression | `python -m pytest -q` | vollständig grün |
| Static quality | `compileall`, `git diff --check` | grün |
| Packaging | Wheel, sdist, sdist→Wheel, externer Clean-Install/Smoke | Store und Schutzcode paketiert, keine Provideraufrufe |

## Rollback and recovery

Vor dem Liveaufruf werden SHA-256 und strukturierter Inhalt beider Stores
geprüft. Der bereits versioniert gesicherte Vorzustand bleibt erhalten. Der
Generator schreibt ausschließlich nach erfolgreicher kompletter
Einzelvalidierung atomar. Der Paketspiegel wird erst aus dem validierten
Checkoutstore atomar synchronisiert. Bei Providerfehler bleibt der alte Store
unverändert und der deutsche Runtime-Fallback aktiv.

## Progress log

- 2026-08-02 — Review-First- und Code-Documentation-Skills vollständig gelesen;
  Auftrag, Arbeitsbaum, aktiver Übersetzungspfad, Schutzinventar, Tests und
  aktueller Restfehler read-only geprüft; Plan vor Quelländerungen erstellt.
- 2026-08-02 — Kanonisches Tokenmodul, eindeutige Marker pro Vorkommen,
  feldgebundener Restore, reservierte Quellmarkerprüfung und Promptversion 3
  implementiert. Alle lokalen Tests und die Vollsuite bestanden vor Livezugriff.
- 2026-08-02 — Vorzustand unter SHA `79d75e37…12a7` gesichert. Genau ein
  Blablador-Aufruf mit `alias-fast` für `23/en` erfolgreich; nur dieser Record
  und `generated_at` änderten sich. Checkout- und Paketstore anschließend
  bytegleich unter SHA `15b57e37…9df0`.
- 2026-08-02 — Vollvalidierung: 104 active/machine/valid, 0 invalid/stale/
  reviewed. Englische Helene-Karte nutzt die Übersetzung mit exakt erhaltenen
  Preisen `5,00 €` und `2,50 €`.
- 2026-08-02 — 452 Tests, Python-Syntax, Wheel/sdist, sdist→Wheel,
  Clean-Install, Template-Smoke und Diffprüfung bestanden; Dokumentation und
  finale Review-First-Selbstprüfung abgeschlossen.

## Decision log

- Decision: Ein Platzhalter pro Vorkommen statt pro Tokenwert.
  - Context: Mehrfachvorkommen müssen exakt und feldbezogen prüfbar bleiben.
  - Choice: Fortlaufende requestlokale Nummerierung in Schema-/Feldreihenfolge.
  - Consequences: Kein Mapping verlässt den Prozess; Restore ist eindeutig.
- Decision: Promptversion auf 3 erhöhen, Storeversion unverändert lassen.
  - Context: Providerinput und Promptvertrag ändern sich, Persistenzschema nicht.
  - Choice: Nur neu erzeugte Übersetzungen tragen Promptversion 3.
  - Consequences: Bestehende 103 Records bleiben identitätsgültig und werden
    nicht künstlich stale.

## Discoveries

- Die gemeinsame präzisierte Tokenregex erzeugte bei den 103 bestehenden
  validen Records keine neue Abweichung; vor dem Liveaufruf blieb ausschließlich
  `23/en` mit zwei Preisfehlern ungültig.
- Ein eindeutiger Marker pro Vorkommen ist notwendig: So lassen sich dasselbe
  Token mehrfach, angrenzende Marker und eine Verschiebung zwischen
  Servicefeldern ohne Klartextheuristik erkennen.
- Reservierte markerähnliche Zeichenfolgen in Quellfeldern werden vor dem
  Providerzugriff fail-safe verworfen, statt mit realem Text verwechselt zu
  werden.
- Der einzelne Providerlauf behielt durch Maskierung beide Kommapreise exakt
  bei und benötigte keinen Retry.

## Final verification summary

- Acceptance: vollständig erfüllt; kein Folgearbeitspaket begonnen.
- Provider: genau ein autorisierter Blablador-Aufruf, Modell `alias-fast`, nur
  maskierte `23/en`-Positivlistenfelder, Promptversion 3.
- Store: 104 aktive Records, 104 `machine`, 104 faktisch valide, 0 ungültig,
  0 stale, 0 reviewed; beide Spiegel bytegleich.
- Runtime: englische Helene-Karte verwendet den neuen Record; keine deutschen
  Kartenfallbacks wegen ungültiger aktiver Übersetzungen.
- Tests/build: 48 fokussierte und 452 vollständige Tests, Syntax, Distribution,
  sdist-Rebuild, externer Clean-Install, Template-Smoke und Diffprüfung grün.
- Documentation: bestehender Datenfluss präzisiert; keine Thesis-/
  Präsentationsdatei verändert.
- Residual risk: Alle Angebotsübersetzungen bleiben maschinell und besitzen
  weiterhin keine menschliche, muttersprachliche oder professionelle Freigabe.
