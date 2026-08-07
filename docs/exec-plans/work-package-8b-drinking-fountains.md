# Arbeitspaket 8B: fest installierte Leipziger Trinkbrunnen

## Status

- State: Reviewed
- Owner: Codex
- Created: 2026-08-02
- Last updated: 2026-08-02

## Objective

LENA integriert ausschließlich fachlich geprüfte, fest installierte
Trinkwasserbrunnen innerhalb der Stadt Leipzig. Die Infrastruktur durchläuft
denselben getrennten Rohdaten-, Normalisierungs-, Release-, Aktivierungs- und
Fallbackprozess wie die Toiletten. Reine Trinkbrunnenresultate werden
deterministisch nach der bereits zentral definierten HBF-Luftlinie geordnet;
höchstens drei Ergebnisse gelangen in Antwort und Karten, während alle
zulässigen Brunnen mit gültiger Geometrie als Marker erscheinen.

## Acceptance contract

- [x] Der unveränderte offizielle KML-Export, die administrative
  Grenzgrundlage, normalisierte Datensätze, Diff und Manifest sind getrennt und
  vollständig hashgebunden.
- [x] Ein Fetch erzeugt höchstens einen Pending-Release; automatische Promotion
  ist nicht möglich.
- [x] Runtime-Fallbacks verwenden nur aktivierte, pointergebundene und
  vollständig reproduzierbar geprüfte Releases oder den paketierten Bootstrap.
- [x] Nur fest installierte Brunnen innerhalb Leipzigs sind runtime-eligible;
  mobile und außerhalb liegende Datensätze bleiben in Snapshot, Normalisierung,
  Diff und Provenienz erhalten.
- [x] Trinkbarkeit, Kostenfreiheit, Saison und Betriebsstatus bleiben getrennte
  Felder. LENA behauptet keine aktuelle Funktion oder Echtzeitverfügbarkeit.
- [x] Trinkwasserresultate verbinden nur positiv belegte soziale Wasserangebote
  und freigegebene Brunnen. Fachliche Mandatory-Ergebnisse bleiben zuerst;
  gleichartige weitere Ergebnisse folgen der HBF-Luftlinie und stabiler ID.
- [x] Stadtteilangaben werden zwar interpretiert, aber weder für Filter,
  Ranking, Marker noch Formulatorbehauptungen verwendet.
- [x] Der LLM-Selector ordnet keine rein räumlichen Brunnenresultate. Der
  Formulator erhält ausschließlich die finalen positiven Evidence-Ansichten.
- [x] Antwort/Karten enthalten höchstens drei Resultate; Marker enthalten alle
  zulässigen Resultate mit gültiger Geometrie.
- [x] Health, Interaktionsmetadaten, CLI, Frontend, I18n und Packaging bilden
  ausschließlich redigierte und implementierte Zustände ab.
- [x] WFS-IDs 1–4 bleiben ausgeschlossen; WP8C, Geolokalisierung, allgemeines
  Stadtteilranking, finales Safety-Paket und produktives Deployment bleiben
  unverändert.
- [x] Kein realer LLM-, STT- oder TTS-Aufruf erfolgt.

## Scope

### In scope

- Offizielle Leipziger-Wasserwerke-Seite, ihr verlinkter My-Maps-KML-Export und
  eine amtliche Leipziger Verwaltungsgrenze zur rein lokalen Stadtprüfung.
- Erweiterung der vorhandenen Infrastrukturmodelle um Trinkbrunnen.
- Eigener, zur Toilettenarchitektur konsistenter Quellen-/Releaseadapter unter
  Wiederverwendung der gemeinsamen Hash-, Atomaritäts- und räumlichen Helfer.
- Kuratierte Runtime-Projektion, KB-Fingerprint, Candidate-/Resultatordnung,
  Evidence/Grounding, API-Karten/Marker, Frontend, Health, CLI und Tests.
- Unmittelbar betroffene README- und technische Dokumentationsabschnitte.

### Out of scope

- Mobile „Brunnos on Tour“ als Runtime-Ergebnisse.
- Nutzerposition, Route, Gehzeit, allgemeines Stadtteil- oder
  Entfernungsranking außerhalb des festen HBF-Ursprungs.
