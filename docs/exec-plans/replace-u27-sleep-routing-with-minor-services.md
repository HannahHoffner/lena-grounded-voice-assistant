# Execution Plan: U18-Schlaflogik und verifizierte Jugendnotangebote

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-20
- Last updated: 2026-08-20

## Objective

LENA behandelt Schlafanfragen nicht mehr nach einer U27-Sonderroute. Minderjährige
erhalten belegte VKKJ-Schutz- und Übernachtungsangebote; Volljährige werden nach
den kuratierten Erwachsenenregeln zu Rücke beziehungsweise Scharni geführt.
Andere Angebote bis 26 werden nur bei ausdrücklich genanntem Jugendangebot,
Jugendhilfebedarf oder passendem Alias aktiviert.

## Acceptance contract

- [x] Alter 18 bis 26 aktiviert bei Schlafen keine Jugendstreetwork-Angebote.
- [x] Volljährige Männer erhalten Rücke, volljährige Frauen Scharni.
- [x] Alter 14 bis 17: Kontakt- und Notschlafstelle zuerst, Jugendnotdienst ergänzend.
- [x] Alter 12 bis 13: Jugendnotdienst zuerst; die Notschlafstelle ab 14 wird nicht als geeignet dargestellt.
- [x] Nur „unter 18“ ohne Zahl: Jugendnotdienst als sicher belegter Kontakt; keine Alterszahl erfinden.
- [x] Explizite Schutz-/Krisenlage priorisiert den Jugendnotdienst; Akutgefahr bleibt im bestehenden Safety-Pfad.
- [x] Hilfebus bleibt bei minderjährigem Schlafbedarf ergänzender Vermittlungskontakt, nicht Übernachtungsstelle.
- [x] Jugendangebote bis 26 erscheinen nur bei explizitem Jugendbezug oder eindeutigem Alias; ein bekanntes Alter allein reicht nicht.
- [x] Neue Website-Angebote besitzen getrennte Quelle, Provenienz, Organisation, Standorte und ServiceOffers.
- [x] Keine WFS-Rohdaten, Thesis- oder Präsentationsdateien werden verändert.
- [x] Genau acht fehlende Übersetzungen der beiden neuen VKKJ-Angebote werden
  für `en`, `pl`, `ro` und `ru` erzeugt und einzeln validiert.
- [x] Die 104 vorhandenen Übersetzungsrecords bleiben byte-inhaltlich
  unverändert; kein bestehendes Angebot wird erneut übersetzt.
- [x] Neue Records bleiben ehrlich `machine`/`valid` und erhalten keine
  menschlichen Reviewmetadaten.
- [x] Der Schlafdialog zeigt ausschließlich „Ich bin unter 18“ und
  „Ich bin eine Frau“; es gibt keinen Erwachsenenbutton.
- [x] Die Frauenauswahl setzt ausschließlich `gender=female` und erfindet kein
  Alter oder Erwachsenenmerkmal. Die vorhandene kurze Altersklärung bleibt
  dafür erreichbar.

## Scope

### In scope

- Strukturierte offizielle Quellrecords für die beiden VKKJ-Angebote.
- Kurationskatalog, Runtime-Projektion und Fingerprintbindung dieser Records.
- Interpretervertrag für Minderjährigenstatus und expliziten Jugend-/Schutzbedarf.
- CandidateSelector, Schlafdialog, Formulator-/Kartenpfad und fünfsprachige Dialogressourcen.
- Providerfreie Tests, Packaging und bestehende technische Dokumentation.

### Out of scope

- Live-Provideraufrufe oder automatische Website-Aktualisierung.
- Klinische oder kinderschutzfachliche Bewertung jenseits der belegten Angebotsrollen.
- Allgemeines geografisches Ranking oder neue Safety-Politik.
- Formale institutionelle Freigabe oder sprachliche Humanprüfung.
- Neugenerierung, sprachliche Überarbeitung oder Statusänderung bestehender
  Übersetzungen sowie UI-, Dialog- und Fallbacktexte.

## Repository review

### Current behavior

