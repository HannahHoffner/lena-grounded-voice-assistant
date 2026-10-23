# Unabhängiger technischer und wissenschaftlicher Audit: LENA

Stand: 23.10.2026. Gegenstand: Forschungsprototyp, keine produktive Beratungssoftware. Es wurden keine Implementierungen, Konfigurationen, Daten oder Thesis-Dateien geändert. Die vier Audit-Dateien sind die einzigen beabsichtigten Repositoryänderungen.

## Executive Summary

**Gesamtampel: GELB – bedingt reproduzierbar.** Der lokale Softwarestart, der Docker-Build und die automatisierten Tests sind tatsächlich reproduziert. Eine reguläre Textsuche wurde auch mit einem vorhandenen Blablador-Zugang erfolgreich ausgeführt. Vollständiger Offlinebetrieb, beliebige Plattformen, verlässliche Sprachausgabe mit der Beispielkonfiguration und deterministisch gleiche externe Modellantworten sind damit nicht nachgewiesen. Die freie Antwortvalidierung bietet keine vollständige semantische Faktenkontrolle.

| Frage | Belastbare Antwort |
|---|---|
| 1. Auf einem fremden Rechner lokal ausführbar? | **Ja, unter Bedingungen.** Ein sauberer Git-Export wurde ohne lokale Konfiguration gebaut und unter Linux/AMD64 im Container getestet. Wheel-Neuinstallation außerhalb des Checkout gehört zur bestandenen Suite. Für normale Freitextsuche wird ein erreichbarer, geeigneter LLM-Dienst benötigt; ohne ihn funktioniert nur der eingeschränkte technische Hilfepfad. |
| 2. Konkrete Voraussetzungen? | Für den belegten Weg: Docker mit Linux/AMD64-Containern, Browser, freier lokaler Port, Build-Netzwerk und anschließend Netzwerk zum LLM-Dienst. Python, Bibliotheken, Frontend und die drei Bootstrap-Datenbestände sind im Image. Für Sprache zusätzlich Browser-/Mikrofonfähigkeiten und erreichbare STT-/TTS-Dienste. Details und Konfigurationsnamen: [Matrix](REPRODUCIBILITY_MATRIX.md). |
| 3. Reicht Blablador? | Für die geprüfte **Textsuche ja**, neben der Softwareumgebung und den enthaltenen Daten. Für den vollständigen Funktionsumfang **nein**: Kartenkacheln kommen von OpenStreetMap; Browser-STT kann einen weiteren Dienst verwenden; Edge-TTS ist ein separater externer Dienst. Der automatisch geerbte Blablador-TTS-Endpunkt mit `gpt-4o-mini-tts` lieferte HTTP 404. |
| 4. Docker/Compose nutzbar? | **Docker ja.** Clean-Room-Build, netzwerklose Tests, Healthcheck, schreibgeschützte Runtime, leerer Zustand, Portfreigabe und eine echte Provideranfrage wurden geprüft. **Keine Compose-Datei vorhanden.** Für diesen Einzelprozess ist Compose keine technische Voraussetzung. |
| 5. Saubere Docker-Paketierung möglich? | **Sie ist im Wesentlichen bereits vorhanden.** Ergänzungsbedarf betrifft eindeutige Betriebsprofile, Speech-Konfiguration, konsistente Dokumentation und die Weitergaberechte der enthaltenen Daten, nicht einen neuen Docker-Grundaufbau. |
| 6. Architektur vertretbar? | **Als begrenzter Forschungsprototyp grundsätzlich ja.** Gute Trennung von Datenfreigabe, Kandidatenbegrenzung, Providerverträgen und Darstellung. Strukturelle Schwächen liegen bei semantischer Antwortabsicherung, der zentralen Anfrageorchestrierung und den Persistenz-/Betriebsverträgen. Kein Anlass für eine komplette Neuentwicklung; bloße zusätzliche Schlüsselwortregeln reichen für die Grounding-Grenze aber nicht. |
| 7. Codequalität? | **Solide Engineeringbasis mit wesentlichen Einschränkungen.** Umfangreiche ausführbare Tests und brauchbare Paketierung; zugleich sehr große Entscheidungsfunktionen, uneinheitliche Defaults, unvollständige Ausgabe strukturierter Logs und dokumentierte Altpfade. Keine nachgewiesene unbenutzte direkte Fremdbibliothek. |
| 8. Stimmen alle relevanten Thesis-Beschreibungen? | **Nein, nicht uneingeschränkt.** Die aktuelle Thesis beschreibt den finalen Aufbau und die negativen Evaluationsergebnisse überwiegend bemerkenswert genau. Einzelne Anforderungsstatus sind stärker als der Nachweis; praktische Konfigurations- und Auslieferungsdetails fehlen. Vollständige Zuordnung: [Traceability](THESIS_CODE_TRACEABILITY.md). |
| 9. Falsche/zu starke/veraltete Aussagen? | Vor allem eine als erreicht lesbare Garantie „keine erfundenen Fakten“ (R-21), uneinheitliche Lizenzzuordnung, noch offene manuelle Ergebnisse und die fehlende Trennung von dokumentiertem Messprofil und auslieferbarem Defaultprofil. Die Repositorydokumentation enthält zusätzlich objektiv veraltete Docker- und Vertragsangaben. Die negativen Live-Gates werden in der Thesis dagegen **nicht** verschwiegen. |
| 10. Fehlende finale Eigenschaften / veröffentlichungsfähiger Zustand? | Ergänzen: reproduziertes Grounding-Gegenbeispiel, TTS-Vererbungsfehler, genaue Profilpriorität, Verlust strukturierter Logfelder und Grenzen persistierter Dialogreservierungen. **Aktuell keine uneingeschränkte Veröffentlichungsempfehlung für das vollständige Paket.** Ungeklärte Datenweitergabe, widersprüchliche Anleitungen und noch nicht versionierte Thesis-Primärbelege müssen vor einem belastbaren Release bearbeitet werden. |

Eine Veröffentlichung als ausdrücklich begrenztes Forschungsartefakt ist ein realistischer nächster Schritt. Eine abgeschlossene Feldvalidierung, Enterprise-Infrastruktur oder vollständige Barrierefreiheitszertifizierung sind dafür keine angemessenen Voraussetzungen. Offene Grenzen müssen jedoch korrekt bezeichnet und die tatsächlich mitgelieferten Daten freigegeben sein.

