# Execution Plan: Angebotsname „Leipziger Oase“

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-25
- Last updated: 2026-08-25

## Objective

Das Tagestreff-Angebot mit WFS-ID 10 wird in Runtime, Antworten, Karten und
allen Sprachansichten als „Leipziger Oase“ angezeigt. Der Organisationsname
„Diakonie Leipzig“ bleibt für die Organisation und ihr anderes Angebot
erhalten; der vollständige WFS-Quellenname bleibt unverändert nachvollziehbar.

## Acceptance contract

- [x] Nur Angebot 10 erhält `display_name = "Leipziger Oase"`.
- [x] „Leipziger Oase“ wird als eindeutiger Angebotsalias auf ID 10 gebunden.
- [x] Angebot 14 behält den Organisationsanzeigenamen „Diakonie Leipzig“.
- [x] WFS-Snapshot, normalisierter Quellenname und Übersetzungstexte bleiben
  inhaltlich unverändert.
- [x] Die 112 Maschinenübersetzungen bleiben technisch gültig und ehrlich als
  `machine` gekennzeichnet; es erfolgt keine Neuübersetzung und kein Provideraufruf.
- [x] Runtime-, Karten-, Evidence-, Alias-, Übersetzungs- und Packagingtests
  belegen den neuen Namen.

## Scope

### In scope

- Kurationskatalog, angebotsspezifischer Anzeigename und Alias
- nachvollziehbare source-normalized Kurationsentscheidung
- lokale Identitätsbindung des unveränderten Übersetzungsbestands
- fokussierte Tests und unmittelbar betroffene technische Dokumentation

### Out of scope

- Änderung des WFS-Snapshots oder normalisierten Quellenrelease
- Umbenennung der Organisation `diakonie_leipzig` oder Angebot 14
- Änderung übersetzbarer Felder oder erneute Maschinenübersetzung
- Provideraufrufe, Fachlogik, Ranking, Thesis und Präsentation

## Repository review

### Current behavior

Organisation `diakonie_leipzig` besitzt den Anzeigenamen „Diakonie Leipzig“.
Da Angebot 10 keinen eigenen Anzeigenamen hat, übernimmt es diesen Namen in
`project_runtime_offers()`. Dasselbe gilt korrekt für Angebot 14. Der
WFS-Quellenname von ID 10 enthält bereits „Leipziger Oase“.

### Relevant architecture and data flow

`app/resources/bootstrap/curation/social_offers.json` wird durch
`load_active_knowledge_base()` validiert und in genau eine Runtimeprojektion
überführt. Ein angebotseigener `display_name` hat Vorrang vor dem
Organisationsnamen. Formulator, Karten, TTS und Übersetzungskarten lesen
anschließend ausschließlich `offer.display_name or offer.name`.
`build_selection_context()` begrenzt ausdrückliche Angebotsaliase vor der
Kandidatenauswahl. Der Übersetzungsstore übersetzt Namen nicht, bindet aber
seine Faktenintegrität an Kurationshash und operative Fakten.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| `ServiceOffer.display_name` | `app/curation.py` | für ID 10 setzen |
| `OfferAlias` | `app/curation.py` | exakten sichtbaren Namen an ID 10 binden |
| source-normalized Entscheidung | `social_offers.json` | bestehendes Provenienzmuster wiederverwenden |
| `operational_facts_hash()` und `translation_version()` | `app/i18n.py` | unveränderte Übersetzungen lokal neu binden |
| Kurationsintegrationstests | `tests/test_curation.py` | Runtime-, Quelle-, Alias- und Kartenname prüfen |
| Übersetzungsintegritätstests | `tests/test_translation_quality.py` | fünfsprachige Namens- und Statusinvariante prüfen |

### Existing tests and commands

- `python -m pytest -q tests/test_curation.py tests/test_translation_quality.py tests/test_formulation.py`
- `python -m app.translate_offers validate`
- `python -m pytest -q`
- `python -m compileall -q app tests`
- `git diff --check`