`CandidateSelector.select()` setzt `u27` bei Alter bis 26 und priorisiert dann
alle Angebote mit `u27_referral_first`; bei Schlafen wird Roßplatz mandatory.
Der Schlafdialog fragt nach „Frau“ und „unter 27“. Daher wird eine 24-jährige
Person allein aufgrund des Alters zu Jugendstreetwork geführt. Die beiden
VKKJ-Angebote fehlen vollständig.

### Relevant architecture and data flow

`interpret_query()` → validierte `ExplicitFacts`/`explicit_service_requests` →
`CandidateSelector` → `choose_dialog()` → LLM-Selector → Evidence/Formulator →
Karten/Marker. Die soziale Runtime-KB entsteht ausschließlich durch
`load_active_knowledge_base()` und `project_runtime_offers()` aus gebundenem
WFS-Release plus Kurationskatalog.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| `SourceReference`, `Organization`, `Location`, `ServiceOffer` | `app/curation.py` | für VKKJ-Provenienz und Runtime-Angebote erweitern |
| strikt validierte Quellmodelle | Toiletten-/Brunnenquellen | kleines paketiertes Official-Source-Modell nach gleichem Muster |
| `ExplicitFacts` und `RequestedService` | `app/interpreter.py` | Minderjährigenstatus und expliziten Jugend-/Schutzbezug ergänzen |
| `CandidateSelector` | `app/candidates.py` | U27-Schlafpriorität entfernen; Jugendgate und U18-Priorität integrieren |
| bestehende Session-/Dialogverwaltung | `app/dialogue*.py` | Schlafdialog ersetzen, keine zweite Sessionlogik |
| `application_texts.json` | paketierte i18n-Ressource | fünfsprachige Choice-/Prompttexte aktualisieren |

### Existing tests and commands

- `tests/test_candidates.py`, `tests/test_dialogue.py`, `tests/test_api.py`
- `tests/test_interpreter.py`, `tests/test_llm_selection.py`, `tests/test_formulation.py`
- `tests/test_curation.py`, `tests/test_packaging.py`, Session-/Safety-Regressionen
- `python -m pytest -q`, `python -m compileall -q app tests`, `git diff --check`

### Working tree considerations

Der Branch `maintenance/repository-cleanup` auf
`fbcc85aa1d4c3eeca096d5a67e39f9df7580a5b2` enthält umfangreiche Änderungen der
Nutzerin, auch in allen zentralen Pfaden. Nur abgegrenzte neue Hunks werden
ergänzt; vorhandene Änderungen werden nicht zurückgesetzt oder umformatiert.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| U27 lediglich in U18 umbenennen | übrige Jugendangebote bleiben bis 26 berechtigt | falsche Schlafroute oder Verlust legitimer Jugendtreffs | Schlafroute und Jugendangebots-Aktivierung getrennt modellieren | Alters-/Intentmatrix |
| Alter 18–26 als Jugendintention behandeln | aktueller `u27`-Boolean tut genau dies | ungewollte Jugendangebote | explizites strukturiertes Jugendservice-Signal verlangen | Interpreter-/Candidate-Test |
| Website-Angebote als WFS-ID fingieren | Projektion verlangt derzeit WFS-ID-Gleichheit | falsche Provenienz, Hashbindung unvollständig | eigene schema-validierte Official-Source-Records vor gemeinsamer Projektion | Loader-/Fingerprinttest |
| „unter 18“ auf Alter 17 abbilden | kein exaktes Alter genannt | erfundener sensibler Fakt | eigener nullable Minderjährigenstatus; Zahl bleibt `null` | Vertragstest |
| Notschlafstelle jedem Minderjährigen empfehlen | Betreiber belegt 14–18 | ungeeignete Empfehlung für unter 14 | exakte Altersschranke; bei unbekannter U18-Zahl Jugendnotdienst zuerst | Candidate-/Groundingtest |
| Jugendnotdienst als gewöhnlichen Schlafplatz darstellen | Quelle beschreibt Schutz/Inobhutnahme | falsches Leistungsversprechen | Rolle `referral_contact`/Schutzdienst; Notschlafstelle ist `direct_service` | Formulator-/Kartentest |
| temporären Schließhinweis dauerhaft übernehmen | Website nennt Ende 05.07.2026 | bereits abgelaufene Sperre | im Quellenbeleg dokumentieren, nicht Runtime-Verfügbarkeit | Dateninventar |