- Toiletten-/WFS-Quellumbau, neue LLM-Verträge außerhalb erforderlicher
  Evidence-Erweiterungen, abschließende Safety-Politik und Live-Providerchecks.
- Thesis- oder Präsentationsdateien.

## Repository review

### Current behavior

- `load_active_knowledge_base()` lädt einen kuratierten sozialen Bestand und
  unabhängig davon einen verifizierten Toilettenrelease. Beide Zustände gehen
  in denselben Runtime-Fingerprint ein.
- `QueryService._query_core()` leitet `Need.TOILET` vor der sozialen
  Kandidatenstufe in den deterministischen Infrastrukturpfad. Trinkwasser läuft
  bisher ausschließlich durch den sozialen `CandidateSelector` und findet nur
  Angebote mit positivem `drinking_water`-Beleg.
- `select_public_toilets()` trennt gesprochene/Kartenresultate (maximal drei)
  von der vollständigen Markermenge. `app/spatial.py` ist die einzige Quelle
  des HBF-Ursprungs und der Haversine-Berechnung.
- Der Toilettenrelease prüft Manifest, exakten Dateibestand, Einzeldateihashes,
  Rohhash, normalisierten Hash und reproduzierbare Normalisierung. Fallbacks
  werden nur über active/last_verified/previous_verified-Pointer oder den
  Paket-Bootstrap zugelassen.
- API, Formulatorvertrag, Grounding und Frontend kennen derzeit nur
  `social_offer` und `public_toilet`. Diese geschlossenen Positivlisten müssen
  kontrolliert um `drinking_fountain` erweitert werden.

### Quellenreview vor Implementierung

Abruf und Prüfung erfolgten read-only am 2026-08-02. Es wurden keine Nutzer-,
Session- oder Interaktionsdaten übertragen.

| Aspekt | Befund |
|---|---|
| Fachquelle | Leipziger Wasserwerke, `https://www.l.de/wasserwerke/leipziger-wasser/trinkwasserbrunnen/` |
| Geodatenquelle | Von der Fachseite verlinkte Google-My-Maps-Karte; reproduzierbarer KML-Export `https://www.google.com/maps/d/kml?mid=1X3y_V9KdgtfsEucc4T-tmNV_hYe8rdEP&forcekml=1` |
| Rohformat | KML 2.2, UTF-8, 12.665 Bytes, HTTP `text/xml; charset=utf-8` |
| Rohhash | SHA-256 `f7cef59936f4a8d5dbf801e4022670c396ffc8567a5163b4caaf39aa1d36adac` |
| Maschinenlesbare Felder | Ordner/Layertyp, Name, Beschreibung, Punktkoordinate; keine stabilen Anbieter-IDs, Gemeinde, Adresse als eigenes Feld, Aktualisierungszeit oder einzelner Betriebsstatus |
| KML-Bestand | 35 Punkte: 30 stationär, 5 mobil; Namen der stationären Punkte sind eindeutig, mobile Namen sind nicht eindeutig |
| Verwaltungsprüfung | Amtliches GeoJSON „Geodaten der Statistischen Bezirke der Stadt Leipzig“, EPSG:25833, 310 Polygone, 1.817.879 Bytes, SHA-256 `8914ae40b8e806d4d6210c9cab97f5d9f51a685a93670b23ff46a3ddf57452b1`, Last-Modified `2023-07-13` |
| Räumliches Ergebnis | 21 stationäre Punkte innerhalb Leipzigs; 9 stationäre Punkte außerhalb; alle 5 mobilen Punkte liegen geometrisch in Leipzig, bleiben aber fachlich ausgeschlossen |
| Außerhalb Leipzigs | Markranstädt/Strandbad, der nur als „Markt“ benannte Punkt östlich der Stadtgrenze, Zwenkauer Markt, Rathausstraße/Südstraße, Cospudener See, Naunhof, Großpösna, Borsdorf und Schkeuditz |
| Fachlich belegte globale Aussagen | Kostenlose Wasserspender; Anschluss an das Trinkwassernetz und regelmäßige Qualitätsprüfung; fest installierte Brunnen grundsätzlich nur April bis Oktober aktiv |
| Echtzeitgrenze | Webseite/Karte enthalten keinen belastbaren Echtzeit-Funktionsstatus pro stationärem Punkt. „Trinkwasser“ und saisonale Listung werden daher nicht als aktuelle Funktionsfähigkeit interpretiert. |
| Mobile Daten | KML enthält fünf Koordinaten und Datumsfragmente, aber keine eindeutigen ortsbezogenen Namen/IDs und kein explizites Jahr. Die Webseite nennt Orte und Zeiträume, die ohne Geocoding nicht sicher je KML-Punkt zugeordnet werden können. Alle mobilen Punkte bleiben ausgeschlossen. |
| Vollständigkeit | Die Webseite spricht allgemein von 32 weiteren Wasserspendern „in und um Leipzig“, der strukturierte Export enthält aktuell 30 stationäre Punkte. LENA behauptet deshalb keine Vollständigkeit. |
| Lizenz | Auf Fachseite und KML wurde keine ausdrückliche Open-Data-Lizenz für diesen Datensatz gefunden. Speicherung als `license_status=not_explicitly_specified`, `usage_scope=reviewed_prototype_source`; keine Open-Data-Behauptung. |
| Reproduzierbarkeit | KML und Verwaltungs-GeoJSON werden unverändert im Release gespeichert. Die fachlichen Webseitenbelege werden als kleine, manuell geprüfte strukturierte Evidenz mit URL/Abrufzeit gespeichert; ein unverändertes HTML-Rohsnapshot ist wegen der vorgeschalteten Zugriffsschutzseite nicht maschinell reproduzierbar. |
| Stabile IDs | Stationäre Source-IDs werden deterministisch aus dem eindeutigen normalisierten Quellnamen gebildet, nicht aus Koordinaten oder Reihenfolge. Dadurch bleibt eine Koordinatenänderung ein `modified`-Diff. Mobile, nicht runtimefähige Duplikate erhalten einen gehash­ten Quellenbezug. |

