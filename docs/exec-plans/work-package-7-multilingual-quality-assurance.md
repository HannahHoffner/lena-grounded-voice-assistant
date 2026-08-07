# Arbeitspaket 7: Übersetzungs-, Lokalisierungs- und Mehrsprachen-QA

## Status

- State: Completed
- Owner: Codex
- Created: 2026-08-01
- Last updated: 2026-08-01

## Objective

LENA unterscheidet nach diesem Paket nachvollziehbar zwischen gespeicherten
Kartenübersetzungen, statischen Anwendungsressourcen und dynamischen
LLM-Antworten. Kartenübersetzungen besitzen eine versionierte Identität,
getrennte sprachliche und automatisierte Integritätsstatus sowie einen
atomaren Reviewprozess. Die Runtime verwendet nur gemäß expliziter Policy
zulässige und lokal valide Übersetzungen. Ein reproduzierbarer synthetischer
Szenario- und Reviewpfad bereitet die spätere menschliche und ausdrücklich
freizugebende Live-Prüfung vor, führt aber in diesem Paket keinen Provideraufruf
aus.

## Acceptance contract

- [x] Einheitliche Statuswerte `machine`, `review_pending`, `reviewed`,
  `rejected`, `stale`; `reviewed` ist ohne vollständige menschliche
  Reviewmetadaten ungültig.
- [x] Kartenübersetzungen umfassen ausschließlich `short_description` und
  `services`; Namen, Aliase und alle operativen Fakten bleiben unverändert.
- [x] Übersetzungsidentität bindet Angebot, Sprache, Quellfeldhash,
  Kuration, Prompt, Provider/Modell und Erstellungszeit; Quelländerungen werden
  als `stale` erkannt.
- [x] Token-, Listen- und Faktenintegrität wird lokal geprüft; eine ungültige
  oder veraltete Übersetzung gelangt in keinem Policy-Modus in die Runtime.
- [x] `TRANSLATION_RUNTIME_POLICY` unterstützt `reviewed_only`,
  `reviewed_or_machine` und `source_language_fallback` mit ehrlichem
  Healthstatus.
- [x] Die CLI bietet `status`, `generate`, `validate`, `export-review` und
  `import-review`; Dry-Run bleibt vollständig schreibfrei und Writes sind
  atomar.
- [x] UI-, Dialog- und Fallbacktexte werden aus einer paketierten,
  versionierten Ressource geladen; 112 und Hilfebus-Fakten bleiben zentrale
  Policy- beziehungsweise Wissensbasiswerte.
- [x] Szenariokatalog, manuelles Reviewraster, konfigurierbare Wiederholungen,
  Opt-in-Live-Smoke und Hörprüf-Fixtures sind synthetisch, versioniert und
  standardmäßig providerfrei.
- [x] STT-/TTS-Sprachcodes, Stimmen und der ausschließlich validierte TTS-Text
  bleiben für DE/EN/PL/RO/RU abgesichert.
- [x] Arbeitspakete zu Infrastrukturimport, geografischem Ranking,
  abschließender Safety-Politik und Deployment bleiben unverändert.
- [x] Vollständige Suite, Syntax, Distributionen, sdist→Wheel, Clean-Install,
  providerfreier Template-Smoke und `git diff --check` bestehen.

## Scope

### In scope

- Übersetzungsvertrag, Migration und Runtime-Policy für Angebotskarten.
- Lokale Integritätsprüfung und atomarer CLI-/Reviewprozess.
- Gemeinsame paketierte Anwendungs-, Dialog- und Fallbackressourcen.
- Healthinventare für Karten- und Anwendungsressourcen.
- Synthetische dynamische Antwortszenarien, Reviewraster und opt-in Live-Smoke.
- Sprach-/TTS-/STT-Vertragstests und zutreffende Betriebsdokumentation.

### Out of scope

- Tatsächlicher Live-Providerlauf oder menschliche Sprachfreigabe.
- Echte Nutzerdaten, Produktivtelemetrie oder produktive Deploymentfunktionen.
- Toiletten-/Trinkbrunnenimporte, allgemeines Distanzranking und neue
  fachliche Auswahlregeln.
- Abschließende Akutrisiko-/Interpreterfehlerpolitik.
- Allgemeine linguistische Qualitätsbehauptungen aus automatischen Tests.

## Repository review

### Current behavior

