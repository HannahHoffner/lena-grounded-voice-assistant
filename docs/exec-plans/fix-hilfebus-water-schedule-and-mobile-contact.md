# Execution Plan: Hilfebus zeit- und ortsrichtig verwenden

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-20
- Last updated: 2026-08-20

## Objective

Der Hilfebus erscheint bei Trinkwasser nur dann als Wasser-Ausgabestelle, wenn
die belegte Sonntagsstandzeit 20:00–21:00 Uhr zur Anfrage oder zur aktuellen
Zeit passt. In allgemeinen oder nicht anderweitig abgedeckten Hilfelagen bleibt
er ein mobiler telefonischer Kontakt während der belegten täglichen
Einsatzzeiten, ohne dass Büroanschrift oder Sonntagsstand pauschal als aktueller
Ort dargestellt werden.

## Acceptance contract

- [x] Eine allgemeine Wasserfrage außerhalb Sonntag 20:00–21:00 nennt den
  Hilfebus weder als Hauptergebnis noch als Karte oder Marker.
- [x] Innerhalb der Sonntagsstandzeit beziehungsweise bei einer ausdrücklich
  auf Sonntag bezogenen Anfrage kann der Hilfebus mit der belegten Standzeit
  und Westseite des Hauptbahnhofs erscheinen.
- [x] Zeitgebundene soziale Wasserangebote werden bei zeitloser Anfrage anhand
  der aktuellen Europe/Berlin-Zeit geprüft, statt `unknown` als passend zu
  behandeln.
- [x] Bei allgemeinem oder nicht abgedecktem Hilfebedarf bleibt der Hilfebus
  ein `referral_contact`; Hilfebus-Fallbacks nennen die mobilen Einsatzzeiten
  aus der Runtime-KB, nicht nur die sonntägliche Standzeit.
- [x] Die Büroanschrift des mobilen Hilfebus wird weder als Angebotskartenort
  noch als Marker ausgegeben; Rohquelle und Runtime-Provenienz bleiben erhalten.
- [x] Bestehende Wasserbrunnen-, Safety-, Dialog-, Übersetzungs- und
  Groundingpfade bleiben unverändert funktionsfähig.

## Scope

### In scope

- Deterministische Zeitprüfung bereits kuratierter `service_schedules` für
  `Need.DRINKING_WATER`.
- Hilfebus-Rolle, Karten-/Markerprojektion und Auswahl der Kontaktzeiten.
- Fokussierte Tests und bestehende technische Datenflussdokumentation.

### Out of scope

- Neue Datenquellen, Stadtteil-/Nutzerstandortranking oder Live-Verfügbarkeit.
- Änderungen an Interpreter-, Selector- oder Formulatorprompts.
- Änderung der WFS-Rohdaten oder neue nicht belegte Hilfebuszeiten.
- Thesis- oder Präsentationsdateien.

## Repository review

### Current behavior

`CandidateSelector.select()` ruft für zeitgebundene Nicht-Essensleistungen
`candidate_context.schedule_matches()` auf. Ohne expliziten Tag und ohne
explizite Uhrzeit liefert diese Funktion `None`; nur `False` sperrt den
Kandidaten. Deshalb bleiben ID 21 (Hilfebus, Wasser nur `sunday_20_21`) und
weitere zeitgebundene Wasserangebote bei „Ich habe Durst“ zulässig.

`select_drinking_water_results()` bildet anschließend aus allen zulässigen
sozialen Wasserangeboten und festen Brunnen eine HBF-Distanzreihenfolge.
`maps.offer_stand_destinations()` erzeugt für den Hilfebus allein aufgrund des
Service-Schedule-Codes den HBF-West-Marker; der aktuelle Tag wird dort nicht
erneut geprüft. So wird der sonntägliche Stand außerhalb Sonntag als nächster
Ort bewertet.

`QueryService._hilfebus_response()` und `_technical_safety_fallback()` wählen
`standzeiten_raw or opening_hours_raw`. Weil Standzeiten vorhanden sind, wird
die tägliche mobile Einsatzzeit 18:00–23:00 Uhr im Kontakttext verdrängt.

### Relevant architecture and data flow

