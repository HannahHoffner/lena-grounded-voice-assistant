# Arbeitspaket 3: Deterministische Kandidatenbegrenzung

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-01
- Last updated: 2026-08-01

## Objective

Nach der strikt validierten Anfrageinterpretation begrenzt eine eigenstaendige, deterministische und erklaerbare Fachkomponente die kuratierte Runtime-Wissensbasis auf belegte direkte Angebote, Verweisstellen und bedingte Kandidaten. Sie trifft keine LLM-Auswahl, formuliert keine neue Dialogpolitik und verwendet weder Rohfelder noch ausgeschlossene WFS-Datensaetze.

## Acceptance contract

- [x] Der aktive Pfad lautet Interpreter -> validierte Bedarfsbeschreibung -> `CandidateSelector` -> bestehender Formulator oder Template.
- [x] Der Selector gibt einen strikt validierten Entscheidungsvertrag mit Status, Kandidatenrollen, Einschluss-/Ausschlussgruenden, fehlenden Fakten und angewandten Prioritaeten zurueck.
- [x] Eignung folgt ausschliesslich positiv kuratierten Leistungs-, Zielgruppen-, Zugangs-, Zeit- und Prioritaetsmerkmalen; Namen, Freitext und `source_index` sind keine Fachregelquelle.
- [x] WFS-IDs 1 bis 4 und ungepruefte Quelldaten koennen nicht in Auswahl, Prompt, Karten oder Marker gelangen.
- [x] U27, allgemeiner Schlafbedarf, Ruecke, Scharni, Helene, Alternative I, Mobile/Kuebel, Wasser, Toilette, Medizin und allgemeine Hilfe folgen den freigegebenen Paketregeln.
- [x] Ein positives Akutrisiko beendet die Anfrage weiterhin vor der Kandidatenstufe; Interpreterfehler sind ein eigener, nicht erfolgreicher Auswahlstatus.
- [x] Bestehende Session-Fingerprint-, Runtime-Fallback-, Packaging- und LLM-Positivlisten bleiben wirksam.
- [x] Fokussierte und vollstaendige Tests sowie Build, Clean-Install, Template-Smoke und Diff-Pruefung sind erfolgreich.

## Scope

### In scope

- Schema-validierte kuratierte Leistungs-, Zielgruppen-, Zugangs-, Verweis- und Prioritaetsmerkmale fuer die 26 Runtime-Angebote.
- Eigener Kandidatenvertrag und deterministischer `CandidateSelector`.
- Kontrollierter Alias- und UI-Hinweis-Kontext sowie explizit injizierbarer lokaler Zeitpunkt.
- Umstellung von `QueryService` auf die Kandidatenstufe und Entfernung des bisherigen Kategorie-zu-Retrieval-Adapters aus dem Primaerpfad.
- Minimale Rollen-/Grunddaten fuer den bestehenden Formulator; bedingte Angebote werden nicht als sicher passend ausgegeben.
- Tests und Aktualisierung bestehender Architektur-, Datenfluss- und Testdokumentation.

### Out of scope

- Arbeitspaket 4: verbindliche mehrstufige Rueckfragepolitik und dauerhafter Dialogzustand.
- Arbeitspaket 5: neue LLM-Kandidatenauswahl.
- Arbeitspaket 6: neue Antwortgenerierung oder umfassende Formulatorarchitektur.
- Import von Toiletten, Trinkwasserbrunnen oder Stadtteilgeometrien; Entfernungsranking.
- Endgueltige Safety-Fehlerpolitik, Kapazitaets- oder Echtzeitverfuegbarkeitsaussagen.
- Aenderungen an Thesis- oder Praesentationsdateien.

## Repository review

### Current behavior

`QueryService._query_core()` ruft zuerst `BlabladorProvider.interpret_query()` auf. Danach bildet `adapt_interpretation_to_legacy_category()` den Bedarf auf vier alte UI-Kategorien ab. `resolve_organization_alias()` kann Angebote frueh begrenzen, bevor `retrieve()` Freitext, Rohtext, Quellkategorien und `source_index` zum Ranking nutzt. Fuer Schlafen folgen weitere Namens-/Adressheuristiken aus `sleep_roles()` und `_sleep_policy_offers()`. `apply_temporal_policy()` enthaelt aktive `source_index`-Sonderfaelle. Diese Kette vermischt Nachweis, Eignung, Prioritaet und Textmatching und ist der zu ersetzende Primaerpfad.

