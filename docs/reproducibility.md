# Reproduzierbarkeit und Docker

## Umfang und Nachweisgrenzen

Der Docker-Build legt eine Linux-Umgebung fest. Er benötigt auf dem Host keine
Python-Installation. Windows und macOS verwenden Docker Desktop mit Linux-
Containern, Linux eine Docker Engine mit BuildKit. Auf ARM-Rechnern ist der
native ARM64-Build vorgesehen; AMD64 kann ausdrücklich mit `--platform
linux/amd64` gewählt werden. Emulation ist kein Leistungsbenchmark.

Die Docker-Ausführung ist noch **nicht verifiziert**: Im lokalen Prüfungsumfeld
vom 20.10.2026 fehlen Docker Engine und WSL. Ein vorhandener Dockerfile ist kein
Build-, Container-Test- oder Startnachweis. Vor einer Freigabe müssen die unten
genannten Befehle tatsächlich erfolgreich ausgeführt und protokolliert werden.

## Fixierte Umgebung

| Bestandteil | Festlegung |
|---|---|
| Betriebssystem | Ubuntu 24.04 LTS, offizielles Image `docker.io/library/ubuntu` |
| OCI-Index-Digest | `sha256:68ee22004a9109b44973313b02ff7b1de250f1de0f5ecb628d73f579aaff33ac` |
| Ubuntu-Paketarchiv | `https://snapshot.ubuntu.com/ubuntu/20261001T000000Z/` |
| Python | CPython 3.12.3, Ubuntu-Paket `3.12.3-1ubuntu0.17` mit Ubuntu-Sicherheitskorrekturen |
| Python-Runtime | 28 direkt/transitiv fixierte Pakete in `requirements/runtime-py312.lock` |
| Build und Tests | eigener Hashlock `requirements/build-py312.lock` |
| Isolierte Paketbuilds | `requirements/constraints-py312.txt` und ausschließlich die verifizierte lokale Wheelablage |

Der Index wurde direkt über die Docker-Registry-API abgerufen und sein SHA-256
gegen den vom Server gemeldeten Digest verifiziert. Er bindet auch die
plattformabhängigen Manifeste. Python-Paketversionen wurden gegen die
Paketmetadaten des genannten Ubuntu-Snapshots geprüft. Die Python-Hashes stammen
aus den PyPI-Release-Metadaten; passende Linux-Wheels für CPython 3.12 auf AMD64
und ARM64 wurden heruntergeladen und hashgeprüft. Das ersetzt keinen
Installationstest oder Containerlauf.

Das festgelegte Archiv wird mit Ubuntus signierten Paketmetadaten verwendet.
Systemabhängigkeiten werden aus diesem zeitlich festen Paketbestand aufgelöst;
sie werden nicht aus einem veränderlichen aktuellen Ubuntu-Mirror bezogen.
Die Snapshot- und Registry-Dienste müssen für einen Neubau weiterhin erreichbar
sein. Für langfristige Unabhängigkeit zusätzlich das tatsächlich geprüfte
Runtime-Image mit `docker image save` außerhalb von Git archivieren und dessen
reale Prüfsumme dokumentieren. Es wird keine Bitidentität unabhängiger Builds
behauptet: Zeitstempel und Buildwerkzeuge können Artefaktbytes beeinflussen.

## Build und vollständige Prüfung

Alle Befehle aus der Repositorywurzel; dieselben einzeiligen Befehle gelten in
PowerShell, Bash und Zsh. Build und initialer Paketdownload benötigen Internet,
aber keine Providerzugänge. Es werden keine lokalen `.env`-Dateien eingelesen.

```text
docker build --target test -t lena-check .
docker run --rm --network none lena-check
docker build --target runtime -t lena:0.2.0 .
```

Der Testcontainer führt die vollständige Pytest-Suite einschließlich Wheel- und
sdist-Bau, sdist-Rebuild und frischer Installation aus. Danach folgen
`compileall`, `pip check`, Frontendtests und JavaScript-Syntaxprüfungen. Auch
isolierte Build-/Installationssubprozesse verwenden nur die zuvor hashgeprüften
Wheels. Der Containerlauf mit `--network none` verhindert externe Transporte
zusätzlich zur Testsperre in `tests/conftest.py`.

Der Mehrstufenbau trennt Tests, Node.js, Buildwerkzeuge, Paketcache und Quellen
vom Runtime-Image. Die Runtime enthält Python, Zertifikate, installierte
Anwendungsabhängigkeiten und das gebaute Wheel mit Bootstrapdaten. Kein Compiler,
kein Node.js, keine Tests, Zugangsdaten oder lokalen Forschungsprotokolle werden
übernommen. `.dockerignore` beschränkt bereits den Buildkontext.

## Sicherer Start und Neustart

```text
docker run -d --name lena-smoke --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m lena:0.2.0
docker exec lena-smoke /opt/lena/bin/python -c "import json,urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8002/api/health'); h=json.load(r); assert h['kb_loaded']; print(h['offer_count'])"
docker inspect --format "{{.State.Health.Status}}" lena-smoke
docker rm -f lena-smoke
```