`LLM-Interpreter` → `CandidateSelector` →
`select_drinking_water_results()` → `build_drinking_water_evidence()` / lokales
Template → Karten und `drinking_water_map_data()`.

Allgemeine Hilfe läuft über denselben CandidateSelector oder nach einem
erfolglosen Dialog über `QueryService._hilfebus_response()`. Der kuratierte
Datensatz enthält getrennt `service_schedules`, tägliche Einsatzzeiten,
Sonntagsstandzeit, Kontakte und `place_type=help_bus`.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| `schedule_matches()` | `app/candidate_context.py` | um opt-in-Prüfung der aktuellen Zeit erweitern |
| kuratierte `service_schedules` | `app/resources/bootstrap/curation/social_offers.json` | unverändert verwenden |
| `place_type=help_bus` | Runtime-`OfferRecord` | mobile Karten-/Markerdarstellung ableiten |
| `opening_hours_raw` | Runtime-`OfferRecord` | belegte mobile Einsatz-/Anrufzeiten verwenden |
| Candidate roles | `app/candidate_contract.py` | Hilfebus bei `general_help` als Referral markieren |

### Existing tests and commands

- `tests/test_candidates.py`: Wasser-Evidence, General-Help-Priorität.
- `tests/test_drinking_fountains.py`: kombinierte soziale und öffentliche
  Wasserresultate, Karten und HBF-Reihenfolge.
- `tests/test_api.py`: Sonntagsstand und API-Ausgabe.
- `tests/test_maps.py` beziehungsweise Kartenregressionen in Infrastrukturtests.
- Validierung: fokussierte Tests, Gesamtsuite, `compileall`, `git diff --check`.

### Working tree considerations

Der Branch `maintenance/repository-cleanup` auf
`fbcc85aa1d4c3eeca096d5a67e39f9df7580a5b2` enthält umfangreiche Änderungen der
Nutzerin, auch in `app/candidates.py`, `app/service.py`, Tests und Dokumentation.
Nur eng begrenzte neue Hunks werden ergänzt; vorhandene Änderungen werden nicht
zurückgesetzt oder umformatiert.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Hilfebus nur nachträglich aus Wasserantwort entfernen | Evidence, Karten und Marker wären bereits falsch gebaut | parallele, widersprüchliche Ergebnislisten | an der deterministischen Kandidatengrenze sperren | Candidate- plus API-Test |
| HBF-Marker lediglich verstecken | Hilfebus bliebe weiter falsches Hauptergebnis | Antwort behauptet weiter Wasserort | zeitgebundene Eignung vor Ranking prüfen | Antwort-, Karten- und Markerassertion |
| Trinkwasserfähigkeit aus Kuration löschen | sonntägliche belegte Ausgabe ginge verloren | korrekter Sonntagspfad unmöglich | Fähigkeit und Schedule erhalten | Sonntagstest |
| Büroanschrift als Ersatzstandort nutzen | `place_type=help_bus`, mobile Einsatzzeit und gesonderter Sonntagsstand | irreführender fester Ort | Büro in sichtbarer Karte/Map für Hilfebus unterdrücken, Rohdaten erhalten | Karteninventartest |
| tägliche Einsatzzeit als tägliche Wasserzeit interpretieren | Katalog bindet Wasser ausdrücklich an `sunday_20_21` | unbelegte Wasserverfügbarkeit | tägliche Zeit nur für Kontakt/Referral nutzen | Zeitmatrix |

## Recommended approach