## Recommended approach

Ein kleiner paketierter, schema-validierter Official-Source-Katalog ergänzt den
unveränderten WFS-Release vor der einzigen Runtime-Projektion. Sein Hash fließt
in den Runtime-KB-Fingerprint ein. Der Interpreter trennt `age_group=under_18` von
einem expliziten Jugend-/Schutzservice. Der CandidateSelector nutzt Minderjährigkeit
nur für den neuen Schlafpfad und aktiviert sonstige U27-Angebote nur durch das
explizite Servicesignal oder einen eindeutigen Alias.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| VKKJ-Daten nur als Python-Konstanten | umgeht Wissensbasis, Provenienz, Übersetzung und Grounding |
| vorhandenen WFS-Bootstrap verändern | würde einen externen Ursprung als WFS ausgeben und die Releasebindung verfälschen |
| Jugendabsicht per Python-Keywordliste erkennen | dupliziert den LLM-Interpreter und ist mehrsprachig fragil |
| alle unbekannten Altersfälle als erwachsen markieren | unbekannt ist kein explizites Faktum; Minderjährige könnten falsch geroutet werden |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/official_offer_source.py` | Create | validierter externer Quellkatalog | mittel |
| `app/resources/bootstrap/official/verified_offers.json` | Create | öffentliche VKKJ-Quelldaten | mittel |
| `app/curation.py`, Kurationskatalog | Modify | externe Angebote und Regeln | mittel |
| `app/kb_loader.py` | Modify | eine gemeinsame Projektion und Fingerprint | mittel |
| Interpreter-/Candidate-/Dialogmodule | Modify | neue strukturierte Entscheidungslogik | mittel/hoch |
| i18n- und Übersetzungsressourcen | Modify | fünfsprachige Dialog-/Kartenanzeige | mittel |
| relevante Tests | Modify/Create | Vertrags-, Daten-, Auswahl- und Regressionsevidence | hoch |
| `docs/architecture.md`, `docs/data-flow.md` | Modify | tatsächliche neue Fachlogik | klein |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: offizieller VKKJ-Beleg und Codepfad in diesem Plan.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run lint/format/type checks.
- [x] Run integration/build checks where relevant.
- [x] Verify registration, imports, routes, configuration, and packaging.
- [x] Review final diff.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Alters-/Intentmatrix | fokussierte Candidate-/Dialogtests | U18/Erwachsene/Jugendintention korrekt getrennt |
| Daten und Provenienz | Curation-/Loader-/Packagingtests | VKKJ-Records validiert, in einer Runtime-KB, Fingerprint gebunden |
| API/Formulator/Karten | providerfreie Doubles | richtige Rollen, Reihenfolge, Fakten und Karten |
| Regression | `python -m pytest -q` | vollständige Suite grün |
| Static quality | `python -m compileall -q app tests`; `git diff --check` | keine Fehler |

## Rollback and recovery

Keine Migration oder externer Abruf. Neue paketierte Quellrecords und ihre
Kurationsprojektion sind atomar mit dem Code auslieferbar; der unveränderte
WFS-Release bleibt reproduzierbar. Bei Validierungsfehler startet keine
ungefilterte oder teilweise Runtime-KB.

## Progress log

- 2026-08-20 — Offizielle Quellen und aktiven U27-/Dialog-/Runtimepfad geprüft;
  Plan vor Quellcodeänderungen erstellt.
- 2026-08-20 — Betreiberquelle, Hashbindung, Interpreter-, Kandidaten-, Dialog-,
  Karten- und Übersetzungsfallbackpfad implementiert; vollständige Suite grün.
- 2026-08-20 — Folgeauftrag geprüft: Die CLI kann über `--offer-ids` und
  `--languages` exakt auf acht fehlende Records begrenzt werden. Bestehende
  valide Records werden ohne `--force` übersprungen; der Runtime-Store wird
  atomar geschrieben und anschließend kontrolliert in den Paketspiegel übernommen.
- 2026-08-20 — Blablador war bei gezielten Versuchen nicht verfügbar
  (`translation_http_error`/`translation_timeout`); es wurde kein ungültiger
  Record übernommen. Acht Codex-gestützte Maschinenübersetzungen wurden danach
  gegen denselben Prompt-4-Vertrag erstellt, lokal validiert und atomar in
  Runtime-Store und Paketspiegel übernommen. Keine Humanfreigabe wurde gesetzt.
- 2026-08-20 — Folgeänderung am Schlafdialog geprüft. Das bisherige technische
  Choice `adult_female` koppelt Frau und Volljährigkeit und wäre bei der neuen
  Beschriftung fachlich falsch. Empfohlen ist ein neues stabiles Choice
  `female`, das nur das ausdrücklich gewählte Geschlecht übernimmt; Freitext,
  Sprache und die nachgelagerte Altersklärung bleiben unverändert.
- 2026-08-20 — Schlafdialog auf genau `under_18` und `female` begrenzt,
  Frauenauswahl ohne Altersannahme umgesetzt, die anschließende Altersfrage auf
  die U18-Grenze korrigiert und die fünf lokalisierten API-Ausgaben getestet.

## Decision log

- Decision: Reiner Schlafbedarf 14–17 priorisiert die Jugend-Notschlafstelle;
  Schutz-/Krisenbezug priorisiert den Jugendnotdienst.
  - Context: Nutzerin bestätigte die vorgeschlagene fachliche Reihenfolge.
  - Choice: deterministische Rollen/Prioritäten aus kuratierten Regeln.
  - Consequences: kein LLM entscheidet über Schutz- oder Altersgrenzen.
- Decision: Ein bekanntes Alter bis 26 aktiviert Jugendangebote nicht.
  - Context: Jugendtreffs bleiben offen, sollen aber nur ausdrücklich gesucht werden.
  - Choice: explizites Interpreter-Service-Signal oder Alias als Gate.
  - Consequences: Erwachsenenvoreinstellung ohne erfundenes Altersfaktum.

## Discoveries

- Die Kontakt- und Notschlafstelle belegt 14 bis unter 18 und 22:00–10:00 Uhr.
- Der Jugendnotdienst belegt 12 bis unter 18 und grundsätzlich 24/7; der auf der
  Webseite sichtbare Schließhinweis endete am 05.07.2026.
- Bestehende 104 Maschinenübersetzungen blieben inhaltlich unverändert und
  wurden nach Positivprüfung an den neuen Kurationshash gebunden. Die acht
  Fremdsprachenkarten der zwei neuen Angebote sind maschinell erzeugt und
  technisch validiert, aber weiterhin nicht menschlich sprachlich geprüft.
- Review der Folgeänderung: Der vorhandene Providerpfad überträgt ausschließlich
  maskierte `short_description`, `services`, `opening_hours_raw` und `notes`.
  Geschützte Tokens werden vor dem Provider ersetzt und vor Speicherung
  wiederhergestellt; Schema-, Listen-, Token- und Skriptprüfung laufen vor dem
  atomaren Write. Ein separater Übersetzungspfad wäre daher ein Dead End.

## Final verification summary

- Acceptance requirements: erfüllt.
- Tests: vollständige Pytest-Suite sowie fokussierte Vertrags- und
  Integrationsprüfungen bestanden.
- Build: Wheel, sdist, sdist-Wheel und Clean-Install über Packagingtests
  bestanden; neue Betreiberressource ist paketiert.
- Documentation: Architektur, Datenfluss, Testinventar, README und dieser
  Ausführungsplan entsprechen dem finalen Übersetzungsbestand.
- Residual risks: Die acht neuen Fremdsprachenkarten besitzen keine menschliche
  Sprachprüfung; keine verifizierten Koordinaten für die beiden VKKJ-Angebote,
  daher bewusst keine Marker oder Distanzwertung.
