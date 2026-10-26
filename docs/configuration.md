# Konfiguration

Priorität (niedrig nach hoch): eingebaute Defaults < `.env` < `.env.local` <
Prozessumgebung. CLI-Optionen wie `--rewrite-provider` setzen die
Prozessumgebung und gewinnen deshalb immer; die Prozessumgebung wird beim Laden
nicht verändert. `.env`/`.env.local` werden nur im Checkout gesucht und sind
ignoriert; sie dürfen Geheimnisse enthalten. `.env.example` ist die vollständige,
kommentierte Vorlage mit den sicheren Defaults. Legacy-Namen mit Präfix `LENA_`
werden für mehrere Provider- und Sessionvariablen weiterhin akzeptiert; nicht
unterstützte Namen (`LENA_LLM_TEMPERATURE`, `LENA_LLM_FALLBACK_PROVIDER`) und
ungültige Profilwerte erscheinen als `configuration_warnings` in `/api/health`
und als `config.warning` im technischen Log, jeweils nur mit Variablennamen.

Mit `LENA_ENV_FILE_MODE=disabled` werden beide lokalen Dateien ignoriert; diese
Einstellung gilt für isolierte Prüfungen und den Docker-Standard. Native Starts,
Docker und `.env.example` verwenden seit dem Audit vom 23.10.2026 dieselben
sicheren Defaults: kein LLM, keine Server-STT/TTS, kein Quellabruf, kein
Interaktionsprotokoll. Siehe [Docker und Reproduzierbarkeit](reproducibility.md).

Jeder externe Dienst hat ein explizites Profil; `/api/health` meldet unter
`external_services` Profil, Konfiguriertheit und fehlende Variablennamen
(`availability: not_checked`). Eine aktive Erreichbarkeits- und
Modellinventarprüfung liefert `python -m app.service_check [--synthesize]`.

## Anwendung und Modell

| Variable | Pflicht | Standard | Zweck |
|---|---:|---|---|
| `LENA_KB_PATH` | nein | `data/canonical/offers.json` | normalisierte Quelle für Wartung/Migration; keine ungefilterte Runtime-Wissensbasis |
| `LENA_CURATION_PATH` | nein | externe Datei unter `LENA_DATA_DIR`, sonst paketierter Prototypkatalog | verpflichtender schema-validierter, hashgebundener Kurationskatalog; ungültige explizite Pfade stoppen den Nutzerbestand kontrolliert |
| `REWRITE_PROVIDER` | nein | `template` | `blablador` aktiviert den Interpreter; `template` liefert den technischen Hinweis mit gegebenenfalls Hilfebus-Kontaktkarte, ohne fachliche Suche |
| `BLABLADOR_BASE_URL` | für Blablador | – | OpenAI-kompatible Basis-URL |
| `BLABLADOR_API_KEY` | für Blablador | – | Zugangstoken; niemals committen |
| `BLABLADOR_MODEL` | für Blablador | – | gemeinsames Modell für alle drei Stufen, sofern keine Stufe unten überschrieben wird |
| `BLABLADOR_INTERPRETER_MODEL` | nein | `BLABLADOR_MODEL` | Stufenmodell für den Interpreter; empfohlen `alias-fast` (siehe unten) |
| `BLABLADOR_SELECTOR_MODEL` | nein | `BLABLADOR_MODEL` | Stufenmodell für die kontrollierte Auswahl; empfohlen `alias-fast` |
| `BLABLADOR_FORMULATOR_MODEL` | nein | `BLABLADOR_MODEL` | Stufenmodell für die Formulierung; empfohlen `alias-fast` |
| `LLM_INTERPRETER_TIMEOUT_SECONDS` | nein | `15` | Gesamtgrenze für den strukturierten LLM-Interpreter, mindestens 0,1 s |
| `LLM_SELECTOR_TIMEOUT_SECONDS` | nein | `10` | Gesamtgrenze für die kontrollierte LLM-Auswahl, mindestens 0,1 s |
| `LLM_FORMULATOR_TIMEOUT_SECONDS` | nein | `30` | Gesamtgrenze für Formulator und Übersetzungswartung, mindestens 0,1 s |
| `LLM_REQUEST_BUDGET_SECONDS` | nein | `45` | kumulierte monotone Obergrenze der tatsächlichen Interpreter-, Selector- und Formulator-Providerwartezeit pro Nutzeranfrage, mindestens 0,1 s |
| `BLABLADOR_TIMEOUT_SECONDS` | nein | – | Legacy-Fallback für Interpreter und Formulator, wenn deren eigene Variablen fehlen; nicht für den Selector |
| `BLABLADOR_MAX_CONTEXT_CHARS` | nein | `50000` | maximale Kontextgröße, mindestens 10000 |
| `BLABLADOR_MAX_TOKENS` | nein | `1200` | Ausgabelimit, mindestens 200 |
| `SESSION_TIMEOUT_SECONDS` | nein | `180` | Sessionablauf in Sekunden; positive Ganzzahl |
| `SESSION_MAX_ENTRIES` | nein | `500` | maximale Zahl lokal persistierter Sessions; Bereich 1–100000 |
| `QUERY_MAX_CHARS` | nein | `1000` | maximales Query-Feld; Bereich 1–10000 Zeichen |
| `TRANSLATION_RUNTIME_POLICY` | nein | `reviewed_or_machine` | `reviewed_only`, `reviewed_or_machine` oder `source_language_fallback`; ungültige Werte werden abgewiesen |
| `TECHNICAL_LOG_LEVEL` | nein | `INFO` | Level der redigierten technischen Ereignisse |
| `INTERACTION_LOGGING_ENABLED` | nein | `false` | lokales Prototyp-Interaktionsprotokoll aktivieren; Safety-Eingaben werden redigiert |
| `INTERACTION_LOG_PATH` | nein | `runtime/logs/interactions.jsonl` | lokale append-basierte UTF-8-JSONL-Datei |

