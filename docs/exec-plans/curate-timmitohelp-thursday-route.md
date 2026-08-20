# Execution Plan: TiMMi-ToHelp-Donnerstagsroute kuratieren

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-20
- Last updated: 2026-08-20

## Objective

LENA gibt TiMMi ToHelp nur im belegten Donnerstagszeitraum als mobile Ausgabe
aus und nennt dabei die drei belegten Tourstationen mit ungefähren Uhrzeiten.
Die Erkennung des bunten Teams mit zwei Bollerwagen darf als belegter Hinweis
erscheinen. Quelle, Kurationsentscheidung und unveränderte WFS-Rohdaten bleiben
nachvollziehbar getrennt.

## Acceptance contract

- [x] ID 16 bleibt ein einziges mobiles Leistungsangebot; es entstehen keine
  duplizierten Angebotsdatensätze je Tourstopp.
- [x] Die Runtime nennt Donnerstag ca. 16:00 Uhr Dittrichring, ca. 16:30 Uhr
  Lennéanlage und ca. 17:30 Uhr Nikolaistraße.
- [x] Der Hinweis auf das bunte Team mit zwei Bollerwagen ist als
  quellengebundene Erkennungshilfe verfügbar.
- [x] Essen, Trinken, Hygiene und Kleidung behalten `thursday_16_19` als
  verbindlichen Leistungszeitbeleg. Ausdrücklich unpassende Tage oder Zeiten
  schließen ID 16 aus; die bestehenden strengeren Current-Time-Regeln für
  Essen und Trinkwasser bleiben unverändert.
- [x] Die WFS-Quelladresse und die alte allgemeine Tourangabe bleiben in den
  Roh-/Quelldaten unverändert.
- [x] Es werden keine unbestätigten Koordinaten oder dauerhaften Marker für die
  mobilen Tourstopps erfunden.
- [x] Die bestehende fünfsprachige Runtime fällt nicht aufgrund einer veralteten
  Übersetzungsidentität aus; keine Humanfreigabe wird erfunden.

## Scope

### In scope

- Kurationskatalog, Provenienz, Runtime-Override für ID 16.
- Bestehende Schedule-Regel und Karten-/Markergrenze für mobile Angebote.
- Eng begrenzte Übersetzungs-/Identitätsanpassung, soweit die Kuration sie
  technisch zwingend stale macht.
- Kandidaten-, Runtime-, Formulator-, Karten-, I18n- und API-Regressionstests.
- Unmittelbar betroffene technische Datenflussdokumentation.

### Out of scope

- Neue Provideraufrufe, automatische Tourplanimporte oder Live-Verfügbarkeit.
- Geokodierung oder allgemeines geografisches Ranking der Tourstopps.
- Veränderung von WFS-Rohdaten, Thesis oder Präsentation.
- Weitere Angebote oder allgemeine Fahrplanmodellierung.

## Repository review

### Current behavior

ID 16 ist ein `basic_supplies`-/`food_distribution`-Angebot mit den
Fähigkeiten Essen, Trinkwasser, Hygiene und Kleidung. Alle Leistungen sind an
`thursday_16_19` gebunden. Die Runtime übernimmt derzeit jedoch die WFS-Adresse
`Dittrichring 15` und lediglich die allgemeine Notiz, die Verteilung erfolge
donnerstags etwa 16:00–19:00 Uhr im Bereich Innenstadt/Hauptbahnhof.

`CandidateSelector` prüft Essen über `food_schedule_matches()` und Trinkwasser
streng über `schedule_matches()`. `maps.uses_stand_location_instead_of_office()`
unterdrückt wegen `thursday_16_19` bereits den einzelnen WFS-Punkt als Marker,
erzeugt für TiMMi aber keine alternativen Marker. Das ist sicherer als eine
scheinexakte Position, macht die Tourdetails bisher jedoch unsichtbar.

Der vom Nutzer bereitgestellte offizielle Tourplan nennt die drei Zwischenpunkte
und den Erkennungshinweis. SHA-256 der geprüften PDF-Datei:
`64155c223575dc152f420f0ebdca7822d5d4b015740e7b34ab7557bbafdbf4d2`.

### Relevant architecture and data flow