Die Quelle ist für einen klar als Prototyp gekennzeichneten, manuell aktivierten
Bootstrap vertretbar, wenn die genannten Lizenz-, Vollständigkeits-, Saison-
und Echtzeitgrenzen sichtbar bleiben. Sie ist nicht vertretbar als automatisch
promotete, vollständig lizenzierte oder echtzeitfähige Betriebsquelle.

### Relevant architecture and data flow

`drinking_fountain_sync fetch` → KML plus amtliche Grenzgrundlage → strikte
Normalisierung und fachliche Webseitenevidenz → Pending-Release → explizites
`activate` → pointergebundener Runtime-Loader → gefilterte
`KnowledgeBase.drinking_fountains` → `CandidateSelector` für belegte soziale
Wasserangebote plus deterministische Brunnenprojektion → fachliche Priority,
HBF-Luftlinie, stabile ID → max. drei Evidence/Karten und vollständige Marker →
bestehender Formulator oder lokalisierter Templatefallback.

### Existing structures to reuse

| Struktur | Pfad | Reuse decision |
|---|---|---|
| Infrastrukturmodelle | `app/infrastructure.py` | Um Trinkbrunnenmodelle erweitern; keinen zweiten Domänenmodellstamm anlegen |
| Hash/Atomarität | `app/release_storage.py` | Unverändert wiederverwenden |
| Pointer-Fallbackprinzip | `app/toilet_releases.py` | Quellartspezifisch nach demselben Vertrag implementieren; keine Verzeichnisheuristik |
| HBF/Haversine | `app/spatial.py` | Unverändert als einzige Distanzquelle verwenden |
| Fachliche soziale Kandidaten | `app/candidates.py` | Positive Wasserangebote und Mandatory-Rollen weiterverwenden |
| Ergebnisprojektion | `app/infrastructure_results.py` | Um gemeinsamen Wasserresultattyp erweitern |
| Evidence/Grounding | `app/formulation.py`, `app/grounding.py` | Geschlossene Positivlisten um belegte Brunnenfakten erweitern |
| Kartenvertrag | `app/models.py`, `app/static/app.js` | Eigenen Karten-/Markertyp ergänzen; sichere DOM-Erzeugung erhalten |
| Anwendungsressourcen | `app/resources/bootstrap/i18n/application_texts.json` | Nur notwendige Karten-/Fallbacktexte in fünf Sprachen ergänzen |
| Providerisolation | `tests/conftest.py` | Unverändert für sämtliche Tests und Smokes nutzen |