Die bestehende Schedule-Funktion erhält einen ausdrücklich opt-in-fähigen
Modus: Fehlen Tag und Uhrzeit bei einer zeitgebundenen Wasserleistung, wird die
aktuelle Europe/Berlin-Zeit geprüft. Nur ein positiver Match bleibt zulässig.
Explizites „Sonntag“ ohne Uhrzeit darf das belegte Sonntagsangebot nennen und
zeigt seine Zeit; eine generische Anfrage muss sich tatsächlich innerhalb des
Fensters befinden. General Help bleibt hiervon getrennt und nutzt den Hilfebus
als mobilen Referral-Kontakt mit `opening_hours_raw`.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| institutionsspezifische ID-21-Abfrage | unnötig hartcodiert; Schedule-Vertrag ist bereits strukturiert |
| neue Kuration oder neue Adresse | vorhandene Kuration enthält alle benötigten Fakten |
| LLM über Zeit/Eignung entscheiden lassen | deterministische Betriebszeit darf nicht vom Modell geraten werden |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/candidate_context.py` | Modify | opt-in aktuelle Schedule-Prüfung | klein |
| `app/candidates.py` | Modify | Wasser-Schedule strikt; General Help als Referral | klein/mittel |
| `app/maps.py` | Modify | mobiles Büro nie als Nutzerstandort markieren | klein |
| `app/infrastructure_results.py` | Modify | Standmarker-ID korrekt dem Angebot zuordnen | klein |
| `app/service.py` | Modify | Einsatzzeit statt nur Sonntagsstand im Kontakttext | klein |
| relevante Tests | Modify | Zeit-, Rollen-, Karten- und APIregression | mittel |
| `docs/data-flow.md` | Modify | tatsächliche Zeit- und Ortssemantik | klein |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Repository review and provider-free reproduction in this plan.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep changes cohesive within the existing modules.
- [x] Update this plan with discoveries.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run integration and full regression checks.
- [x] Review final diff with the review template.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes and rerun affected checks.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Candidate time matrix | focused pytest | Friday excluded; Sunday window included; boundaries deliberate |
| Water API | provider doubles with fixed clock | no Hilfebus outside window in text/cards/markers; Sunday correct |
| General help | Candidate/API tests | Hilfebus referral, callable at mobile deployment times, no fixed office marker |
| Regression | `python -m pytest -q` | complete suite green |
| Static quality | `python -m compileall -q app tests`; `git diff --check` | no failures |

## Rollback and recovery

Keine Datenmigration oder externe Aktualisierung. Die Änderung besteht aus
kleinen Logik-, Projektions-, Test- und Dokumentationshunks; Runtime-Rohdaten
und Kuration bleiben unverändert.

## Progress log

- 2026-08-20 — Aktiven Candidate-, Wasser-, Formulator-, Karten- und
  Hilfebus-Fallbackpfad geprüft; Fehler providerfrei reproduziert; Plan erstellt.
- 2026-08-20 — Zeitbindung, mobile Ortsprojektion, Referralrolle und Kontaktzeiten
  implementiert; fokussierte Regressionen sowie vollständige Suite bestanden.

## Decision log

- Decision: Zeitbindung vor der räumlichen Ergebnisbildung durchsetzen.
  - Context: `schedule_matches=None` wurde bisher als zulässig behandelt.
  - Options: nachträglich entfernen, Marker verstecken, Capability löschen,
    strukturierten Schedule strikt auswerten.
  - Choice: vorhandenen strukturierten Schedule opt-in gegen aktuelle Zeit prüfen.
  - Consequences: kein falscher Ort/Prompt; Sonntagspfad und mobile Referralrolle bleiben erhalten.

## Discoveries

- Der Fehler ist nicht primär ein Formulatorfehler: Der Formulator erhält den
  Hilfebus bereits als zulässiges und räumlich erstplatziertes Wasserergebnis.
- Die Kontaktfallbacks verdrängen mit `standzeiten_raw or opening_hours_raw`
  derzeit die tägliche Einsatzzeit durch die einzelne Sonntagsstandzeit.
- Standmarker verwenden IDs wie `21:hbf-west`; die Wasserreihenfolge zerlegte
  zuvor nur das nicht mehr verwendete Format `-stand-`.
- Die Büroadresse bleibt in Quelle und Runtime erhalten. Sie wird erst in der
  öffentlichen Hilfebus-Kartenprojektion entfernt, damit Übersetzungs- und
  Provenienzverträge unverändert bleiben.

## Final verification summary

- Acceptance requirements: erfüllt.
- Tests: 169 fokussierte Tests sowie 711 Tests der vollständigen Suite bestanden.
- Static checks: `python -m compileall -q app tests` und `git diff --check`
  ohne Fehler.
- Documentation: `docs/data-flow.md` und `docs/architecture.md` aktualisiert.
- Residual risks: Der bereits laufende Entwicklungsserver muss neu gestartet
  werden, damit er den geänderten Python-Code lädt. Live-Verfügbarkeit oder
  Kapazität des Hilfebusses wird weiterhin nicht behauptet.
