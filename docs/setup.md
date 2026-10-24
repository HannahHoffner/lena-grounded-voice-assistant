# Installation und Betrieb

Für Windows, Linux und macOS steht zusätzlich der vorbereitete
[Docker-Build](reproducibility.md) mit festgelegter Ubuntu-/Python-Umgebung zur
Verfügung. Build, Tests und Runtime wurden auf Linux/AMD64 unter Docker Desktop
geprüft. Die folgenden Abschnitte beschreiben die direkte Python-Installation.

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

Setze `REWRITE_PROVIDER=template`, `WFS_AUTO_SYNC=false`,
`TOILET_AUTO_SYNC=false` und `DRINKING_FOUNTAIN_AUTO_SYNC=false`, wenn der
Start keine Modell- oder Quellenanfrage auslösen soll. Für isolierte Prüfungen
verhindert `LENA_ENV_FILE_MODE=disabled`, dass `.env.local` Prozesswerte wieder
überschreibt; `LENA_RUNTIME_DIR` sollte auf ein temporäres Verzeichnis zeigen.
Das Frontend bleibt nutzbar;
freie Anfragen werden ohne Interpreter jedoch bewusst nicht fachlich
klassifiziert. Sie erhalten einen technischen Hinweis mit bedingter 112-Angabe
und gegebenenfalls die lokal belegte Hilfebus-Kontaktkarte, ohne Kartenmarker
oder fachliche Suchresultate. Speech und Kartenkacheln benötigen weiterhin
Netzwerk und sind kein Teil einer providerfreien Prüfung.

Für langsame oder kontrolliert blockierte Provider können die Timeoutwerte aus
[Konfiguration](configuration.md) angepasst werden. Sehr kleine Werte eignen
sich nur für Tests. Ein Timeout führt bei Query-Providern in den vorhandenen
Fallback; Speech antwortet mit HTTP 503 und WFS behält den zuletzt aktivierten
Datenstand.

## Spracheingabe in Firefox

Ohne Browser-Spracherkennung verwendet LENA `MediaRecorder` und den
konfigurierten STT-Server. Auf `http://127.0.0.1:8002/` bzw. `localhost`:
Mikrofonzugriff erlauben, Mikrofon einmal zum Starten und erneut zum Beenden
anklicken. Erst danach wird die Aufnahme transkribiert. Das erkannte Ergebnis
erscheint im Eingabefeld und kann geprüft und gesendet werden.