## Gegenstand, Kanonizität und Methode

### Maßgeblicher Stand

| Material | Feststellung und Begründung |
|---|---|
| `code/` | Kanonisch: eigenständiges Git-Repository, HEAD `597e1f0216c72eedd01b7b9e6d49be67ca8150f9`, Version `0.2.0`, initial sauberer Arbeitsbaum; README, `pyproject.toml`, CLI, Dockerfile, Tests und ausführbares Paket passen zusammen. 85 erreichbare Commits. |
| `Chatbot-MA/` | `README_LEGACY.txt` bezeichnet den Ordner ausdrücklich als Altbestand und verweist auf `code`, `thesis`, `presentations`. Kein konkurrierender aktueller Implementierungsstand. |
| `Code3-archive-pre-git-20260717/` | Archivierter älterer Paketstand; keine maßgebliche Git-Historie. `code/docs/setup.md:276` warnt ausdrücklich vor dessen lokalen Konfigurationen und Laufzeitdaten. Kein Releasekandidat. |
| `legacy_review_backup/2026-04-23_pre_cleanup_layout/` | `README.txt` dokumentiert Sicherungs-/Migrationszweck. Nicht aktiv. |
| Weitere Workspaceordner | `migration_quarantine`, frühere Audit-/Strukturprüfungen, `THESIS_TECHNICAL_BUILD`, `thesis-ap11-FINAL`, Präsentationen: Kontext-/Forschungsartefakte, kein Ersatz für die ausführbare Implementierung. Nicht aufgrund ihrer Namen als löschbar eingestuft. |
| `thesis/` | Maßgeblich ist der **vorbestehende aktuelle Arbeitsbaum**, nicht allein Git-HEAD `62a7de6`. Mehrere aktive Kapitel und Evaluationsunterlagen waren bereits geändert; `Evaluation/technische-evaluation-2026-10-22/`, `ABGLEICH_FINALER_STAND.md` und `EVALUATIONSSTAND.md` waren unversioniert. |
| `thesis/thesis.pdf` | 187 PDF-Seiten, Buildstand 22.10.2026; SHA-256 `714efd0ca43307f8451fb29748d2219ce4d42c5be4b0085fead592b0f64d3d87`. Abgleich mit den aktiven TeX-Includes, textextrahierter Gesamtinhalt und visuelle Kontrolle ausgewählter technischer Seiten. Gedruckte Seitenzahlen unterscheiden sich von PDF-Blattnummern, z. B. S. 79 = PDF-Blatt 93, S. 149 = Blatt 163. |

### Vollständige Bestandsaufnahme vor Änderungen

Der versionierte Codebestand umfasst **194 Dateien / 5.938.753 Bytes**: 11 Wurzeldateien, 1 CI-Datei, 95 Dateien unter `app/`, 10 unter `data/`, 29 unter `docs/`, 4 unter `requirements/`, 44 unter `tests/`. Darin: 59 Pythondateien der Anwendung und 42 unter Tests einschließlich `conftest.py`; 41 eigentliche Python-Testmodule. Die vollständige Git-Dateiliste, Verzeichnisstruktur, ignorierte Zustände, Packaginglisten, Import-/Referenzstellen und aktiven Thesis-Includes wurden erfasst. Alle 101 Pythondateien konnten statisch geparst werden.

Vorhandene lokale, ignorierte Zustände wurden gesondert inventarisiert: `.env`, `.env.local`, Python-/Pytest-Caches, Egg-Metadaten sowie 303 Dateien unter `runtime/` (darunter 181 WFS-, 117 Live-Evaluations-, 3 Übersetzungsdateien, eine Sessiondatei und ein Interaktionslog). Diese Zahlen beschreiben den vorgefundenen Workspace, **nicht** das Git- oder Docker-Release. Ein Blablador-Secret ist lokal vorhanden; sein Wert wurde weder ausgegeben noch in die Berichte übernommen. Keine Löschung erfolgte.

Arbeitsfolge: Inventar und Kanonizität → statischer Architektur-/Datenflussabgleich → isolierter Export und Tests → Laufzeit- und Gegenbeispielprüfungen → Prüfung der Thesis-Primärbelege → vier Berichte. Keine Tests in der produktähnlichen lokalen Datenablage; isolierte Laufzeitzustände im temporären Auditverzeichnis bzw. Container.

**Evidenzregeln:** „Verifiziert“ bezeichnet direkt gelesenen Code/Artefakt oder tatsächlich ausgeführten Test. „Schlussfolgerung“ bezeichnet eine begründete Bewertung dieser Beobachtung. „Empfehlung“ ist keine bereits umgesetzte Änderung. Ein grüner Test beweist nur seinen geprüften Vertrag. Vollständigkeit bedeutet hier Inventar und systematischer Abgleich aller relevanten Systembereiche, keine formale Verifikation jedes möglichen Programmpfads oder unabhängige Prüfung aller Literaturbehauptungen.

Alle Codepfade in diesen Berichten sind relativ zu `code/`; `../thesis/…` bezeichnet die bereitgestellte Thesis. Zeilen beziehen sich auf den geprüften Stand. JSON-Pointer/Feldnamen ergänzen bei kompakten Messdateien die Fundstelle.

## Tatsächlich ausgeführte Prüfungen

### Clean-Room und Regression

Quelle war `git archive HEAD`, außerhalb des Workspace extrahiert. Damit fehlen `.env`, `.env.local`, lokale Runtime, Entwicklungsumgebungen und nicht versionierte Daten. Docker lief mit Linux/AMD64; Host: Windows, Python 3.14.3; Docker Engine 29.9.1, Desktop 4.96.0, Compose 5.6.0. Die installierte Compose-Version beweist keine projektseitige Compose-Konfiguration.

