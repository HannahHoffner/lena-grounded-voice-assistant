# LENA

LENA ist eine lokal betriebene, mehrsprachige Webanwendung zur Suche nach
Hilfsangeboten für wohnungslose Menschen in Leipzig. Ein statisches Browser-
Frontend spricht mit einem FastAPI-Backend. Antworten werden ausschließlich aus
einem lokal aktivierten, aus dem städtischen WFS normalisierten Datenbestand
abgeleitet; ein optionales Sprachmodell formuliert diese Fakten, ist aber keine
Wissensquelle.

Die Anwendung richtet sich an technisch betreuende Personen sowie an Fachkräfte,
die LENA installieren, Datenänderungen prüfen, Übersetzungen pflegen und die
fachlichen Leitplanken weiterentwickeln.

## Funktionsumfang

- Textanfragen in Deutsch, Englisch, Polnisch, Rumänisch und Russisch
- deterministisches Retrieval mit sicherem Template-Fallback
- optionale zweistufige Blablador-Verarbeitung (Routing und Formulierung)
- Karten und Kartenansicht für Angebote mit verwertbaren Koordinaten
- lokale Sitzungsverläufe für kurze Folgefragen
- serverseitige Speech-to-Text- und Text-to-Speech-Schnittstellen
- geprüfte WFS-Synchronisation mit Staging, Diff und atomarer Aktivierung
- persistierte Kartenübersetzungen mit manuellen Overrides

LENA ersetzt keine Notfallversorgung, medizinische oder soziale Beratung und
kennt weder freie Kapazitäten noch eine garantierte Aufnahme.

## Schnellstart

Voraussetzung ist Python 3.11 oder neuer.

```powershell
cd code
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -c requirements/constraints-py311.txt -e ".[dev]"
Copy-Item .env.example .env
python -m app --port 8002
```

Öffne `http://127.0.0.1:8002`. Die Beispielkonfiguration startet ohne
Blablador-Zugang im deterministischen Modus.

Unter Linux oder macOS lautet die Aktivierung `source .venv/bin/activate`; das
Kopieren der Konfiguration erfolgt mit `cp .env.example .env`.

## Dokumentation

- [Architektur](docs/architecture.md)
- [Installation und Betrieb](docs/setup.md)
- [Konfigurationsreferenz](docs/configuration.md)
- [Datenflüsse und Schnittstellen](docs/data-flow.md)
- [Tests und Qualitätssicherung](docs/testing.md)

## Projektstruktur

| Pfad | Verantwortung |
|---|---|
| `app/main.py` | FastAPI-App, Lifecycle und HTTP-Endpunkte |
| `app/service.py` | Anfrageorchestrierung, Sicherheits- und Fallbackpfade |
| `app/retrieval.py` | deterministisches Ranking der Angebote |
| `app/providers/llm.py` | Blablador-Router, Formulierung und Grounding-Prüfung |
| `app/wfs_sync.py` | WFS-Validierung, Normalisierung, Diff und Promotion |
| `app/i18n.py`, `app/translate_offers.py` | gespeicherte Übersetzungen und Overrides |
| `app/sessions.py` | lokale, zeitlich begrenzte Gesprächszustände |
| `app/maps.py`, `app/temporal.py` | Kartendaten und vorsichtige Zeitlogik |
| `app/speech.py` | serverseitige Transkription und Sprachsynthese |
| `app/static/` | Browser-Frontend und vendored Leaflet-Dateien |
| `data/canonical/` | aktivierter normalisierter Laufzeitdatenbestand |
| `data/wfs/` | aktivierte Rohdaten, Snapshots und Änderungsbericht |
| `data/i18n/` | maschinelle Übersetzungen und manuelle Korrekturen |
| `runtime/` | generierte Sessions und ausstehende WFS-Prüfdaten |
| `tests/` | lokale Pytest-Suite und WFS-Testfixture |

## Häufige Befehle

```powershell
# Anwendung starten
python -m app --port 8002

# Tests ausführen
python -m pytest

# WFS nur prüfen und Änderungen bereitstellen
python -m app.wfs_sync --check

# bereitgestellte WFS-Daten validieren und aktivieren
python -m app.wfs_sync --promote

# fehlende Kartenübersetzungen erzeugen
python -m app.translate_offers --provider blablador
```

Die Details und Sicherheitsfolgen dieser Befehle stehen in den verlinkten
Dokumentationsdateien.