„Die Spracherkennung ist gerade nicht erreichbar“ bezeichnet einen technischen
Dienst-/Netzwerkfehler; es ist kein Urteil über die Aussprache. „Nicht verstanden“
bezeichnet leeres oder nicht verwertbares Audio. Die Verfügbarkeitsanzeige der
Speech-Konfiguration prüft die Einstellungen, nicht die Erreichbarkeit des
Servers. Ein funktionierendes Mikrofon und erfolgreiches TTS beweisen deshalb
keine funktionierende STT-Verbindung. Ogg/Opus und WebM/Opus werden serverseitig
zu WAV normalisiert. Allgemeine HTTP-LAN-Adressen benötigen für Mikrofonzugriff
einen sicheren Kontext, typischerweise HTTPS; siehe
[MDN: getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

Technische Fehler erscheinen im Serverlog mit einem redigierten Fehlercode und,
falls vorhanden, dem HTTP-Status des STT-Servers. Audioinhalte, Zugangsdaten und
Antworttexte des Providers werden dabei nicht protokolliert.

## Zustandsdateien

`runtime/` enthält WFS-Pending-Releases, Sessions und bei aktivierter
Prototyp-Protokollierung `logs/interactions.jsonl`. Das Verzeichnis ist laut
`.gitignore` lokal. Neue aktive WFS-Stände liegen unveränderlich unter
`data/wfs/releases/`; `data/wfs/active_release.json` wählt genau einen davon.
`data/canonical/offers.json` und die bisherigen WFS-Dateien bleiben während der
Migration als Wartungsquellen erhalten, nicht als ungefilterter Runtime-Fallback.

Öffentliche Toiletten verwenden einen getrennten Releasepfad. Lokal aktivierte
Stände liegen unter `data/toilets/releases/`, ausstehende Abrufe unter
`runtime/toilets/pending/`. Ohne lokalen Stand verwendet die Anwendung den
manifest- und hashgeprüften Paket-Bootstrap. Ein Abruf aktiviert nie automatisch
einen neuen Stand.

Feste Trinkwasserbrunnen verwenden entsprechend
`data/drinking_fountains/releases/` und
`runtime/drinking_fountains/pending/`. Active-, Last-Verified- und
Previous-Verified-Pointer sind die einzigen lokalen Allowlist-Einstiege. Der
Paket-Bootstrap ist der letzte sichere Fallback; mobile und außerhalb Leipzigs
liegende Quellpunkte bleiben darin nachvollziehbar, sind aber nicht runtimefähig.

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

## Toilettenbetrieb

```powershell
# amtliche CSV abrufen, validieren und eine Änderung nur als Pending bereitstellen
python -m app.toilet_sync fetch

# aktuellen Quellenstand read-only vergleichen oder lokalen Status anzeigen
python -m app.toilet_sync diff
python -m app.toilet_sync status

# einen Release prüfen, ausdrücklich aktivieren oder zurückrollen
python -m app.toilet_sync validate <release-id> --pending
python -m app.toilet_sync promote <release-id>
python -m app.toilet_sync rollback <release-id>
```

`fetch` verändert den aktiven Pointer nicht. Vor `promote` müssen Manifest,
Dateihashes, normalisierte Datensätze und Diff geprüft werden. Eine laufende
Anwendung übernimmt einen ausdrücklich aktivierten Stand erst nach einem
Neustart; Sessions werden dabei über den zusammengesetzten
Wissensbasisfingerabdruck vom alten Datenstand getrennt.

## Trinkbrunnenbetrieb

```powershell
# KML und amtliche Grenzquelle abrufen, validieren und nur bereitstellen
python -m app.drinking_fountain_sync fetch

# lokalen Status oder einen Live-Diff ohne Aktivierung anzeigen
python -m app.drinking_fountain_sync status
python -m app.drinking_fountain_sync diff

# Pending-Release lokal prüfen und genau diesen Stand aktivieren
python -m app.drinking_fountain_sync validate <release-id> --pending
python -m app.drinking_fountain_sync activate <release-id>
```

Prüfe vor `activate` insbesondere hinzugefügte, entfernte und verschobene
Punkte sowie die Zählungen für Leipzig, externe und mobile Standorte. Fetch und
Diff übertragen nur die öffentlichen Quellabrufe; sie initialisieren keinen
LLM-, STT- oder TTS-Provider. Eine laufende Anwendung übernimmt den neuen
Fingerprint nach Neustart. Die Quelle belegt keinen aktuellen Funktionsstatus;
ein technischer Abruf ersetzt keine fachliche Freigabe.

## Übersetzungswartung

```powershell
python -m app.translate_offers status
python -m app.translate_offers validate
python -m app.translate_offers generate --provider blablador --dry-run
python -m app.translate_offers generate --provider blablador
python -m app.translate_offers export-review --languages en,pl,ro,ru --output translation-review.json
python -m app.translate_offers import-review --input translation-review.json
```

Mit `--provider copy` werden deutsche Inhalte kopiert; dies ist ein technischer
Test-Double, keine Übersetzung oder Sprachprüfung. `generate` überschreibt keine
dokumentiert geprüfte Fassung und schreibt erst nach lokaler Integritätsprüfung
atomar. Der Dry-Run verändert weder Store noch Status oder temporäre
Repositorydateien. Reviewentscheidungen werden nur für unveränderte Versionen
mit Rolle, Zeitpunkt und Prüfumfang importiert. Eine Autorinnen-, fachliche,
muttersprachliche und professionelle Prüfung sind getrennte Rollen.

Ein providerfreies Szenario-Review wird so exportiert:

```powershell
python -m app.multilingual_review export --output multilingual-review.json
```

Der providerfreie Plan der kontrollierten Live-Provider-Evaluation kann ohne
Providerinitialisierung geprüft werden. Er liest nur freigegebene, nicht geheime
Konfigurationswerte einschließlich `.env`/`.env.local`. Sein fester Status
`prepared_not_executed` trifft keine Aussage über frühere dokumentierte Läufe:

```powershell
python -m app.multilingual_review live-dry-run --stage all
```

Ein späterer Live-Lauf verlangt zusätzlich zum Unterbefehl, `--confirm-live`
und `LENA_ALLOW_LIVE_SMOKE=true` eine einzelne freigegebene Stufe, die erwartete
Modellkennung und Providerdomain sowie sieben exakte harte Laufgrenzen. Stufen
starten einander nie automatisch. Befehle, Dateninventar, Abbruchkriterien und
Reportpfade stehen in [Kontrollierte Live-Provider-Evaluation](live-provider-evaluation.md).
Ohne gesonderte Freigabe darf kein dort dokumentierter Live-Befehl ausgeführt
werden. Pytest und CI führen ausschließlich providerfreie Prüfungen aus.

## Wheel-Installation

Die kanonische Softwareversion steht in `pyproject.toml`; derzeit ist dies die
Prototypversion `0.2.0`. Wheel, API, `python -m app --version` und neue
Interaktionsdatensätze lesen dieselbe Version. Interaktionsschema 11 und
WFS-Manifestschema 1 sind davon unabhängige Datenverträge.

Ein Distributionsbuild erzeugt Wheel und Source Distribution:

```powershell
python -m build
python -m pip install -c requirements/constraints-py311.txt dist\lena_code3-0.2.0-py3-none-any.whl
python -m app --version
```

Das Wheel enthält Pythonmodule, das vollständige Frontend einschließlich der
Leaflet-Bilder und einen rein lesbaren Bootstrap-Stand aus kanonischen
Angeboten, Übersetzungen, Anwendungs-/Reviewressourcen sowie WFS-Rohdaten und letztem Bericht. Es
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
führt nur dann zu einem sichtbaren Knowledge-Base-Fehler, wenn auch der exakt
kataloggebundene verifizierte lokale Stand und der Paket-Bootstrap nicht nutzbar
sind. Ein erfolgreicher gebundener Fallback meldet `degraded` und den
Quellenfehler in Health. Pending-Daten und versteckte Netzwerkabrufe sind keine
Fallbacks.

Die Constraints gelten für CPython 3.11 und enthalten noch keine
Artefakthashes. Der Build ist hinsichtlich Name, Version und Dateiinventar
reproduzierbar getestet; eine Bitidentität der Archive wird wegen möglicher
ZIP-/Tar-Zeitstempel nicht behauptet.

Der lokale Ordner `Code3-archive-pre-git-20260717` ist die reversible
Archivierung der unversionierten Vorläuferkopie. Arbeite ausschließlich in
`code/`. Das Archiv enthält lokale Konfigurations- und Laufzeitdateien und darf
nicht veröffentlicht oder als zweite Codebasis gepflegt werden.

## Prototyp-Protokollierung und Masterarbeitsbezug

LENA protokolliert im aktuellen Entwicklungs- und Forschungsprototyp grundsätzlich
verarbeitete Anfragen gemeinsam mit den tatsächlich ausgegebenen Antworten
lokal. Safety-Eingaben werden durch einen festen Redaktionstoken ersetzt;
Gefahrenbeschreibung, Diagnose, Risikoscore und Modellbegründung werden nicht
persistiert. Antwortpfad, Sprache, Quellen sowie minimale Safety- und Fallbackstatus ergänzen
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

Das Repository enthält ein geprüftes `Dockerfile` (Test- und Runtime-Ziel,
siehe README und [Docker und Reproduzierbarkeit](reproducibility.md)), aber
keine Service-/Cloud- oder Compose-Konfiguration. Ein Produktivbetrieb benötigt
außerhalb dieses Codes mindestens einen Prozessmanager, TLS, Zugriffsschutz,
Logging-, Datenschutz-, Backup- und Updatekonzept. Container und Startbefehl
sind ein lokaler Forschungs-/Prototypbetrieb mit genau einem Prozess.