| Prüfung | Ergebnis / Reichweite |
|---|---|
| `docker build --pull --no-cache --progress=plain --target test …` | Erfolgreich aus sauberem Export. Basisimage-Digest, Ubuntu-Snapshot, Hashlocks und Paketbuild tatsächlich aufgelöst. |
| `docker build --progress=plain --target runtime …` | Erfolgreich; gemeinsame Stufen des unmittelbar vorher neu gebauten Testimages wiederverwendet. Kein zweiter vollständiger No-Cache-Build behauptet. |
| Container: `python -m pytest --junitxml=/tmp/audit-regression.xml` unter `--network none` | **1.219 passed, 1 xfailed, 1 warning**, 286,82 s. Alle 41 Module einschließlich sieben Packagingtests. |
| Container: `python -m compileall -q app tests` und `python -m pip check` | Erfolgreich; keine gebrochenen Abhängigkeitsanforderungen. |
| Container: `node --test tests/frontend.test.cjs` | **17/17 bestanden**, 365,88 ms. Anschließend beide `node --check` für `app.js` und `dialogue.js` erfolgreich. |
| Windows: `python -m pip check`; `python -B -m pytest -p no:cacheprovider --junitxml=…` im Export | **1.219 passed, 1 xfailed, 1 warning**, 385,63 s. Host-Python war vorinstalliert; dieser Lauf allein ist keine frische Abhängigkeitsinstallation. |
| Wheel-/sdist-Prüfung | In beiden Suiten bestanden: Build, sdist→Wheel, Ressourcenvollständigkeit, Ausschluss lokaler Zustände und Wheel-Neuinstallation in separater venv außerhalb des Checkout (`tests/test_packaging.py:81–85,112–121,167–215`). Im Container stammen Build-/Installationsabhängigkeiten ausschließlich aus dem geprüften Wheelhouse. |
| Zwei unabhängige Runtime-Starts | Jeweils `--network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m`, UID 10001, frischer Zustand. Docker-Health `healthy`, HTTP 200 für Oberfläche/Static/Health; Sessions entstanden erst nach Anfrage, Interaktionslogs blieben aus. |
| Persistentes Docker-Volume | Zusätzlich zwei getrennte Container mit demselben neu angelegten Named Volume; Eigentümer 10001:10001, Modus 0700, `LENA_RUNTIME_DIR=/persist/runtime`, `LENA_DATA_DIR=/persist/data`. Sessiondatei blieb über Containerentfernung hinweg bytegleich, dieselbe Session wurde wiederaufgenommen, Verlauf wuchs von einem auf zwei Schritte. Nur synthetische Fallbackanfragen, kein Netzwerk. Eigenes Testvolume anschließend entfernt. |
| Offline-Query | `Wo kann ich essen?` ergab HTTP 200, fachlich `status=error`, `answer_type=technical_fallback`, eine Hilfebuskarte. **Kein erfolgreicher fachlicher Offline-Suchlauf.** |
| Port und echte Textsuche | Frisches Runtime-Image, `127.0.0.1:18762:8002`, 1 CPU / 512 MiB Limit. Mit `alias-fast`, 4096 Tokens, Selectorlimit 30 s: HTTP 200, `status=ok`, `answer_type=grounded_result`, Karten `22,10,9`, Laufzeit 14,402 s. Eine Momentaufnahme danach zeigte 65,08 MiB; dies ist **kein Mindest-RAM oder Lasttest**. |
| Providerinventar | Authentifiziertes `GET /v1/models`: HTTP 200, 59 Kennungen; `alias-fast` und `faster-whisper-large-v3` vorhanden, `gpt-4o-mini-tts` nicht enthalten. Keine Zugangsdaten im Protokoll. |
| TTS-Gegenprobe | Ein kurzer synthetischer Aufruf `/audio/speech`, Modell `gpt-4o-mini-tts`, Voice `alloy`, Text `LENA.` am geerbten Blablador-Endpunkt: **HTTP 404**. |
| Semantische Gegenprobe | Tatsächlich ausgeführt und wiederholt: unbelegte Fahrradreparatur bei Scharni wird als `fact`/`action` akzeptiert, als `service` verworfen. Siehe F-01. |

Beide Pythonläufe meldeten dieselbe Deprecation-Warnung zur künftigen Änderung der FastAPI/Starlette-TestClient-HTTPX-Integration. Das ist kein Testfehler und rechtfertigt keinen ungeprüften Bibliotheksaustausch.

Der einzige `strict xfail` ist `tests/test_formulation.py:1013–1022`: englisch „minor injuries“ wird lexikalisch als Zielgruppenhinweis fehlinterpretiert. Er ist ein bewusst dokumentierter Fehler, kein bestandener Test. Es gab keine weiteren ausgelassenen Python-Testfälle.

Nicht ausgeführt: native Python-3.11-Suite (nur CI-Konfiguration vorhanden), natives ARM64/macOS, kompletter neuer Vier-Stufen-Live-Evaluationslauf, echter mehrsprachiger Mikrofon-/Hörtest, Edge-TTS-Liveprüfung, visuelle Endnutzer-/Assistive-Technologie-Prüfung, längerfristiger Mehrbenutzer-/Lasttest, neue Quellensynchronisation mit Promotion/Rollback im realen Datenverzeichnis, CVE-Datenbankscan oder externe Penetrationsprüfung. Dafür wird kein Erfolg behauptet. Der Verzicht auf den vollständigen Live-Rerun lag **nicht** an fehlenden Secrets; vorhandene Primärbelege wurden geprüft und nur ein begrenzter synthetischer Funktionstest neu ausgeführt.

### Docker-Bewertung

Verifiziert vorhanden: Basisimage mit Digest (`Dockerfile:3`), CA-Bootstrap mit Prüfsumme (`:7`), datiertes Ubuntu-Paketarchiv (`:14–16`), Hashprüfung der Wheels (`:33–36`), netzloser Paketbuild (`:40`), separates Testziel (`:52–53`), Runtime ohne Buildwerkzeuge, Benutzer 10001 (`:60`), Port 8002, Healthcheck und explizites internes Containerbinding (`:61–65`). `.dockerignore` hält Secrets, lokale Daten und alte Reviews aus dem Kontext. Die Runtime enthält die paketierten Bootstrap-Daten; ein lokaler Modellserver oder ein manuell kopierter Datenbestand ist nicht erforderlich.

Die zwei leeren Starts luden jeweils 28 soziale Angebote mit Fingerprint `9471e7051acb8d4e0fc62d59c1d74bb54f72cec1c28b6cffe291ac15499ec0d9`. `runtime_kb_status=degraded` / `source_status=pointer_error` bezeichnet den fehlenden externen Active-Pointer bei erfolgreich geladenem Paket-Bootstrap. Der Docker-Healthcheck prüft Prozess/Datenladung, **nicht** LLM-, Speech- oder Kartenverfügbarkeit. „Healthy“ ist daher kein vollständiger Funktionsnachweis.