- `app/i18n.py` nutzt ein untypisiertes Schema 1. `review_status` liegt pro
  Angebot statt pro Sprache; alte Werte wie `needs_update` und `review_needed`
  werden heuristisch zusammengefasst.
- `TRANSLATED_FIELDS` enthält `name`, `short_description` und `services`.
  Der Generator fordert zusätzlich Öffnungszeiten, Standzeiten,
  Telefonnummern und Notizen als freien Übersetzungstext an. Arbeitspaket 6
  verhindert deren Runtimeüberschreibung, der Store und Prompt enthalten sie
  jedoch weiterhin.
- `offer_translation_hash()` bindet teils den gesamten Quellen-/Kurstand und
  trennt übersetzbare Felder nicht von operativen Fakten. Dadurch ist weder der
  konkrete Veraltungsgrund noch ein Kartenreview bei operativer Änderung
  strukturiert sichtbar.
- `update_translations(..., dry_run=True)` ruft zuerst
  `mark_translation_state_for_offers()` auf; diese Funktion kann externe Daten
  und Zeitstempel schreiben. Der bestehende Dry-Run ist daher nicht
  nebenwirkungsfrei.
- Der Runtimepfad lädt den Store einmal in `QueryService.__init__()` und wendet
  Hashgleichheit plus geschützte Token an. Eine explizite Statuspolicy fehlt.
- Dialogtexte sind paketiert in `resources/bootstrap/dialogue/messages.json`,
  übrige Frontendtexte liegen in `app/static/app.js`, und Fallback-/Safetytexte
  liegen parallel in `app/service.py`.
- Health aggregiert Kartenstatus nicht pro Sprache und verwendet für
  Dialogtexte eigene, nicht vereinheitlichte Statusnamen.
- Die vorhandenen 30 Storeeinträge stammen aus maschineller Erzeugung. Vier
  davon gehören zu den aus der Runtime ausgeschlossenen WFS-IDs 1–4. Es gibt
  keine dokumentierte menschliche Sprachfreigabe und keine belastbare
  Modellkennung für die Altbestände.

### Relevant architecture and data flow

1. `create_app()` lädt die kuratierte 26-Angebote-KB und erzeugt genau einen
   `QueryService`.
2. `QueryService.__init__()` lädt Übersetzungsstore und Overrides.
3. `_card()` → `localize_offer_card()` baut Karten aus dem aktuellen kuratierten
   `OfferRecord`; der kuratierte Anzeigename gewinnt abschließend.
4. Dialogtexte werden serverseitig über `dialogue_text()` und
   `/api/dialogue/copy` verwendet; sonstige UI-Texte kommen direkt aus einer
   JavaScript-Konstante.
5. `/api/health` liest Store und Dialogstatus erneut und veröffentlicht
   Summen. Speechkonfiguration und Stimmen liegen in `app/speech.py`.
6. `python -m app.translate_offers` lädt dieselbe kuratierte Runtime-KB,
   generiert derzeit alle vier Sprachen in einem Providerrequest und schreibt
   den Store nach jedem Angebot.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Kuratierte Runtime-KB/Fingerprint | `app/kb_loader.py` | Für ID-, Quell-, Katalog- und Szenariobindung wiederverwenden |
| Atomarer JSON-Write | `app/i18n.py` | Härten und für Store/Reviewimport zentral wiederverwenden |
| Sprache/OfferCard | `app/models.py` | Bestehende Enums und Kartenvertrag beibehalten |
| Dialogressourcen/API | `app/dialogue.py`, `/api/dialogue/copy` | Auf gemeinsames Ressourceninventar migrieren; Kompatibilitätsroute erhalten |
| Formulatorverträge | `app/formulation.py` | Versionen und Szenarioerwartungen referenzieren, keine zweite Formulierung bauen |
| TTS/STT-Zuordnung | `app/speech.py` | Bestehende Codes/Stimmen explizit inventarisieren und testen |
| Paketressourcen | `app/resources.py`, `pyproject.toml`, `MANIFEST.in` | Bestehenden Bootstrapmechanismus erweitern |

### Existing tests and commands

- Relevante Tests: `tests/test_formulation.py`, `tests/test_dialogue.py`,
  `tests/test_dialogue_frontend.py`, `tests/test_api.py`,
  `tests/test_observability.py`, `tests/test_provider_timeouts.py`,
  `tests/test_packaging.py`.
