# Tests und Qualitätssicherung

## Ausführung

```powershell
cd code
python -m pip install -c requirements/constraints-py311.txt -e ".[dev]"
python -m pytest
```

Pytest liest `pyproject.toml`, sucht unter `tests/` und verwendet den Quiet-Modus.
`tests/conftest.py` setzt `LENA_ENV_FILE_MODE=disabled`, unterdrückt dadurch
Checkout-`.env`/`.env.local` auch in Testsubprozessen, entfernt geerbte
Providerkonfiguration für die Testsitzung und blockiert reale HTTP- sowie
nichtlokale Sockettransporte. Zusätzlich wird die Laufzeitwurzel der Testsitzung
isoliert: `LENA_RUNTIME_DIR` zeigt auf ein temporäres Verzeichnis, und
`Settings`-Objekte, deren `runtime_dir` beziehungsweise `interaction_log_path`
mangels eigener Angabe auf das Checkout-`runtime/` fallen würde, werden auf
dieselbe temporäre Wurzel umgelenkt. Ein Testlauf schreibt dadurch weder den
lokalen Sessionstore noch das Interaktionsprotokoll des Checkouts.
Netzwerkprovider werden durch explizite Settings und Test-Doubles ersetzt; ein
vergessener LLM-, STT-, TTS-, WFS- oder Toiletten- oder
Trinkbrunnenquellenaufruf lässt den Test sofort fehlschlagen.

## Abdeckung nach Testmodul

Zusätzlich führt `node --test tests/frontend.test.cjs` die echten Frontend-Skripte
mit DOM-/Transport-Doubles aus. Abgedeckt sind unter anderem Single-Flight,
Reset bei laufenden Requests, späte STT-Ergebnisse/Mikrofonfreigaben und das
Stoppen erneuter Wiedergabe. Syntaxprüfungen: `node --check app/static/app.js`
und `node --check app/static/dialogue.js`. Diese Prüfungen sind kein Browser-E2E
oder Barrierefreiheitsnachweis. Für den manuellen Übergang gilt die
[Evaluationscheckliste](manual-evaluation-prerequisites.md).

