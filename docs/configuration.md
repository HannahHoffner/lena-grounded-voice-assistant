# Konfiguration

Die Anwendung lädt zuerst `.env` und anschließend `.env.local`; Werte aus
`.env.local` überschreiben auch bereits gesetzte Prozessvariablen. Beide Dateien
sind ignoriert und dürfen Geheimnisse enthalten. `.env.example` enthält nur
sichere Platzhalter. Legacy-Namen mit Präfix `LENA_` werden für mehrere Provider-
und Sessionvariablen weiterhin akzeptiert.

## Anwendung und Modell

| Variable | Pflicht | Standard | Zweck |
|---|---:|---|---|
| `LENA_KB_PATH` | nein | `data/canonical/offers.json` | Laufzeit-Wissensbasis |
| `REWRITE_PROVIDER` | nein | `template` | `template` oder `blablador` |
| `BLABLADOR_BASE_URL` | für Blablador | – | OpenAI-kompatible Basis-URL |
| `BLABLADOR_API_KEY` | für Blablador | – | Zugangstoken; niemals committen |
| `BLABLADOR_MODEL` | für Blablador | – | Modell-ID oder Alias |
| `LLM_ROUTER_TIMEOUT_SECONDS` | nein | `15` | Gesamtgrenze für den kompakten LLM-Router, mindestens 0,1 s |
| `LLM_FORMULATOR_TIMEOUT_SECONDS` | nein | `30` | Gesamtgrenze für Formulator und Übersetzungswartung, mindestens 0,1 s |
| `BLABLADOR_TIMEOUT_SECONDS` | nein | – | Legacy-Fallback für beide LLM-Grenzen, wenn deren neue Variablen fehlen |
| `BLABLADOR_MAX_CONTEXT_CHARS` | nein | `50000` | maximale Kontextgröße, mindestens 10000 |
| `BLABLADOR_MAX_TOKENS` | nein | `1200` | Ausgabelimit, mindestens 200 |
| `SESSION_TIMEOUT_SECONDS` | nein | `180` | Sessionablauf in Sekunden; positive Ganzzahl |
| `SESSION_MAX_ENTRIES` | nein | `500` | maximale Zahl lokal persistierter Sessions; Bereich 1–100000 |
| `QUERY_MAX_CHARS` | nein | `1000` | maximales Query-Feld; Bereich 1–10000 Zeichen |
| `TECHNICAL_LOG_LEVEL` | nein | `INFO` | Level der redigierten technischen Ereignisse |
| `INTERACTION_LOGGING_ENABLED` | nein | `true` | lokales vollständiges Prototyp-Interaktionsprotokoll aktivieren |
| `INTERACTION_LOG_PATH` | nein | `runtime/logs/interactions.jsonl` | lokale append-basierte UTF-8-JSONL-Datei |

## Speech

| Variable | Pflicht | Standard | Zweck |
|---|---:|---|---|
| `SPEECH_TRANSCRIPTION_BASE_URL` | für STT | Blablador-URL | Audio-Endpunkt-Basis |
| `SPEECH_TRANSCRIPTION_API_KEY` | für STT | Blablador-Key | Zugangstoken |
| `SPEECH_TRANSCRIPTION_MODEL` | nein | `whisper-large-v3` | STT-Modell |
| `STT_TIMEOUT_SECONDS` | nein | `45` | STT-Gesamt- und HTTPX-Transportgrenze, mindestens 0,1 s |
| `SPEECH_TRANSCRIPTION_TIMEOUT_SECONDS` | nein | – | Legacy-Name für `STT_TIMEOUT_SECONDS` |
| `SPEECH_TRANSCRIPTION_MAX_BYTES` | nein | `10485760` | maximales Audio; Bereich 1024–26214400 Bytes |
| `SPEECH_SYNTHESIS_PROVIDER` | nein | `edge` oder automatisch `openai` | `edge`/`openai` |
| `SPEECH_SYNTHESIS_BASE_URL` | für OpenAI-TTS | – | TTS-Endpunkt-Basis |
| `SPEECH_SYNTHESIS_API_KEY` | für OpenAI-TTS | – | Zugangstoken |
| `SPEECH_SYNTHESIS_MODEL` | nein | `gpt-4o-mini-tts` bei OpenAI | TTS-Modell |
| `SPEECH_SYNTHESIS_VOICE` | nein | `alloy` | Voice-Name |
| `SPEECH_SYNTHESIS_RESPONSE_FORMAT` | nein | `mp3` | Antwortformat |
| `TTS_TIMEOUT_SECONDS` | nein | `45` | TTS-Gesamtgrenze für OpenAI-kompatibles und Edge-TTS, mindestens 0,1 s |
| `SPEECH_SYNTHESIS_TIMEOUT_SECONDS` | nein | – | Legacy-Name für `TTS_TIMEOUT_SECONDS` |
| `SPEECH_SYNTHESIS_MAX_CHARS` | nein | `4000` | maximaler TTS-Text; Bereich 1–20000 Zeichen |