## Speech

| Variable | Pflicht | Standard | Zweck |
|---|---:|---|---|
| `SPEECH_TRANSCRIPTION_PROVIDER` | nein | `disabled`, bzw. `openai` bei eigenen STT-Werten | `disabled`, `blablador` (ausdrückliche Wiederverwendung von `BLABLADOR_BASE_URL`/`BLABLADOR_API_KEY`) oder `openai` |
| `SPEECH_TRANSCRIPTION_BASE_URL` | für `openai` | – (bei `blablador`: Blablador-URL) | Audio-Endpunkt-Basis |
| `SPEECH_TRANSCRIPTION_API_KEY` | für `openai` | – (bei `blablador`: Blablador-Key) | Zugangstoken |
| `SPEECH_TRANSCRIPTION_MODEL` | für `openai` | – (bei `blablador`: `faster-whisper-large-v3`) | STT-Modell |
| `STT_TIMEOUT_SECONDS` | nein | `45` | STT-Gesamt- und HTTPX-Transportgrenze, mindestens 0,1 s |
| `SPEECH_TRANSCRIPTION_TIMEOUT_SECONDS` | nein | – | Legacy-Name für `STT_TIMEOUT_SECONDS` |
| `SPEECH_TRANSCRIPTION_MAX_BYTES` | nein | `10485760` | maximales Audio; Bereich 1024–26214400 Bytes |
| `SPEECH_SYNTHESIS_PROVIDER` | nein | `disabled`, bzw. `openai` bei eigenen TTS-Werten | `disabled`, `edge` (externer Microsoft-Dienst über `edge-tts`) oder `openai`; nie aus dem LLM-Zugang abgeleitet |
| `SPEECH_SYNTHESIS_BASE_URL` | für `openai` | – | TTS-Endpunkt-Basis |
| `SPEECH_SYNTHESIS_API_KEY` | für `openai` | – | Zugangstoken |
| `SPEECH_SYNTHESIS_MODEL` | für `openai` | – | am Endpunkt tatsächlich angebotenes TTS-Modell; Blablador bot am 23.10.2026 keines an (`gpt-4o-mini-tts` → HTTP 404) |
| `SPEECH_SYNTHESIS_VOICE` | nein | `alloy` | Voice-Name |
| `SPEECH_SYNTHESIS_RESPONSE_FORMAT` | nein | `mp3` | OpenAI-kompatibles Antwortformat; Edge liefert immer MP3, auch in `/api/speech/config` |
| `TTS_TIMEOUT_SECONDS` | nein | `45` | TTS-Gesamtgrenze für OpenAI-kompatibles und Edge-TTS, mindestens 0,1 s |
| `SPEECH_SYNTHESIS_TIMEOUT_SECONDS` | nein | – | Legacy-Name für `TTS_TIMEOUT_SECONDS` |
| `SPEECH_SYNTHESIS_MAX_CHARS` | nein | `4000` | maximaler TTS-Text; Bereich 1–20000 Zeichen |

