# Repository-Cleanup-Bericht

## Ergebnis

Das kanonische LENA-Repository wurde konservativ um nachweislich generierte,
obsolete und historisch bereits aufgegebene lokale Restartefakte bereinigt. Es
wurde keine versionierte Anwendungscode-, Test-, Frontend-, Konfigurations- oder
fachliche Datendatei gelöscht. Die vollständige Testsuite, Distribution, echte
Serverpfade und eine Installation aus dem Wheel funktionieren nach der
Bereinigung wie zuvor.

## Repository und Git-Sicherheit

| Merkmal | Ergebnis |
|---|---|
| Repository | `C:/Users/User/OneDrive/Dokumente/MA Projekt/code` |
| Arbeitsbranch | `maintenance/repository-cleanup` |
| Ausgangsbranch/-commit | `modernization/packaging-versioning`, `cadec30` |
| Sicherungscommit | `de6ff13` |
| Remote | `origin` → `HannahHoffner/lena-grounded-voice-assistant` |
| Privatstatus | GitHub bestätigte `visibility=PRIVATE` und `isPrivate=true` |
| Upstream-Ausgangszustand | Ausgangsbranch synchron, `+0/-0` |
| Offene Git-Operationen | keine Merge-, Rebase-, Cherry-pick-, Revert- oder Bisect-Operation |
| Push/History-Rewrite | nicht durchgeführt |

Der ursprünglich unversionierte aktive WFS-Pointer und der dazugehörige Release
wurden vor der Bereinigung als funktionsfähiger Ausgangszustand in `de6ff13`
gesichert. Dadurch ist der komplette aktive Datenstand wiederherstellbar.

## Baseline vor der Bereinigung

| Prüfung | Ergebnis |
|---|---|
| `python --version` | Python 3.14.3 |
| `python -m pytest` | 158 bestanden, 0 übersprungen, 0 fehlgeschlagen; 38,25 s |
| `python -m compileall -q app` | erfolgreich |
| `python -m build` | Wheel und sdist erfolgreich |
| `python -m app --version` | `0.1.0` |
| echter Uvicorn-Start | erfolgreich auf `127.0.0.1:8765` mit isolierter Runtime |
| Health/Frontend/Asset | jeweils HTTP 200; 30 Angebote; aktiver Release `legacy-3b72f95a88f9` |
| E2E-Query | Status `ok`, Templateprovider, 4 Karten und 4 Kartenziele |
| Folgefrage | gleiche Session, 2 History-Turns |
| Runtime-Erzeugung | eine Sessiondatei und eine JSONL-Datei mit 2 Interaktionen |
| WFS-Verify/List | aktiver Release und valider Pending-Release verifiziert |
| Clean-Install | durch `tests/test_packaging.py` außerhalb des Checkouts erfolgreich geprüft |

Der vorhandene Paketierungstest baut Wheel und sdist, baut erneut aus dem sdist,
installiert das Wheel in eine frische Umgebung und startet die installierte App
aus einem fremden Arbeitsverzeichnis. Damit beruht die Baseline nicht auf
unversionierten Restdateien des Checkouts.

## Entfernte Dateien und Verzeichnisse

### Generierte Caches und Buildausgaben

- `.pytest_cache/`
- `app/__pycache__/`
- `app/providers/__pycache__/`
- `tests/__pycache__/`
- `build/`
- `dist/`

Diese Inhalte sind vollständig aus Quellcode und Buildkonfiguration
reproduzierbar, werden bereits von `.gitignore` ausgeschlossen und sind weder
Teil der Laufzeitquelle noch des kanonischen Distributionsbestands. Nach den
abschließenden Tests und Builds wurden die dabei erneut erzeugten Exemplare ein
zweites Mal entfernt.

### Alte Test- und Modernisierungsoutputs

| Pfad | Umfang/Alter | Löschbegründung |
|---|---|---|
| `runtime/wheel-smoke/` | 2.189 Dateien, 36.760.220 Bytes, Stand 17.07.2026 | alte vollständige lokale venv; null Referenzen; aktuelle Packagingtests erzeugen eigene Temp-Umgebungen; durch frische Wheel-Installation ersetzt |
| `runtime/dependency-report.json` | 525.970 Bytes, Stand 17.07.2026 | reproduzierbares pip-Abhängigkeitsinventar; null Referenzen; Constraints und Paketmetadaten sind kanonisch |
| `runtime/pr-body.md` | 1.715 Bytes, Stand 17.07.2026 | Text des bereits gemergten GitHub-PR #1; null Repositoryreferenzen |