## Schnittstellen

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/` | Frontend ausliefern |
| `GET` | `/api/health` | Daten-, Provider-, WFS- und Übersetzungsstatus |
| `GET` | `/api/speech/config` | verfügbare Speech-Funktionen melden |
| `POST` | `/api/speech/transcribe` | rohe Audiodaten transkribieren |
| `POST` | `/api/speech/synthesize` | Antworttext als Audio erzeugen |
| `POST` | `/api/query` | Frage beantworten und Karten liefern |

Die Datenmodelle stehen in `app/models.py`; eine ausführliche Beschreibung
enthält [docs/data-flow.md](docs/data-flow.md).

## Datenquelle und externe Dienste

Fachliche Quelle ist der WFS `OpenData:wohnungslosenhilfe` der Stadt Leipzig.
Blablador beziehungsweise ein OpenAI-kompatibler Speech-Endpunkt sind optional.
`edge-tts` wird standardmäßig für Sprachsynthese verwendet und benötigt eine
Netzwerkverbindung. Leaflet wird lokal aus `app/static/vendor/` ausgeliefert; die
Kartenkacheln werden im Frontend von OpenStreetMap geladen.

Quelle: Stadt Leipzig, WFS Wohnungslosenhilfe,
[Datenlizenz Deutschland – Namensnennung – Version 2.0](https://www.govdata.de/dl-de/by-2-0).

## Bekannte Einschränkungen

- Das Repository kennt keine Kapazitäten oder garantierte Aufnahme.
- Zeitangaben werden nur für ausdrücklich unterstützte Regeln ausgewertet.
- Server-STT und beide TTS-Varianten benötigen externe Dienste.
- WFS-Promotion und Übersetzungsprüfung besitzen keine Admin-Oberfläche.
- `runtime/sessions.json` kann Nutzereingaben enthalten und ist nicht für eine
  gemeinsame oder öffentliche Ablage bestimmt.
- Das Wheel enthält Frontend, vendorte Leaflet-Dateien und den versionierten
  aktiven Datenstand. Für lokale Entwicklung bleibt die editable Installation
  aus dem Checkout der einfachste Weg.

## Versionskontrolle und CI

Das kanonische Repository ist `lena-grounded-voice-assistant`. Der Branch
`modernization/code3-baseline` übernimmt den geprüften Code3-Stand auf Basis des
historischen Commits `c20a38a`. Der Baseline-Commit dokumentiert einen
kontrollierten Ausgangsstand; er rekonstruiert nicht die außerhalb von Git
entstandene Entwicklungsgeschichte von Code3.

Erstelle Änderungen auf kurzen Arbeitsbranches und halte Commits auf ein
reviewbares Thema begrenzt. Echte Zugangsdaten, Sessions und lokale Runtime-
Artefakte dürfen nicht versioniert werden. Vor einem Commit sollten mindestens
folgende Befehle erfolgreich sein:

```powershell
python -m pytest
python -m compileall -q app
git diff --check
```

`.github/workflows/test.yml` führt die beiden Python-Prüfungen bei Pushes und
Pull Requests auf GitHub aus. Zusätzlich baut er das Wheel, prüft dessen Inhalt
und startet eine clean installierte App. `requirements/constraints-py311.txt`
fixiert die direkte und transitive Auflösung für CPython 3.11. Ein vorhandener
Workflow ist noch kein Nachweis eines erfolgreichen Remote-Laufs; maßgeblich ist
der jeweilige Checkstatus auf GitHub.

Der frühere unversionierte Arbeitsordner wurde nach Datei- und Secret-Prüfung in
`Code3-archive-pre-git-20260717` umbenannt. Er ist nur ein lokales, sensibles
Herkunftsarchiv und kein zweiter Checkout.

## Weiterentwicklung und Wartung

Ändere fachliche Fakten nicht direkt in Antworten oder Prompts. Aktualisiere sie
über den WFS-Prüf- und Promotionsprozess. Neue Antwortlogik muss sowohl den
deterministischen Fallback als auch die Grounding-Prüfung berücksichtigen.
Erweitere Datenmodelle rückwärtskompatibel und ergänze für jede fachliche Regel
einen Test. Echte Zugangsdaten gehören ausschließlich in die ignorierten Dateien
`.env` oder `.env.local`, niemals in Quellcode, Dokumentation oder Testfixtures.