Tmpfs-Betrieb ist für flüchtige Forschungsdemos sinnvoll. Persistente Volumes sind kein Startzwang. Bei gewünschter Persistenz müssen `LENA_DATA_DIR`/`LENA_RUNTIME_DIR`, Schreibrechte für UID/GID 10001, Aufbewahrung und Sicherung ausdrücklich eingerichtet werden. Ein eigens angelegtes Named Volume wurde mit dieser Rechtevorbereitung über zwei getrennte Container erfolgreich geprüft; beliebige benutzereigene Host-Bind-Mounts und Langzeitbetrieb sind damit nicht nachgewiesen. Sessionpersistenz ist außerdem durch die automatisierten Dateisystemtests abgedeckt. Compose würde diese Einstellungen bequemer zusammenfassen, aber keine externe Dienstabhängigkeit beseitigen.

Build-Netzwerk bleibt nötig: Registry, Ubuntu-Snapshot und Python-Paketindex. Hashes sichern Integrität, nicht dauerhafte Verfügbarkeit. Ein vollständig offline wiederbaubares Distributionspaket müsste zusätzlich Basisimage, OS-Pakete und Wheelhouse archivieren. Bitidentische Images, beliebige CPU-Architekturen und deterministische Providerantworten sind nicht zugesichert.

### Wissenschaftliche Primärbelege

Alle **31** in `../thesis/Evaluation/technische-evaluation-2026-10-22/SHA256.json` aufgeführten Dateien stimmen mit ihren SHA-256-Werten überein; keine zusätzlichen unindizierten Dateien außer dem Index selbst. JSONL-Zeilen und Kennzahlen wurden zusätzlich gelesen/gezählt. Der Hashnachweis belegt Integrität relativ zum mitgelieferten Index, keine unabhängige Zeitstempelung oder fachliche Wahrheit.

| Lauf / Messreihe vom 22.10.2026 | Fälle / Requests / Provideraufrufe | Technisch beanstandete Fälle | Inhaltsbefund / Gates |
|---|---:|---:|---|
| `run_1977f38ae9474934b478bb4c5a83fa4c` | 15 / 15 / 15 | 0 | 0; Gates bestanden |
| `run_ea2ce8564da94843895ada6e8cf2e04e` | 16 / 16 / 24 | 5 | 0; Gates nicht bestanden |
| `run_50d9cdb41a564aab909d737f0811546d` | 27 / 34 / 59 | 8 | 1 betroffenes Szenario mit 2 Einzelmarkierungen; Gates nicht bestanden; 54 ungeprüfte Metriken |
| `run_fced37b8811c44f382b4e2266146d78f` | 18 Wiederholungen / 18 / 40 | 4 | 0; Gates nicht bestanden; 51 ungeprüfte Metriken |

Belege: jeweils `manifest.json`, `stage-results.jsonl`, `summary.json` unter dem genannten Belegverzeichnis. Die Thesis unterscheidet korrekt technische Beanstandungen einschließlich erfolgreicher Retrys, endgültige Fallbacks und Inhaltsabweichungen (`Chapters/6Resultsneu.tex:173–233`). Gleiche Antworttypen in sechs dreifach wiederholten Szenarien sind kein Nachweis gleicher Texte, allgemeiner Zuverlässigkeit oder inhaltlicher Vollständigkeit. `content_evaluation_complete=false` bleibt wesentlich. Die manuelle qualitative Bewertung ist noch offen; sichtbare Platzhalter dürfen nicht durch abgeleitete oder erfundene Ergebnisse ersetzt werden.

## Priorisierte Befunde

Maßnahmenkategorien: **A** Ursache auf Architekturebene; **B** notwendige strukturelle Verbesserung innerhalb der bestehenden Architektur; **C** optionale Verbesserung; **D** Konfigurations-/Dokumentationskorrektur. Davon unabhängig ist die Artefaktklassifikation im [Cleanup-Plan](REPOSITORY_CLEANUP_PLAN.md).

### F-01 – Kritisch für die Stärke der Sicherheits-/Groundingbehauptung, A → B

**Verifiziert:** Der Validator akzeptiert `Scharni bietet eine Fahrradreparatur an.` mit einer gültigen Referenz auf den Namen von Angebot 8, obwohl dessen Evidence keine Fahrradreparatur enthält. Akzeptiert bei `claim_type=action` und `fact`, verworfen bei `service`. Das ist ein absichtlich eingespeistes synthetisches Modellresultat, **keine beobachtete Live-Antwort des Providers**.

**Ursache:** Die semantische Prüfung verwendet einen begrenzten Konzeptwortschatz und den vom Modell deklarierten Claimtyp. Die strengere Behandlung unbekannter Leistungsclaims gilt nur für `SERVICE` (`app/grounding.py:474–506`); ein `FACT` benötigt lediglich irgendeinen Nicht-Namensfakt im verfügbaren Angebotspool (`:528–532`). Dieser Pool wird aus allen Fakten desselben ausgewählten Angebots gebildet, nicht nur aus tatsächlich passenden Zitaten (`app/grounding_references.py:30–45`). Ein gültiger Verweis beweist somit nicht die Aussagebedeutung.

**Risiko / Schlussfolgerung:** Unbelegte freie Aussagen können trotz gültiger Verträge ausgeliefert werden. Umgekehrt zeigt der bekannte `minor injuries`-xfail unnötige Ablehnungen. Die Regelprüfung ist eine begrenzte Schutzmaßnahme, keine allgemeine Faktengarantie. R-21 „must / implementiert“ (`../thesis/Chapters/AppendixLenaDesign.tex:113`, gedruckt S. 149) und die kategorische README-Formulierung (`README.md:5–10`) benötigen eine engere Aussage. Die Thesis erläutert `not_checked` bereits ausdrücklich (`5Solutionneu.tex:508`); dieser richtige Vorbehalt muss in die zusammenfassenden Statusangaben durchgezogen werden.

