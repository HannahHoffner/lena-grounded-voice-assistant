# LENA

LENA ist eine lokal betriebene, mehrsprachige Webanwendung zur Suche nach
Hilfsangeboten für wohnungslose Menschen in Leipzig. Ein statisches Browser-
Frontend spricht mit einem FastAPI-Backend. Antworten werden ausschließlich aus
lokal freigegebenen, getrennt geprüften Beständen für soziale Angebote,
öffentliche Toiletten und feste Trinkwasserbrunnen abgeleitet. Die normale
Bedarfsauswahl benötigt einen konfigurierten LLM-Interpreter. Nachgelagerte
LLM-Auswahl und Formulierung haben deterministische Rückfälle; das Modell ist
keine Wissensquelle. Ohne Interpreter startet die Anwendung, liefert bei
normalen Anfragen aber nur den technischen Hilfepfad.

Die Anwendung richtet sich an technisch betreuende Personen sowie an Fachkräfte,
die LENA installieren, Datenänderungen prüfen, Übersetzungen pflegen und die
fachlichen Leitplanken weiterentwickeln.

## Funktionsumfang

Vor einer manuellen Prüfung: [Evaluationsvoraussetzungen](docs/manual-evaluation-prerequisites.md).

- Textanfragen in Deutsch, Englisch, Polnisch, Rumänisch und Russisch
- deterministische, begründete Kandidatenbegrenzung mit Mandatory-/Selectable-Trennung
- kontrollierte optionale LLM-Auswahl nur innerhalb zulässiger Kandidaten sowie satz- und faktengebundene Formulierung
- Karten und Kartenansicht für Angebote mit verwertbaren Koordinaten
- lokale Sitzungsverläufe für kurze Folgefragen
- serverseitige Speech-to-Text- und Text-to-Speech-Schnittstellen
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

Öffne `http://127.0.0.1:8002`. Ohne konfigurierten Interpreter startet die
Anwendung. Freie Anfragen erhalten einen lokalisierten technischen Hinweis mit
bedingter 112-Angabe und, falls in der Wissensbasis vorhanden, die telefonische
Hilfebus-Kontaktkarte. Eine fachliche Suche oder Standortempfehlung findet dann
nicht statt; der mobile Hilfebus erhält dabei keinen Kartenmarker.

Der Server bindet standardmäßig nur lokal. Nicht lokale Hosts erfordern
zusätzlich `--allow-public`; dieses Flag ersetzt keine TLS-, Authentifizierungs-
oder Reverse-Proxy-Konfiguration. Query-, STT- und TTS-Eingaben besitzen
serverseitige, in `docs/configuration.md` beschriebene Grenzen.

Unter Linux oder macOS lautet die Aktivierung `source .venv/bin/activate`; das
Kopieren der Konfiguration erfolgt mit `cp .env.example .env`.

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
| `app/service.py` | Anfrageorchestrierung, Sicherheits- und Fallbackpfade |
| `app/safety.py`, `app/policy_facts.py` | versionierte Safety-Policy, enger Preflight, zentrale 112 und synthetischer Szenariovertrag |
| `app/interpreter.py` | versionierter Interpretervertrag, Prompt und minimale Alias-Hinweise |
| `app/candidate_contract.py`, `app/candidates.py` | strikter Auswahlvertrag und deterministische Kandidatenbegrenzung |
| `app/llm_selection.py` | kompakter Selectorvertrag, Prompt, Bypass, ID-Validierung und deterministischer Fallback |
| `app/formulation.py`, `app/grounding.py` | versioniertes Evidence-/Satzschema, Prompt sowie atomare Fakten-, Rollen-, Sprach- und Kartenprüfung |
| `app/llm_budget.py` | kumulatives monotones Zeitbudget der drei externen LLM-Stufen |
| `app/dialogue.py`, `app/dialogue_flow.py` | versionierter Dialogzustand, lokalisierte Rückfragen und begrenzte Auflösung |
| `app/retrieval.py` | isolierte lexikalische Hilfsfunktionen; kein Fallback bei Interpreterausfall |
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
| `app/speech.py` | serverseitige Transkription und Sprachsynthese |
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

# Tests ausführen
python -m pytest

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
jedoch den LLM-Interpreter. Ein Speech-Endpunkt ist nur für den serverseitigen
Sprachpfad erforderlich.
Der Anwendungsdefault für Sprachsynthese ist `edge-tts` und benötigt eine
Netzwerkverbindung. Die sichere `.env.example` und der Docker-Standard lassen
Sprachsynthese zunächst unkonfiguriert; Edge-TTS kann ausdrücklich aktiviert
werden. Leaflet wird lokal aus `app/static/vendor/` ausgeliefert; die
Kartenkacheln werden im Frontend von OpenStreetMap geladen.

Quelle: Stadt Leipzig, WFS Wohnungslosenhilfe,
[Datenlizenz Deutschland – Namensnennung – Version 2.0](https://www.govdata.de/dl-de/by-2-0).

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
- Die gespeicherten Fremdsprachen und dynamischen LLM-Antworten sind derzeit
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
- `runtime/logs/interactions.jsonl` enthält bei Standardkonfiguration grundsätzlich
  Anfrage-Antwort-Paare für Evaluation und Verbesserung. Safety-Eingaben werden
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
Zustand. Details und sichere Startbefehle stehen in
[Docker und Reproduzierbarkeit](docs/reproducibility.md). Eine Zenodo-DOI
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
