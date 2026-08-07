# Arbeitspaket 9 (Methodikkapitel-Nummerierung): Räumliche Auswahl — Hbf-Referenzkoordinate als Settings-Wert

## Status

- State: Complete
- Owner: Claude
- Created: 2026-08-04
- Last updated: 2026-08-04

## Einordnung und Zuschnitt

Dies ist **nicht** dasselbe wie `work-package-9a-final-safety-policy.md`,
`work-package-9b-controlled-live-provider-evaluation.md` oder
`work-package-9c-test-clock-determinism.md` — jene WP9A/9B/9C sind Codex'
eigene Datei-Nummerierung für Safety-Policy, Live-Evaluation und
Testdeterminismus. Dieses Dokument setzt das inhaltliche „Arbeitspaket 9:
Räumliche Auswahl" aus dem ursprünglichen Methodikkapitel-Auftrag um, mit
einem vom Nutzer ausdrücklich korrigierten Zuschnitt:

> Fachliche Eignung hat Vorrang vor geografischer Nähe. Ohne genannten
> Stadtteil: Infrastrukturangebote nach Entfernung vom Leipziger Hauptbahnhof
> sortieren, Hbf-Referenzkoordinate zentral konfigurieren, verwendete
> Distanzmethode dokumentieren. [...]

Stadtteillogik wurde vom Nutzer für den aktuellen Stand explizit als
„vorerst irrelevant" zurückgestellt und ist **nicht** Teil dieses Pakets.

## Audit-Ergebnis (vor dieser Änderung)

Ein Read-only-Audit ergab: Fachliche Eignung vor Distanz, Hbf-Distanzsortierung
selbst und die Dokumentation der Distanzmethode (Luftlinie) waren bereits
vollständig umgesetzt (`app/result_ordering.py`, `app/infrastructure_results.py`,
`app/spatial.py`, Tests `test_mandatory_and_fachpriority_precede_distance` u. a.).
Einzige Lücke: Die Referenzkoordinate `app/spatial.py::LEIPZIG_HBF` war zwar an
einer einzigen Stelle definiert (keine Duplikate), aber als Python-Literal statt
als `Settings`/ENV-Konfigurationswert — ein bereits selbst dokumentierter
offener Punkt (`docs/architecture/codebase-review.md`). Auf Rückfrage hat der
Nutzer sich für die Settings/ENV-Variante entschieden.

## Acceptance contract

- [x] `Settings.hbf_latitude`/`hbf_longitude` sind neue Felder mit Standard
  `51.34556`/`12.38222` (identisch zu `LEIPZIG_HBF`, also keine
  Verhaltensänderung ohne explizite Konfiguration).
- [x] `HBF_LATITUDE`/`HBF_LONGITUDE` werden atomar als Paar gelesen: fehlt
  einer, bleibt der andere beim Standard; ist das Paar kein gültiges
  Fließkommazahlenpaar oder liegt es außerhalb des Leipziger
  Umgebungsrahmens (51.1-51.6 / 12.0-12.8), wird das gesamte Paar auf den
  Standard zurückgesetzt statt einen aus zwei Quellen gemischten Ursprung zu
  erzeugen.
- [x] `Settings.__post_init__` weist ein explizit konstruiertes, ungültiges
  Koordinatenpaar hart ab (`ValueError`), analog zu den bestehenden
  Timeout-/Grenzwertprüfungen.
- [x] `app/spatial.py` bleibt eine reine, konfigurationsfreie Geometrie-
  Bibliothek; `LEIPZIG_HBF` bleibt der eingebaute Standard- und Testwert für
  jeden Aufruf ohne explizites `origin`.
- [x] `QueryService` löst den tatsächlichen Ursprung einmal pro Prozess aus
  `Settings` auf (`self.hbf_origin`) und reicht ihn explizit an jede Stelle
  weiter, die bisher `LEIPZIG_HBF`/`distance_from_hbf` ohne Parameter
  verwendet hat: `order_social_results`, `build_map_data`,
  `select_drinking_water_results`, `drinking_fountain_card`,
  `drinking_water_map_data`, `select_public_toilets`, `toilet_card`,
  `toilet_map_data`.
- [x] Fachliche Eignung bleibt unverändert vorrangig vor Distanz (keine
  Änderung an `order_social_results`s Sortierschlüsselreihenfolge).
- [x] Bestehende Tests, die ohne explizites `origin` aufrufen, bleiben
  unverändert grün (Standardwert identisch zum bisherigen `LEIPZIG_HBF`).

## Implementation

`origin: MapOrigin = LEIPZIG_HBF` wurde als Keyword-Parameter durch die
gesamte Aufrufkette gereicht (`app/spatial.py::distance_from_hbf` →
`app/maps.py::build_map_data`/`offer_stand_destinations`/`_stand_destination`
→ `app/result_ordering.py::social_result_distance`/`order_social_results` →
`app/infrastructure_results.py`s sechs betroffene Funktionen). `app/service.py`
baut in `QueryService.__init__` einmalig
`self.hbf_origin = LEIPZIG_HBF.model_copy(update={"latitude": ..., "longitude": ...})`
aus `Settings` und übergibt ihn an allen elf Aufrufstellen explizit. Kein
globaler mutierbarer Zustand, keine Umgebungsvariablen-Lesung außerhalb von
`app/config.py` — `app/spatial.py` bleibt dadurch weiterhin ohne
Seiteneffekte testbar.

## Verification

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Gezielte neue/angepasste Tests | siehe unten | grün |
| Volle Suite | `python -m pytest -q` | grün |
| Compile | `python -m compileall -q app tests` | COMPILE_OK |