### Relevant architecture and data flow

- API-Einstieg: `app/main.py:create_app()` -> `QueryService.query()`.
- Interpreter: `app/providers/llm.py:BlabladorProvider.interpret_query()` -> `app/interpreter.py:QueryInterpretation`.
- Runtime-Daten: `app/kb_loader.py:load_active_knowledge_base()` -> `app/curation.py:project_runtime_offers()` -> exakt 26 freigegebene `OfferRecord`-Objekte.
- Sessionkontext: `app/sessions.py:SessionStore.resolve()` verwirft veraltete oder fingerprintfremde Verlaeufe vor dem Interpreter.
- Alter Auswahlpfad: `app/interpreter.py:adapt_interpretation_to_legacy_category()` -> `app/curation.py:resolve_organization_alias()` -> `app/retrieval.py:retrieve()` -> Schlaf-/Zeit-Sonderregeln in `app/service.py`, `app/offer_roles.py` und `app/temporal.py`.
- Ausgabe: positiv gelistete `FormulatorOfferView`-Payloads oder lokalisierte Karten; Marker entstehen nur aus ausgegebenen Karten.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Strikter Interpretervertrag | `app/interpreter.py` | Als fachlichen Eingang verwenden; minimal um explizite Einzelleistungen erweitern, weil der grobe Bedarf Grundversorgungsarten nicht sicher trennt |
| Kurationskatalog und Runtime-Projektion | `app/curation.py`, `app/resources/bootstrap/curation/social_offers.json` | Um explizite Fachmerkmale erweitern |
| Runtime-Fingerprint und sicherer Loader | `app/kb_loader.py` | Bewahren; Katalogaenderung fliesst automatisch in den Fingerprint ein |
| Organisationsalias-Bindungen | `app/curation.py` | Nur als kontrollierten, kuratierten Auswahlkontext verwenden |
| LLM-Positivliste | `app/models.py`, `app/providers/llm.py` | Bestehende Formulatorsicht bewahren; Auswahlrollen nur im Routing-Kontext uebergeben |
| Lokalisierung, Karten und Marker | `app/i18n.py`, `app/maps.py` | Nur bereits sicher ausgewaehlte Angebote uebergeben |
| Provider-Test-Doubles | `tests/test_api.py`, `tests/test_interpreter.py` | Fuer Kontrollfluss ohne externe Aufrufe wiederverwenden |

### Existing tests and commands

- `python -m pytest tests/test_interpreter.py tests/test_api.py tests/test_curation.py tests/test_safety.py`
- `python -m pytest`
- Relevante Dateien: `tests/test_retrieval.py`, `tests/test_sessions.py`, `tests/test_session_persistence.py`, `tests/test_packaging.py`.

### Working tree considerations