## Karte

| Variable | Pflicht | Standard | Zweck |
|---|---:|---|---|
| `MAP_PROVIDER` | nein | `osm` | `osm`: Browser lädt Basiskacheln von OpenStreetMap; `disabled`: keine Basiskarte, Marker bleiben lokal (Offline/datensparsam). Ausgeliefert über `/api/client-config` |

## WFS

| Variable | Pflicht | Standard | Zweck |
|---|---:|---|---|
| `WFS_URL` | nein | städtischer Wohnungslosenhilfe-WFS | Datenquelle |
| `WFS_AUTO_SYNC` | nein | `false` | periodische Prüfung aktivieren (externer Abruf) |
| `WFS_AUTO_PROMOTE` | nein | `false` | geprüfte Änderungen automatisch aktivieren |
| `WFS_CHECK_INTERVAL_HOURS` | nein | `24` | Prüfintervall, mindestens 1 h |
| `WFS_CONNECT_TIMEOUT_SECONDS` | nein | `10` | Verbindungs-/Poolgrenze des WFS-Clients, mindestens 0,1 s |
| `WFS_READ_TIMEOUT_SECONDS` | nein | `30` | Lese-/Schreibgrenze des WFS-Clients, mindestens 0,1 s |

`WFS_CHECK_INTERVAL_HOURS` steuert ausschließlich die technische Prüfung der
Quelle. Es ist kein fachlicher Kurations-Prüfturnus. Der aktuelle Katalog setzt
`review_interval` deshalb auf `null` und meldet
`review_policy_status=not_yet_formally_defined` über `/api/health`.
Der prototypische Reviewstatus ist ausdrücklich keine formale oder produktive
Freigabe. `/api/health` weist dies als `formal_approval_status=not_granted`
aus.

## Öffentliche Toiletten

| Variable | Pflicht | Standard | Zweck |
|---|---:|---|---|
| `TOILET_SOURCE_URL` | nein | amtliche Leipziger CSV-Ressource | separater Infrastrukturabruf |
| `TOILET_AUTO_SYNC` | nein | `false` | periodisch prüfen und Änderungen als Pending bereitstellen |
| `TOILET_AUTO_PROMOTE` | nein | `false` | reservierter Sicherheitsschalter; `true` wird im Prototyp abgewiesen |
| `TOILET_SYNC_INTERVAL_SECONDS` | nein | `86400` | technisches Prüfintervall, mindestens 300 Sekunden |
| `TOILET_CONNECT_TIMEOUT_SECONDS` | nein | `10` | Verbindungs-/Poolgrenze |
| `TOILET_READ_TIMEOUT_SECONDS` | nein | `30` | Lese-/Schreibgrenze |

Eine automatische Toiletten-Promotion ist im Prototyp absichtlich gesperrt;
`TOILET_AUTO_PROMOTE=true` verhindert den Start mit einer klaren
Konfigurationsfehlermeldung. `fetch` aktiviert keinen Datenstand. Nur
`python -m app.toilet_sync promote <release-id>` ersetzt den Pointer nach einer
erneuten vollständigen Manifest-, Datei- und Schemaprüfung.

## Feste Trinkwasserbrunnen

| Variable | Pflicht | Standard | Zweck |
|---|---:|---|---|
| `DRINKING_FOUNTAIN_SOURCE_URL` | nein | Wasserwerke-My-Maps-KML | strukturierter Standortabruf |
| `DRINKING_FOUNTAIN_SOURCE_PAGE_URL` | nein | offizielle Wasserwerke-Seite | bindende Fachquellenidentität |
| `DRINKING_FOUNTAIN_BOUNDARY_URL` | nein | amtliche Leipziger Bezirks-GeoJSON | lokale administrative Leipzig-Prüfung |
| `DRINKING_FOUNTAIN_AUTO_SYNC` | nein | `false` | periodisch prüfen und Änderungen nur als Pending bereitstellen |
| `DRINKING_FOUNTAIN_AUTO_PROMOTE` | nein | `false` | reserviert; `true` wird abgewiesen |
| `DRINKING_FOUNTAIN_SYNC_INTERVAL_SECONDS` | nein | `86400` | technisches Prüfintervall |
| `DRINKING_FOUNTAIN_CONNECT_TIMEOUT_SECONDS` | nein | `10` | Verbindungs-/Poolgrenze beider öffentlichen Abrufe |
| `DRINKING_FOUNTAIN_READ_TIMEOUT_SECONDS` | nein | `30` | Lese-/Schreibgrenze beider öffentlichen Abrufe |