**Strukturelle Lösung:** Für faktische Kernaussagen einen entscheidbaren Darstellungsvertrag wählen: strukturierte Auswahl belegter Fakten plus kontrolliertes Rendering; freie Ergänzungen entweder entsprechend begrenzen oder ausdrücklich als nicht vollständig semantisch verifiziert behandeln. Sicherheitsrelevante Aufnahme-/Zielgruppen-/Verfügbarkeitsaussagen dürfen nicht allein durch selbstdeklarierte Claimtypen freigegeben werden. Unabhängige mehrsprachige Negativ-/Paraphrasenfälle und Fehlklassifikation von Claimtypen ergänzen. **Kein lokaler Fahrrad-Schlüsselwortpatch als Lösung.**

Reproduzierbare Gegenprobe aus einem sauberen Checkout/Export mit Testabhängigkeiten, ohne Providerzugang:

```python
import sys
sys.path.insert(0, "tests")
from test_formulation import _settings, _evidence, _response
from app.main import create_app
from app.formulation import ClaimType, FormulatorError
from app.grounding import validate_formulation

evidence = _evidence(create_app(_settings()))
assert not any("fahrrad" in f.value.lower()
               for o in evidence.selected_offers for f in o.facts)
for kind in (ClaimType.ACTION, ClaimType.FACT, ClaimType.SERVICE):
    response = _response(evidence,
        text="Scharni bietet eine Fahrradreparatur an.", claim_type=kind)
    try:
        validate_formulation(response, evidence)
        print(kind.value, "ACCEPTED")
    except FormulatorError as exc:
        print(kind.value, "REJECTED", exc.diagnostic_code)
```

Beobachtet: `action ACCEPTED`, `fact ACCEPTED`, `service REJECTED …SERVICE_FACT_MISSING`.

### F-02 – Kritisch für die öffentliche Weitergabe des vollständigen Pakets, D / gegebenenfalls B

**Verifiziert:** Trinkbrunnendaten werden mitgeliefert, obwohl eine ausdrückliche Datensatzlizenz fehlt (`THIRD_PARTY_NOTICES.md:18–22`, Bootstrap-`source_evidence.json`/`manifest.json`). Zusätzlich erklärt `THIRD_PARTY_NOTICES.md:15–17` die Leipzig-WFS-Daten pauschal als dl-de/by-2-0, während die aktuelle Thesis die konkrete Lizenzzuordnung zum WFS-Endpunkt ausdrücklich als ungeklärt behandelt (`4Approachneu.tex:291–294`). Die UI verlinkt diese Lizenz ebenfalls (`app/static/index.html:148–150`).

**Ursache/Risiko:** Dokumentarisch widersprüchliche Rechtezuordnung bei bewusst mitverteilten Snapshots. GPL für eigenen Code ersetzt keine Datenfreigabe. Dies ist ein nachgewiesener Dokumentations-/Provenienzkonflikt, **kein abschließendes juristisches Urteil über eine Rechtsverletzung**.

**Lösung:** Datensatzweise Weitergabeberechtigung belegen und dieselbe belegte Aussage in Manifest, Notices, UI und Thesis verwenden. Falls Weitergabe nicht möglich ist, getrenntes beschaffbares Datenpaket mit nachvollziehbarem Aufbau und offen lizenziertem Testbestand planen; nicht lediglich Snapshots löschen und Reproduktion behaupten. Der aktuelle Release-Leitfaden benennt diesen Vorbehalt bereits korrekt (`docs/release.md:11–15,54–58`).

### F-03 – Wesentlich: Speech-Konfiguration suggeriert nicht vorhandene TTS-Fähigkeit, A/B + D

**Verifiziert:** `.env.example:69` und `Dockerfile:23` setzen `SPEECH_SYNTHESIS_PROVIDER=openai`. Fehlen explizite TTS-Werte, übernimmt `load_settings` Blablador-URL und -Secret und ergänzt `gpt-4o-mini-tts` (`app/config.py:420–428`). `speech_synthesis_configured` prüft nur nichtleere Werte (`:179–187`); `/api/speech/config` meldet daraus Verfügbarkeit (`app/main.py:421–431`). Am hier verwendeten Blablador-Endpunkt schlug der synthetische TTS-Aufruf mit 404 fehl. `docs/configuration.md:54–55` führt diese Vererbung nicht auf.

**Risiko:** Nach erfolgreicher LLM-Konfiguration wirkt Vorlesen verfügbar, funktioniert aber nicht. Ohne die Beispiel-/Dockerwerte kann alternativ Edge-TTS automatisch gewählt werden (`config.py:363–371`) und einen weiteren externen Dienst einschalten. Ein Blablador-Key ist somit keine vollständige Speech-Einrichtung.

**Lösung:** Explizite getrennte Profile `deaktiviert`, `edge`, `kompatibler Endpunkt`; TTS-Ziel nicht stillschweigend aus LLM-Zugang ableiten. Konfiguriertheit und geprüfte Erreichbarkeit/Fähigkeit getrennt ausweisen. Beispiel mit tatsächlich gewähltem Dienst und geeignetem Modell; Edge bleibt optional und separat dokumentiert. Für STT ist `faster-whisper-large-v3` im Modellinventar vorhanden, tatsächliche Erkennungsqualität wurde hier nicht live geprüft.

### F-04 – Wesentlich: uneinheitliche Startprofile und Konfigurationspriorität, B + D

**Verifiziert:** `load_settings` aktiviert ohne sichere Beispiel-/Dockerwerte vollständige Interaktionslogs und WFS-Autosync (`app/config.py:439,499`); `.env.example:56,81` und Docker deaktivieren beides. `.env.local` überschreibt Prozessvariablen (`config.py:287–288`; dokumentiert in `docs/configuration.md:3–13`). Paketinstallation lädt nicht einfach eine beliebige `.env` aus dem aktuellen Arbeitsverzeichnis. Die lokalen Legacy-Variablen `LENA_LLM_TEMPERATURE`/`LENA_LLM_FALLBACK_PROVIDER` haben keinen entsprechenden Leser; Temperatur ist im Provider fest vorgegeben.

**Risiko:** Native Starts können unerwartet Netzverkehr und persistente Interaktionen erzeugen; lokale Dateien können vermeintliche CLI-/Umgebungsentscheidungen übersteuern. Auf OneDrive liegende Laufzeitdaten werden dadurch nicht automatisch vertraulich. Secrets sind zwar ignoriert, aber ein manuelles Workspace-ZIP würde sie einschließen.