Branch `maintenance/repository-cleanup`, Ausgangscommit `9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`. Der Arbeitsbaum enthaelt die vom Nutzer freigegebenen, nicht committen Aenderungen aus Arbeitspaket 1 und 2. Diese werden weder zurueckgesetzt noch als fremde Altlast bereinigt. Arbeitspaket 3 beruehrt nur die unten aufgefuehrten fachlich erforderlichen Pfade und trennt seinen Abschlussdiff inhaltlich von den bestehenden Aenderungen.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Neue Auswahl laeuft neben altem Retrieval | `QueryService` ruft derzeit immer `retrieve()` auf | Zwei widerspruechliche Wahrheiten | Alten Adapter und Retrievalaufruf aus dem aktiven Primaerpfad entfernen | Kontrollflusstest; Suche nach Aufrufen |
| Fachregeln bleiben in Namen/Freitext versteckt | `sleep_roles()`, `detect_target()`, `_score_offer()` | Nicht erklaerbare oder falsche Eignung | Kuratierte Enums fuer Leistungen, Zielgruppen, Zugang, Verweis und Prioritaet | Inventar- und Mutationsregressionstests |
| Zu groesse zentrale Dateien | `service.py` > 500 Zeilen, `llm.py` > 400 Zeilen | Schlechte Wartbarkeit | Neue kohesive Komponente in `app/candidates.py`; Service-Helfer entfernen | Zeilen-/Importreview |
| Unbekannt wird als passend behandelt | Alte Suche kennt keine dreiwertige Eignung | Unbelegte Empfehlung | Ausschluss, bedingt und irrelevant explizit modellieren | Alters-/Geschlechts-/Drogen-Tests |
| Bedingte Kandidaten werden sichtbar als passend dargestellt | Aktuelles UI kennt keine Kandidatenrolle | Irrefuehrende Karte/LLM-Aussage | Bedingte Kandidaten im Protokoll behalten, aber bis WP4 nicht an Ausgabe/Formulator geben | API- und Payloadtests |
| Zeitbezug leitet `tonight` als 18:00 ab | `build_temporal_context()` setzt implizite Uhrzeit | Helene koennte zu frueh empfohlen werden | Selector nutzt nur strukturierte explizite Uhrzeit; Tagesangabe bleibt getrennt | Helene-Zeitgrenztests |
| Wasser wird weiterhin auf Essen abgebildet | `adapt_interpretation_to_legacy_category()` | Unbelegte Wasserausgabe | Eigenes Need ohne Kategorieadapter; nur kuratierte `drinking_water`-Leistung | Wasser-/Brunnen-Tests |
| Alias enthaelt mehrere Angebote | A1 und Mobile sind Organisationsaliase | Willkuerliche Wahl | Aliasbindung als Filterbedingung; bei verbleibender Mehrdeutigkeit `clarification_recommended` | A1-/Kuebel-Tests |
| Interpreterfehler wird als erfolgreiche Interpretation behandelt | bisheriger Fallback setzt alte Kategorie fort | Unkontrollierte sensitive Ableitung | Eigener Status `interpreter_unavailable`, keine erfolgreiche Kandidatenentscheidung | Providerfehler-API-Test |
| Neue Katalogfelder brechen Packaging/Fingerprint | Katalog ist paketiert und hashgebunden | Start-/Installationsfehler | Manifest aktualisieren, Wheel/sdist/Install aus sdist pruefen | Packaging-Suite und Clean-Install |

## Recommended approach