### Leere historische Altordner

- `scripts/`
- `app/scraper/`
- `data/evals/`
- `data/maintenance/`
- `data/prompts/`
- `data/scraper_sources/`
- `data/published/index/`
- `data/published/pages/`
- der danach ebenfalls leere Elternordner `data/published/`

Unmittelbar vor der Entfernung war jeder Ordner vollständig leer. Es existieren
keine aktuellen Code-, Test-, Dokumentations-, Packaging- oder dynamischen
Pfadreferenzen. Die Git-Historie liefert einen unabhängigen zweiten Beleg:
Commit `43b88bc` entfernte die früheren Scraper-, Prompt-, Evaluations-, Skript-
und Publishinginhalte bewusst aus der überprüften Code3-Baseline. Git konnte nur
die anschließend lokal verbleibenden leeren Verzeichnisse nicht abbilden.

## Bewusst nicht gelöschte Kandidaten

| Pfad/Komponente | Entscheidung |
|---|---|
| sämtliche Pythonmodule unter `app/` | erhalten; alle statisch, über CLI, Runtime oder Tests angebunden; kein Teil bestand die doppelte Nichtverwendungsprüfung |
| `lena_code3.egg-info/` | erhalten; eine isolierte Entfernung änderte die CLI-Version auf `0+unknown` und ließ 1 von 7 Packagingtests scheitern; sofort über den vorgesehenen Editable-Installationsweg wiederhergestellt |
| `runtime/sessions.json` | erhalten; Stand 29.07.2026, möglicherweise reale oder wissenschaftliche Evidenz |
| `runtime/logs/interactions.jsonl` | erhalten; laut Projektdokumentation ausdrücklich für Evaluation/Masterarbeit vorgesehen |
| `runtime/wfs/state.json` | erhalten; aktueller Laufzeit-/Syncstatus |
| `runtime/wfs/pending/20260729T055851Z-3b72f95a88f9-02ade2e6/` | erhalten; gültiger Pending-Release mit demselben fachlichen Inhaltshash wie der aktive Stand, aber ungeklärter operativer/Evidenzstatus |
| `data/wfs/active_release.json` und `data/wfs/releases/legacy-3b72f95a88f9/` | erhalten und versioniert; aktiver Datenstand |
| Bootstrap-, kanonische, WFS-, Übersetzungs- und Override-Daten | erhalten; Wissensbasis, Karten, Installation und Reproduzierbarkeit |
| Frontend und alle Leaflet-Assets | erhalten; HTML-/CSS-/JS-Referenzen und Wheel-Inventartests |
| `.env`, `.env.local` | erhalten und ignoriert; lokale Konfiguration/Secrets |

Die fehlschlagende isolierte `egg-info`-Entfernung wurde nicht verschwiegen: Sie
war die verlangte zweite Sicherheitsprüfung und verhinderte eine funktional
falsche Bereinigung. Nach der Wiederherstellung bestanden alle 7 Packagingtests.

## `.gitignore`

`.gitignore` wurde nicht geändert. Die bestehenden Regeln decken Caches,
Buildausgaben, Wheel-/Egg-Metadaten, Runtime, Sessions, Logs, Testreports und
lokale Secretkonfiguration bereits ab. Eine zusätzliche Regel hätte keinen
Nutzen gebracht und könnte fachlich relevante Daten unbeabsichtigt verbergen.

## Vorher-/Nachher-Vergleich

| Prüfung | Vorher | Nachher |
|---|---|---|
| vollständige Suite | 158 bestanden, 0 übersprungen, 0 fehlgeschlagen | 158 bestanden, 0 übersprungen, 0 fehlgeschlagen |
| Laufzeit | 38,25 s | 33,75 s |
| Compile | erfolgreich | erfolgreich |
| Wheel/sdist | erfolgreich | erfolgreich |
| CLI-Version | 0.1.0 | 0.1.0 |
| aktiver Checkout-WFS | `legacy-3b72f95a88f9`, 30 Angebote | unverändert |
| Pending-WFS | gültig | unverändert gültig |
| Backend/Health/UI/Asset | erfolgreich | erfolgreich |
| Query/Karten/Folgefrage | erfolgreich | erfolgreich |
| Clean-Wheel-Installation | automatisiert erfolgreich | automatisiert und manuell aus fremdem Arbeitsverzeichnis erfolgreich |

Zusätzlich bestanden nachher 39 von 39 fokussierten Tests für atomare
Sessionwrites, Parallelzugriffe, TTL, Kapazitätslimit, Quarantäne, API-
Fehlertoleranz, Interaktionslogging und WFS-Releases.