WFS-Quellrelease → `CurationCatalog` → `project_runtime_offers()` → eine
Runtime-KB → `CandidateSelector` → Evidence/Formulator → Karte und
Angebotskarte. `standzeiten_raw` und `notes` gelangen als positiv gelistete
Fakten in Evidence, Karte und TTS. Die gespeicherten Kartenübersetzungen sind
an den globalen Kurationshash und die jeweiligen Feldhashes gebunden.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| `runtime_overrides` | `app/curation.py` | Route und Erkennungshinweis ohne Rohdatenänderung kuratieren |
| `service_schedules` | `app/resources/bootstrap/curation/social_offers.json` | `thursday_16_19` unverändert weiterverwenden |
| `standzeiten_raw` / `notes` | `app/models.py` | vorhandene Karten-, Evidence- und TTS-Felder verwenden |
| mobile Markergrenze | `app/maps.py` | keine unbelegten Koordinaten ergänzen |
| Übersetzungsidentität | `app/i18n.py` | bestehende Hashprüfung respektieren; keine parallele Lokalisierung |

### Existing tests and commands

- `tests/test_candidates.py`, `tests/test_result_ordering.py`: Zeitbindung.
- `tests/test_curation.py`, `tests/test_runtime_loader.py`: Runtime-Projektion.
- `tests/test_api.py`, `tests/test_formulation.py`: Evidence und sichtbare Karte.
- `tests/test_translation_quality.py`: Übersetzungsidentität und Runtimepolicy.
- Validierung: fokussierte Tests, Gesamtsuite, `compileall`, Packaging und
  `git diff --check`.

### Working tree considerations

Der Branch `maintenance/repository-cleanup` auf
`fbcc85aa1d4c3eeca096d5a67e39f9df7580a5b2` ist umfangreich durch die Nutzerin
geändert. Alle vorhandenen Änderungen bleiben erhalten; nur eng begrenzte Hunks
im bestehenden WP1–WP9-Pfad werden ergänzt.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Drei neue Offers für drei Stopps | ein Team erbringt dieselbe Leistung entlang einer Route | Duplikate, falsche Kapazität und Auswahl | ein ServiceOffer mit mehreren Standzeitzeilen | genau eine Runtime-ID 16 |
| WFS-Adresse als dauerhaften Standort anzeigen | Tourplan beschreibt mobile Route | irreführender Marker/Ort | mobile Markergrenze erhalten; Route textuell darstellen | Karten-/API-Test |
| Koordinaten aus PDF-Karte schätzen | PDF enthält keine verifizierten Geodaten | falsches Entfernungsranking | keine neuen Koordinaten | Marker-Inventartest |
| Route nur im Prompt hardcodieren | umgeht Kuration und Karten/TTS | zweite Wissensbasis | Runtime-Override als einzige Faktenquelle | Evidence-Inventar |
| Kurationshash ändern, Translationstore ignorieren | Store bindet jeden Record global an den Kataloghash | alle Fremdsprachenkarten werden stale | bestehende Records atomar und ohne Neuübersetzung an den neuen Hash binden; nur geänderte ID 16 inhaltlich anpassen | kompletter I18n-Status |

## Recommended approach