### Working tree considerations

Der Arbeitsbaum enthält die unmittelbar vorher umgesetzte Änderung der
Anwendungstexte und des Formulatorprompts. Diese Änderungen bleiben
unangetastet. Ausgangs-HEAD ist
`6d51aa8a01f2ea3a9f5e6d926475ae0ef7d5d011` auf
`maintenance/repository-cleanup`.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Organisation umbenennen | IDs 10 und 14 teilen `diakonie_leipzig` | Angebot 14 würde fälschlich „Leipziger Oase“ heißen | angebotseigenen Namen setzen | beide Runtime-Namen testen |
| nur sichtbaren Text im Frontend ersetzen | Backend, Evidence, TTS und Karten lesen die Runtime | widersprüchliche Namen | Kurationsprojektion ändern | API-/Evidence-/Kartentest |
| Quellenname überschreiben | WFS führt den vollständigen Rechts- und Leistungsnamen | Provenienzverlust | Roh- und normalisierte Quelle unverändert lassen | Quelltest |
| nur `display_name` setzen | Interpreter erhält nur kuratierte Aliashinweise | Anfrage nach sichtbarem Namen wäre nicht eindeutig gebunden | exakten OfferAlias ergänzen | Alias- und Kandidatentest |
| Kurationshash ändern, Übersetzungsstore nicht binden | globale Kataloghashbindung | alle 112 Sprachdatensätze würden stale | ausschließlich Identitätsmetadaten lokal neu berechnen | vollständige CLI-Validierung |
| Texte neu übersetzen | Name ist ein geschütztes, nicht übersetzbares Runtimefeld | unnötige Provideraufrufe und Textänderungen | Felder bytegleich bewahren | Vorher-/Nachher-Hash der `fields` |

## Recommended approach

