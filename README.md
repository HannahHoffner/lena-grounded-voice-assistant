# LENA

LENA ist ein lokal betriebener, mehrsprachiger **Forschungsprototyp** zur Suche
nach Hilfsangeboten für wohnungslose Menschen in Leipzig. Ein statisches
Browser-Frontend spricht mit einem FastAPI-Backend. Fachliche Inhalte stammen
aus lokal freigegebenen, getrennt geprüften Beständen für soziale Angebote,
öffentliche Toiletten und feste Trinkwasserbrunnen; das Sprachmodell ist keine
Wissensquelle. Die Verarbeitung ist in vier Schichten getrennt:

| Schicht | Module | Verantwortung |
|---|---|---|
| Datenbasis | `kb_loader`, `curation`, `*_releases`, `official_offer_source` | hashgebundene, manuell freigegebene Bestände |
| Fachregeln | `candidates`, `candidate_context`, `dialogue_flow`, `result_time`, `result_ordering` | deterministische Kandidatenbegrenzung, Dialoge, Zeit- und Ortsregeln nach Interpretation und vor Auswahl/Formulator |
| LLM-Stufen | `providers/llm`, `llm_stages`, `formulation` | Interpretation, kontrollierte Auswahl und Antwortplanung aus einem Evidence-Paket; Budget, Retry, Template-Rückfall |
| Prüfung/Renderer | `grounding`, `answer_plan`, `answer_act_texts` | atomare Plan-/Referenzprüfung und Text aus gebundenen Fakten/Akten; ohne Zugriff auf Provider, Wissensbasis oder Fachregeln |

