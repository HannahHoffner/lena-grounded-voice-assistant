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
python -m pip install -c requirements/constraints-py311.txt -e ".[dev]"
Copy-Item .env.example .env
python -m app --port 8002
```

`python -m app --help` zeigt `--host`, `--allow-public`, `--port`, `--reload`
und `--rewrite-provider`. Standardmäßig bindet der Server an
`127.0.0.1:8002`. Nicht lokale Hosts werden ohne das zusätzliche
`--allow-public` abgewiesen. Dieses Flag schützt gegen versehentliche
Exposition, ersetzt aber weder TLS, Authentifizierung noch einen Reverse Proxy.
`--reload` ist nur für lokale Entwicklung vorgesehen.

## Sicherer Offline-naher Start

Setze mindestens `REWRITE_PROVIDER=template` und `WFS_AUTO_SYNC=false`, wenn der
Start keine Modell- oder WFS-Anfrage auslösen soll. Das Frontend bleibt nutzbar;
Speech und Kartenkacheln können ohne Netzwerk eingeschränkt sein.

Für langsame oder kontrolliert blockierte Provider können die Timeoutwerte aus
[Konfiguration](configuration.md) angepasst werden. Sehr kleine Werte eignen
sich nur für Tests. Ein Timeout führt bei Query-Providern in den vorhandenen
Fallback; Speech antwortet mit HTTP 503 und WFS behält den zuletzt aktivierten
Datenstand.

## Zustandsdateien

`runtime/` enthält WFS-Pending-Releases, Sessions und bei aktivierter
Prototyp-Protokollierung `logs/interactions.jsonl`. Das Verzeichnis ist laut
`.gitignore` lokal. Neue aktive WFS-Stände liegen unveränderlich unter
`data/wfs/releases/`; `data/wfs/active_release.json` wählt genau einen davon.
`data/canonical/offers.json` und die bisherigen WFS-Dateien bleiben während der
Migration als Legacy-Fallback erhalten.

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

# aktive und ausstehende Release-IDs anzeigen
python -m app.wfs_sync --list

# einen Pending-Release ohne neuen Download prüfen
python -m app.wfs_sync --verify <release-id>

# exakt diesen geprüften Release aktivieren
python -m app.wfs_sync --promote <release-id>

# atomar auf einen früheren Release zurückwechseln
python -m app.wfs_sync --rollback <release-id>
```

Der erste Check übernimmt einen vorhandenen konsistenten Legacy-Stand
idempotent als `legacy-<hash>` und setzt dafür den ersten Pointer; dafür ist kein
WFS-Neuabruf erforderlich. Prüfe vor Promotion Manifest und `diff.json` des
ausstehenden Releases. Promotion lädt niemals erneut und verändert keine
Einzeldateien des bisherigen Releases. Ein fehlgeschlagener Pointerwechsel kann
einen vollständigen, aber inaktiven Releaseordner hinterlassen; derselbe Befehl
ist danach wiederholbar. Während einer Nutzeranfrage findet kein WFS-Zugriff
statt. Die lokale Sperre schützt nur einen Prozess; starte Wartungsbefehle nicht
parallel aus mehreren Prozessen.

## Übersetzungswartung

```powershell
python -m app.translate_offers --provider blablador --dry-run
python -m app.translate_offers --provider blablador
```

Mit `--provider copy` werden deutsche Inhalte kopiert; dies ist ein technischer
Fallback, keine fachlich geprüfte Übersetzung. Manuelle Korrekturen gehören in
`data/i18n/manual_overrides.json` und überschreiben maschinelle Werte.

## Wheel-Installation

Die kanonische Softwareversion steht in `pyproject.toml`; derzeit ist dies die
Prototypversion `0.1.0`. Wheel, API, `python -m app --version` und neue
Interaktionsdatensätze lesen dieselbe Version. Interaktionsschema 2 und
WFS-Manifestschema 1 sind davon unabhängige Datenverträge.

Ein Distributionsbuild erzeugt Wheel und Source Distribution:

```powershell
python -m build
python -m pip install -c requirements/constraints-py311.txt dist\lena_code3-0.1.0-py3-none-any.whl
python -m app --version
```