## WFS

| Variable | Pflicht | Standard | Zweck |
|---|---:|---|---|
| `WFS_URL` | nein | städtischer Wohnungslosenhilfe-WFS | Datenquelle |
| `WFS_AUTO_SYNC` | nein | `true` | periodische Prüfung aktivieren |
| `WFS_AUTO_PROMOTE` | nein | `false` | geprüfte Änderungen automatisch aktivieren |
| `WFS_CHECK_INTERVAL_HOURS` | nein | `24` | Prüfintervall, mindestens 1 h |
| `WFS_CONNECT_TIMEOUT_SECONDS` | nein | `10` | Verbindungs-/Poolgrenze des WFS-Clients, mindestens 0,1 s |
| `WFS_READ_TIMEOUT_SECONDS` | nein | `30` | Lese-/Schreibgrenze des WFS-Clients, mindestens 0,1 s |

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

Ein Router-Timeout führt in das deterministische Retrieval und gilt weder als
erkannte noch als ausgeschlossene Akutgefahr. Ein Formulator-Timeout verwendet
den vorhandenen Template-Fallback. Es gibt keinen automatischen LLM-Retry.
STT- und TTS-Timeouts ergeben generische HTTP-503-Antworten. WFS trennt
Verbindungs- und Lesetimeout; vor vollständigem Download und Validierung wird
kein aktiver Datenstand verändert.

`WFS_AUTO_PROMOTE=true` aktiviert nur den Release, der aus demselben einzelnen
Hintergrundabruf vollständig erstellt und verifiziert wurde. Der manuelle
`--promote <release-id>`-Befehl führt keinen Netzwerkabruf aus. Automatische und
manuelle Vorgänge sind nur innerhalb eines Prozesses gesperrt.

`INTERACTION_LOGGING_ENABLED` ist bewusst unabhängig vom technischen Log-Level.
Für Tests oder Betriebsformen ohne Volltextspeicherung kann der Schalter auf
`false` gesetzt werden. Relative Interaktionspfade werden gegen den ermittelten
Projekt-Root aufgelöst. Der Standardpfad liegt unter dem von Git und Packaging
ausgeschlossenen `runtime/`. Konfiguriere keinen versionierten Pfad und keine
Cloud-Synchronisation für diese Datei.

Die API lehnt zu große Query- und TTS-Texte mit HTTP 422 ab. STT-Audio über
dem konfigurierten Limit erhält HTTP 413; geprüft werden sowohl ein vorhandener
`Content-Length`-Header als auch die tatsächlich gestreamten Bytes. Unterstützt
sind WebM, Ogg, MP4, MPEG/MP3 und WAV. Ein ausdrücklich anderer Medientyp erhält
HTTP 415, ein leerer Audiobody HTTP 422. Diese Anwendungsgrenzen ergänzen, aber
ersetzen keine engeren Reverse-Proxy-Limits.

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