`app/service.py` orchestriert diese Schichten; `tests/test_architecture_boundaries.py`
sichert die Importgrenzen. Der produktive Formulator liefert einen
**geschlossenen Antwortplan**; der Server prüft Referenzen und setzt Quellwerte
mit festen Antwortakten ein. Freie Modellprosa wird nicht ausgegeben. Das ist
Pakettreue, keine allgemeine semantische Wahrheitsgarantie: Interpretation,
Auswahl, Quellaktualität und sprachliche Eignung können weiterhin fehlerhaft sein
(siehe [Systemgrenzen](#systemgrenzen)). Die frühere lexikalische
Claimprüfung bleibt als historisches Forschungsartefakt erhalten.

Die normale Bedarfsauswahl benötigt einen konfigurierten LLM-Interpreter. Ohne
ihn startet die Anwendung, liefert bei normalen Anfragen aber nur den
technischen Hilfepfad. LENA ersetzt keine Notfallversorgung, medizinische oder
soziale Beratung und kennt weder freie Kapazitäten noch eine garantierte Aufnahme.

Die Anwendung richtet sich an technisch betreuende Personen sowie an Fachkräfte,
die LENA installieren, Datenänderungen prüfen, Übersetzungen pflegen und die
fachlichen Leitplanken weiterentwickeln.

## Funktionsumfang

Vor einer manuellen Prüfung: [Evaluationsvoraussetzungen](docs/manual-evaluation-prerequisites.md).

- Textanfragen in Deutsch, Englisch, Polnisch, Rumänisch und Russisch
- deterministische, begründete Kandidatenbegrenzung mit Mandatory-/Selectable-Trennung
- kontrollierte optionale LLM-Auswahl nur innerhalb zulässiger Kandidaten sowie faktengebundene Antwortplanung mit serverseitiger Ausgabe
- Karten und Kartenansicht für Angebote mit verwertbaren Koordinaten
- lokale Sitzungsverläufe für kurze Folgefragen
- optionale serverseitige Speech-to-Text- und Text-to-Speech-Schnittstellen
- unveränderliche WFS-Releases mit Manifest, Diff, atomarer Aktivierung und Rollback
- separat freigegebene Releases der amtlichen Leipziger Toiletten-CSV mit
  HBF-Luftlinienordnung und getrennten Primär-, Karten- und Markerlisten
- manifest- und hashgebundene Releases der Wasserwerke-KML mit 21 freigegebenen
  festen Leipziger Trinkbrunnen, saisonaler Begrenzung und manueller Aktivierung
- schema-validierte Kurationsschicht für Organisationen, Standorte, getrennte
  Leistungen, Aliase, Ausschlüsse und Provenienz
- versionierte Kartenübersetzungen mit getrenntem Sprachreview- und Faktenintegritätsstatus
- deterministische Safety-Policy mit zentral gebundener 112, dreistufigem
  Risikosignal und strukturiertem Safety-Dialog

## Voraussetzungen

| Zweck | Voraussetzung |
|---|---|
| Empfohlener, geprüfter Weg | Docker mit Linux-Containern (geprüft: Linux/AMD64, Docker Engine 29.9.1 / Desktop 4.96.0), Browser, freier lokaler Port |
| Erster Docker-Build | Internet zu Docker Hub, `snapshot.ubuntu.com` und PyPI (hashgeprüft); kein Projekt-Secret |
| Nativer Start | Python 3.11 oder neuer (CI 3.11, Container 3.12.3, Host geprüft 3.14.3) |
| JavaScript-Tests nativ | Node.js (im Docker-Testziel enthalten) |
| Normale Textsuche | erreichbarer OpenAI-kompatibler LLM-Endpunkt mit Zugang, z. B. Blablador |
| Sprache (optional) | Mikrofon/Lautsprecher, Browserfreigabe; für Server-STT/TTS je ein konfigurierter Dienst |

Keine GPU, keine lokalen Modellgewichte, kein Ollama, keine Vektordatenbank und
kein zusätzlicher Server sind nötig.

## Schnellstart mit Docker (empfohlen)

Aus diesem Verzeichnis (`code/`); Befehle gelten in PowerShell und Bash:

```text
# 1. Vollständige Tests offline im Container (Python, Packaging, JavaScript)
docker build --target test -t lena-check .
docker run --rm --network none lena-check

# 2. Runtime-Image bauen und flüchtig starten (Kernprofil ohne Zugangsdaten)
docker build --target runtime -t lena:0.2.0 .
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -p 127.0.0.1:8002:8002 lena:0.2.0
```

Öffne `http://127.0.0.1:8002`; `http://127.0.0.1:8002/api/health` zeigt Daten-
und Dienststatus. Den Port immer an `127.0.0.1` binden: Es gibt weder
Authentifizierung noch TLS.

**Textsuche mit LLM:** Zugangsdaten nie in Befehlszeilen oder Dateien im
Repository schreiben. Eine geschützte Datei außerhalb des Repositorys (Vorlage:
[`.env.example`](.env.example)) mit `--env-file` übergeben, mindestens:

```text
REWRITE_PROVIDER=blablador
BLABLADOR_BASE_URL=https://api.blablador.fz-juelich.de/v1
BLABLADOR_API_KEY=<eigener Zugang>
BLABLADOR_MODEL=alias-fast
```

```text
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --env-file <pfad/zur/lena.env> -p 127.0.0.1:8002:8002 lena:0.2.0
```

**Persistenter Zustand (optional):** Standardmäßig liegt der Zustand im
flüchtigen `/tmp` und verschwindet mit dem Container. Für Sessions über Neustarts
hinweg ein Named Volume einmalig für UID 10001 vorbereiten und einbinden:

```text
docker volume create lena-state
docker run --rm --user 0 --entrypoint /bin/sh -v lena-state:/persist lena:0.2.0 -c "mkdir -p /persist/runtime /persist/data && chown -R 10001:10001 /persist && chmod 700 /persist"
docker run -d --name lena --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -v lena-state:/persist -e LENA_RUNTIME_DIR=/persist/runtime -e LENA_DATA_DIR=/persist/data -p 127.0.0.1:8002:8002 lena:0.2.0
```

Sessions sind sensible Daten (Session-ID wirkt als Zugriffsschlüssel). Ein
Reset in der Oberfläche löscht keine Serverdaten; Sessions verfallen nach 180 s
beim nächsten Zugriff, beschädigte Sessiondateien werden höchstens dreifach in
Quarantäne aufbewahrt. Volume bei Bedarf mit `docker volume rm lena-state` löschen.
Der Store ist für **genau einen Prozess** ausgelegt.

Eine Compose-Datei ist bewusst nicht enthalten: LENA ist ein einzelner Prozess
ohne eigene Begleitdienste (LLM, STT, TTS und Kartenkacheln sind externe Dienste,
keine Container dieses Projekts). Compose würde nur die obigen Optionen bündeln.

## Nativer Start

```powershell
cd code
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -c requirements/constraints-py311.txt -e ".[dev]"
Copy-Item .env.example .env
python -m app --port 8002
```

Unter Linux oder macOS: `source .venv/bin/activate` und `cp .env.example .env`.
Native Starts verwenden dieselben sicheren Defaults wie Docker (kein LLM, keine
Server-Sprache, kein Quellabruf, kein Interaktionsprotokoll). Priorität:
Defaults < `.env` < `.env.local` < Prozessumgebung; `--rewrite-provider` gewinnt
immer. Der Server bindet standardmäßig nur lokal; nicht lokale Hosts erfordern
`--allow-public`, das weder TLS noch Authentifizierung ergänzt.

## Betriebsprofile und externe Dienste

Jeder externe Dienst hat ein **explizites Profil**; kein Profil übernimmt
Zugangsdaten eines anderen stillschweigend. Fehlt etwas, startet LENA trotzdem
und degradiert kontrolliert.

| Dienst | Profilvariable (Default) | Ohne Konfiguration | Datenempfänger bei Nutzung |
|---|---|---|---|
| LLM (Interpreter, Selector, Formulator) | `REWRITE_PROVIDER` (`template`) | kein fachliches Suchergebnis; technischer Hinweis mit 112-Angabe und Hilfebus-Kontaktkarte | LLM-Anbieter: aktuelle Frage, kurze Sessionnutzertexte, begrenztes Evidence-Paket |
| Server-STT | `SPEECH_TRANSCRIPTION_PROVIDER` (`disabled`; `blablador` nur ausdrücklich) | Browser-Spracherkennung, falls vorhanden, sonst Texteingabe | STT-Anbieter: normalisierte Audioaufnahme |
| TTS | `SPEECH_SYNTHESIS_PROVIDER` (`disabled`; `edge` oder `openai` ausdrücklich) | kein Vorlesen; Text vollständig nutzbar | TTS-Anbieter (Edge: Microsoft): vorgelesener Antworttext |
| Kartenkacheln | `MAP_PROVIDER` (`osm`) | `disabled`: Marker ohne Basiskarte | OpenStreetMap, direkt aus dem Browser |
| Quellabgleich WFS/Toiletten/Brunnen | `*_AUTO_SYNC` (`false`) | gebündelte, hashgeprüfte Bootstrap-Daten | städtische Quellen, nur bei Wartung |

Für Blablador gilt: Der Zugang reicht für die geprüfte **Textsuche**; das
Modellinventar bot am 23.10.2026 `faster-whisper-large-v3` (STT), aber **kein**
TTS-Modell (`gpt-4o-mini-tts` → HTTP 404). Sprachausgabe erfordert daher Edge-TTS
oder einen anderen kompatiblen TTS-Endpunkt. Die gepinnten Constraints und der
Docker-Lock verwenden `edge-tts 7.3.1`; der frühere Client 7.2.8 wurde vom
externen Dienst mit HTTP 403 abgewiesen. Edge bleibt optional und dienstabhängig.
Der Audioerfolg vom 25.10. ist kein neuer Hör-/TTS-Nachweis für den 26.10.

Das tatsächlich geprüfte Blablador-Messprofil setzt zusätzlich 4096 Tokens und
15/30/30 Sekunden Stufenlimits bei 45 Sekunden Gesamtbudget. Die Minimalwerte
oben aktivieren den Zugang; ohne Overrides gelten 1200 Tokens im Code bzw.
2000 beim Übernehmen der Vorlage und 10 Sekunden Selectorlimit. Das kommentierte
Messprofil in `.env.example` dokumentiert die Abweichung; keine Erfolgsgarantie
für jedes Modell oder jede Anfrage.

## Offline-Grenzen

Ohne Netzwerk funktionieren: Start, Healthcheck, Oberfläche, lokale Daten,
Sessions, Safety-Preflight, technischer Hilfepfad mit Hilfebus-Kontakt,
alle automatisierten Tests (`docker run --network none lena-check`). **Nicht**
offline verfügbar: fachliche Freitextsuche (benötigt LLM), Server-STT, TTS,
Browser-Spracherkennung einiger Browser, OpenStreetMap-Basiskarte sowie jeder
Docker-Neubau (Basisimage, Ubuntu-Snapshot, PyPI).

## Fehlerdiagnose

| Beobachtung | Ursache / Prüfung |
|---|---|
| Jede Anfrage liefert `answer_type=technical_fallback` | LLM-Profil fehlt oder unvollständig: `/api/health` → `external_services.llm` (`missing` nennt fehlende Variablen) bzw. `interpreter_error_code` im Interaktionstrace |
| Vorlese-/Mikrofonknopf fehlt | Profil `disabled` oder unvollständig: `external_services.speech_synthesis` / `speech_transcription` |
| „konfiguriert“, aber Dienst scheitert | `python -m app.service_check` bzw. im Container `docker run --rm --env-file <datei> --entrypoint /opt/lena/bin/python lena:0.2.0 -m app.service_check`: prüft Erreichbarkeit und Modellinventar ohne Secrets in der Ausgabe; `--synthesize` sendet zusätzlich „LENA.“ an den TTS-Dienst |
| `tts.failed error_code=tts_provider_http_error upstream_status=404` im Log | TTS-Modell am Endpunkt nicht vorhanden |
| HTTP 503 `session_persistence_unavailable` | Runtimeverzeichnis nicht beschreibbar; eine Rückfrage kann ohne gespeicherten Zustand nicht sicher beantwortet werden |
| `config.warning reason=… setting=…` im Log | ungültiger Profilwert oder nicht unterstützte Variable (nur Name, nie Wert) |
| `runtime_kb_status=degraded`, `source_status=pointer_error` | kein externer Active-Pointer; paketierter Bootstrap wurde korrekt geladen (Normalfall im Container) |

Das technische Log (stdout) schreibt Ereignisname plus erlaubnislistenbasierte
Felder, z. B. `request.completed method=POST path=/api/query status_code=200 duration_ms=…`.
Zusätzliche Diagnosefelder werden über eine Erlaubnisliste begrenzt. Ein
vollständiger Ausschluss sensibler Inhalte aus technischen Logs ist derzeit
nicht gewährleistet: Rohpfade und Uvicorn-Query-Strings werden protokolliert
(Nachprüfung N-03). Vollständige Frage/Antwort-Paare entstehen mit
`INTERACTION_LOGGING_ENABLED=true`.

## Tests

```text
python -m pytest                          # vollständige Python-Suite inkl. Packaging
node --test tests/frontend.test.cjs       # Frontend-Verhaltenstests
docker run --rm --network none lena-check # beides offline im fixierten Container
```

Kein Test benötigt Providerzugänge; `tests/conftest.py` sperrt externe
Netzwerkzugriffe. Ein bewusst dokumentierter `strict xfail`
(`tests/test_formulation.py`, „minor injuries“) markiert eine bekannte
Überablehnung und zählt nicht als bestanden. Live-Provider-Läufe sind getrennt
freizugeben ([Live-Provider-Evaluation](docs/live-provider-evaluation.md)).
Aktueller Prüfstand vom 26.10.2026: nativ und im netzlosen Container jeweils
**1476 Python-Tests bestanden, 1 bekannter strikter XFAIL**, je **19/19 JS**;
bekannte Starlette-TestClient-DeprecationWarning bleibt sichtbar. Sauberer
Docker-Neubau, HTTP-Runtime, Blablador und Sessionerhalt nach Neustart und
Containerersatz sind geprüft. Zehn direkte Live-Formulatorfälle ergaben neun
gültige Pläne und eine korrekte Ablehnung; das ersetzt keinen vollständigen
Vierstufenlauf. Anschließend wurde am Commit `2462e7d` die vollständige
Reihe neu erhoben: 83 Anfragen/122 Provideraufrufe. Selector/Formulator besteht
beide Gates, Interpreter nur Vertragsgate; E2E/Stabilität bleiben wegen erholter
Fehler negativ. Kein katalogseitig kritischer Fehler in dieser Reihe; menschliche
Prüfung und manuelle Evaluation weiter offen.
Nachweise: [IMPLEMENTATION_REPORT.md, Abschnitt 11](IMPLEMENTATION_REPORT.md#11-technisch-geprüfter-stand-für-den-manuellen-release-review-26102026).
Neue Live-Bewertung: [Bericht 12](IMPLEMENTATION_REPORT.md#12-abschließende-vierstufige-live-messung-am-commit-2462e7d).
Vor manueller Evaluation: [Release-Review-Checkliste](RELEASE_REVIEW_CHECKLIST.md).
Keine uneingeschränkte Abgabe- oder Veröffentlichungsempfehlung.

Der [diagnostische Promptvergleich vom 24.10.2026](docs/formulator-prompt-comparison.md)
trennt ungefilterte Modellantworten, Schemafehler und Grounding-Ergebnis.
130 ursprüngliche und 30 separat ergänzende Liveaufrufe wurden ausgewertet;
Semantikurteile stammen von Codex, menschliches Review bleibt offen. Der
Kandidatenprompt ist nicht produktiv übernommen. Nach Ergänzung von zwölf
Offline-Werkzeugtests: nativ 1355 bestanden, ein bekannter XFAIL; JS 19/19.

## Systemgrenzen

- Forschungsprototyp für isolierten lokalen Betrieb: keine Authentifizierung,
  kein TLS, keine Rate-Limits, ein Prozess; nicht für öffentlichen Betrieb.
- Seit 25.10.2026 liefert der Formulator einen geschlossenen Antwortplan
  (Vertrag 6, Prompt 24, Validator 6). Das Backend setzt ausgewählte Fakten
  und feste Antwortakte ein; freie Modellprosa wird nicht ausgegeben. Die
  frühere Wortprüfung bleibt ausschließlich für historische Replays erhalten.
  Das verhindert frei erfundene Leistungsformulierungen, garantiert aber weder
  richtige Bedarfserkennung noch passende Auswahl oder aktuelle Quelldaten.
  Der Renderer hält 600 Zeichen durch vollständige Faktengruppen samt
  Pflichtbedingungen ein; passt keine Gruppe, bleibt ein kurzer Kontaktauftrag. Fremdsprachige
  Rohfelder können in der Quellsprache verbleiben. Die festen Texte sind noch
  nicht unabhängig sprachlich geprüft. Interpreter-`explicit_facts` werden
  weiterhin nicht gegen Quellspannen geprüft.
  Aufbau und neue Prüfbelege: [Kontrollierte Antwortakte](docs/controlled-answer-acts.md).
- Modellantworten sind nicht deterministisch wiederholbar; Modellaliase des
  Anbieters können sich ändern.
- Datenweitergaberechte: Für die Trinkbrunnendaten ist keine ausdrückliche
  Datensatzlizenz ausgewiesen; die konkrete Lizenzzuordnung des WFS-Endpunkts ist
  nicht abschließend belegt (siehe [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md),
  [Release](docs/release.md)). Vor öffentlicher Weitergabe klären.

## Dokumentation

- [Architektur mit Systemübersicht](docs/architecture.md)
- [Installation und Betrieb](docs/setup.md)
- [Konfigurationsreferenz](docs/configuration.md)
- [Datenflüsse und Schnittstellen](docs/data-flow.md)
- [Tests und Qualitätssicherung](docs/testing.md)
- [Docker und Reproduzierbarkeit](docs/reproducibility.md)
- [Release und Zenodo-Archivierung](docs/release.md)
- [Lizenz und Herkunft](THIRD_PARTY_NOTICES.md)
- [Safety- und Fehlerpolitik](docs/safety-and-error-policy.md)

## Projektstruktur

| Pfad | Verantwortung |
|---|---|
| `app/main.py` | FastAPI-App, Lifecycle und HTTP-Endpunkte |
| `app/service.py` | Anfrageorchestrierung: Safety-Entscheidung, Fachregelpfade, Ergebnisprojektion |
| `app/llm_stages.py` | Aufrufsteuerung der drei LLM-Stufen: Budget, Retry, Fehlerklassen, Template-Rückfall |
| `app/safety.py`, `app/policy_facts.py` | versionierte Safety-Policy, enger Preflight, zentrale 112 und synthetischer Szenariovertrag |
| `app/interpreter.py` | versionierter Interpretervertrag, Prompt und minimale Alias-Hinweise |
| `app/candidate_contract.py`, `app/candidates.py` | strikter Auswahlvertrag und deterministische Kandidatenbegrenzung |
| `app/llm_selection.py` | kompakter Selectorvertrag, Prompt, Bypass, ID-Validierung und deterministischer Fallback |
| `app/formulation.py`, `app/grounding.py`, `app/answer_plan.py`, `app/answer_act_texts.py` | Evidence, Prompt, strikter Planvertrag und Renderer; gebundene Fakten/Akte, Bedingungen, Länge und Karten |
| `app/grounding_claims.py`, `app/grounding_constraints.py`, `app/grounding_content.py`, `app/grounding_references.py` | historische Freitext-/Claimprüfung und zugehörige Forschungsreplays; kein produktives freies Ausgabeformat |
| `app/llm_budget.py` | kumulatives monotones Zeitbudget der drei externen LLM-Stufen |
| `app/dialogue.py`, `app/dialogue_flow.py` | versionierter Dialogzustand, lokalisierte Rückfragen und begrenzte Auflösung |
| `app/text_normalization.py` | gemeinsame Textnormalisierung des Anfragepfads |
| `app/retrieval.py` | historischer lexikalischer Retrievalbaseline, nur durch Tests genutzt; kein Fallback bei Interpreterausfall |
| `app/providers/llm.py` | getrennte Blablador-Aufrufe für Interpretation, Auswahl und geerdete Formulierung |
| `app/wfs_sync.py`, `app/wfs_releases.py` | WFS-Validierung, Releasevertrag, Promotion und Rollback |
| `app/infrastructure.py`, `app/toilet_sync.py`, `app/toilet_releases.py` | gemeinsame Infrastrukturmodelle sowie Toiletten-CSV und manuell aktivierte Releases |
| `app/drinking_fountain_source.py`, `app/drinking_fountain_sync.py`, `app/drinking_fountain_releases.py` | Wasserwerke-KML, kommunale Grenzprüfung, Diff und manuell aktivierte Trinkbrunnen-Releases |
| `app/infrastructure_results.py` | getrennte Primär-, Karten- und Markerprojektionen für Toiletten und Trinkwasser |
| `app/spatial.py`, `app/result_ordering.py`, `app/result_time.py` | gemeinsame HBF-Luftlinie, Fachprioritäten und belegte Essenszeitfenster |
| `app/curation.py`, `app/resources/bootstrap/curation/` | Kurationsschema, Quellbindung und freigegebene Runtime-Sicht |
| `app/i18n.py`, `app/translation_contract.py`, `app/translate_offers.py` | gespeicherte Übersetzungen, Integrität, Runtime-Policy und Review-CLI |
| `app/application_texts.py`, `app/multilingual_review.py` | versionierte UI-/Dialog-/Fallbacktexte sowie synthetischer Sprachreview |
| `app/sessions.py` | lokale, zeitlich begrenzte Gesprächszustände |
| `app/interactions.py` | lokales, vollständiges JSONL-Interaktionsprotokoll des Prototyps |
| `app/maps.py` | Kartendaten aus kuratierten Ortstypen und Einsatzzeitregeln |
| `app/speech.py` | serverseitige Transkription und Sprachsynthese mit geschlossenen Fehlercodes |
| `app/config.py`, `app/external_services.py`, `app/service_check.py` | Profile und Priorität, secretfreier Dienststatus, aktive Verfügbarkeitsprüfung |
| `app/logging_setup.py` | technisches Logformat mit Erlaubnisliste der Diagnosefelder |
| `app/static/` | Browser-Frontend und vendored Leaflet-Dateien |
| `data/canonical/` | normalisierte Quelle für Wartung/Migration, kein ungefilterter Runtime-Fallback |
| `data/wfs/releases/`, `data/wfs/active_release.json` | unveränderliche Releases und atomarer Active-Pointer |
| `data/i18n/` | versionierter Kartenübersetzungsstore; keine automatischen menschlichen Freigaben |
| `runtime/` | ignorierte Sessions, Interaktionsprotokolle und WFS-Prüfdaten |
| `tests/` | lokale Pytest-Suite und WFS-Testfixture |

## Häufige Befehle

```powershell
# Anwendung starten
python -m app --port 8002

# konfigurierte externe Dienste aktiv prüfen (ohne Secrets in der Ausgabe)
python -m app.service_check

# WFS nur prüfen und Änderungen bereitstellen
python -m app.wfs_sync --check

# amtliche Toilettenquelle prüfen und nur als Pending-Release bereitstellen
python -m app.toilet_sync fetch
python -m app.toilet_sync status

# nach manueller Diff-/Manifestprüfung ausdrücklich aktivieren
python -m app.toilet_sync promote <release-id>

# Trinkbrunnenquelle prüfen, nur als Pending bereitstellen und explizit aktivieren
python -m app.drinking_fountain_sync fetch
python -m app.drinking_fountain_sync status
python -m app.drinking_fountain_sync validate <release-id> --pending
python -m app.drinking_fountain_sync activate <release-id>

# aktive und ausstehende Releases anzeigen
python -m app.wfs_sync --list

# bereitgestellten Release erneut validieren und aktivieren
python -m app.wfs_sync --promote <release-id>

# auf einen früheren validen Release zurückschalten
python -m app.wfs_sync --rollback <release-id>

# lokalen Status und Integrität prüfen
python -m app.translate_offers status
python -m app.translate_offers validate

# fehlende Kartenübersetzungen erzeugen und Reviewpaket exportieren
python -m app.translate_offers generate --provider blablador
python -m app.translate_offers export-review --languages en,pl,ro,ru --output translation-review.json
```

Die Details und Sicherheitsfolgen dieser Befehle stehen in den verlinkten
Dokumentationsdateien.

## Schnittstellen

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/` | Frontend ausliefern |
| `GET` | `/api/health` | Daten-, Provider-, WFS- und Übersetzungsstatus |
| `GET` | `/api/i18n/copy` | versionierte UI-Texte für eine Sprache |
| `GET` | `/api/dialogue/copy` | kompatible Teilansicht der Dialogressourcen |
| `GET` | `/api/speech/config` | verfügbare Speech-Funktionen melden |
| `GET` | `/api/client-config` | Speech-Verfügbarkeit und Kartenkachelprofil für den Browser |
| `POST` | `/api/speech/transcribe` | rohe Audiodaten transkribieren |
| `POST` | `/api/speech/synthesize` | freigegebene Antwort-, Rückfrage- und Angebotstexte des letzten Session-Turns vorlesen |
| `POST` | `/api/query` | Frage beantworten und Karten liefern |

Die Datenmodelle stehen in `app/models.py`; eine ausführliche Beschreibung
enthält [docs/data-flow.md](docs/data-flow.md).

## Datenquelle und externe Dienste

Ausgangsquelle ist der WFS `OpenData:wohnungslosenhilfe` der Stadt Leipzig. Die
Runtime-Sicht wird zusätzlich aus einem schema-validierten Kurationskatalog
gebildet. Er bindet die Prototypfreigabe an einen unveränderlichen WFS-Hash,
behält Quelldaten unverändert und dokumentiert fachliche Ausschlüsse, Aliase,
Overrides und Provenienz. Ein neuer aktiver WFS-Release wird als Quelländerung
sichtbar, ersetzt den freigegebenen Katalog aber nicht automatisch. Die
Nutzeranwendung kann die Kuration nicht deaktivieren: Ohne expliziten Pfad gilt
der paketierte Standardkatalog. Bei Pointer- oder Releasefehlern wird nur der
exakt kataloggebundene lokale Release beziehungsweise der hashverifizierte
Paket-Bootstrap verwendet; andernfalls startet die Anwendung ohne Angebote und
meldet einen redigierten Fehlercode.
Zwei Jugendnotangebote werden getrennt davon aus paketierten, verifizierten
VKKJ-Betreiberangaben geladen. Sie imitieren keine WFS-Datensätze: Ihr eigener
Quellenhash und ihre offiziellen URLs sind an denselben Kurations- und
Runtime-Fingerprint gebunden, bevor sie in die einzige Runtime-Sicht gelangen.
Die Quelle wird im Nutzerpfad nicht live abgerufen. Die Betreiberseiten
veröffentlichen für beide Anschriften strukturierte WGS84-Koordinaten; nur
diese hashgebundenen Punkte erzeugen die VKKJ-Kartenmarker.
Providerzugänge sind für den Start optional; normale Bedarfsauswahl benötigt
jedoch den LLM-Interpreter. Server-STT und TTS sind standardmäßig deaktiviert und
werden nur über ihre Profile aktiviert (siehe
[Betriebsprofile](#betriebsprofile-und-externe-dienste)). Leaflet wird lokal aus
`app/static/vendor/` ausgeliefert; die Kartenkacheln lädt der Browser bei
`MAP_PROVIDER=osm` von OpenStreetMap.

Quelle: Stadt Leipzig, WFS Wohnungslosenhilfe. Die vorhandenen Notices/UI
ordnen die [Datenlizenz Deutschland – Namensnennung – Version 2.0](https://www.govdata.de/dl-de/by-2-0)
zu; die konkrete Endpunkt-/Weitergabeberechtigung ist noch nicht abschließend
belegt. Diese Attribution ersetzt die offene Rechteklärung nicht.

Öffentliche Toiletten stammen aus dem amtlichen Datensatz „Öffentliche
Toiletten, Stadt Leipzig“. Ressourcen-URL, Abrufzeit, SHA-256, Lizenz und
Namensnennung sind im separaten Release gebunden. Die Sortierung ist eine
Luftlinie vom Leipzig Hauptbahnhof, keine Geh-, Fahr- oder barrierefreie Route.
Snapshot, normalisierte Positivliste, Diff, Quellenmetadaten und beide
Inhaltshashes sind gemeinsam manifestgebunden und werden vor der Runtime-Nutzung
erneut reproduzierbar geprüft.

Feste Trinkwasserbrunnen stammen aus der offiziellen Seite der Leipziger
Wasserwerke und deren verlinktem My-Maps-KML-Export. Die administrative
Begrenzung auf Leipzig wird lokal gegen die amtlichen Polygone der statistischen
Bezirke geprüft. Der Paketstand enthält 35 Quellpunkte: 21 feste Leipziger
Runtimepunkte, neun feste Punkte außerhalb der Stadt und fünf mobile Punkte.
Die ausgeschlossenen Punkte bleiben in Snapshot, Normalisierung, Diff und
Provenienz. Die Quelle belegt Kostenfreiheit, Trinkwasser und einen grundsätzlichen
Betrieb von April bis Oktober, aber keinen Echtzeit-Funktionsstatus. Eine
ausdrückliche Datensatzlizenz ist nicht ausgewiesen; der Release speichert daher
`not_explicitly_specified` und behauptet weder Open Data noch Vollständigkeit.

## Bekannte Einschränkungen

- Das Repository kennt keine Kapazitäten oder garantierte Aufnahme.
- LENA diagnostiziert keine Gefährdung und löst weder Alarmierung, Anruf noch
  Standortübermittlung aus. Die Risikoklassifikation des Sprachmodells kann
  trotz striktem Vertrag falsch liegen; der enge Preflight erkennt nur wenige
  vollständig explizite Akutsätze. WP9A ist keine Produktivfreigabe.
- Safety-Texte sind technisch integriert, aber nicht muttersprachlich,
  professionell oder akustisch menschlich freigegeben. Deutsch steht auf
  `review_pending`, Englisch, Polnisch, Rumänisch und Russisch auf `machine`.
- Ohne ausdrückliche Zeit werden Essen und Trinkwasser gegen die aktuelle
  Europe/Berlin-Zeit geprüft. Andere Bedarfswege verwenden nur ihre ausdrücklich
  unterstützten Regeln. Der Hilfebus kann jederzeit als nicht räumlicher
  Telefon-/Vermittlungshinweis mit dokumentierten Zeiten erscheinen; als
  Essens-/Wasserstand am Hbf nur Sonntag 20:00--21:00.
- Stadtteile steuern außerhalb kuratierter Aliaszuordnungen wie „Kübel in
  Grünau“ noch kein geografisches Filter oder Ranking. Toiletten und
  Trinkwasserresultate werden ausschließlich zum Hauptbahnhof sortiert;
  Nutzergeolokalisierung fehlt.
- Trinkbrunnen werden nur von April bis Oktober als direkte Runtime-Ergebnisse
  verwendet. LENA kennt weder ihren aktuellen technischen Zustand noch eine
  taggenaue Einschaltung. Mobile Brunnen und externe Standorte sind ausgeschlossen.
- Server-STT und beide TTS-Varianten benötigen externe Dienste. Browseraudio
  wird serverseitig im Speicher zu PCM16/16-kHz-WAV normalisiert; deshalb muss
  die deklarierte PyAV-Laufzeitabhängigkeit installiert sein.
- Externe Provider sind zeitlich begrenzt. Bei Edge-TTS beendet Cancellation den
  lokalen Stream, garantiert aber keinen Abbruch bereits gestarteter externer Arbeit.
- Interpreter, Selector und Formulator haben eigene Grenzen von 15, 10 und 30
  Sekunden; die kumulierte tatsächliche Providerwartezeit einer Anfrage ist
  zusätzlich standardmäßig auf 45 Sekunden begrenzt.
- WFS-Promotion und Übersetzungsprüfung besitzen keine Admin-Oberfläche.
- Toiletten- und Trinkbrunnenstände werden nie automatisch promotet; `fetch` erzeugt höchstens
  einen Pending-Release. Ein mobiler Essensstand ohne verifizierte Lage erhält
  weder Distanzrang noch ersatzweise einen Marker an der Büroadresse.
- Die gespeicherten Fremdsprachen und gebundenen Antworttexte sind derzeit
  nicht als muttersprachlich oder professionell geprüft freigegeben. Die
  Standardpolicy `reviewed_or_machine` nutzt nur lokal integritätsgültige
  Maschinenübersetzungen und weist diesen Zustand in `/api/health` aus;
  fehlerhafte oder veraltete Einträge fallen auf deutsche Basisdaten zurück.
- Für fachliche Kurationsreviews ist noch kein periodischer Turnus vereinbart.
  `/api/health` meldet die Review-Policy und ausstehende Quelländerungen; die
  prototypisch geprüften Einträge bleiben bis zur nächsten fachlichen Entscheidung nutzbar.
- WFS-Promotionen sind nur innerhalb eines Prozesses synchronisiert; mehrere
  parallele Wartungsprozesse benötigen weiterhin operative Koordination.
- `runtime/sessions.json` kann Nutzereingaben enthalten und ist nicht für eine
  gemeinsame oder öffentliche Ablage bestimmt. Der Einzelprozess-Store entfernt
  abgelaufene und überzählige Sessions bei Zugriffen und ersetzt die JSON-Datei
  atomar. Sessions sind an den Fingerabdruck aus Quellenrelease, Quellenhash und
  Kurationsstand gebunden; Legacy- oder abweichende Verläufe werden nicht erneut
  an Interpreter oder Formulator gegeben. Der Interpreter erhält aus gültigen
  Sessions nur die letzten Nutzertexte, nicht frühere Assistentenantworten.
  Bei gleichem Fingerabdruck bleibt ein offener strukturierter Dialog auch bei
  einem Sprachwechsel erhalten. Buttonwerte werden gegen Dialog und Session
  geprüft und nicht als technische Werte im Chat oder Forschungsprotokoll gespeichert.
  Mehrere Serverprozesse werden nicht
  koordiniert.
- `runtime/logs/interactions.jsonl` entsteht nur mit
  `INTERACTION_LOGGING_ENABLED=true` und enthält dann Anfrage-Antwort-Paare für
  Evaluation und Verbesserung; es hat keine automatische Löschfrist. Safety-Eingaben werden
  durch einen festen Redaktionstoken ersetzt; gespeichert werden nur minimale
  Statusfelder, nicht Gefahrenbeschreibung, Modellbegründung, Diagnose oder Score. Andere Daten sind nicht
  anonym und die einfache lokale Speicherung ist nicht produktionsreif; Details
  und offene Datenschutzanforderungen stehen in [Installation und Betrieb](docs/setup.md).
- Das Wheel enthält Frontend, alle referenzierten vendorten Leaflet-Dateien und
  genau einen unveränderlichen Bootstrap-Datenstand. Externe WFS-Releases,
  Active-Pointer, Sessions, Interaktionsprotokolle und andere Runtime-Daten sind
  bewusst ausgeschlossen.
- Wheel-Installationen schreiben in eine externe Benutzer-Daten- und
  Runtimewurzel, niemals nach `site-packages`. Mehrere Prozesse sowie ein
  produktives Deployment bleiben weiterhin operativ zu konzipieren.

## Versionskontrolle und CI

Das kanonische Repository ist
[`lena-grounded-voice-assistant`](https://github.com/HannahHoffner/lena-grounded-voice-assistant).
Historische Import- und Reviewstände bleiben in Git nachvollziehbar; sie sind
keine Rekonstruktion der zuvor außerhalb von Git entstandenen Entwicklung.

Erstelle Änderungen auf kurzen Arbeitsbranches und halte Commits auf ein
reviewbares Thema begrenzt. Echte Zugangsdaten, Sessions und lokale Runtime-
Artefakte dürfen nicht versioniert werden. Vor einem Commit sollten mindestens
folgende Befehle erfolgreich sein:

```powershell
python -m pytest
python -m compileall -q app
python -m build
git diff --check
```

`.github/workflows/test.yml` führt diese Python-Prüfungen bei Pushes und Pull
Requests auf GitHub aus. Die Tests bauen Wheel und Source Distribution, prüfen
deren Inventar, bauen das Wheel erneut aus dem Source-Archiv und starten eine
frisch installierte App außerhalb des Checkouts. `requirements/constraints-py311.txt`
fixiert die direkte und transitive Auflösung für CPython 3.11. Ein vorhandener
Workflow ist noch kein Nachweis eines erfolgreichen Remote-Laufs; maßgeblich ist
der jeweilige Checkstatus auf GitHub.

Der zusätzliche CI-Job `container` baut die Docker-Test- und Runtime-Images,
führt die vollständige Suite ohne Netzwerk aus und prüft Healthcheck und zwei
Starts mit leerem temporärem Zustand. Dieser neue Job wurde noch nicht remote
ausgeführt.

Der Ubuntu-24.04-Docker-Build mit Python 3.12 und hashgesperrten Abhängigkeiten
wurde am 21.10.2026 auf Linux/AMD64 unter Docker Desktop erfolgreich geprüft:
vollständige Tests, Paketierung, Healthcheck und Neustart mit leerem temporärem
Zustand. Am 23.10.2026 wurde der Stand nach Umsetzung der Audit-Maßnahmen
erneut aus einem sauberen Export ohne Cache gebaut und geprüft (1.343 Python-Tests
bestanden, ein bekannter `xfail`, 19 Frontendtests, Volume/Neustart, Start ohne
Zugangsdaten, Blablador-Textanfrage, Edge-TTS); siehe
[IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md). Am 26.10.2026 bestand
auch der korrigierte Blockerstand den sauberen Neubau, vollständige netzlose
Containerregression und Runtime-/Volumeprüfung (1476 + 1 XFAIL, JS 19/19).
Zwei vorausgehende Buildversuche scheiterten am Ubuntu-Snapshotserver; der
erfolgreiche dritte Versuch änderte keine Locks. Historische Messungen bleiben
standgebunden; der anschließende vollständige Live-Lauf am Commit 2462e7d
ist separat in Bericht 12 dokumentiert und besteht nicht alle Gates.
Details und sichere
Startbefehle stehen in [Docker und Reproduzierbarkeit](docs/reproducibility.md). Eine Zenodo-DOI
existiert für diesen vorbereiteten Stand noch nicht.

## Weiterentwicklung und Wartung

Ändere fachliche Fakten nicht direkt in Antworten oder Prompts. Aktualisiere sie
über den WFS-Prüf- und Promotionsprozess und, wo fachlich erforderlich, über
den getrennten Kurationskatalog. Neue Antwortlogik muss sowohl den
deterministischen Fallback als auch die Grounding-Prüfung berücksichtigen.
Erweitere Datenmodelle rückwärtskompatibel und ergänze für jede fachliche Regel
einen Test. Echte Zugangsdaten gehören ausschließlich in die ignorierten Dateien
`.env` oder `.env.local`, niemals in Quellcode, Dokumentation oder Testfixtures.

Der providerfreie WP9B-Dry-Run meldet stets `prepared_not_executed`. Dieser
Status beschreibt den Dry-Run, nicht die gesamte Evaluationshistorie. Bereits
dokumentierte Modellläufe und ihre begrenzte Aussagekraft stehen getrennt in
der Evaluationsdokumentation. Ablauf, Aussagegrenzen und der erst nach gesonderter Freigabe
zulässige Stufe-1-Befehl stehen in
[Kontrollierte Live-Provider-Evaluation](docs/live-provider-evaluation.md).