Für den Neustart die vier Befehle mit demselben Namen erneut ausführen. Jeder
neue Container erhält eine leere temporäre Daten-/Runtimewurzel; das Wheel
liefert denselben Bootstrap. Der Healthstatus kann unmittelbar nach dem Start
noch `starting` sein. Erst `healthy` bestätigt den periodischen Check. Der
Prüfpfad verlangt HTTP 200 und eine geladene Wissensbasis; er prüft keinen
Modellprovider. Bei Bedarf `docker logs lena-smoke` vor dem Entfernen prüfen.

Für eine lokale Browseransicht ohne konfigurierte Provider:

```text
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -p 127.0.0.1:8002:8002 lena:0.2.0
```

Aufruf: `http://127.0.0.1:8002`. Der Entrypoint ist `python -m app`, intern auf
Port 8002 und `0.0.0.0` mit der erforderlichen ausdrücklichen Bindefreigabe.
Die Host-Portfreigabe bleibt auf Loopback beschränkt. Der Prozess läuft als
UID/GID 10001. Ein einzelner Container genügt; eine zusätzliche Compose-Datei
würde hier keine notwendigen Dienste oder Volumes koordinieren.

## Konfiguration und Daten

Der Standard aktiviert weder automatische Quellabrufe noch Interaktionslogging
oder Edge-TTS. Der kompatible TTS-Provider besitzt keine Zugangsdaten und ist
damit nicht einsatzbereit. Ohne LLM-Interpreter liefert eine normale Anfrage
den dokumentierten technischen Hilfepfad; Docker ersetzt keinen Provider.

`LENA_ENV_FILE_MODE=disabled` verhindert das Einlesen lokaler Konfigurationsdateien.
Bewusste Providerkonfiguration kann über Docker-Umgebungsvariablen beziehungsweise
eine außerhalb des Repositorys gespeicherte `--env-file` erfolgen; die Namen
stehen in [configuration.md](configuration.md). Dies ist ein gesonderter,
netzwerkfähiger Betriebsmodus und kein Teil der providerfreien Verifikation.
Die mitgelieferte `.env.example` deaktiviert Quellsynchronisation und vollständige
Interaktionslogs ebenfalls; die Anwendungsdefaults bleiben aus Kompatibilitäts-
gründen dokumentiert. Edge-TTS muss bei Bedarf ausdrücklich aktiviert werden.

Standardmäßig ist kein persistentes Volume nötig. Sessions und abgeleiteter
Zustand sind temporär; Logs sind deaktiviert. Nur für bewusst persistente
Wartungs-/Evaluationsstände externe, zugriffsgeschützte Verzeichnisse über
`LENA_DATA_DIR` und `LENA_RUNTIME_DIR` einbinden und deren UID-/GID-Zugriff
sicherstellen. Diese Daten gehören nicht automatisch ins Softwarearchiv.

## Grenzen der Reproduktion

1. **Build und Laufzeit:** Basisimage, Paketarchiv und Hashlocks identifizieren
   die Umgebung; erfolgreiche Containerprüfungen sind zusätzlich nachzuweisen.
2. **Anwendungsdaten:** Das Wheel enthält freigegebene, manifestgebundene
   Snapshots und Kurations-/Übersetzungsstände. Deren Provenienz und fachlich
   relevante Hashes bleiben erhalten. Checkout-Wartungsdaten sind separat.
3. **Veränderliche Quellen:** WFS, CSV, KML und Betreiberseiten können später
   abweichen. Ein erneuter Abruf reproduziert keinen früheren Datenstand.
4. **Externe Modelle und Dienste:** Aliaszuordnungen, Dienstversionen und
   Verfügbarkeit können wechseln. LLM-Antworten können bei gleicher Eingabe
   variieren; STT/TTS und Kartenkacheln sind ebenfalls externe Voraussetzungen.

Docker belegt keine deterministische Wiederholung externer Modellantworten und
ändert keine früheren Evaluationsbefunde. Der archivierte Softwarestand wird
über die Versions-DOI referenziert; technische Kennungen dienen ergänzend der
Verifikation. Siehe [Release und Archivierung](release.md).

## Aktualisierung

Bei Dependencyänderungen zuerst die bestehende Auflösung prüfen. Neue Versionen
und SHA-256-Wheelhashes aus den offiziellen PyPI-Release-Metadaten übernehmen,
direkte und transitive Abhängigkeiten für Python 3.12/Linux vollständig auflösen,
beide Locks und die Constraints gemeinsam aktualisieren. Hashprüfung mit
`pip download --require-hashes --only-binary=:all:` und Installation auf beiden
Zielarchitekturen prüfen. Danach alle obigen Build-/Testbefehle ausführen.
Nur `pip freeze` oder ein ungeprüfter Hash aus einer beliebigen Downloadquelle
genügt nicht. Die frühere Python-3.11-Constraintsdatei bleibt für den bestehenden
CI-/Entwicklungsweg erhalten und ist kein Hashlock des Containers.