- Geplante Befehle: fokussierte neue I18n-/CLI-/Ressourcen-/Reviewtests,
  `python -m pytest`, `python -m compileall -q app`, JavaScriptprüfung falls
  verfügbar, `python -m build`, sdist→Wheel, Clean-Install,
  providerfreier Template-Smoke, `git diff --check`.

### Working tree considerations

Der Branch `maintenance/repository-cleanup` steht auf Commit
`9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`. Sämtliche nicht committeden
Änderungen aus Arbeitspaketen 1–6 sind freigegebener Ausgangsstand. Sie werden
nicht zurückgesetzt, verworfen oder außerhalb des WP7-Umfangs umformatiert.
Die WP7-Dateiliste und der Abschlussreview werden gegen diesen erfassten
Startzustand geführt, nicht gegen den historischen Commit.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Zweiter Übersetzungsstore neben dem bestehenden | Runtime lädt bereits `offer_translations.json` | widersprüchliche Karten und Healthwerte | Schema 2 als kontrollierte, idempotente Migration desselben Stores | Migrations-/Runtime-/Clean-Install-Test |
| Status nur pro Angebot | Eine Sprache kann geprüft, andere maschinell sein | falsche Freigabebehauptung | Status und Reviewmetadaten pro Angebots-/Sprachdatensatz | Statusmatrix pro Sprache |
| `reviewed` aus Altwert oder Mock ableiten | Keine dokumentierten Reviewerrollen/-daten vorhanden | methodisch falsche Evidenz | Altbestände maximal `machine`; unvollständiges `reviewed` scheitert strikt | Schema-/Migrationstest |
| Namen und operative Felder weiter übersetzen | alter Prompt/Store enthalten diese Felder | kuratierte Fakten oder Eigennamen können driften | positive Feldliste nur Beschreibung/Leistungen; operative Hash- und Tokenprüfung | vollständiges 26-Angebote-Inventar |
| Nur bekannte Tokens per Regex schützen | Eigennamen/Aliase sind nicht vollständig regexerkennbar | scheinbar valide Faktänderung | explizites Tokeninventar aus kuratierter Karte plus formale Tokenklassen | Integritätsangriffstests |
| Dry-Run auf mutierendem Statushelper aufbauen | bestehender Aufruf schreibt vor der Dry-Run-Abfrage | versteckte Dateisystemänderung | reine Analysefunktion, Clone im Speicher, erst nach erfolgreichem Gesamtergebnis atomar schreiben | kompletter Baum-/Hashvergleich |
| UI-Texte zusätzlich in neuer JSON-Datei ablegen | `app.js`, `service.py`, Dialog-JSON enthalten bereits Kopien | dreifache Pflege | eine gemeinsame Ressource, Python und Frontend lesen denselben Endpunkt; alte Ressource ersetzen | Duplikat-/Callsite-/Frontendtest |
| 112/Hilfebusdaten in Übersetzungen duplizieren | Safetytexte enthalten 112, Dialogtext Platzhalter | veraltete oder widersprüchliche operative Fakten | Ressourcen enthalten nur Platzhalter; zentrale Policy bzw. Runtime-Angebot setzt Werte ein | Inventartest |
| Automatische Sprachchecks als Review ausgeben | WP6 prüft nur Vertrag/Skript | falsche Qualitätsaussage | `factual_integrity_status` und `linguistic_review_status` trennen; Reviewraster bleibt offen | Health-/Reporttest |
| Live-Smoke versehentlich in Pytest ausführen | Providerfunktionen sind verfügbar | Kosten/Netzwerk/Datenschutz | eigener Opt-in-Befehl mit Bestätigungsflag, keine Testdiscovery, synthetische Daten | Test ohne Flag, Providerdouble zählt null Calls |
| Breiter Safety-/Formulatorumbau | Texte liegen derzeit im Service | WP8 wird vorweggenommen | nur Textquelle zentralisieren, Kontrollfluss und Policy unverändert lassen | Safety-/Formulatorregression |

## Recommended approach

Das bestehende I18n-Modul bleibt der einzige Kartenlokalisierungspfad, erhält
aber strikte Pydantic-Verträge und reine Analysefunktionen. Das Store-Schema 2
speichert Identität und Status pro Sprache. Der Prototyp verwendet standardmäßig
`reviewed_or_machine`, damit vorhandene valide Maschinenübersetzungen sichtbar
bleiben, meldet diesen Zustand aber ausdrücklich als ungeprüft/degraded;
`reviewed_only` und deutscher Quellfallback bleiben konfigurierbar.