Das Wheel enthält Pythonmodule, das vollständige Frontend einschließlich der
Leaflet-Bilder und einen rein lesbaren Bootstrap-Stand aus kanonischen
Angeboten, Übersetzungen, Overrides sowie WFS-Rohdaten und letztem Bericht. Es
enthält keine Tests, Dokumentation, `.env*`, Sessions, Interaktionsprotokolle,
Pending-Releases, extern aktivierte Releases, Pointer, Logs oder Audiodaten. Das
Source-Archiv enthält zusätzlich Tests, Dokumentation, Beispielkonfiguration und
Constraints, damit daraus erneut ein Wheel gebaut werden kann.

Im Checkout liest LENA weiterhin aus `data/` und schreibt nach `runtime/`. Eine
normale Wheel-Installation liest den unveränderlichen Bootstrap aus dem Paket
und schreibt Daten beziehungsweise Runtime-Zustand in das betriebsspezifische
Benutzerverzeichnis (`%LOCALAPPDATA%\LENA` unter Windows beziehungsweise
`~/.local/share/lena` ohne `LOCALAPPDATA`). `LENA_DATA_DIR` und
`LENA_RUNTIME_DIR` setzen diese externen Wurzeln explizit. WFS-Promotionen
erzeugen Releases und den Active-Pointer nur dort; der Bootstrap wird niemals
überschrieben. Ein ungültiger externer Pointer oder ein fehlender Bootstrap
ergibt einen sichtbaren Knowledge-Base-Fehler und fällt nicht auf Pending-Daten
oder einen versteckten Netzwerkabruf zurück.

Die Constraints gelten für CPython 3.11 und enthalten noch keine
Artefakthashes. Der Build ist hinsichtlich Name, Version und Dateiinventar
reproduzierbar getestet; eine Bitidentität der Archive wird wegen möglicher
ZIP-/Tar-Zeitstempel nicht behauptet.

Der lokale Ordner `Code3-archive-pre-git-20260717` ist die reversible
Archivierung der unversionierten Vorläuferkopie. Arbeite ausschließlich in
`code/`. Das Archiv enthält lokale Konfigurations- und Laufzeitdateien und darf
nicht veröffentlicht oder als zweite Codebasis gepflegt werden.

## Prototyp-Protokollierung und Masterarbeitsbezug

LENA protokolliert im aktuellen Entwicklungs- und Forschungsprototyp vollständige
verarbeitete Anfragen gemeinsam mit den tatsächlich ausgegebenen Antworten
lokal. Antwortpfad, Sprache, Quellen sowie Safety- und Fallbackstatus ergänzen
das Paar. Diese bewusst einfache Umsetzung unterstützt technische
Nachvollziehbarkeit, Fehleranalyse, Evaluation und iterative Verbesserung; sie
benötigt weder Datenbank noch Cloudübertragung. Die Dateien sind wegen möglicher
personenbezogener und sensibler Inhalte kein Teil des versionierten Repositorys.

Diese Umsetzung ist kein fertiges Datenschutzkonzept und die Daten sind nicht
anonym. Vor einem produktiven Einsatz oder einer institutionell geregelten
Forschungsnutzung sind mindestens informierte Einwilligung, Zweckbindung,
Trennung von Forschungs- und Betriebsdaten, differenzierte Zugriffskontrolle,
definierte Aufbewahrungs- und Löschfristen, Pseudonymisierung beziehungsweise
Anonymisierung, kontrollierter Forschungsexport und die besondere Behandlung
von Kriseninhalten neu zu konzipieren. Zusätzlich sind die rechtlichen und
institutionellen Anforderungen zu prüfen; eine Freigabe wird hier nicht
behauptet.

## Deployment-Stand

Das Repository enthält weder Dockerfile noch Service-/Cloud-Konfiguration. Ein
Produktivbetrieb benötigt daher außerhalb dieses Codes mindestens einen
Prozessmanager, TLS, Zugriffsschutz, Logging-, Datenschutz-, Backup- und
Updatekonzept. Der vorhandene Startbefehl ist ein Entwicklungs-/Prototypbetrieb.
