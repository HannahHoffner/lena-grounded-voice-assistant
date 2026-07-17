# Installation und Betrieb

## Voraussetzungen

- Python 3.11 oder neuer
- Netzwerkzugriff nur für WFS-Prüfung, Blablador, serverseitiges Speech und
  OpenStreetMap-Kartenkacheln
- optional ein Blablador-/OpenAI-kompatibler API-Zugang

## Entwicklungsinstallation

```powershell
cd code
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m app --port 8002
```

`python -m app --help` zeigt `--host`, `--port`, `--reload` und
`--rewrite-provider`. Standardmäßig bindet der Server an `127.0.0.1:8002`.
`--reload` ist nur für lokale Entwicklung vorgesehen.

## Sicherer Offline-naher Start

Setze mindestens `REWRITE_PROVIDER=template` und `WFS_AUTO_SYNC=false`, wenn der
Start keine Modell- oder WFS-Anfrage auslösen soll. Das Frontend bleibt nutzbar;
Speech und Kartenkacheln können ohne Netzwerk eingeschränkt sein.

## Zustandsdateien

`runtime/` enthält generierte WFS-Stagingdaten und Sessions. Das Verzeichnis ist
laut `.gitignore` lokal. `data/canonical/offers.json` und die Dateien unter
`data/wfs/` sind dagegen der aktivierte, nachvollziehbare Datenstand.

## Git-Arbeitsweise und lokale Daten

Das kanonische Checkout-Verzeichnis ist `code/`. Der erste Code3-Baseline-
Commit baut auf der erhaltenen LENA-v1/v2-Historie auf, bildet aber nicht die
vollständige Entstehungsgeschichte des zuvor unversionierten Code3-Ordners ab.
Neue Arbeiten erfolgen auf einem kurzen Branch vom jeweils freigegebenen Stand;
Commits sollen ein fachlich zusammengehöriges Thema enthalten.

Versioniert werden die aktivierten Daten unter `data/canonical/`, `data/wfs/`
und `data/i18n/` sowie Testfixtures. Lokal bleiben insbesondere:

- `.env` und `.env.*` außer `.env.example`,
- `runtime/` einschließlich Fragen und Antworten in Sessions,
- Caches, virtuelle Umgebungen, Builds und Coverage-Artefakte,
- Audio, lokale Datenbanken, Browserprofile und heruntergeladene Modelle,
- temporäre WFS-Promotionen und OneDrive-Konfliktdateien.

Prüfe vor jedem Commit mindestens `git status`, `git diff --check` und die
vollständige Staging-Liste. Übertrage keine lokale `.env` oder Sessiondatei in
Issues, Logs oder CI-Konfigurationen.

## WFS-Betrieb

```powershell
# Abrufen, validieren und nur bereitstellen
python -m app.wfs_sync --check

# Abrufen, validieren und aktivieren
python -m app.wfs_sync --promote
```

Promotion verändert fachliche Laufzeitdaten. Prüfe vorher den ausstehenden Diff
und sichere den bisher aktivierten Stand über Versionskontrolle. Während einer
Nutzeranfrage findet kein WFS-Zugriff statt.

## Übersetzungswartung

```powershell
python -m app.translate_offers --provider blablador --dry-run
python -m app.translate_offers --provider blablador
```

Mit `--provider copy` werden deutsche Inhalte kopiert; dies ist ein technischer
Fallback, keine fachlich geprüfte Übersetzung. Manuelle Korrekturen gehören in
`data/i18n/manual_overrides.json` und überschreiben maschinelle Werte.

## Deployment-Stand

Das Repository enthält weder Dockerfile noch Service-/Cloud-Konfiguration. Ein
Produktivbetrieb benötigt daher außerhalb dieses Codes mindestens einen
Prozessmanager, TLS, Zugriffsschutz, Logging-, Datenschutz-, Backup- und
Updatekonzept. Der vorhandene Startbefehl ist ein Entwicklungs-/Prototypbetrieb.