ID 10 erhält den angebotsspezifischen Anzeigenamen und den exakten OfferAlias.
Eine source-normalized Entscheidung verweist auf den unveränderten WFS-
Quellenrelease. Die Katalogversion wird erhöht. Danach werden für beide
identischen Übersetzungsstores ausschließlich Kurations-, operative und
Translation-Identitätshashes mit den vorhandenen Projektfunktionen neu
berechnet; Textfelder, Sprachstatus, Provider, Modell und Erstellungszeitpunkt
bleiben unverändert.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Organisationsanzeigename ändern | betrifft zusätzlich ID 14 |
| Name in Prompt oder Template hartcodieren | umgeht die einzige Runtime-Wissensbasis |
| Übersetzungsprovider erneut aufrufen | keine übersetzbaren Inhalte ändern sich |
| veralteten Store akzeptieren | würde fremdsprachige Karten auf deutsche Basisdaten zurückfallen lassen |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/resources/bootstrap/curation/social_offers.json` | Modify | Name, Alias, Provenienz, Version | klein |
| `data/i18n/offer_translations.json` | Modify | lokale Identitätsbindung | mechanisch, mittel |
| `app/resources/bootstrap/i18n/offer_translations.json` | Modify | Clean-Install identisch halten | mechanisch, mittel |
| `tests/test_curation.py` | Modify | Runtime-/Quell-/Aliasregression | klein |
| `tests/test_translation_quality.py` | Modify | fünfsprachige Integrität | klein |
| bestehende technische Dokumentation | Modify if needed | tatsächliche Kurationsbezeichnung | klein |
| dieser Plan | Create/Update | Review- und Prüfnachweis | klein |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: IDs 10 und 14 teilen eine Organisation; der bestehende
angebotsspezifische Vorrang und OfferAlias lösen die Anforderung ohne
Parallelpfad.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

Evidence: Bestehende deklarative Kurations-, Alias- und Provenienzmodelle
wurden erweitert; es entstand kein neuer Quellcode- oder Runtimepfad. Beide
Übersetzungsstores wurden mit vorhandenen Hashfunktionen atomar neu gebunden.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run lint/format/type checks.
- [x] Run integration/build checks where relevant.
- [x] Verify registration, imports, routes, configuration, and packaging.
- [x] Review final diff.

Evidence: 178 fokussierte Tests und die vollständige Suite mit 753 Tests
bestanden. `compileall`, `translate_offers validate` und `git diff --check`
waren erfolgreich; die beiden Storedateien besitzen denselben SHA-256.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: `docs/architecture.md` und `docs/data-flow.md` dokumentieren den
angebotsspezifischen Namensvorrang und die unveränderte Quell-/Organisationsebene.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Runtime | fokussierter Kurations-/API-Test | ID 10 heißt „Leipziger Oase“, ID 14 nicht |
| Alias | CandidateContext-/Interpreterinventar | exakter Alias bindet ausschließlich ID 10 |
| Quelle | normalisierten Release laden | vollständiger Quellenname unverändert |
| Übersetzung | `translate_offers validate` | 112 `machine`, 0 stale/invalid |
| Regression | `python -m pytest -q` | vollständige Suite grün |
| Static quality | `compileall`; `git diff --check` | erfolgreich |
| Packaging | relevante Packagingtests | beide Stores identisch und paketiert |

## Rollback and recovery

Alle Änderungen sind versionierte, deterministische Daten- und Teständerungen.
Die beiden Übersetzungsstores bleiben identisch und können gemeinsam auf ihre
vorherigen Hashmetadaten zurückgeführt werden; keine Quelle oder Runtime-Datei
wird gelöscht.

## Progress log

- 2026-08-25 — Repository, Kurationsprojektion, Aliasauflösung,
  Übersetzungsbindung und vorhandene Tests review-first geprüft; Plan vor
  Implementierungsänderungen erstellt.
- 2026-08-25 — ID 10, Alias, source-normalized Provenienz und Katalogversion
  aktualisiert; Runtimepfad lokal bestätigt.
- 2026-08-25 — 112 bestehende Sprachdatensätze pro Store ohne Text- oder
  Statusänderung technisch neu gebunden; vollständige Integrität bestätigt.
- 2026-08-25 — Dokumentation, Fokus- und Volltests sowie abschließender Diff
  review-first geprüft.

## Decision log

- Decision: Angebotsname plus OfferAlias, Organisationsname unverändert.
  - Context: Eine Organisation besitzt zwei fachlich getrennte Angebote.
  - Options: Organisation, Angebot, Frontendtext oder Prompt umbenennen.
  - Choice: vorhandene Angebotskuration.
  - Consequences: ID 10 ist korrekt sichtbar und suchbar; ID 14 bleibt korrekt.
- Decision: Übersetzungstexte lokal neu binden, nicht neu erzeugen.
  - Context: Nur ein nicht übersetzbares operatives Namensfeld ändert sich.
  - Options: stale lassen, Providerneugenerierung, lokale Identitätsaktualisierung.
  - Choice: lokale Aktualisierung mit bestehenden Hashfunktionen.
  - Consequences: keine linguistische Scheinfreigabe und kein Provideraufruf.

## Discoveries

- Der vollständige Kataloghash bindet jede Sprachfassung. Deshalb änderten
  sich in jedem Store 336 globale Identitätswerte; nur die vier Sprachfassungen
  von ID 10 erhielten zusätzlich einen neuen `operational_facts_hash`.
- Der strukturierte Diffvergleich gegen HEAD bestätigt: keine `fields`,
  Sprachstatus, Provider-/Modellangaben oder Erstellungszeitpunkte änderten sich.

## Final verification summary

- Acceptance requirements: erfüllt
- Tests: 178 fokussierte und 753 vollständige Tests erfolgreich
- Build: Packagingpfad durch Tests bestätigt; kein neuer Buildcode
- Manual verification: Runtime ID 10/14, Quelle und Store-Diff geprüft
- Documentation: Architektur und Datenfluss aktualisiert
- Residual risks: Fremdsprachen bleiben bewusst `machine`, nicht menschlich geprüft