ID 16 erhält einen quellenbelegten Override für `standzeiten_raw` und `notes`.
Die Zeitregel `thursday_16_19` bleibt fachlich unverändert. Die WFS-Geometrie
wird weiterhin nicht als Tourstopp verwendet. Ein eigener SourceReference mit
PDF-Hash sowie eine explizite Override-Entscheidung machen die Herkunft
nachvollziehbar. Weil der globale Kurationshash Teil jedes Translationrecords
ist, werden unveränderte Records nur technisch neu gebunden, nicht erneut
übersetzt; ID 16 erhält ausschließlich die erforderlichen aktualisierten
Maschinenfelder und bleibt `machine`, nicht `reviewed`.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| neue allgemeine Route-Engine | für einen belegten Einzelfall unverhältnismäßig und außerhalb des Auftrags |
| fixe Kartenmarker je Stopp | keine verifizierten Koordinaten und keine belastbaren exakten Ankunftszeiten |
| nur sichtbaren Antworttext ändern | würde Evidence, Karten und TTS widersprüchlich lassen |
| alle Karten neu übersetzen | fachlich unnötig; unveränderte Texte sollen erhalten bleiben |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/resources/bootstrap/curation/social_offers.json` | Modify | Route, Quelle, Entscheidung und Katalogversion | mittel |
| `data/i18n/offer_translations.json` | Modify | Hashbindung und ID-16-Texte konsistent halten | mechanisch/mittel |
| `app/resources/bootstrap/i18n/offer_translations.json` | Modify | paketierter Spiegel | mechanisch/mittel |
| relevante Tests | Modify | Route, Zeit, Evidence, Marker und I18n absichern | mittel |
| `docs/data-flow.md` | Modify | mobile Tourprojektion dokumentieren | klein |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: PDF lokal gelesen; WFS-, Kurations-, Candidate-, Evidence-, Karten-
und I18n-Pfade bis zur sichtbaren Ausgabe verfolgt.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep changes cohesive within the existing modules.
- [x] Update this plan with discoveries.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run integration/build checks where relevant.
- [x] Verify packaging and runtime resources.
- [x] Review final diff.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Runtime facts | focused curation/runtime pytest | genau drei Routezeilen und Erkennungshinweis auf ID 16 |
| Schedule | candidate/result-ordering pytest | Donnerstag passend; andere Tage/unpassende Uhrzeiten ausgeschlossen |
| Evidence/API | formulation/API pytest | Route kann belegt ausgegeben werden; keine erfundene Position |
| I18n | translation-quality pytest/CLI validate | keine stale/invalid aktiven Records; Status bleibt ehrlich |
| Regression | `python -m pytest -q` | vollständige Suite grün |
| Static/build | `compileall`, Wheel/sdist/Clean-install, `git diff --check` | fehlerfrei |

## Rollback and recovery

Keine externe Mutation oder Datenmigration. Runtime- und Paket-
Übersetzungsstore werden atomar erzeugt beziehungsweise kontrolliert gespiegelt.
Die WFS-Rohdaten bleiben unverändert. Bei einem Fehler wird kein teilweise
geschriebener Store aktiviert.

## Progress log

- 2026-08-20 — Repository und PDF read-only geprüft; Route, Zeitbindung,
  Kartenunterdrückung und globale Translation-Hashbindung nachvollzogen; Plan
  vor Implementierungsänderungen erstellt.
- 2026-08-20 — ID 16 mit PDF-Hash, drei ungefähren Tourstopps,
  Erkennungshinweis und unterdrückter alter Punktgeometrie kuratiert. 112
  Translationrecords lokal an den neuen Kataloghash gebunden; nur die vier
  ID-16-Maschinenfassungen inhaltlich angepasst, ohne Provideraufruf oder
  Humanfreigabe.
- 2026-08-20 — 218 initial fokussierte sowie 89 abschließende Candidate-/
  Kurationsprüfungen und 739 Tests der Gesamtsuite bestanden;
  Translation-CLI meldet 112 `machine`/`valid`, 0 stale und 0 Integritätsfehler.
  Wheel und sdist einschließlich Wheel-Neubau aus sdist erfolgreich gebaut.

## Decision log

- Decision: Ein mobiles Angebot mit strukturierten Standzeitzeilen statt drei
  duplizierter Angebote.
  - Context: Alle drei Stationen gehören zur selben Donnerstagsverteilung.
  - Options: drei Offers, drei Marker, Text-Override, allgemeine Route-Engine.
  - Choice: bestehende Runtime-Felder und Schedule-Regel kuratiert erweitern.
  - Consequences: keine falsche Angebotsvervielfachung und kein ungeprüftes
    geografisches Ranking.

## Discoveries

- Der PDF-Tourplan nennt `ca.`-Zeiten; sie dürfen nicht als minutengenaue
  Echtzeitankunft oder garantierte Anwesenheit formuliert werden.
- Der Translationstore bindet alle Records an den globalen Kurationshash. Eine
  Katalogänderung erfordert deshalb eine technische Neubindung auch bei
  inhaltlich unveränderten Records, aber keine Neuübersetzung.
- Die bestehende Markerlogik behandelt `thursday_16_19` bereits als mobile
  Standzeit und unterdrückt damit die WFS-Büro-/Punktgeometrie. Für die drei
  nur textuell belegten Stopps war keine neue Kartenlogik erforderlich.
- Allgemeine Hygiene-/Kleidungsanfragen ohne expliziten Zeitbezug verwenden
  weiterhin die bestehende dreiwertige Schedule-Policy. Dieses Datenpaket
  ändert sie nicht; ausdrückliche Donnerstags-/Freitags- und Uhrzeitangaben
  werden für alle vier TiMMi-Leistungen deterministisch geprüft.

## Final verification summary

- Acceptance requirements: erfüllt.
- Tests: fokussierte Teil-Suites und 739 vollständige Tests bestanden.
- Build: `compileall`, Wheel, sdist und Wheel-Neubau aus sdist bestanden;
  Clean-Install-/Bootstrapprüfung war Teil der grünen Packagingtests.
- Manual verification: PDF-Inhalt und SHA-256 geprüft; Runtime-/Source-
  Trennung sowie fünfsprachige Kartenprojektion lokal inventarisiert.
- Documentation: bestehende Architektur- und Datenflussdokumentation ergänzt.
- Residual risks: Die drei `ca.`-Zeiten sind keine Livepositionen. Ohne
  verifizierte Koordinaten gibt es bewusst keine Tourmarker oder
  Entfernungswertung. Alle vier Fremdsprachenfassungen bleiben maschinell und
  benötigen weiterhin eine menschliche Sprachprüfung.