| Datei | Schwerpunkt |
|---|---|
| `tests/test_api.py` | Health, Query-API, LLM-Stufen und Fallbacks |
| `tests/test_interpreter.py` | versionierter Vertrag, fünf Sprachen, Fakten/Hinweise, Aliase, Sessionkontext, Injection, Parserfehler, Scope und Akutrisiko-Reihenfolge |
| `tests/test_candidates.py` | strikter Kandidatenvertrag, Leistungen, Rollen, Zielgruppen, Aliasbegrenzung, U18-Schlafmatrix, explizites Jugend-Intent-Gate, Zeitregeln, Reason Codes und sprachunabhängige Entscheidungen |
| `tests/test_llm_selection.py` | Selectorvertrag und -prompt, Positivlisteninventar, Mandatory/Selectable, ID-Angriffe, Mehrsprachigkeit, Bypässe und Providerfehler |
| `tests/test_formulation.py` | Evidence- und Satzvertrag, Grounding, Rollen, Karten, fünf Sprachen, OOS-/Hilfebus-Policies, Promptangriffe, Gesamtbudget und TTS-Textbindung |
| `tests/test_dialogue.py` | Dialogvertrag, Schlafmatrix, A1/Schoppi, Mobile/Kübel, Hilfebus, Buttons, Text/STT, Sprache/Thema, Fehler, Replay, TTL, Datenschutz und I18n-Status |
| `tests/test_dialogue_frontend.py` | semantische Buttons, unsichtbare technische Werte, Doppelklickschutz und Sprachwechselbindung |
| `tests/test_kb_loader.py` | Markdown- und kanonisches JSON-Laden |
| `tests/test_curation.py` | Kurationsschema, Provenienz, Aliasauflösung, Scharni-Override, Rohdatenerhalt und Ausschluss aus allen Runtime-Verbrauchern |
| `tests/test_runtime_loader.py` | verpflichtende Kuration, exakt gebundener lokaler/Paket-Fallback, Pointer-/Releasefehler und Runtime-Fingerabdruck |
| `tests/test_official_offer_source.py` | strikt validierte VKKJ-Betreiberquelle, Quellenreferenzen, Hashbindung, minimiertes Feldinventar, verifizierte WGS84-Kartenpunkte, CRS-/Gebietsgrenzen und Ablehnung WFS-artiger Rohfelder |
| `tests/test_retrieval.py` | isolierte lexikalische Legacy-Hilfen; nicht der aktive primäre Kandidatenpfad |
| `tests/test_sessions.py` | Session-Lebenszyklus, Dialogpersistenz, einmaliges Claiming, Sprachwechselerhalt und Invalidierung bei Wissensstandswechsel |
| `tests/test_session_persistence.py` | atomare Writes, Parallelzugriffe, TTL/Kapazität, Recovery und API-Fehlerrobustheit |
| `tests/test_wfs_sync.py` | Validierung, Normalisierung, Diff und Promotion |
| `tests/test_wfs_releases.py` | Manifest, Manipulationsschutz, atomarer Pointer, Migration, Konkurrenz und Rollback |
| `tests/test_frontend_security.py` | statische Absicherung der Leaflet-Popup-Sinks |
| `tests/test_safety.py` | Akutgefahr-Vertrag, kontrollierte Antwort und TTS |
| `tests/test_safety_policy.py` | enger fünfsprachiger Preflight-Sofortstopp, Safety-Dialog für unklare Fälle, fail-closed Providerfehler, Redaktion und Health |
| `tests/test_observability.py` | technische Events, finale JSONL-Paare, Redaktionsgrenzen und Schreibfehler |
| `tests/test_provider_timeouts.py` | LLM-, Speech-, WFS- und Übersetzungs-Timeouts sowie Fallbacks |
| `tests/test_request_boundaries.py` | Query-/STT-/TTS-Eingabegrenzen, Medientyp- und Payloadabweisung, Loopback-Bindung und geklemmte Umgebungs-/HBF-Werte |
| `tests/test_speech_transcription.py` | Browseraudio-zu-PCM-WAV-Normalisierung, Dauergrenze, redigierte Upstream-Status und Ablehnung nicht dekodierbarer Aufnahmen |
| `tests/test_provider_isolation.py` | `.env`-Isolation, Transportblockade und dreifache Live-Smoke-Freigabe |
| `tests/test_live_evaluation.py` | WP9B-Stufenkatalog, feste Erwartungen, Payloadinventar, harte Limits, atomare Reports, Redaktion, providerfreier Dry-Run und isolierter Stufe-1-Runner |
| `tests/test_translation_tokens.py` | maskierte operative Platzhalter, Inventarprüfung beim Zurückschreiben und sprachunabhängiger Maskierungsvertrag |
| `tests/test_translation_quality.py` | Statusmodell, Hash-/Kurationsbindung, Runtime-Policies, aktives Übersetzungsinventar mit deutschem Fallback für neue ungeprüfte Angebote, CLI/Review, vollständiger Dry-Run, gemeinsame Sprachressourcen, Szenariokatalog, Live-Opt-in und STT/TTS |
| `tests/test_public_toilets.py` | amtliches CSV-Schema, Fail-safe-Kosten/Geometrie, Diff, Promotion/Rollback/Fallback, Runtime, API, Evidence, fünf Sprachen und Health |
| `tests/test_drinking_fountains.py` | Wasserwerke-KML, amtliche Grenzprüfung, Manifest/Fallback, Ausschlüsse, Saison, kombinierte Wasserresultate, HBF-Ranking, fünf Sprachen, Evidence/Grounding, Frontend und Health |
| `tests/test_result_ordering.py` | Europe/Berlin-Zeitfenster, mobile Standorte, Fach-/Mandatory-Priorität, HBF-Luftlinie und stabile Ordnung |
| `tests/test_packaging.py` | Version, Wheel-/sdist-Inventar, Ressourcenreferenzen, sdist-Rebuild und echte Clean-Installation außerhalb des Checkouts |

## Continuous Integration

`.github/workflows/test.yml` verwendet GitHub Actions mit Python 3.11 und führt
dieselben nachgewiesenen Befehle wie lokal aus:

```powershell
python -m pytest
python -m compileall -q app
python -m build
```

Der Workflow besitzt nur Leserechte auf Repository-Inhalte und benötigt keine
Secrets. `tests/test_packaging.py` baut Wheel und Source Distribution, prüft
explizite Ein- und Ausschlüsse, baut aus dem Source-Archiv erneut ein Wheel und
installiert das Artefakt in eine frische virtuelle Umgebung. Der Smoke-Test
entfernt `PYTHONPATH`, wechselt in ein fremdes Arbeitsverzeichnis, verifiziert
`app.__file__` unter `site-packages` und prüft Version, Startseite, Static Asset,
Wissensbasis, Templatequery sowie externe Runtime-Schreibpfade.
Der Workflow enthält bewusst kein Deployment, keinen Node-/Browser-Schritt und
keine noch unkonfigurierten Linter, Type-Checker oder Security-Scanner. Ein
Remote-CI-Lauf kann erst nach Push beziehungsweise Pull Request bestätigt
werden; die lokale Ausführung prüft nur Befehle und Workflowstruktur.

## Manuelle Smoke-Checks

1. Starte mit `REWRITE_PROVIDER=template`, `WFS_AUTO_SYNC=false`,
   `TOILET_AUTO_SYNC=false` und `DRINKING_FOUNTAIN_AUTO_SYNC=false`.