## Nachher-Start und End-to-End-Smoke

Der echte Nachher-Server lief auf `127.0.0.1:8766` mit einer leeren, isolierten
Runtime und deaktiviertem WFS-Autosync. Geprüft wurden:

- `GET /api/health`, `/` und `/static/app.js`: HTTP 200;
- aktive KB: 30 Angebote aus `legacy-3b72f95a88f9`;
- normale Essensanfrage: `ok`, Template, 4 Karten, 4 Kartenziele;
- Folgefrage: dieselbe Session und 2 History-Turns;
- fachfremde Frage: kontrollierter `no_results`-Pfad;
- überlange Query: HTTP 422;
- frische Runtime: `sessions.json` und `logs/interactions.jsonl` automatisch
  angelegt, 2 Sessions und 3 vollständige Interaktionen geschrieben.

Die höhere Nachher-Anzahl gegenüber der Baseline ist beabsichtigt: Der
Nachher-Smoke prüfte zusätzlich den fachfremden Fallback. TTL-, Limit- und
Quarantänelogik wurden nicht an realen Forschungsdateien provoziert, sondern in
den vollständig bestandenen isolierten Persistenztests geprüft.

LLM-, STT- und TTS-Provider wurden über ihre vorhandenen kontrollierten Testpfade
einschließlich Timeout-, Fehler-, Safety- und Fallbackverhalten geprüft. Es wurden
keine echten externen Speech- oder LLM-Aufrufe benötigt.

## Saubere Installation

Das finale Wheel wurde in ein neues temporäres venv installiert. Der korrigierte
manuelle Nachweis lief aus dessen fremdem Arbeitsverzeichnis und bestätigte:

- `app.__file__` liegt tatsächlich unter dem neuen `site-packages`;
- Version 0.1.0, Bootstrap-KB, Health, Frontend und `app.js` funktionieren;
- Query liefert 4 Karten und 4 Kartenziele;
- Session und Interaktionslog entstehen in der externen Runtime;
- unter dem installierten Paket entsteht kein `runtime/`-Ordner;
- bei `WFS_AUTO_SYNC=false` bleibt der rein lesbare Bootstrap aktiv und es wird
  erwartungsgemäß kein externer Active-Pointer vorausgesetzt.

Die temporären manuellen Smoke- und Installationsumgebungen wurden anschließend
vollständig entfernt.

## Warnungen und Restrisiken

1. Lokal ist nur Python 3.14.3 installiert. Die Vorher-/Nachher-Suite lief daher
   auf 3.14. Der vorhandene GitHub-Workflow und die Constraints zielen auf
   Python 3.11; ohne Push wurde kein neuer Remote-CI-Lauf erzeugt.
2. Die festgeschriebene saubere Installationsumgebung meldet eine vorhandene
   `StarletteDeprecationWarning` zur späteren Migration von `httpx` auf
   `httpx2`. Sie war bereits im Baseline-Clean-Install sichtbar und wurde nicht
   durch die Bereinigung verursacht.
3. Die Editable-Neuinstallation meldete außerdem lokale pip-Hinweise zu nicht im
   `PATH` liegenden Scripts und einem nicht vollständig entfernbaren temporären
   `~ydantic_core`-Verzeichnis außerhalb des Repositorys. Die Anwendungstests
   und Paketierung blieben erfolgreich.
4. Der gültige Pending-WFS-Release bleibt bis zu einer fachlichen Entscheidung
   bestehen. Es wurde weder promotet noch gelöscht.
5. Für reale Sessions und Interaktionslogs bleibt eine explizite
   Aufbewahrungs-/Löschentscheidung für die Masterarbeit offen. Gemäß
   Entscheidungsregel wurden sie erhalten.

## Commits

| Commit | Zweck |
|---|---|
| `de6ff13` | `chore: snapshot repository before cleanup` |
| `ce0b44e` | `docs: add repository cleanup plan` |
| `e04b08f` | `chore: record verified repository cleanup` |

Der Commit, der diesen Bericht hinzufügt, folgt als separater
Dokumentationscommit und wird im abschließenden Benutzerbericht mit seinem
Kurz-Hash genannt.

## Finaler Status

Vor Erstellung dieses Berichts war der Arbeitsbaum sauber. Alle sicheren lokalen
Gruppe-A-Artefakte waren entfernt; alle geschützten Gruppe-B/C-Pfade waren
vorhanden. Nach Commit dieses Berichts wird `git status --short --branch` erneut
geprüft. Es erfolgt kein Push.