**Lösung:** Ein zentrales, getestetes Profilmodell mit sicheren, kanalübergreifenden Defaults und klarer Priorität; externe Konfiguration außerhalb des installierten Pakets. Ungültige/alte Namen gezielt melden. Bis dahin für reproduzierbare Starts `LENA_ENV_FILE_MODE=disabled` und alle Betriebsflags explizit setzen. Kein Secretwert in Diagnoseausgaben.

### F-05 – Wesentlich für Wartung: Anfrageorchestrierung bündelt Fachregeln und Darstellung, A → B

**Verifiziert:** `app/service.py` hat 1.618 Zeilen; `_query_core` (`:567–1189`) umfasst 623 Zeilen mit Safety, Interpretation, Dialogen, Fachsonderfällen, Kandidaten, Modellaufrufen und Ergebnisaufbereitung. Trinkwasser-/Toilettenpfade (`:1334–1588`) enthalten ähnliche Orchestrierung. `create_app` in `app/main.py:104–610` verbindet zahlreiche Laufzeit- und API-Aufgaben.

**Risiko:** Neue Sonderfälle erhöhen die Wahrscheinlichkeit widersprüchlicher Prioritäten und mehrfach nötiger Änderungen. Die vielen Tests begrenzen Regressionen, ersetzen aber keine klare Verantwortungsverteilung. Ähnliche Pfade sind wegen ihrer verschiedenen Datenverträge nicht automatisch identische, löschbare Duplikate.

**Lösung:** Bestehende Verträge beibehalten; schrittweise Stage-Orchestrierung, Dialog-/Safety-Entscheidungen und Ergebnisprojektion trennen. Gemeinsame Infrastrukturabläufe erst nach einem Vergleich ihrer Invarianten extrahieren. Verhalten mit vorhandenen Charakterisierungstests sichern; keine willkürliche Komplettumstrukturierung nach Zeilenzahl.

### F-06 – Wesentlich: Grenzen von Session-/Dialogpersistenz, B; Mehrprozessausbau C

**Verifiziert:** Der JSON-Store verwendet prozesslokale `RLock`s und atomare Dateiersetzung (`app/sessions.py:31–35,355` ff.). TTL-Bereinigung erfolgt bei Zugriff (`:310–323`), nicht zeitgesteuert. Quarantänedateien beschädigter Sessions werden ohne eigenen Ablauf erzeugt (`:344–353`). Bei Dialogreservierung wird der Bool-Rückgabewert eines fehlgeschlagenen Schreibens nicht ausgewertet (`:237–245`).

**Schlussfolgerung:** Für den vorgesehenen einzelnen lokalen Prozess ist dies eine vertretbare einfache Persistenz. Die Behauptung einer zuverlässig einmaligen Dialogannahme gilt jedoch nicht uneingeschränkt bei Schreibfehlern; mehrere Worker sind nicht durch den Prozesslock koordiniert. Der Schreibfehlerfall wurde hier statisch festgestellt, kein neu ausgeführter Race-/Diskfull-Nachweis behauptet.

**Lösung:** Persistenzfehler im Reservierungsvertrag sichtbar und kontrolliert behandeln; Single-Worker-Grenze dokumentieren. Aufbewahrung einschließlich Quarantäne und optionalem Interaktionslog festlegen. Transaktionaler Store erst bei tatsächlichem Bedarf an Mehrprozessbetrieb; keine Enterprise-Datenbank als Voraussetzung des Forschungsstarts verlangen. UI-Reset ist bereits korrekt als kein sofortiger serverseitiger Löschauftrag dokumentiert (`5Solutionneu.tex:762–807`).

### F-07 – Wesentlich: aktuelle Betriebsdokumentation widerspricht sich, D

**Verifiziert:** `docs/setup.md:305` behauptet trotz vorhandenem und geprüftem Dockerfile, es gebe keines. `docs/data-flow.md:48,145–146,163–164` nennt Satzvertrag 2 bzw. Formulatorvertrag 3 und Prompt 17/19; aktuell sind Vertrag 5 und Prompt 22 (`app/formulation.py:29–31`). `docs/testing.md:143–148` beschreibt die Hashlock-Lage unvollständig gegenüber vorhandenen Python-3.12-Hashlocks. `.env.example:1–4` nennt die LLM-Interpretation optional, ohne den Ausfall normaler Suche zu erläutern; README tut dies dagegen korrekt.

**Risiko:** Fachkundige Dritte können die Anwendung installieren, müssen aber widersprüchliche Anleitungen selbst gegen den Code auflösen. Historische, mit 21.10. datierte Testzahlen von 1.178 sind als Historie nicht falsch; es fehlt eine eindeutige Verknüpfung mit dem finalen Stand von 1.219 Tests.

**Lösung:** Einen kurzen verbindlichen Startpfad und eine einzige maßgebliche Konfigurations-/Versionsübersicht festlegen. Historische Evaluationsabschnitte explizit datieren/abgrenzen. Architekturdetails verlinken statt aktuelle Versionsnummern über mehrere lange Dokumente unabhängig fortzuschreiben. Alle geprüften relativen Markdown-Dateilinks in README und regulären exportierten `docs/*.md` waren vorhanden; das Problem ist vor allem semantische Aktualität, nicht ein allgemeiner Linkzerfall.

### F-08 – Wesentlich: Thesis-Auslieferung und manuelle Bewertung nicht abgeschlossen, B/D

**Verifiziert:** Die aktuellen technischen Primärbelege und mehrere finale Thesis-Korrekturen gehören noch nicht zum Git-HEAD der Thesis. Die Zusammenfassung und Ergebnis-/Diskussionskapitel enthalten sichtbare manuelle Ergebnisplatzhalter (`FrontBackmatter/Summary.tex:25`, `Chapters/6Resultsneu.tex:235–243`, `Chapters/7Discussion.tex:49–54`).

**Risiko:** Ein normales Archiv des Thesis-HEAD würde nicht die hier geprüfte Beschreibung/Evidenz ausliefern. Offene Eigenbewertungen sind kein wissenschaftlicher Nachweis. Negative technische Gates sind dagegen korrekt dokumentiert und dürfen bei einer späteren Bereinigung nicht verschwinden.