Die drei Quell-URLs sind Bestandteil der Releaseidentität. Eine abweichende
Konfiguration kann einen paketierten oder lokalen Stand daher nicht als
quellgleich laden. `fetch` aktiviert nichts; nur
`python -m app.drinking_fountain_sync activate <release-id>` wechselt nach
erneuter vollständiger Prüfung den Active- und Last-Verified-Pointer. Ein
automatischer Hintergrundcheck erzeugt ebenfalls höchstens Pending-Daten.

## Räumliche Auswahl

| Variable | Pflicht | Standard | Zweck |
|---|---:|---|---|
| `HBF_LATITUDE` | nein | `51.34556` | Breitengrad der Referenzkoordinate für Luftliniensortierung |
| `HBF_LONGITUDE` | nein | `12.38222` | Längengrad der Referenzkoordinate für Luftliniensortierung |

Beide Werte bilden gemeinsam den einzigen Ursprung, gegen den `app/spatial.py`
für alle kuratierten sozialen/WFS-Angebote, öffentlichen Toiletten und
Trinkbrunnen die Haversine-Luftlinie berechnet (`app/spatial.py::LEIPZIG_HBF`
bleibt der eingebaute Standard- und Testwert). Räumliche Sortierung bleibt in
jedem Fall nachgeordnet gegenüber fachlicher Eignung/Priorität. Ist nur eine
der beiden Variablen gesetzt oder liegt das Paar außerhalb des Leipziger
Umgebungsrahmens (51.1-51.6 / 12.0-12.8), wird das gesamte Paar verworfen und
der Standard verwendet; es entsteht kein aus zwei unterschiedlichen Quellen
gemischter Ursprung.

Booleans akzeptieren `1`, `true`, `yes` oder `on` als wahr. Ungültige numerische
Werte fallen auf die im Code definierten Standards zurück.

Alle Timeoutwerte müssen positiv und endlich sein. Ungültige Umgebungswerte
fallen auf sichere Standards zurück; explizite `Settings` mit null, negativen
oder nicht endlichen Grenzen werden abgewiesen. Die Untergrenze von 0,1 Sekunden
dient schnellen kontrollierten Tests und ist kein empfohlener Betriebswert.

Der Session-Store entfernt Einträge erst, wenn ihre letzte Aktivität die TTL
überschreitet; exakt an der Grenze bleibt die Session aktiv. Nach dem
TTL-Cleanup werden bei Bedarf die ältesten Einträge bis
`SESSION_MAX_ENTRIES` entfernt. Beide Grenzen gelten für den lokalen
Einzelprozessbetrieb und sind keine prozessübergreifende Kapazitätssteuerung.

Ein Interpreter-Timeout sowie HTTP-, JSON-, Schema-, Vertrags-, Budget- oder
Verfügbarkeitsfehler führen fail-closed zum lokalisierten technischen Hinweis
mit bedingter 112-Angabe -- zusätzlich mit dem
deterministischen Hilfebus-Kontakt (Telefon, Zeiten, Karte), sofern die
Wissensbasis ihn liefert (siehe
[Safety- und Fehlerpolitik](safety-and-error-policy.md)). CandidateSelector,
Infrastruktur, Selector und Formulator werden nicht gestartet. Ein
Selector-Timeout verwirft die gesamte Modellantwort, verwendet nur die
deterministische Kandidatenreihenfolge und sperrt denselben Provider für den
Formulator dieser Anfrage. Ein Formulator-Timeout verwendet den vorhandenen
Template-Fallback. Es gibt keinen automatischen LLM-Retry (außer dem einen
Formulator-Retry bei einem Grounding-/Parsingfehler, nicht bei einem
Transportfehler). Die drei Stufengrenzen sind bewusst so zu wählen, dass sie
einzeln nicht über `LLM_REQUEST_BUDGET_SECONDS` liegen (Standard: 15 + 10 + 30
= 55 Sekunden nominell, aber 45 Sekunden Budget) -- `LLMRequestBudget` klemmt
jede Stufe ohnehin auf `min(Stufenlimit, Restbudget)`, ein Stufenlimit über dem
Budget ist aber irreführend und lässt eine einzelne langsame Stufe (typischerweise
den Interpreter) das gesamte Budget verbrauchen, bevor die folgenden Stufen
überhaupt starten. Der veraltete Legacy-Schalter `BLABLADOR_TIMEOUT_SECONDS`
(bzw. `LENA_LLM_TIMEOUT_SECONDS`) sollte aus demselben Grund vermieden werden,
da er kaskadierend sowohl Interpreter- als auch Formulator-Stufenlimit setzt.
Ist es erschöpft, wird die nächste Stufe nicht gestartet und der kontrollierte
deterministische beziehungsweise Templatepfad verwendet.