### Existing tests and commands

- Ausgangsprüfung:
  `python -m pytest tests/test_public_toilets.py tests/test_candidates.py tests/test_formulation.py tests/test_frontend_security.py -q`
  → 146 Tests bestanden.
- Relevante Tests: `tests/test_public_toilets.py`, `tests/test_candidates.py`,
  `tests/test_formulation.py`, `tests/test_api.py`,
  `tests/test_observability.py`, `tests/test_frontend_security.py`,
  `tests/test_packaging.py`, `tests/test_provider_isolation.py`.

### Working tree considerations

Branch `maintenance/repository-cleanup`, Ausgangscommit
`9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`. Der gesamte uncommittete Stand aus
WP1–WP8A gehört der Nutzerin. Keine dieser Änderungen darf zurückgesetzt,
überschrieben oder außerhalb der WP8B-Hunks formatiert werden. `.env` und
`.env.local` wurden nicht gelesen.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| KML-Punkte allein über Leipziger Bounding Box zulassen | Quelle heißt ausdrücklich „in und um Leipzig“; neun stationäre Punkte liegen im breiten WP8A-Rahmen, aber außerhalb der Stadt | Außerstädtische Marker und falsche lokale Behauptung | Amtliche Bezirksgeometrien als hashgebundene administrative Punkt-in-Polygon-Prüfung | 35-Punkte-Inventar mit 21/9/5-Aufteilung |
| KML-Reihenfolge als ID verwenden | KML hat keine Anbieter-ID; Reihenfolge ist nicht als stabil dokumentiert | Verschiebungen erzeugen flächige Scheindiffs | Eindeutigen stationären Namen slugifizieren; Koordinaten nicht in die ID aufnehmen | Reordering- und Koordinatenänderungstest |
| Alle fünf mobilen Punkte anhand ihrer Koordinaten der Webseitenliste zuordnen | Gleicher Name, KML-Beschreibung nur Zeitraum, Webseite nennt Orte getrennt | Geocoding/Zuordnung würde Fakten erfinden | Mobil vollständig in Runtime ausschließen und im Roh-/Normalisierungsstand behalten | Mobile-Exclusion- und Marker-Test |
| „April bis Oktober“ als aktuelle Funktionsfähigkeit behandeln | Fachseite beschreibt Saison, aber keinen Echtzeitstatus je Standort | Falsche „jetzt geöffnet/funktioniert“-Aussage | Saison, Trinkbarkeit und Operation getrennt; außerhalb Saison keine direkten Brunnenresultate, innerhalb stets Unsicherheitspolicy | Uhr-injizierte Saison- und Groundingtests |
| Wasser als zweite soziale Angebotsart modellieren | Brunnen haben keine soziale Zielgruppe/Leistungslogik | Vermischte Kurations- und Eignungsregeln | Infrastrukturtyp in bestehendem Infrastrukturmodell; Kombination erst in Resultatprojektion | Typ-, Candidate- und Payloadinventartests |
| LLM-Selector zwischen Brunnen einsetzen | Reihenfolge ist rein fachlich/räumlich bestimmt | Nicht reproduzierbare Geografie | Bypass `deterministic_spatial_ranking` | Providerdouble darf nicht aufgerufen werden |
| Den Webseiteninhalt bei jedem Runtime-Start abrufen | Zugriffsschutz, kein stabiler HTML-Vertrag | Kaltstart-/Verfügbarkeitskopplung | Manuell geprüfte, releasegebundene Evidenz; Live-Abruf nur im Wartungspfad | Offline-/Clean-Install-Smoke |
| Automatische Aktivierung bei identischem oder geändertem Fetch | Fachliche Prüfung ist vorgeschrieben | Ungeprüfte Quelle wird Nutzerbestand | Fetch ausschließlich Pending, Auto-Promote-Konfiguration ablehnen | Pointer- und CLI-Tests |

## Recommended approach