**Lösung:** Nach separater Freigabe einen konsistenten Thesis-/Software-Evidenzstand versionieren und mit Manifest verbinden. Manuelle Bewertung tatsächlich durchführen und protokollieren oder den finalen Untersuchungsumfang ausdrücklich ohne diese Resultate deklarieren; Platzhalter entfernen, ohne Resultate zu erfinden. Eine DOI ist erst nach tatsächlicher Archivierung zu ergänzen.

### F-09 – Wesentlich für Diagnose: strukturierte Ereignisfelder fehlen im Standardlog, B/D

**Verifiziert:** Zahlreiche Ereignisse schreiben Methode, Pfad, Dauer und Fehlerklasse über `extra` (`app/main.py:231–247`). `logging.basicConfig` rendert aber nur Zeit, Level, Loggername und Nachricht (`:118–121`). Standard-Containerlogs zeigen damit etwa `request.started`, nicht sämtliche zugehörigen strukturierten Felder. `caplog`-Tests können die Felder trotzdem direkt am LogRecord sehen.

**Risiko:** Der Code enthält Diagnosedaten, die eine externe Person im normalen Log nicht erhält. Vollständige Interaktionslogs sind kein angemessener Ersatz für technische Beobachtbarkeit.

**Lösung:** Ein expliziter, erlaubnislistenbasierter technischer JSON-/Textformatter und ein Test des tatsächlich serialisierten Logausgangs. Keine freien Nutzertexte, Secrets oder Providerrohantworten hinzufügen. Die Thesis sollte zwischen vorhandenen LogRecord-Metadaten und standardmäßig ausgeliefertem Logformat unterscheiden.

### F-10 – Redaktionell bis wesentlich für Pflege: Altpfade und unklare Artefaktrollen, B/C/D

**Verifiziert:** Das alte lexikalische `retrieve`/`select_card_offers` wird im produktiven Anfragepfad nicht verwendet; `normalize_text` aus derselben Datei aber schon (`app/service.py:84`; `app/retrieval.py:12,224,276`). Markdown-Loader/Fixture, historische WFS-Releases, doppelte Bootstrap-/Wartungsdaten und alte Arbeitspläne besitzen belegbare Test-, Herkunfts- oder Wartungsrollen. CLI-`print`-Ausgaben dienen Ergebnissen von Wartungskommandos; keine Grundlage für pauschales Entfernen als Debugcode.

**Risiko/Lösung:** Nicht unbesehen löschen. Aktive Hilfsfunktion vom historischen Retrievalbaseline-Vertrag trennen; über Aufbewahrung des Baselines gesondert entscheiden. Forschungshistorie indexieren und aus aktuellen Betriebsanweisungen klar abgrenzen. Unklare Kommentare wie „siehe Untersuchung Zeile 11“ (`service.py:926,1015`) durch stabile Belege ersetzen. Konkrete Einzelklassifikation im [Cleanup-Plan](REPOSITORY_CLEANUP_PLAN.md).

## Gesamturteil zur Qualität und Sicherheitsgrenze

| Bereich | Urteil mit praktischer Grenze |
|---|---|
| Modulgrenzen / Datenmodell | Gut erkennbare Verträge für Interpretation, Auswahl, Evidence, Infrastruktur und Releases; zentrale Orchestrierung zu dicht. |
| Datenfluss / Kuration | Positivlisten, Hashbindung, getrennte Quellen, manuelle Aktivierung und stabile IDs sind eine belastbare Basis. Quellenaktualität und fachliche Richtigkeit werden durch Hashes nicht bewiesen. |
| LLM / Safety | Begrenzte Providerkontexte, deterministische Kandidatenmenge, Preflight, Fail-closed-Interpreterpfad, Retrybudget und Templates sind sinnvoll. Freitextsemantik bleibt teilweise modell-/wortschatzabhängig; Interpreter-`explicit_facts` sind keine unabhängig bestätigten Tatsachen. Tests belegen Szenarien, keine allgemeine Akutgefahr- oder Wahrheitsgarantie. |
| Fehlerbehandlung | Redigierte Fehlercodes und getrennte Providerfehler meist gut; degradierter Start wird sichtbar. Konfigurationsgültigkeit, Dienstverfügbarkeit und Persistenzerfolg nicht überall sauber getrennt. |
| Tests | Für einen Forschungsprototyp umfangreich und ausführbar; Packaging und netzlose Tests sind besonders positiv. Mehr Tests allein lösen fehlende semantische Prüfbarkeit nicht. Keine Coverage-Prozentzahl wurde ermittelt. |
| Sicherheitsgrenzen | Loopback-Default mit explizitem Public-Opt-in (`app/__main__.py:25–39`), sichere Textdarstellung, TTS-Bindung an Session/Sprache und Audio-/Textgrenzen sind vorhanden. Keine Authentisierung, TLS-Terminierung oder Rate-Limits: für isolierten lokalen Forschungsbetrieb kein automatischer Mangel, für öffentlichen Betrieb unzureichend. |
| Session / Logging | Begrenzte Sessions, atomare Writes, Safety-Redaktion; vollständige Nicht-Safety-Interaktionen können lokal gespeichert werden. TTL ist keine sofortige Löschung, Reset keine Lösch-API. |
| Abhängigkeiten / Portabilität | Alle direkten Pythonabhängigkeiten haben erkennbare Verwendung, einschließlich optionalem `edge-tts`, PyAV und Windows-Zeitzonendaten. Kein Ollama, keine Modellgewichte, kein Vektorserver, kein lokales STT-/TTS-Modell erforderlich. Linux/AMD64 und Windows geprüft; andere Plattformen offen. |
| Dokumentation | Zweck, Komponenten und Wartung sind ausführlich erklärt; konkrete Widersprüche verschlechtern Verlässlichkeit. Umfang ist kein Ersatz für einen widerspruchsfreien Startvertrag. |
| Geheimnisse / personenbezogene Daten | In versionierten Dateien und 1.219 untersuchten erreichbaren Git-Blobs keine Treffer der verwendeten privaten-Schlüssel-/Tokenmuster; keine versionierten `.env`, Session-/Interaktionslogs oder Audioaufnahmen gefunden. Begrenzter Muster-/Pfadscan, keine Garantie, dass jede denkbare Geheimnisform ausgeschlossen ist. Öffentliche Einrichtungs-/Kontaktangaben sind Quellendaten, nicht automatisch private Testpersonen. Lokale ignorierte Secrets/Logs bleiben sensibel und dürfen nicht pauschal mitveröffentlicht werden. |