Interpreter, Selector und Formulator können über `BLABLADOR_INTERPRETER_MODEL`,
`BLABLADOR_SELECTOR_MODEL` und `BLABLADOR_FORMULATOR_MODEL` getrennte
Stufenmodelle verwenden; unkonfiguriert fällt jede Stufe auf das gemeinsame
`BLABLADOR_MODEL` zurück. Empfohlen ist aktuell `alias-fast` für alle drei
Stufen: ein informeller Test am 2026-08-06 fand `alias-large` nach ~50 s
hängend mit Verbindungsabbruch (3/3 Versuchen) und `alias-huge` mit in
`content` leakendem `<think>`-Reasoning, das den strikten JSON-Parser bricht;
`alias-fast` lieferte sauberes, geerdetes JSON. Der erste offizielle
WP9B-Live-Smoke-Gate für die Interpreter-Stufe (Lauf
`run_e5ef56937b0d47e3a409d43d3ce4db09`, 2026-08-14, Commit `fbcc85a`)
bestätigt das für die Interpreter-Stufe: 15/15 technisch valide, 0
Fehler, 0 kritische inhaltliche Fehler.

Für WP9B wird diese Konfiguration nicht verändert. Der providerfreie
Evaluationsplan liest nur eine feste Positivliste nicht geheimer Planwerte und
gibt von der Basis-URL nur den Hostnamen aus. `LENA_ALLOW_LIVE_SMOKE=true` ist
keine dauerhafte Anwendungskonfiguration, sondern eine von mehreren jeweils
neu zu setzenden Live-Freigaben. Ohne Stufe, Bestätigungsflag, erwartete
Provideridentität und alle stufengebundenen Limits endet der Lauf vor
Settings und Provider. Siehe
[Kontrollierte Live-Provider-Evaluation](live-provider-evaluation.md).

STT- und TTS-Timeouts ergeben generische HTTP-503-Antworten. Server-STT
normalisiert die vom Browser gelieferten WebM-, Ogg-, MP4-, MP3- oder
WAV-Aufnahmen unabhängig von der Endung zu mono PCM16/16-kHz-WAV, bevor der
externe Endpunkt aufgerufen wird. Der laufende Server muss nach einer
Installation oder Aktualisierung mit der deklarierten PyAV-Abhängigkeit neu
gestartet werden. Nicht dekodierbares Audio ergibt HTTP 422; Provider- und
Timeoutdetails bleiben öffentlich redigiert und werden technisch nur als
Fehlercode, Dauer und gegebenenfalls Upstream-Status protokolliert. WFS trennt
Verbindungs- und Lesetimeout; vor vollständigem Download und Validierung wird
kein aktiver Datenstand verändert.

`WFS_AUTO_PROMOTE=true` aktiviert nur den Release, der aus demselben einzelnen
Hintergrundabruf vollständig erstellt und verifiziert wurde. Der manuelle
`--promote <release-id>`-Befehl führt keinen Netzwerkabruf aus. Automatische und
manuelle Vorgänge sind nur innerhalb eines Prozesses gesperrt.

`INTERACTION_LOGGING_ENABLED` ist bewusst unabhängig vom technischen Log-Level.
Für Tests oder Betriebsformen ohne Volltextspeicherung kann der Schalter auf
`false` gesetzt werden. Relative Interaktionspfade werden gegen
`LENA_RUNTIME_DIR` beziehungsweise dessen Standard aufgelöst; ein führendes
`runtime/` bleibt zur bestehenden Beispielkonfiguration kompatibel. Der Pfad
liegt außerhalb von Git und Packaging. Konfiguriere keinen versionierten Pfad
und keine Cloud-Synchronisation für diese Datei.