Die kleinste tragfähige Lösung erweitert die geschlossenen Infrastruktur- und
API-Verträge, lässt aber soziale Angebote, Toiletten und Trinkbrunnen als eigene
Quelltypen bestehen. Der neue Releaseadapter verwendet die bereits geprüften
Pointer-, Hash- und Atomaritätsregeln. Eine einzige Wasserresultatprojektion
verbindet danach nur positive soziale CandidateItems und runtimefähige Brunnen,
setzt Mandatory zuerst und sortiert alle übrigen rankbaren Ergebnisse mit der
zentralen HBF-Distanz. Dadurch entstehen weder eine zweite Wissensbasis noch
eine zweite räumliche Implementierung.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| My-Maps-Viewer-HTML scrapen | Nicht der strukturierte Export, instabil und schlechter reproduzierbar |
| Fehlende Adressen reverse-geocodieren | Nicht quellbelegt und ausdrücklich außerhalb des Pakets |
| Amtliche Grenze nur zur einmaligen manuellen Liste verwenden | Eine neue KML-Fassung wäre nicht reproduzierbar prüfbar |
| Trinkbrunnen in `OfferRecord` konvertieren | Vermischt Infrastruktur mit sozialer Kuration und Zielgruppenlogik |
| Toilet-Releasecode umfassend generisch refaktorieren | Für WP8B unnötig breit und risikoreich; gemeinsame Primitive existieren bereits |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/infrastructure.py` | Modify | Trinkbrunnen-, Quellen- und Normalisierungsvertrag | Hoch, geschlossenes Modell |
| `app/drinking_fountain_releases.py` | Create | Separater verifizierter Release-/Fallbackadapter | Hoch, neuer Wartungspfad |
| `app/drinking_fountain_sync.py` | Create | `status/fetch/validate/diff/activate` ohne Promotion durch Fetch | Mittel |
| `app/infrastructure_results.py` | Modify | Kombinierte Wasserresultate, Karten und Marker | Hoch, Auswahlpfad |
| `app/config.py`, `.env.example` | Modify | Quell- und Wartungskonfiguration, Auto-Promotion ablehnen | Mittel |
| `app/kb_loader.py` | Modify | Runtimeprojektion, Metadaten und Fingerprint | Hoch |
| `app/models.py` | Modify | Positive Karten-/Marker-/Responseverträge | Mittel |
| `app/formulation.py`, `app/grounding.py` | Modify | Brunnen-Evidence und Grounding | Hoch |
| `app/service.py` | Modify | Wasserbranch, Selectorbypass, Fallback und Observability | Hoch |
| `app/main.py`, `app/interactions.py` | Modify | Health, optionaler Fetchloop, minimierte Metadaten | Mittel |
| `app/static/app.js`, `app/static/styles.css` | Modify | eigener semantischer Karten-/Markertyp | Mittel |
| `app/resources/bootstrap/i18n/application_texts.json` | Modify | notwendige fünfsprachige UI-/Fallbacktexte | Daten |
| `app/resources/bootstrap/drinking_fountains/**` | Create | verifizierter Bootstrap mit Roh- und Normalisierungsartefakten | Daten, groß durch Grenz-GeoJSON |
| `MANIFEST.in`, `pyproject.toml` | Modify if needed | KML-Paketinventar ergänzen | Klein |
| `tests/test_drinking_fountains.py` | Create | Quelle, Release, Auswahl, Saison, API, Grounding | Hoch, Tests |
| vorhandene API/Health/Packaging/Frontendtests | Modify | geschlossene Inventare und Regressionen | Mittel |
| README und bestehende `docs/*.md` | Modify | tatsächlich implementierte Quelle, Grenzen und Betrieb | Mittel |

## Milestones

### Milestone 1: Review and design

- [x] Anhang, beide Skills, Repositoryanweisungen, Arbeitsbaum und WP1–WP8A-Pläne prüfen.
- [x] Aktiven Infrastruktur-, Candidate-, Formulator-, Karten-, Health- und Packagingpfad verfolgen.
- [x] KML, Fachseite und amtliche Grenzgrundlage read-only inventarisieren.
- [x] Quellenreview, Reuse-Entscheidungen und Dead Ends dokumentieren.

Evidence: dieser Plan; 146 grüne Ausgangstests; KML-/Boundary-Hashes und
35-Punkte-Inventar oben. Keine Quellcodedatei wurde vor diesem Plan geändert.

### Milestone 2: Implementation

- [x] Trinkbrunnenmodelle, Normalisierung, Diff, Release, Fallback und Bootstrap implementieren.
- [x] Runtime-KB, Fingerprint, Health und CLI verdrahten.
- [x] Wasser-Candidates, Saison, HBF-Ordnung, Evidence, Grounding und Fallback implementieren.
- [x] Karten-/Marker-/I18n-Verträge und minimierte Beobachtbarkeit ergänzen.
- [x] Plan mit tatsächlichen Entdeckungen aktualisieren.

### Milestone 3: Verification

- [x] Fokussierte Quellen-, Release-, Candidate-, Saison-, Grounding-, API-, Karten- und I18n-Tests ausführen.
- [x] Vollständige Suite und Syntaxprüfungen ausführen.
- [x] Wheel/sdist, sdist→Wheel, Clean-Install, Bootstrap und providerfreien Template-Smoke ausführen.
- [x] `git diff --check`, Ressourcenregistrierung und vollständigen WP8B-Diff reviewen.

### Milestone 4: Documentation

- [x] `code-documentation` auf den finalen Diff und nur die betroffenen bestehenden Dokumente anwenden.
- [x] Dokumentationsaussagen gegen Runtime, CLI und Tests verifizieren.
- [x] Betroffene Checks nach Dokumentationsänderungen erneut ausführen.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Quelle/Normalisierung | `python -m pytest tests/test_drinking_fountains.py -q` | 35 Roh-/Normaldatensätze, 21 runtimefähig, 9 außerhalb, 5 mobil ausgeschlossen |
| Regression | `python -m pytest tests/test_public_toilets.py tests/test_candidates.py tests/test_formulation.py tests/test_api.py tests/test_observability.py -q` | vorhandene soziale/Toilettenpfade unverändert |
| Providergrenze | `python -m pytest tests/test_provider_isolation.py -q` | kein externer LLM-/STT-/TTS-Transport |
| Full suite | `python -m pytest -q` | vollständig grün |
| Syntax | `python -m compileall -q app tests`; `node --check` falls verfügbar | keine Syntaxfehler |
| Distribution | `python -m build`; bestehende Packagingtests | Wheel/sdist/Neuaufbau/Clean-Install enthalten Bootstrap und KML |
| Runtime | isolierter Template-Smoke mit `LENA_ENV_FILE_MODE=disabled` | Wasserantwort max. drei Karten, 21 Brunnenmarker, keine Provideraufrufe |
| Diff | `git diff --check`; WP8B-Hunkinventar gegen Ausgangsstatus | keine Whitespacefehler, kein Fremdumfang |

## Rollback and recovery

Die Implementierung verändert keine aktiven lokalen Nutzerpointer und führt
keine automatische Promotion aus. Tests nutzen ausschließlich temporäre
Verzeichnisse. Der paketierte Bootstrap ist unveränderlich und kann durch
Rücknahme ausschließlich der WP8B-Hunks entfernt werden; sämtliche bestehenden
WP1–WP8A-Änderungen bleiben unangetastet. Ein fehlender oder beschädigter
Brunnenbestand degradiert nur den Brunnenbereich und darf weder soziale Angebote
noch Toiletten löschen.

## Progress log

- 2026-08-02 — Vollständige Anforderung und Skills gelesen; Arbeitsbaum und
  aktiver WP8A-Pfad geprüft.
- 2026-08-02 — Fachseite, KML/KMZ und amtliche Grenzgrundlage read-only
  inventarisiert; 21/9/5-Abgrenzung und Vollständigkeitsdifferenz bestätigt.
- 2026-08-02 — 146 betroffene Ausgangstests bestanden.
- 2026-08-02 — Plan als erste Repositoryänderung von WP8B angelegt.
- 2026-08-02 — KML-/Grenznormalisierung, 21-Punkte-Runtime, manuelle
  Releaseaktivierung, sicherer Pointerfallback und zusammengesetzter
  Wissensbasisfingerabdruck implementiert.
- 2026-08-02 — Deterministische Wasserprojektion, Saison, HBF-Ordnung,
  Evidence/Grounding, 3-Karten-/vollständige Markertrennung, Health, Frontend,
  I18n und 29 fokussierte Trinkbrunnentests ergänzt.
- 2026-08-02 — README, Architektur, Datenfluss, Konfiguration, Setup und
  Testdokumentation mit `code-documentation` gegen den aktiven Pfad aktualisiert.
- 2026-08-02 — Release- und Recordidentität abschließend über URL-, Hash- und
  Release-ID-Kreuzprüfungen gehärtet; 36 fokussierte Packaging-/Trinkbrunnentests
  und die vollständige Suite mit 589 Tests bestanden.

## Decision log

- Decision: Amtliche Bezirksgeometrie als administrative Leipzig-Prüfung
  mitspeichern.
  - Context: Der breite Koordinatenrahmen aus WP8A kann „in und um Leipzig“
    nicht fachlich trennen.
  - Choice: Reproduzierbare Punkt-in-Polygon-Prüfung gegen das offizielle
    EPSG:25833-GeoJSON.
  - Consequences: Der Bootstrap wird größer; Stadtzuordnung bleibt dafür lokal,
    quellgebunden und ohne Geocoding reproduzierbar.
- Decision: Alle mobilen Punkte bleiben normalisiert, aber runtime-ineligible.
  - Context: Zeiträume sind nicht eindeutig mit Jahr und Ortsidentität
    verbunden.
  - Choice: Kein mobiler Runtimepfad in WP8B.
  - Consequences: Kein Risiko abgelaufener oder falsch zugeordneter Marker.
- Decision: Saisonmonate sind Evidence, kein Echtzeitstatus.
  - Context: April–Oktober ist belegt, aktuelle Funktion je Brunnen nicht.
  - Choice: Außerhalb des Saisonrahmens keine direkten Brunnenresultate;
    innerhalb stets `operation_status=unknown` und Unsicherheitshinweis.
  - Consequences: Soziale Wasserangebote können außerhalb der Saison verbleiben;
    LENA verspricht nie aktuelle Funktion.

## Discoveries

- Die KML enthält keine stabilen Placemark-IDs und keine `ExtendedData`-Felder.
- Der Punkt „Cospudener See“ liegt laut amtlicher Bezirksgeometrie außerhalb
  Leipzigs, obwohl die Bezeichnung allein dies nicht sicher erkennen ließe.
- Die drei nächsten stationären Leipziger Punkte vom kanonischen HBF-Ursprung
  sind Katharinenstraße (605 m), EM-Brunnen (747 m) und Kurt-Masur-Platz (820 m).
- Die Fachseite ist über den Dokumentationsbrowser lesbar, ein gewöhnlicher
  HTTP-Abruf erhält jedoch eine vorgeschaltete 403-Zugriffsschutzseite. Ein
  automatischer HTML-Scraper wäre deshalb kein belastbarer Releasebestandteil.

## Final verification summary

- Acceptance requirements: vollständig erfüllt; keine bekannte Runtime- oder
  Release-Umgehung innerhalb von WP8B.
- Tests: 36 fokussierte Trinkbrunnen-/Packagingtests und 589 Tests der
  vollständigen Suite bestanden; eine bekannte Starlette/httpx-Warnung.
- Build: Wheel, sdist, sdist→Wheel und Clean-Install außerhalb des Checkouts
  bestanden; paketierter Bootstrap und Template-Smoke verifiziert.
- Syntax: Python-Compile und `git diff --check` bestanden; Node.js war lokal
  nicht verfügbar, statische Frontendtests sind bestanden.
- Manual verification: CLI `status` und `validate`, Quelleninventar,
  Karten-/Markertrennung und finaler Diff geprüft; keine LLM-, STT- oder
  TTS-Provideraufrufe.
- Documentation: README und betroffene technische Dokumente mit
  `code-documentation` gegen den implementierten Pfad aktualisiert.
- Residual risks: Lizenz nicht ausdrücklich spezifiziert; keine menschliche
  Prüfung neuer Fremdsprachentexte; keine Echtzeitfunktion; kein Anspruch auf
  vollständigen Brunnenbestand.