Die Module `app/candidate_contract.py`, `app/candidate_context.py` und `app/candidates.py` trennen strikten Entscheidungsvertrag, kontrollierten Alias-/Zeitkontext und regelbasierte Auswahl. Die Daten, auf denen Regeln operieren, werden als geschlossene, schema-validierte Positivlisten im Kurationskatalog gepflegt und in `OfferRecord` projiziert. Der Selector wertet diese Merkmale in einer festen Reihenfolge aus: globale Runtime-Freigabe, Bedarf, explizite Zielgruppe/Zugang, explizite Zeit, Alias-/Ortskontext, kuratierte Prioritaet und stabile ID-Sortierung. `QueryService` behandelt Scope und Akutrisiko weiterhin vor der Auswahl, ruft dann genau diesen Selector auf und uebergibt nur direkte oder Verweiskandidaten an den bestehenden Formulator beziehungsweise die Kartenansicht.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Bestehendes Retrieval mit weiteren Gewichten erweitern | Freitext, Rohfelder und `source_index` blieben fachliche Wahrheitsquelle |
| Alle Regeln als ID-Pruefungen in Python kodieren | Fachliche Herkunft, Versionierung und spaetere Pflege waeren verstreut |
| Interpretervertrag um Tier-/Paar-/Aliasfelder erweitern | WP2-Vertrag ist freigegeben; WP3 soll keinen konkurrierenden Dialogzustand erzeugen |
| Bedingte Angebote sofort als Karten anzeigen | Die aktuelle UI kann fehlende Voraussetzungen nicht sicher kennzeichnen |
| Toiletten oder Brunnen aus sozialen Angeboten ableiten | Der freigegebene Bestand belegt diese Infrastruktur nicht |
| Distanz- oder Stadtteilranking simulieren | Geometrie-/Zustaendigkeitsarbeit ist ausdruecklich spaeter vorgesehen |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/candidate_contract.py` | Create | Strikter, versionierter Entscheidungsvertrag | Klein |
| `app/candidate_context.py` | Create | Kontrollierte Alias-, UI- und Zeitabhängigkeiten | Klein |
| `app/candidates.py` | Create | Kohesiver deterministischer Selector | Mittel; zentraler neuer Pfad, 324 Zeilen |
| `app/curation.py` | Modify | Strikte kuratierte Fachmerkmale validieren/projizieren | Mittel; Datenvertragsaenderung |
| `app/models.py` | Modify | Runtime-Fachmerkmale und minimales Interaktionsstatusfeld | Klein bis mittel |
| `app/resources/bootstrap/curation/social_offers.json` | Modify | Belegte Leistungen, Zielgruppen, Zugang, Verweise und Prioritaeten | Hoch fachlich; vollstaendiges Inventar testen |
| `app/service.py` | Modify | Alten Auswahladapter entfernen, Selector integrieren | Hoch; aktiver Kontrollfluss |
| `app/providers/llm.py` | Modify | Rollen-/Grundkontext fuer bestehenden Formulator binden | Klein |
| `app/interpreter.py` | Modify | Veralteten Kategorieadapter entfernen; konkrete explizite Leistung getrennt vom groben Bedarf modellieren | Klein, Vertrag/Prompt Version 2 |
| `app/offer_roles.py` | Modify/Delete | Namensheuristik aus aktivem Pfad entfernen | Klein; Referenzen pruefen |
| `app/temporal.py` | Delete | `source_index`-Fachregeln aus aktivem Auswahlpfad entfernen | Mittel |
| `app/retrieval.py` | Review only | Nicht mehr primaer; nur lexikalische Hilfsfunktionen und isolierte Altverträge belassen | Klein |
| `app/maps.py` | Modify | Standorte nur noch über kuratierte Ortstyp-/Zeitregeln zuordnen | Mittel |
| `app/main.py`, `app/interactions.py` | Modify | Vertragsversion in Health und redigierten Auswahlstatus im Forschungsprotokoll ausweisen | Klein |
| `tests/test_candidates.py` | Create | Vollstaendige Entscheidungs- und Regelmatrix | Hoch, aber isoliert |
| `tests/test_api.py`, `tests/test_curation.py`, `tests/test_interpreter.py`, `tests/test_safety.py` | Modify | Kontrollfluss- und Sicherheitsregression | Mittel |
| `docs/architecture.md`, `docs/data-flow.md`, `docs/testing.md`, `README.md` | Modify | Tatsae chlich aktiven WP3-Stand dokumentieren | Klein; erst nach Implementierung |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: aktiver Pfad und Dateninventar in `service.py`, `retrieval.py`, `offer_roles.py`, `temporal.py`, `curation.py` und dem paketierten Kurationskatalog geprueft.

### Milestone 2: Implementation

- [x] Kurationsschema und 26-Angebote-Inventar erweitern.
- [x] Strikten Kandidatenvertrag und Selector implementieren.
- [x] `QueryService` auf den einzigen neuen Primaerpfad umstellen.
- [x] Alte Fachheuristiken und den WP2-Uebergangsadapter aus dem aktiven Pfad entfernen.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

Evidence: `app/candidates.py` besitzt 324 Zeilen; Vertrag und Kontext sind in zwei kleine kohesive Module getrennt. Der aktive Service importiert weder `retrieve()` noch die entfernten Schlaf-/Zeitmodule. Die kuratierte Primärpriorität `u27_primary_contact` bleibt auch bei geänderter Angebots-ID wirksam.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run syntax/static checks.
- [x] Run full regression and build checks.
- [x] Verify imports, runtime path, packaging and clean installs.
- [x] Review final diff and LLM payload inventory.

Evidence: 305 Tests erfolgreich; fokussierte Kandidaten-/API-/Kurations-/Session-/Safety-/Observability-Suiten erfolgreich; `compileall`, `build --no-isolation`, 7 Packagingtests mit sdist-Wheel-Rebuild und Clean-Install sowie `git diff --check` erfolgreich. Das lokale Inventar bestätigte 26 Runtime-Angebote, 15 ID-freie Alias-Hinweise, 26 positiv gelistete Formulatorrecords und keine IDs 1 bis 4.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: README sowie Architektur-, Datenfluss- und Testdokumentation beschreiben Interpretervertrag 2, Kandidatenvertrag 1, Fehlerpfad und ausschließlich flüchtige Entscheidungsdetails.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Kandidatenvertrag und Fachregeln | `python -m pytest tests/test_candidates.py` | Alle Rollen, Status, Ausschluesse und Prioritaeten korrekt |
| API/Provider/Session/Safety | `python -m pytest tests/test_api.py tests/test_interpreter.py tests/test_curation.py tests/test_sessions.py tests/test_session_persistence.py tests/test_safety.py` | Neuer Kontrollfluss ohne Regression |
| Runtime- und Payloadinventar | fokussierte Curation-/Provider-Tests und lokales Inventarskript | 26 Runtime-Angebote; keine IDs 1-4/Rohfelder; nur ausgewaehlte IDs |
| Vollstaendige Regression | `python -m pytest` | Gesamte Suite erfolgreich |
| Syntax | `python -m compileall -q app` | Keine Fehler |
| Build | `python -m build --no-isolation` | Wheel und sdist erfolgreich |
| Clean install | Wheel aus sdist neu bauen und in temporaerer Umgebung installieren/testen | Paketressourcen und Runtime funktionieren ausserhalb des Checkouts |
| Template smoke | lokaler `create_app()`-/Query-Smoke ohne Provider | Kein externer Aufruf, sichere Kandidaten |
| Diff | `git diff --check` und Review gegen Ausgangscommit | Keine Whitespacefehler oder fremden Aenderungen |

## Rollback and recovery

Es gibt keine Datenmigration oder externe Mutation. Die Aenderung besteht aus Python-, JSON-, Test- und Dokumentationsdateien im Arbeitsbaum. Ein Rollback darf wegen der bestehenden Nutzerarbeit nicht mit Reset-Befehlen erfolgen; stattdessen waeren ausschliesslich die in diesem Plan dokumentierten WP3-Hunks gezielt rueckgaengig zu machen. Der unveraenderte gebundene WFS-Quellenrelease bleibt erhalten; nur der Kurationskatalog und dessen Paketmanifest werden erweitert.

## Progress log

- 2026-08-01 — Skills und Repository-Anweisungen vollstaendig gelesen; Arbeitsbaum und Ausgangscommit erfasst.
- 2026-08-01 — Aktiven Interpreter-, Alias-, Retrieval-, Schlaf-, Zeit-, Formulator-, Karten- und Sessionpfad verfolgt.
- 2026-08-01 — Alle 26 Runtime-Angebote mit Quellleistungen, Zeiten, Hinweisen und bestehenden Kurationsentscheidungen inventarisiert.
- 2026-08-01 — Plan vor der ersten Quellcodeaenderung angelegt.
- 2026-08-01 — Alle 26 Runtime-Angebote positiv mit Ortstyp, Leistungen, Zielgruppen, Zugang, Verweis, Zeit und Prioritaet modelliert.
- 2026-08-01 — Alten Kategorie-/Retrievalpfad, Namensrollen und `source_index`-Zeitmodul aus dem aktiven Anwendungspfad entfernt.
- 2026-08-01 — Strikten Kandidatenvertrag 1, sprachunabhängigen Selector und redigierte Formulatorbindung integriert.
- 2026-08-01 — Roßplatz-Priorität von einer festen Python-ID in die katalogisierte Regel `u27_primary_contact` verschoben.
- 2026-08-01 — Vollständige Suite, Syntax, Wheel/sdist, Neuaufbau aus sdist, Clean-Install, Template-Smoke, Payloadinventar und Diff-Prüfung erfolgreich abgeschlossen.

## Decision log

- Decision: Fachliche Auswahlmerkmale werden positiv im Kurationskatalog modelliert.
  - Context: Bestehende `needs` sind zu grob; aktuelle Regeln lesen Namen, Freitext und `source_index`.
  - Options: Python-ID-Regeln, Freitextheuristik erweitern, kuratierte strukturierte Merkmale.
  - Choice: Kuratierte strukturierte Merkmale.
  - Consequences: Nachvollziehbare Herkunft und strikte Validierung; Katalog und Manifest muessen aktualisiert werden.
- Decision: Mehrdeutige oder bedingte Angebote bleiben im Entscheidungsprotokoll, werden aber vor WP4 nicht als passende Karten oder Formulatorangebote ausgegeben.
  - Context: Die aktuelle UI besitzt keine sichere Darstellung fehlender Voraussetzungen.
  - Options: Als Karte anzeigen, ganz verwerfen, intern bedingt halten.
  - Choice: Intern bedingt halten.
  - Consequences: Keine falsche Eignungsbehauptung; spaetere Dialogpolitik kann die Kandidaten uebernehmen.
- Decision: Tier-/Paarhinweise und unvalidierte Stadtteile werden nicht durch neue Freitextlogik zu Eignungsfakten.
  - Context: Der freigegebene Interpretervertrag strukturiert diese Merkmale noch nicht.
  - Choice: Vorhandene unsichere Hinweise nur als nicht aufgeloeste Bedingung protokollieren.
  - Consequences: Kontrollierte Grenze statt unbelegter Auswahl; Erweiterung bleibt spaeteren Paketen vorbehalten.
- Decision: Der Interpretervertrag erhält mit Version 2 eine begrenzte Liste ausdrücklich verlangter Einzelleistungen.
  - Context: `food`, `advice` und `general_help` unterscheiden Essen, Wasser, Hygiene, Dusche, Wäsche, Kleidung und Postservice nicht hinreichend; der Selector darf diese Leistung nicht selbst aus Freitext erraten.
  - Choice: Explizite Leistung getrennt vom breiten Bedarf interpretieren und streng validieren.
  - Consequences: Fachliche Positivfilterung bleibt sprachunabhängig; der Interpreter wählt weiterhin keine Angebote und sieht keinen Angebotsindex.
- Decision: Der vollständige Kandidatenentscheid bleibt flüchtig; persistiert wird nur der Status.
  - Context: Fakten, Ausschlüsse und Reason Codes würden sensible Angaben und interne IDs unnötig im Forschungsprotokoll duplizieren.
  - Choice: `candidate_selection_status` in Interaktionsschema 3; redigierter Kandidatenkontext nur für den laufenden Formulatoraufruf.
  - Consequences: Operativer Pfad ist beobachtbar, ohne das Protokoll um neue sensible Inhalte zu erweitern.

## Discoveries

- `tonight` wird in der bisherigen Zeitlogik implizit zu 18:00 Uhr; diese Ableitung darf Helene nicht freischalten.
- Die bisherigen medizinischen Zeitregeln adressieren alte `source_index`-Werte 15 und 30, waehrend Runtime-IDs stabil 15 und 25 sind.
- Der Hilfebus ist Runtime-ID 21 und belegt Verweisberatung, Grundversorgung, Essen/Getraenke sowie Vermittlung an Notuebernachtungen.
- Die Runtime-Geometrie von Scharni bleibt nach Adressaenderung bewusst `null` und darf durch die Kandidatenstufe nicht rekonstruiert werden.
- Der paketierte `runtime_manifest.json` bindet den unveränderten normalisierten Quellrelease, nicht den separat gehashten Kurationskatalog; deshalb benötigt die fachliche Katalogerweiterung keine Manifeständerung. Der Runtime-Fingerprint enthält weiterhin beide Hashes.
- Die alte Aliasauflösung in `app/curation.py` war nach der Serviceumstellung nur noch testseitig erreichbar und wurde entfernt; genau eine kontrollierte Aliasbegrenzung verbleibt in `app/candidate_context.py`.

## Final verification summary

- Acceptance requirements: erfüllt; Arbeitspaket 4 bis 6 und Infrastrukturimporte wurden nicht begonnen.
- Tests: 305/305 erfolgreich; nur bestehende Starlette-Deprecation-Warnung.
- Build: Wheel und sdist erfolgreich; Wheel aus sdist erneut gebaut und außerhalb des Checkouts installiert.
- Manual verification: aktiver Pfad enthält keinen Aufruf von altem Retrieval, Aliasresolver, Namensrollen, Temporalmodul oder `source_index`; LLM-Payloadinventar positiv gelistet.
- Documentation: README, Architektur, Datenfluss, Tests und dieser Plan entsprechen dem implementierten Stand.
- Residual risks: Linguistische Providerqualität ist mangels realem Aufruf nicht belegt; der Interpreterfehlerstatus besitzt noch keine abschließende Safety-Politik; bedingte Kandidaten warten auf WP4; Stadtteilvalidierung, Entfernung, Toiletten/Brunnen und LLM-Kandidatenauswahl bleiben bewusst späteren Paketen vorbehalten.