## Paket-, Daten- und Runtimepfade

`LENA_DATA_DIR` bezeichnet die veränderliche externe Datenwurzel für aktivierte
WFS-Releases, Active-Pointer und Übersetzungswartung. `LENA_RUNTIME_DIR`
bezeichnet die externe Wurzel für Sessions, Interaktionsprotokolle, WFS-Pending
und Statusdateien. Im Source-Checkout sind die Standards `data/` und `runtime/`;
in einer Wheel-Installation liegen beide außerhalb von `site-packages` im
Benutzer-Datenverzeichnis. Absolute Pfade sind für Dienstinstallationen am
eindeutigsten. `LENA_KB_PATH` bezeichnet eine normalisierte Wartungs- und
Migrationsquelle, keinen frei austauschbaren Runtime-Bootstrap.

Das Wheel enthält einen unveränderlichen Bootstrap. Für soziale Angebote muss
das WFS-Release zusätzlich zur technischen Verifikation exakt zur Quellenbindung
des Kurationskatalogs passen. Ein abweichender Active-Pointer setzt diese Bindung
nicht außer Kraft: der Loader versucht das exakt gebundene lokale Release und
danach den passenden paketierten Bootstrap, niemals beliebige ältere oder
Pending-Verzeichnisse. Toiletten und Brunnen haben eigene verifizierte
Active-/Last-verified-/Previous-verified-/Bootstrap-Rückfälle. Ist eine dieser
Infrastrukturquellen vollständig unbrauchbar, bleibt die soziale Wissensbasis
verfügbar; fehlt deren gültige Kurations-/Quellenbindung, scheitert das Laden.

Die API lehnt zu große Query- und TTS-Texte mit HTTP 422 ab. STT-Audio über
dem konfigurierten Limit erhält HTTP 413; geprüft werden sowohl ein vorhandener
`Content-Length`-Header als auch die tatsächlich gestreamten Bytes. Unterstützt
sind WebM, Ogg, MP4, MPEG/MP3 und WAV. Ein ausdrücklich anderer Medientyp erhält
HTTP 415, ein leerer Audiobody HTTP 422. Diese Anwendungsgrenzen ergänzen, aber
ersetzen keine engeren Reverse-Proxy-Limits. Query- und TTS-Textgrenzen greifen
nach dem Parsen des JSON-Bodys; sie begrenzen nicht dessen gesamte Bytegröße.

## Serverbindung

`python -m app` bindet standardmäßig an `127.0.0.1`. Loopback-Adressen und
`localhost` dürfen ohne weitere Option verwendet werden. Eine LAN- oder
öffentliche Bindung erfordert eine doppelte, ausdrückliche Angabe:

```powershell
python -m app --host 0.0.0.0 --allow-public
```

`--allow-public` fügt weder TLS noch Authentifizierung, Rate-Limiting oder einen
Produktionsserver hinzu. Eine nicht lokale Exposition benötigt weiterhin einen
geeigneten Reverse Proxy sowie ein Datenschutz- und Betriebskonzept.

## Sicherheitsregeln

- Keine echten Keys in `.env.example`, README, Tests oder Fehlermeldungen.
- Für Entwicklung `WFS_AUTO_PROMOTE=false` beibehalten.
- `.env.local` hat absichtlich höchste Priorität; prüfe diese Datei bei schwer
  erklärbaren lokalen Abweichungen, ohne ihren Inhalt zu veröffentlichen.
- `/api/health` meldet Verfügbarkeit, aber keine geheimen Werte.
- Technische Logs enthalten keine vollständigen Anfrage-/Antworttexte. Das
  getrennte Interaktions-JSONL enthält diese Volltexte absichtlich und ist daher
  als besonders schützenswerte lokale Forschungsdatei zu behandeln.

## Ausgabeprotokoll ab 25.10.2026

Formulatorvertrag 6, Prompt 24 und Validator 6 verwenden einen geschlossenen
Antwortplan. Dafür sind keine neuen Umgebungsvariablen oder Dienste nötig.
Ein Rückschalter auf freie Modellprosa ist nicht vorgesehen.
Siehe [Antwortakte](controlled-answer-acts.md).