## A–F: Abschluss und getrennter Folgeauftrag

**A. Kann eine externe Person die Anwendung lokal starten? – Ja, unter Bedingungen.** Empfohlener nachgewiesener Weg: sauberer Export von `597e1f0`, Docker mit Linux/AMD64, Build-Netzzugang, Browser, freier Loopback-Port und beschreibbares temporäres Laufzeitverzeichnis. Das Runtime-Image bringt Python, Abhängigkeiten, Frontend und Bootstrap mit. Für reguläre Textsuche zusätzlich `REWRITE_PROVIDER=blablador`, `BLABLADOR_BASE_URL=https://api.blablador.fz-juelich.de/v1`, gültiger `BLABLADOR_API_KEY`, verfügbarer `BLABLADOR_MODEL` (geprüft `alias-fast`) und Netzwerk. Für das geprüfte Profil außerdem 4096 Ausgabetokens und 15/30/30 s bei 45 s kumulierter Providerwartezeit. Andere geeignete Werte können funktionieren, sind hier kein neuer Nachweis. Sprache und Karten benötigen die in der Matrix genannten separaten Voraussetzungen. Ohne LLM startet das System, die normale Suche endet jedoch im technischen Fallback.

**B. Ist Docker in der aktuellen Form ausreichend? – Ja für reproduzierbaren lokalen Start, Paketprüfung und Tests; nein als vollständige Einrichtung aller externen Funktionen.** Compose fehlt, ist aber kein Blocker. Speech-Konfiguration und Dokumentation müssen korrigiert, Datenweitergaberechte vor öffentlicher Verteilung geklärt werden.

**C. Maximal fünf strukturelle Maßnahmen mit größter Wirkung:**

1. Faktendarstellung und semantische Vertrauensgrenze neu festlegen; kritische Aussagen durch einen entscheidbaren Vertrag absichern und Gegenbeispiele unabhängig prüfen.
2. Einheitliche explizite Betriebs-/Providerprofile einschließlich deaktivierter Speech-Dienste, konsistenter Defaults und separater Verfügbarkeitsdiagnose schaffen.
3. Anfrageorchestrierung schrittweise entlang vorhandener Verträge zerlegen, ohne die Fachregeln oder Datenbestände unbeabsichtigt zu verändern.
4. Persistenzfehler-/Dialogreservierungsvertrag und tatsächlich ausgegebene technische Logs absichern; Single-Worker-/Aufbewahrungsgrenze klar machen.
5. Ein konsistentes Release-/Evidenzpaket mit geklärter Datenherkunft, aktueller Dokumentation und explizit erhaltener Forschungshistorie herstellen.

**D. Vorschlag für einen zweiten, getrennten Implementierungsauftrag:** „Behebe nach priorisierter Entscheidung F-01 bis F-09 in kleinen überprüfbaren Schritten. Zuerst Rechte-/Artefaktentscheidungen und das gewünschte Fakten-/Sprachprofil festlegen; dann Profil-/TTS-/Logging-/Persistenzkorrekturen, eng begrenzte Orchestrierungsrefaktorierung und dokumentierte Bereinigung. Ergänze nur aussagekräftige Gegenbeispiel-/Fehlerpfadtests, führe dieselben Clean-Room-Gates erneut aus und aktualisiere die Thesis ohne erfundene Evaluationsergebnisse. Keine Veröffentlichung, Datenlöschung oder Entfernung von Forschungsbaselines ohne zugehörige ausdrückliche Freigabe.“ **Dieser Auftrag wurde nicht begonnen und darf erst nach ausdrücklicher Freigabe umgesetzt werden.**

**E. Für fachkundige Externe verständlich, installierbar und wartbar?** Zweck und Hauptarchitektur: ja. Installation über den geprüften Dockerweg: ja, bedingt. Widerspruchsfreie Einrichtung sämtlicher Funktionen: derzeit nein. Wartung: mit Einarbeitung möglich, aber durch lange Orchestrierung und parallele Dokumentationsstände unnötig erschwert. Das vollständige Paket ist aktuell noch kein sauber freigegebenes wissenschaftliches Release.

**F. Minimal-invasive Bereinigung:** Zuerst Inventar/Hashmanifest und Rollenindex sichern; danach ausschließlich regenerierbare lokale Caches aus einer später freigegebenen Arbeitskopie entfernen. Unwirksame Konfiguration und aktuelle Dokumentationswidersprüche separat korrigieren. Historisches Retrieval erst nach Trennung der aktiven Hilfsfunktion und Entscheidung über Forschungsnutzen behandeln. Hashgebundene Rohdaten, Manifeste, negative Evaluationen und historische Entscheidungen erhalten. Abschließend Export/Wheel/Docker erneut auf Inhalt und Funktion prüfen. Detaillierte Reihenfolge und Einzelentscheidungen stehen im Cleanup-Plan.

## Nachweisablage dieses Audits

Temporäre Rohprotokolle befinden sich außerhalb des Repositorys unter `%LOCALAPPDATA%/Temp/lena-independent-audit-1550ee6a266a4344afd61ba56526fd36/`: `build-test.log`, `build-runtime.log`, `native-tests.log`, `native-regression.xml`, `container-tests.log`, `container-regression.xml`, `runtime-smokes.json`, `runtime-1.log`, `runtime-2.log`, `live-smoke.json`, `live-runtime.log`, `tts-smoke.json`, `grounding-probe.json`, `volume-smoke.json`. Sie sind lokale Hilfsbelege, kein dauerhaft veröffentlichtes Archiv. Die entscheidenden Resultate und reproduzierbare Gegenprobe sind deshalb oben enthalten. Eigene Test-/Smoke-Container und das eigene Testvolume wurden entfernt; gebaute Auditimages bleiben lokal verfügbar.

Testimage: `sha256:c85d85cda5b4b53994920678261b5c224b56eaa58e335a7b9b43bef9257a5f44`.
Runtime-Image: `sha256:fad8127de2aced419d6d4ab703bfb6e2b4ce9f72dfe24a94529733ff849d9195`, Linux/AMD64, ausgewiesene Imagegröße 374.256.445 Bytes. Diese IDs bezeichnen tatsächlich lokal gebaute Images, keine veröffentlichten Registryartefakte.