Eine gemeinsame paketierte Anwendungsressource ersetzt Dialog-JSON,
JavaScript-`TEXTS` und Python-Fallbacktabellen. Sie enthält ausschließlich
Texttemplates und Reviewmetadaten; 112 sowie Hilfebustelefon/-zeiten werden
zentral eingesetzt. Der bestehende Dialog- und API-Kontrollfluss bleibt
erhalten. Ein getrenntes synthetisches Szenarioinventar und Reviewmodell nutzt
die bereits versionierten Interpreter-/Selector-/Formulatorverträge und den
aktuellen KB-Fingerprint, ohne einen Provider automatisch aufzurufen.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| `reviewed_only` als Prototypstandard | würde mangels dokumentierter menschlicher Reviews sämtliche Karten auf Deutsch zurückfallen lassen und bestehende Mehrsprachigkeit verdecken; `reviewed_or_machine` bleibt ehrlich sichtbar degradiert |
| Automatische Migration bei jedem Runtime-Read mit Schreibzugriff | Nutzeranwendung soll keine Wartungsdaten implizit verändern; Runtime migriert nur im Speicher, explizite CLI schreibt atomar |
| Übersetzte Anzeigenamen mit Allowlist | fachlich freigegebene Eigennamen sollen unverändert bleiben; zusätzliche Komplexität ohne belegte lokalisierte Namen |
| Vollständiger Browser-i18n-Buildschritt | keine JS-Buildtoolchain vorhanden und Abhängigkeiten dürfen nicht installiert werden; API-geladene Paketressource passt zum bestehenden statischen Frontend |
| LLM-as-a-Judge für Sprachqualität | Methodikkapitel begründet die Grenze automatischer semantischer Bewertung; manuelles Raster bleibt maßgeblich |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/translation_contract.py` | Create | strikte Store-, Status-, Review- und Policymodelle | mittel |
| `app/i18n.py` | Modify | Hashes, Migration, Runtimepolicy, Integrität, Summary | hoch |
| `app/translate_offers.py` | Modify | Subcommands, Dry-Run, Reviewexport/-import, atomare Writes | hoch |
| `app/application_texts.py` | Create | einheitlicher Zugriff auf versionierte Texte | mittel |
| `app/multilingual_review.py` | Create | Szenario-/Reviewexport und gesperrter Live-Smoke | mittel |
| `app/policy_facts.py` | Create | zentrale unveränderte Safetyfakten | klein |
| `app/config.py`, `.env.example` | Modify | Runtimepolicy | klein |
| `app/dialogue.py` | Modify | gemeinsames Ressourcenmodell statt Parallelstatus | mittel |
| `app/service.py` | Modify | Textlookup statt Sprachdictionaries; Kontrollfluss unverändert | mittel |
| `app/main.py` | Modify | Copy-API und präzises Healthinventar | mittel |
| `app/static/app.js`, `app/static/index.html` | Modify | UI-Copy aus gemeinsamer Ressource | mittel |
| `app/speech.py` | Modify | zentrale Safetyzahl und prüfbares Sprachinventar | klein |
| `app/resources/bootstrap/i18n/offer_translations.json` | Modify | Store-Schema-2-Migration | groß/deklarativ |
| `data/i18n/offer_translations.json` | Modify | Checkout-Spiegel derselben Migration | groß/deklarativ |
| `app/resources/bootstrap/i18n/application_texts.json` | Create | fünfsprachige UI-/Dialog-/Fallbackressource | groß/deklarativ |
| `app/resources/bootstrap/i18n/dynamic_scenarios.json` | Create | synthetischer Evaluationskatalog | mittel/deklarativ |
| `app/resources/bootstrap/i18n/listening_review.json` | Create | synthetische spätere Hörprüfung | klein |
| `app/resources/bootstrap/dialogue/messages.json` | Delete | durch einheitliche Ressource vollständig ersetzt | mittel |
| `tests/test_i18n.py` | Create | Status, Hash, Runtime, Integrität, Migration | hoch |
| `tests/test_translation_cli.py` | Create | CLI, Review, Dry-Run, atomare Fehler | hoch |
| `tests/test_language_resources.py` | Create | Ressourcen, Szenarien, Live-Gate, STT/TTS | hoch |
| bestehende Dialog-/API-/Packagingtests | Modify | reale Integration und Ressourceninventar | mittel |
| `README.md`, `docs/configuration.md`, `docs/data-flow.md`, `docs/testing.md`, `docs/setup.md` | Modify | tatsächliche Policy, Befehle, Evidenzgrenzen | mittel |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Skillanweisungen und Templates vollständig gelesen; Git-/Pfadreview,
Callsite-Suchen, Store-/Ressourcen-/CLI-/Health-/Speech-/Packagingprüfung sowie
relevante Abschnitte aus `4Approachneu.tex` ausgeführt.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

Evidence: Strikte Verträge, Runtime-Policy, Storemigration, gemeinsame
Anwendungsressource, Review-CLI, Szenario-/Hörreview und Tests implementiert.
Die größten neu gefassten Module `app/i18n.py` und `app/translate_offers.py`
bleiben mit 383 beziehungsweise 351 Zeilen unter der Zielgröße.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run lint/format/type checks.
- [x] Run integration/build checks where relevant.
- [x] Verify registration, imports, routes, configuration, and packaging.
- [x] Review final diff.

Evidence: 435 Pytests erfolgreich; `compileall`, Wheel/sdist, Wheelneubau aus
sdist, Clean-Install und providerfreier Template-Smoke erfolgreich.
`git diff --check` ist sauber. Node.js ist nicht installiert, daher konnte
`node --check` nicht ausgeführt werden; die statischen Frontendtests bestanden.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: README, Konfigurations-, Datenfluss-, Setup- und Testdokumentation
gegen den implementierten Ablauf geprüft und anschließend vollständige Suite
und Artefaktprüfungen erneut ausgeführt.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| I18n/Status/Policy | `python -m pytest tests/test_i18n.py -q` | alle Status-, Hash-, Policy- und Integritätsfälle bestehen |
| CLI/Review/Dry-Run | `python -m pytest tests/test_translation_cli.py -q` | fünf Subcommands, atomare Fehler und null Dry-Run-Schreibzugriffe |
| Ressourcen/Szenarien/Speech | `python -m pytest tests/test_language_resources.py -q` | vollständige fünfsprachige Inventare, gesperrter Livepfad, STT/TTS-Verträge |
| Regression | fokussierte Formulator-, Dialog-, API-, Health-, Safety- und Packagingtests | bestehender Kontrollfluss unverändert |
| Full suite | `python -m pytest` | vollständig grün ohne externe Provider |
| Python syntax | `python -m compileall -q app` | Exit 0 |
| JavaScript syntax | `node --check app/static/app.js` oder verfügbare Alternative | Exit 0; sonst Umgebungslücke dokumentiert |
| Distribution | `python -m build` plus Packagingtests | Wheel/sdist enthalten alle Runtime- und Reviewressourcen |
| Clean install | `tests/test_packaging.py` | sdist→Wheel und Start außerhalb Checkout bestehen |
| Diff | `git diff --check` plus WP7-Dateiinventar | keine Whitespace-/Scopefehler |

## Rollback and recovery

Das versionierte Store-Schema wird ausschließlich über denselben atomaren
Zielpfad geschrieben. Runtime kann Schema 1 im Speicher migrieren, sodass eine
Rücknahme des paketierten Schema-2-Snapshots nicht zur ungeprüften Aktivierung
führt. Reviewimporte prüfen Source-/Kurations-/Translationsversion vor dem
Replace und verändern weder WFS- noch Kurationsdaten. Bei Fehlern bleibt die
vorherige Storedatei unverändert. Da es keinen Live-Aufruf im Abschlusslauf
gibt, entstehen keine externen Seiteneffekte.

## Progress log

- 2026-08-01 — Skills `review-first-coding` und `code-documentation` sowie Plan-/Reviewtemplates vollständig gelesen.
- 2026-08-01 — WP1–6-Arbeitsbaum, Runtime-/CLI-/UI-/Health-/Speech-/Packagingpfade und Methodikbezug geprüft; keine Quellcodeänderung vor diesem Plan.
- 2026-08-01 — Plan nach Dead-end-Analyse als `Reviewed` angelegt.
- 2026-08-01 — Store und Paketspiegel idempotent auf Schema 2 migriert; keine
  Altfassung als `reviewed` markiert.
- 2026-08-01 — Gemeinsame Textressource, Runtime-Policy, Review-CLI,
  synthetischer Szenario-/Hörreview und strikt gesperrter Live-Smoke integriert.
- 2026-08-01 — Eine beim Umbau erkannte unvollständige Zwischendarstellung von
  `service.py` aus dem vollständigen Patchprotokoll exakt rekonstruiert; danach
  Syntax- und Gesamtregression erfolgreich verifiziert.
- 2026-08-01 — 435 Tests, Build, sdist→Wheel, Clean-Install, Template-Smoke,
  vollständiger Dry-Run-Baumvergleich und Diffprüfung abgeschlossen.

## Decision log

- Decision: Runtime-Standard `reviewed_or_machine` mit explizit degradiertem Maschinenstatus.
  - Context: Es existiert aktuell keine dokumentierte vollständige menschliche Prüfung; nur Deutsch würde die prototypische Mehrsprachigkeit faktisch deaktivieren.
  - Options: `reviewed_only`, `reviewed_or_machine`, `source_language_fallback`.
  - Choice: `reviewed_or_machine`; ungültig/stale/rejected bleiben ausgeschlossen.
  - Consequences: Maschinenübersetzung bleibt sichtbar nutzbar, Health darf sie niemals als geprüft darstellen.
- Decision: Ein Ressourceninventar für Backend, Dialog und Frontend.
  - Context: Drei parallele Textquellen erzeugen Drift.
  - Options: bestehende Quellen nur annotieren; zusätzliche JSON; vollständige Konsolidierung.
  - Choice: vollständige Konsolidierung mit Kompatibilitätsroute für Dialogcopy.
  - Consequences: einmaliger breiter, aber WP7-begründeter Daten-/Callsite-Diff; keine zweite Runtimequelle.
- Decision: Automatisierte Integrität und menschlichen Sprachreview getrennt modellieren.
  - Context: Token-/Schemaerfolg belegt keine Natürlichkeit oder fachliche Reviewfreigabe.
  - Choice: `factual_integrity_status` neben `linguistic_review_status`.
  - Consequences: Health und Reviewpakete können die Evidenzgrenze präzise ausweisen.

## Discoveries

- Der alte Store enthält 30 Angebote einschließlich ausgeschlossener IDs 1–4;
  die aktive Runtime hat 26. Die Migration muss Altwerte erhalten, aber nur
  aktuelle Runtime-IDs als aktiv und verwendbar behandeln.
- Der Altstore dokumentiert Provider, jedoch keine verlässliche Modellkennung
  und keine Promptversion. Diese Werte dürfen nicht erfunden werden und werden
  explizit als nicht aufgezeichnete Legacyidentität markiert.
- Der bisherige Frontend-Sprachwechsel lädt bereits Dialogcopy über HTTP. Dieser
  Pfad eignet sich als kleinster Anschluss für das gemeinsame Ressourceninventar.
- 15 Alt-Sprachdatensätze verletzen die neue Listen-/Tokenintegrität (EN 3,
  PL 4, RO 4, RU 4) und erzeugen zusammen 17 Fehlercodes. Sie
  bleiben als Maschinenbestand nachvollziehbar, sind faktisch `invalid` und
  werden in der Runtime sicher durch deutsche Basisdaten ersetzt.
- Für keine Sprache liegt eine dokumentierte muttersprachliche oder
  professionelle Prüfung vor. Deutsche Anwendungsressourcen sind
  `review_pending`, die vier Fremdsprachen `machine`.

## Final verification summary

- Acceptance requirements: technisch umgesetzt; keine menschliche oder
  Live-Provider-Freigabe behauptet.
- Tests: 435 bestanden; keine realen Provideraufrufe.
- Build: Wheel und sdist gebaut, Wheel aus sdist neu gebaut und außerhalb des
  Checkouts installiert.
- Manual verification: Template-Smoke und Ressourcen-/CLI-Inventar geprüft;
  keine Hör- oder muttersprachliche Prüfung durchgeführt.
- Documentation: Code-Dokumentationsreview abgeschlossen.
- Residual risks: 17 Altintegritätsfehler mit sicherem Deutschfallback; alle
  Sprachen/Ressourcen weiterhin ohne dokumentierte professionelle Freigabe;
  Node.js-Syntaxcheck mangels Laufzeit nicht ausgeführt; Live-Smoke bewusst
  nicht gestartet.