2. Prüfe `GET /api/health`, öffne `/` und verifiziere den fail-closed
   technischen 112-Hinweis mit gegebenenfalls Hilfebus-Kontaktkarte ohne Marker. Fachliche Smokes benötigen einen
   kontrollierten Test-Double oder bewusst konfigurierten Interpreter.
3. Prüfe mit Test-Double je eine Frage zu Essen, Schlafen, Medizin und Beratung.
4. Prüfe Karten, Kartendarstellung, Sprachwechsel und eine Folgefrage.
   Prüfe außerdem den Hilfebus außerhalb 18:00--23:00 als Telefon-/Vermittlungs-
   hinweis mit Zeiten, ohne Marker und ohne Behauptung aktueller Erreichbarkeit;
   prüfe ihn für Essen/Trinkwasser nur im Sonntag-20:00--21:00-Standfenster.
5. Prüfe im Zeitraum April bis Oktober eine Trinkbrunnenanfrage: höchstens drei
   primäre Antwortkarten, vollständige Brunnenmarkermenge, HBF als Ursprung und kein
   Echtzeitversprechen. Prüfe außerhalb des Zeitraums den sozialen Wasserfallback.
   Die sichtbaren aufklappbaren Tafeln vereinigen sämtliche Kartenziele mit
   ausgewählten Angeboten ohne Geometrie und können daher mehr als drei sein.
6. Prüfe Speech nur mit bewusst konfiguriertem externem Dienst.
7. Prüfe bei bewusst aktivierter Prototyp-Protokollierung eine erzeugte
   `runtime/logs/interactions.jsonl` und lösche lokale Testdaten anschließend.

Fokussierte Prüfung des Protokollpfads:

```powershell
python -m pytest tests/test_observability.py -q
python -m pytest tests/test_interpreter.py tests/test_safety.py tests/test_safety_policy.py -q
python -m pytest tests/test_candidates.py tests/test_curation.py tests/test_api.py -q
python -m pytest tests/test_llm_selection.py tests/test_provider_timeouts.py -q
python -m pytest tests/test_formulation.py tests/test_api.py -q
python -m pytest tests/test_provider_timeouts.py -q
python -m pytest tests/test_translation_quality.py -q
python -m pytest tests/test_session_persistence.py -q
python -m pytest tests/test_wfs_releases.py tests/test_wfs_sync.py -q
python -m pytest tests/test_drinking_fountains.py tests/test_public_toilets.py -q
```

## Fehlende automatisierte Prüfungen

Im Projekt sind derzeit keine Linter-, Type-Checker-, Coverage- oder
Dokumentations-Linkprüfungen konfiguriert. Es gibt außerdem keine Browser-End-to-
End-Suite. Die Python-3.11-Constraints fixieren Versionen, aber noch keine
Artefakthashes und sind kein universeller Lock für andere Python-Versionen oder
Plattformen. Ein Hash-Lock und zusätzliche Werkzeuge benötigen eine bewusste
Projektentscheidung in einem separaten Paket.

Die Dialogoberfläche wird statisch, über API-Integration und mit ausführbaren
JavaScript-Verhaltenstests geprüft.
Native Buttons liefern Tastatur- und Fokussemantik; ein echter Screenreader- und
Browserlauf bleibt manuell. `node --check` kann zusätzlich ausgeführt werden,
wenn eine Node.js-Laufzeit vorhanden ist; sie gehört nicht zu den
Python-Projektabhängigkeiten.

```powershell
node --test tests/frontend.test.cjs
node --check app/static/app.js
node --check app/static/dialogue.js
```

Die Verhaltenstests führen die echten Browserskripte mit lokalen DOM- und
Transport-Doubles aus. Sie prüfen Folgedialoge, Sprachwechsel während einer
Anfrage, Doppelsenden, Fehler-Recovery sowie Sessionbindung und Freigabe von
TTS-Audio. Sie sind im Source-Archiv enthalten und laufen getrennt von Pytest
und der bisherigen Python-CI. Ein echter Browser-/Screenreader-Test bleibt offen.

Automatische Mehrsprachigkeitstests belegen Schema, Kontrollfluss,
Tokenintegrität, Grounding und offensichtliche Skriptfehler. Sie belegen weder
Natürlichkeit noch idiomatische oder fachsprachliche Qualität. Der synthetische
Reviewexport verlangt deshalb weiterhin eine dokumentierte menschliche
Bewertung pro Sprache und Szenario. Der providerfreie WP9B-Dry-Run meldet `prepared_not_executed`; bereits
dokumentierte Live-Läufe sind davon unabhängig. Der
Live-Smoke wird nie von Pytest oder CI gestartet und benötigt Unterbefehl,
einzelne Stufe, Flag, unabhängige Umgebungsfreigabe, erwartete Provideridentität
und sieben exakte Laufgrenzen. Der vollständige providerfreie Plan wird mit
`python -m app.multilingual_review live-dry-run --stage all` geprüft; Details
stehen in [Kontrollierte Live-Provider-Evaluation](live-provider-evaluation.md).
