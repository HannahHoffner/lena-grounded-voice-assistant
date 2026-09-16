# Qualitätsreview und konservative Bereinigung — LENA

Stand: 16. September 2026. Umfang: Anwendung in `code/`, lokale und sichere
Prüfungen. Verantwortlich für diesen Zusatzreview: Codex.

Dieser Bericht beschreibt den abgeschlossenen ersten Prüfstand. Die danach vom
Nutzer gemeldeten Dusch-, Schlafdialog- und Firefox-Probleme werden im
[gezielten Folgereview](../exec-plans/fix-shower-sleep-firefox.md) behandelt.

## 1. Zusammenfassung

Die überprüfte Anwendung startet aus dem installierten Wheel, enthält ihre
vollständigen Paketressourcen und besteht die betroffenen Regressionstests.
Bestätigte Fehler in Safety-Routing, Dialogbedienung, Faktenübernahme,
Öffnungszeiten, beschädigten Daten und Speech-Grenzen wurden gezielt korrigiert.
Insbesondere erreicht TTS beide vorhandenen Adapter mit sessiongebundenem Text;
unterbrochenes Audio gibt seine Ressourcen jetzt frei.

Claudes Bereinigung und Testisolationskorrektur wurden übernommen und geprüft.
Die Aussage seines Berichts, es gebe keine Fehler im Anfragepfad, wird durch die
zusätzlich gefundenen Regressionen korrigiert. Es wurden keine produktiven
LLM-, STT-, TTS-, WFS-, Quellen- oder Kartenaufrufe ausgeführt. Externe
Erreichbarkeit, Sprachqualität und vollständige Produktionsreife sind damit
ausdrücklich **nicht** nachgewiesen.

Ergebnis: **629 unterschiedliche betroffene Python-Tests und sechs ausführbare
Frontendtests erfolgreich**, zusätzlich zehn STT-Tests nach einer abschließenden
Testcodebereinigung erneut erfolgreich. Die frühere vollständige Baseline mit
754 erfolgreichen Tests wird gemäß aktualisiertem Nutzerauftrag wiederverwendet;
ein vollständiger Nachlauf aller heutigen Tests wird nicht behauptet.
Neue Mermaid-Diagramme wurden auf ausdrücklichen Nutzerwunsch zurückgestellt.

## 2. Baseline, Git und Evidenz

| Zeitpunkt | Zustand / Nachweis |
|---|---|
| Ursprüngliche Baseline | Branch `maintenance/repository-cleanup`, sauberer Commit `534ffbaea561417c0719008d81281201bfe60a76`, 407 versionierte Dateien |
| Eigener früher Baselinelauf | `python -m pytest`: 754 bestanden, eine Warnung, 234,28 s; Syntax, Abhängigkeiten, Version und Diffprüfung erfolgreich |
| Claudes Bericht | 754 Tests vorher/nachher; Wheel 94, Source-Archiv 190 Dateieinträge; Startup- und Runtimeprüfung berichtet. Das ist ergänzende Fremdevidenz |
| Während der Arbeit vom Nutzer committet | `8e7b204` enthält die 212 Altbaum-Löschungen; `3433c7a93afa5fd4ded57927859e08da89da8f14` enthält die weitere übernommene Bereinigung und den Arbeitsplan |
| Eigener Implementierungsvergleich | Sauberer `3433c7a`, 196 versionierte Dateien; alle folgenden Änderungen bleiben ungestagt |
| Umgebung | Windows, Python 3.14.3; vorhandene Electron-Node-Laufzeit 24.18.0; CI-Konfiguration zielt auf Python 3.11 |

Struktur, aktuelle/recent Commits, Status, ignorierte Dateien, Worktree-Liste,
Package-Metadaten, Manifest, CI, Konfiguration, Appmodule, Ressourcen,
zugehörige Tests und aktuelle Betriebsdokumentation wurden geprüft. Die
55 Python-Appmodule und handgeschriebenen Browserskripte waren Gegenstand des
Codereviews. Vendored Leaflet wurde auf Einbindung/Paketierung und verwendete
Schnittstellen geprüft; dies ist kein eigenständiger vollständiger Audit seiner
minifizierten Drittanbieterimplementierung. Historische Pläne und Daten wurden
als Referenz-/Provenienzevidenz behandelt, nicht fachlich neu kuratiert.

Temporäre, nicht einzucheckende Evidenz liegt unter
`%TEMP%/lena-quality-audit-20260915-0s9xv94c/`: Baseline-Inventare, übernommene
Patches, Hashvergleich der Altbäume, Teilreviewnotizen, Buildlog und
`verification-final.json`. Der persistente
[Arbeitsplan](../exec-plans/quality-review-2026-09.md) dokumentiert Entscheidungen
vor Änderungen und Löschungen.

**Früherer Sessionverlust:** Claude berichtet, dass sein Baselinelauf wegen
fehlender Testisolation lokale Sessions überschrieben hat und 56 Sessions aus
einer älteren Momentaufnahme wiederhergestellt wurden. Der eigene frühere
Baselinelauf verwendete ebenfalls den ungeschützten Teststand. Eine vollständige
Rekonstruktion damaliger Sessiondaten ist nicht belegt. Seit Wiederaufnahme
sind alle **224** geschützten Dateien unter `data/`, `runtime/`, `.env` und
`.env.local` per SHA-256 unverändert; es kamen dort keine neuen Dateien hinzu.

## 3. Rekonstruierte Architektur und Anfragefluss

1. **Start:** `python -m app` validiert die lokale Bind-Adresse und startet
   Uvicorn mit der Factory `app.main:create_app`. Settings laden Prozesswerte
   und optional `.env`/`.env.local`. Letztere kann Prozesswerte überschreiben.
2. **Wissensbasis:** `kb_loader` prüft Kuration, exakte Releasebindung,
   Manifeste und Hashes. Ein gebundener Paket-Bootstrap ermöglicht den Betrieb
   ohne externe Dateninstallation. Betreiberangebote, öffentliche Toiletten
   und Trinkbrunnen besitzen nachvollziehbar getrennte Quellenpfade.
3. **Eingang:** Browsertext, Kategorie oder Dialogauswahl gelangen an
   `POST /api/query`. STT schaltet bei Audio zuerst
   `POST /api/speech/transcribe` davor. Pydantic und Endpunktgrenzen prüfen
   Eingaben; Sessions sind an Wissensbasis-Fingerprint und Sprache gebunden.
4. **Safety und Dialog:** Ein enger lokaler Gefahr-Preflight kann sofort
   abbrechen. Reine bekannte Selbstbeschreibungsfragen und ein initial leerer
   Dialog sind eng begrenzte Sonderfälle. Sonst interpretiert das LLM die
   Anfrage strukturiert. Akutgefahr stoppt die Fachsuche; unsichere Gefahr
   öffnet einen bindenden Bestätigungsdialog. Ein Themenwechsel löscht ihn nicht.
5. **Suche:** Deterministische Regeln begrenzen die fachlich erlaubten Angebote,
   Zugangsbedingungen und belegten Zeiten. Toiletten verwenden einen eigenen
   räumlichen Pfad; Trinkwasser verbindet zulässige soziale Angebote und
   freigegebene Brunnen. Fehlende Fakten können gezielt rückgefragt werden.
6. **Auswahl und Formulierung:** Ein optionaler Selector darf ausschließlich
   erlaubte Kandidaten-IDs wählen. Pflichtangebote und stabile Reihenfolge
   bleiben lokal kontrolliert. Der Formulator erhält begrenzte belegte Fakten;
   Grounding prüft seine gesamte Antwort. Maximal drei Angebote werden als
   Hauptresultate ausgegeben. Ungültige Antworten fallen auf lokale Texte zurück.
7. **Fehler:** Interpreterausfall beendet den fachlichen Pfad. Sichtbar bleiben
   ein lokalisierter technischer Hinweis mit bedingter 112-Angabe und ggf. eine
   lokal belegte Hilfebus-Kontaktkarte **ohne Marker**. Selectorfehler nutzen
   deterministische Auswahl und Template. Formulator-Parsing/Grounding erlaubt
   höchstens einen Wiederholungsversuch innerhalb des Restbudgets.
8. **Ausgabe:** Lokalisierte Antwort, Karten, Marker und Dialog werden gerendert;
   letzte freigegebene Vorlesetexte werden in der Session registriert.
   Finale Interaktionspaare können lokal protokolliert werden; Safety-Eingaben
   werden redigiert. Persistenz verwendet atomare Dateiwechsel.

**Speech-Verbindung:** Die lokale Konfiguration wählt Edge-TTS mit 45 s Timeout;
LLM und STT sind konfiguriert, ihre Zugangsdaten wurden nicht ausgegeben.
TTS sendet nur Texte des letzten Session-Turns in derselben Sprache an Edge
oder den OpenAI-kompatiblen `/audio/speech`-Adapter. `112` wird vor der Synthese
sprachabhängig ziffernweise umgesetzt. Edge liefert MP3. STT prüft tatsächliche
Audiobytes, dekodiert mit PyAV zu PCM-WAV und begrenzt die Dauer auf 120 s.

**Externe Grenzen:** LLM-Stufen teilen standardmäßig 45 s Providerwartezeit
(Einzelgrenzen 15/10/30 s). STT/TTS begrenzen ihr Warten separat. Quellen-Sync,
Releasepromotion, Übersetzungswartung und Evaluations-CLIs sind getrennte
Betriebseinstiege; Nutzeranfragen laden keine neuen Quelldaten. Der Browser
verwendet externe OSM-Kacheln. Lokal ist WFS-Autosync aktiviert; bei allen
Audit-Starts wurde es ausdrücklich deaktiviert.

## 4. Befunde nach Schweregrad

### Hoch

| ID / Klassifikation | Evidenz und Auswirkung | Entscheidung |
|---|---|---|
| H1 — bestätigter Defekt | Selbstbeschreibung wurde als Teilstring vor Interpretation erkannt; Zusatztext konnte die Risikoprüfung umgehen. Leere/Kategorieanfragen konnten einen offenen Safety-Dialog umgehen | Vollständiges normalisiertes Matching, offene Safety-Dialoge zuerst übernehmen; reine Fragen in fünf Sprachen bleiben providerfrei; Regressionen bestanden |
| H2 — bestätigter Defekt, übernommen | Test-Settings schrieben in die reale Checkout-Runtime und konnten Forschungsdaten verdrängen | Claudes zentrale temporäre Runtime-Isolation erhalten; aktuelle 224-Dateien-Hashprüfung erfolgreich; früherer Verlust bleibt ungeklärt |

### Mittel

| ID / Klassifikation | Evidenz und Auswirkung | Entscheidung |
|---|---|---|
| M1 — bestätigter Defekt | Tippen setzte bereits den Sende-Lock; erfolgreiche Folgedialoge blieben busy; Auswahl enthielt ggf. unzulässig eine alte Kategorie | Lock an tatsächlichen Request gebunden, beim Ergebnis zurückgesetzt, beim Relokalisieren erhalten; Auswahl ohne Kategorie; ausführbare JS-Tests |
| M2 — bestätigter Defekt | Neue explizite Altersgruppe wurde mit widersprechender alter Alterszahl kombiniert | Nur kompatible Altfakten übernehmen, bestehende Validierung wiederverwenden; echter Dialog/API-Fall und sechs Faktenfälle |
| M3 — bestätigter Defekt | Mehrfachbedarf Essen/Wasser plus Beratung wählte den Hilfebus-Zeitplan aus einer ungeordneten Menge | Primärbedarf bestimmt seinen belegten Zeitplan; zwölf Fälle zu Tagen, Uhrzeiten und Leistungsreihenfolge |
| M4 — bestätigter Defekt | Vertauschte Kurations-Quell-IDs erfüllten den Mengenvergleich und konnten falsche Quellzuordnung erzeugen | ID-Gleichheit pro Angebot validieren; Kuration selbst unverändert |
| M5 — bestätigter Defekt | Defekte Sessiondatei mit ungültigem UTF-8 bzw. einzelne naive Zeitstempel konnten andere Sessions blockieren | Bestehende Quarantäne/Record-Verwerfung erweitern; Bytes und valide Nachbarsessions geprüft |
| M6 — bestätigter Defekt | Verkürzte Toiletten-CSV und defekte Grenzkoordinaten konnten rohe Pythonfehler erzeugen | Fehlende Spaltenzellen/Geometriestruktur vor Verarbeitung validieren; kontrollierte vorhandene Quellenfehler |
| M7 — bestätigter Defekt | Dataset-Hash im Toilettendiff markierte unveränderte Datensätze als verändert | Nur beim fachlichen Recordvergleich den Gesamtquellenhash ausschließen; Hash-/Releaseprüfung bleibt bestehen |
| M8 — bestätigter Defekt | Falsche Legacy-Übersetzungs-Mappings/UTF-8 führten nicht zuverlässig zum sicheren Katalogfallback | Vorhandene Fallbackbehandlung erweitern; keine Übersetzungen oder Freigaben geändert |
| M9 — bestätigter Defekt | LLM-JSON-Wurzeln als Liste/null und STT-Text als Liste/Zahl wurden nicht sauber behandelt | Bestehende Providerfehlerpfade statt AttributeError bzw. erfundenem Transkript; 503 für ungültiges STT-Ergebnis |
| M10 — bestätigter Defekt | Abbruch von TTS pausierte Audio, ließ Blob-URL und Wiedergabe-Promise offen | Gemeinsame lokale Abschlussfunktion für Audioende, Fehler und Unterbrechung; alte Fehler löschen kein neueres Audio |
| M11 — bestätigter Defekt, offen im Evaluationswerkzeug | E2E-Runner ignoriert deklarierte Interpreterfehler-Injection, erwartet beim Fallback keine Karte und zählt Aufrufe nachträglich/unvollständig | Forschungsergebnisse erhalten; Grenzen in Betriebsdokumentation markiert. Vor neuen E2E-/Stabilitätsfreigaben korrigieren; keine Produktfreigabe daraus ableiten |

### Niedrig

| ID / Klassifikation | Evidenz | Entscheidung |
|---|---|---|
| L1 — bestätigter Defekt | Speech-Konfiguration konnte für Edge `wav` melden, obwohl der Adapter MP3 liefert | Formatmeldung an tatsächlichen Adapter gebunden; beide Adapter × fünf Sprachen geprüft |
| L2 — Wartbarkeitsproblem | Unerreichbare interne Interpreterfehler-Zweige nach früher Rückgabe | Entfernt/vereinfacht; öffentliche Legacy-Methoden und Vertragswerte behalten |
| L3 — Wartbarkeitsproblem | Sprachressourcentest schlug wegen veralteter Versionsnummer fehl, nicht wegen getesteter Reviewmetadaten | Aktuelle Konstante und konkrete Fehlermeldung prüfen; Assertion präzisiert |
| L4 — Wartbarkeitsproblem | README/Betriebsdocs widersprachen Hilfebus-, TTS-, Retry-, Übersetzungs- und Offlineverhalten | Beschreibungen am implementierten Vertrag ausgerichtet |
| L5 — obsolete Artefakte | Vier nicht registrierte identische Altbäume, tote Definitionen, Imports und generierte Altoutputs | Übernommene Löschungen verifiziert; Details unten |

### Grenzen und optionale Verbesserungen

- **Fehlende Evidenz:** Reale Dienstverfügbarkeit, Ausgabequalität aller Sprachen,
  echter Browser-/Screenreaderlauf und Remote-CI auf Python 3.11. DOM-Doubles
  prüfen Verhalten, keine vollständige Browserdarstellung. Kein Dependency-CVE-
  Audit; `pip check` prüft installierte Versionsverträglichkeit.
- **Begründete Prototypbegrenzung:** Lokal gebundener Einzelprozess ohne
  Authentifizierung, TLS, Rate-Limiter oder koordinierte Mehrprozess-Sessions.
  `--allow-public` bleibt eine bewusste Betriebsentscheidung.
- **Begründete Prototypbegrenzung:** Query-/TTS-Textlimits greifen nach dem
  JSON-Parsen; sie begrenzen nicht den gesamten Body. STT begrenzt tatsächliche
  Bytes. Timeouts beenden einen bereits laufenden Decoderthread oder Remotejob
  nicht zwingend physisch.
- **Fehlende Evidenz:** Sprachwechsel/Reset während laufender Query/STT sowie
  konkurrierende Requests derselben Session sind nicht vollständig durch einen
  Browser-End-to-End-Test abgesichert. Die korrigierte Sendesperre deckt
  versehentliches Doppelsenden ab.
- **Begründete Prototypbegrenzung:** Maximal 40 zusätzliche Vorlesetexte pro
  Session-Turn stehen einer größeren Marker-Vertragsobergrenze gegenüber.
  Der aktuelle Bestand ist klein; eine beliebige Skalierung wird nicht belegt.
- **Optionale Verbesserung:** Große Orchestrierungs-/Frontend-/Evaluationsmodule,
  zusätzliche statische Typ-/Lint-Prüfungen und JS-Ausführung in CI. Keine
  Aufteilung oder neue Werkzeuge ohne konkreten aktuellen Nutzen eingeführt.

## 5. Bereinigungsinventar und Löschungsnachweis

| Ort / Zweck | Evidenz, Referenzen und Risiko | Aktion / Auswirkung |
|---|---|---|
| `.claude/worktrees/agent-*`, alte Appkopien | Alle 212 Dateien mit kanonischen historischen Git-Blobs abgeglichen; vier Bäume identisch; keine Worktree-Registrierung, Paket-/Startreferenz. Niedriges Risiko | Bereits vom Nutzer committete Claude-Löschung erhalten: 90.472 duplizierte Zeilen entfernt; kein aktiver Einstieg verloren |
| `dialogue_translation_summary`, `canonical_page_evidence`, `LLMTransportModel`, `SCENARIO_SCHEMA_VERSION`, `_SAFETY_NON_ACUTE_CASES` | Claude-Diff und Referenzprüfung; keine Verwendung/Exporte im verbleibenden Repository. Niedrig | Übernommene fünf Definitionen und 17 ungenutzte Imports bleiben entfernt |
| `service.py`, interne Altfehlerzweige | Frühe Rückgabe bei Interpreterfehler macht spätere Behandlung unerreichbar. Niedrig | Interne Zweige vereinfacht; `CandidateSelector.interpreter_unavailable` und öffentliche Verträge bleiben |
| `dist/lena_code3-0.1.0.*` | Überholte regenerierbare, ignorierte Buildoutputs; keine Runtimeabhängigkeit. Niedrig | Bereits von Claude entfernt; vorhandene andere Buildoutputs nicht pauschal gelöscht |
| `.pytest_cache/`, `app/__pycache__/`, `app/providers/__pycache__/`, `tests/__pycache__/` | Von Tests/Syntaxprüfung regenerierbare Caches; keine kuratierten Ressourcen. Niedrig | Abschließende rekursive Löschung automatisch mit `blocked by policy` abgelehnt; ignorierte Caches bleiben erhalten |
| `tests/test_frontend_runtime.js` | Unversionierte Zwischenfassung dieses Reviews; alle fünf Fälle im dokumentierten `frontend.test.cjs`, dort zusätzlich TTS; keine Referenzen. Niedrig | Zwischenfassung entfernt, ein Testeinstieg erhalten |
| `lena_code3.egg-info/` | Metadaten der editierbaren Installation/Versionsermittlung. Mittleres Risiko | Behalten |
| `app/retrieval.py`, kompatible Env-Aliase/Methoden | Aktive Normalisierung, Tests, dokumentierte Kompatibilität. Mittleres Risiko | Behalten |
| `data/`, Paket-Bootstrap, Fixtures, Releases und Snapshots | Betrieb, Offlineinstallation, Hashbindung, Migration und Provenienz. Hohes Risiko | Vollständig erhalten; unterschiedliche Ressourcenrollen widerlegen pauschale Duplikatlöschung |
| `runtime/`, historische Pläne, Review-/Liveberichte, Backups, Git-Branches | Forschungs-/Betriebsdaten oder Entscheidungsverlauf. Hohes bzw. ungeklärtes Risiko | Behalten; kein Inhalt mangels offensichtlichem Import gelöscht |

## 6. Änderungen und Begründung

Die Befunde H1 und M1–M10 wurden in den vorhandenen Verantwortungsbereichen
korrigiert. Vorhandene Validatoren, Fehlerklassen, Sessionquarantäne,
Dialogzustände und Provideradapter werden wiederverwendet. Es gibt keine neuen
API-Endpunkte, Laufzeitmodule, Abhängigkeiten oder fachlichen Datenregeln.

`tests/frontend.test.cjs` ergänzt ausführbare Verhaltenstests mit eingebauten
Node-Werkzeugen. `MANIFEST.in` nimmt diesen Test ins Source-Archiv auf.
Tests ersetzen keine realen Browserprüfungen und sind ausdrücklich getrennt
von Pytest dokumentiert. Keine bestehende Assertion wurde abgeschwächt.

Dokumentation beschreibt nun tatsächliche Fallbackkontakte, TTS-Allowlist und
Format, Sprachstore 3 mit vier übersetzbaren Feldern, Evidence-Vertrag 3,
Retrybudget, sichere Offlinekonfiguration und den Unterschied zwischen
providerfreiem Dry-Run und historischen Live-Ergebnissen.

## 7. Prüfungen und Befehle

Alle Pytests verwenden die vorhandene HTTP-/Socket-Sperre und isolierte Runtime.
Die Befehle wurden im Checkout ausgeführt, soweit nicht anders angegeben.

| Prüfung | Ergebnis |
|---|---|
| Früher `python -m pytest` | Eigene Baseline: 754 bestanden; Claude berichtet ebenfalls 754 vorher/nachher |
| `python -m pytest tests/test_session_persistence.py tests/test_sessions.py -q` | 24 bestanden; vier neue Korruptionsfälle zuvor nachweislich fehlgeschlagen |
| `python -m pytest tests/test_candidates.py tests/test_dialogue.py tests/test_safety_policy.py tests/test_curation.py tests/test_public_toilets.py tests/test_drinking_fountains.py tests/test_translation_quality.py -ra` | 313 bestanden, 93,99 s |
| `python -m pytest tests/test_api.py tests/test_speech_transcription.py tests/test_provider_timeouts.py tests/test_request_boundaries.py tests/test_formulation.py tests/test_dialogue_frontend.py tests/test_frontend_security.py -ra` | 176 bestanden, 33,47 s |
| `python -m pytest tests/test_runtime_loader.py tests/test_wfs_releases.py tests/test_wfs_sync.py tests/test_translation_tokens.py tests/test_provider_isolation.py tests/test_observability.py tests/test_live_evaluation.py -ra` | 116 bestanden, 29,82 s; Live-Evaluation ausschließlich mit Doubles |
| `python -m pytest tests/test_speech_transcription.py -q` | Zehn erneut erfolgreich nach Testimportbereinigung |
| `node --test tests/frontend.test.cjs` | Sechs bestanden; ausgeführt über vorhandenes VS Code `Code.exe`, `ELECTRON_RUN_AS_NODE=1`, zusätzlich `--test-isolation=none` |
| `node --check app/static/app.js`, `node --check app/static/dialogue.js` | Beide erfolgreich über dieselbe Laufzeit |
| `python -m compileall -q app tests` | Erfolgreich |
| `python -m pip check` | Keine inkompatiblen installierten Anforderungen |
| `python -m app --version`, `python -m app --help` | Version 0.2.0 und unveränderte CLI-Optionen |
| `python -m build --no-isolation --outdir <audit>/final-dist` | Wheel und Source-Archiv erfolgreich; keine neuen Buildabhängigkeiten geladen |
| `python -m pip install --no-deps --no-index --target <audit>/wheel-install <wheel>` | Lokale Paketinstallation außerhalb Checkout erfolgreich; vorhandene Abhängigkeiten verwendet, kein vollständiger neuer Dependency-Install |
| `<audit>/verify-final.py` | Installiertes Appmodul, Factory/Lifespan, HTML/JS/Health/Speech-Konfiguration, fünf Sprachen und technischer Fallback erfolgreich; externe Sockets blockiert, temporäre Daten-/Runtimewurzeln |
| Paketvergleich | Wheel weiterhin 94 Dateien; alle 90 `app/`-Dateien vollständig und bytegleich zum finalen Checkout; keine `.env`, Runtime oder externen Daten im Wheel |
| Finales Source-Archiv | Enthält den neuen JS-Test und diesen Bericht; zusätzliche Dokumentations-/Testdateien erklären die Inventarerweiterung |
| `git -c core.safecrlf=false diff --check`, finaler manueller Diff | Keine Whitespacefehler; Änderungen den Befunden zugeordnet |

Einzige Pythonwarnung: bestehende Starlette-TestClient/httpx-Deprecation.
Keine Abhängigkeit allein zum Unterdrücken dieser Warnung ergänzt.
Ein erster temporärer Wheel-Smoke blockierte versehentlich auch die interne
Windows-Loopback-Socketpair-Verbindung. Nach Beschränkung der Sperre auf externe
Adressen bestand er; dies war ein Fehler der Audit-Harness, kein Appdefekt.

## 8. Erhaltung, Restrisiken und bewusste Grenzen

Entry Points, öffentliche Routen, Konfigurationsoptionen, Datenverträge,
Quellreleases, fünf Sprachen, Übersetzungs-/Safety-Texte und Paketressourcen
bleiben erhalten. Unterschiede betreffen belegte Defekte: ungültige Eingaben
führen kontrolliert in bestehende Fehlerpfade; gültige Folgedialoge und
Audio-Unterbrechung funktionieren wieder; Safety kann nicht über den
Selbstbeschreibungs-Shortcut umgangen werden.

Ein hashgleicher Datenbestand belegt unveränderte Inhalte, keine inhaltliche
Aktualität öffentlicher Angebote. Ebenso belegt die TTS-Mockkette die lokale
Verdrahtung, nicht die Erreichbarkeit von Edge oder eines konkreten API-Servers.
Diese Grenzen sowie der frühere mögliche Sessionverlust bleiben ausdrücklich
offen. Die Evaluationsrunner-Abweichung M11 wird nicht durch grüne Mocktests
als erledigt behandelt. Ein öffentlicher Mehrnutzerbetrieb und eine vollständige
Live-/Sprachfreigabe sind nicht Teil des verifizierten Ergebnisses.

## 9. Komplexitätsbilanz

**Architektur unverändert; Duplikation und einige interne Verzweigungen reduziert.**
Es bleiben 55 Python-Appmodule und dieselben sieben Laufzeitabhängigkeiten.
Keine neuen Frameworks, Schichten oder produktiven Schnittstellen. Claudes
übernommene Bereinigung entfernt 212 Altdateien und fünf tote Definitionen.
Der Zusatzreview entfernt unerreichbare interne Fehlerzweige und verwendet für
TTS einen gemeinsamen Abschlussweg.

Die aktiven Appdateien wachsen gegenüber `3433c7a` netto um **95 Zeilen**
(148 hinzugefügt, 53 entfernt): überwiegend belegte Validierung und Zustandsfixes.
Eine pauschale Verringerung der Codegröße wird deshalb nicht behauptet.
Zusätzliche Tests und Dokumentation erhöhen die Nachprüfbarkeit ohne neue
Laufzeitstruktur.

## 10. Finaler Git-Zustand und dateiweise Übersicht

Branch: `maintenance/repository-cleanup`. HEAD: `3433c7a`.
**33 geänderte versionierte Dateien, zwei neue Dateien, keine gestagten
Änderungen.** Kein eigener Commit, Push, Reset oder Eingriff in die Historie.
Die vom Nutzer zwischenzeitlich erstellten Cleanup-Commits bleiben bestehen.

| Datei (`M` geändert, `??` neu) | Änderung / Befund |
|---|---|
| M `MANIFEST.in` | JS-Verhaltenstest im Source-Archiv |
| M `README.md` | Tatsächliche Fallback-/TTS-Verträge, Evaluationsstatus, Berichtlink |
| M `app/candidates.py` | Deterministischer Zeitplan M3 |
| M `app/curation.py` | Unveränderliche ID-Bindung M4 |
| M `app/dialogue_flow.py` | Konsistente Alterskorrektur M2 |
| M `app/drinking_fountain_source.py` | Kontrollierte Grenzgeometrievalidierung M6 |
| M `app/i18n.py` | Sicherer Legacy-/Encodingfallback M8 |
| M `app/infrastructure.py` | CSV-Grenze M6 und fachlicher Diff M7 |
| M `app/main.py` | Tatsächliches Edge-Ausgabeformat L1 |
| M `app/providers/llm.py` | JSON-Wurzelprüfung M9 |
| M `app/service.py` | Safety-Shortcuts H1, tote Zweige L2 |
| M `app/sessions.py` | Isolierte Behandlung beschädigter Persistenz M5 |
| M `app/speech.py` | STT-Ergebnistyp M9 |
| M `app/static/app.js` | Sende-/Auswahlzustand M1, Audiofreigabe M10 |
| M `app/static/dialogue.js` | Folgedialoge und Busy-Erhalt M1 |
| M `docs/architecture.md` | Reale Reihenfolge, Releases, Retry und TTS |
| M `docs/configuration.md` | Fallback, Format und Bodylimit-Grenze |
| M `docs/data-flow.md` | Vertragsversionen, Übersetzungsfelder, Speech |
| M `docs/exec-plans/quality-review-2026-09.md` | Plan, Inventar, Entscheidungen und Abschluss |
| M `docs/live-provider-evaluation.md` | Explizite offene Runnergrenzen M11 |
| M `docs/safety-and-error-policy.md` | Shortcutbindung, Hilfebus ohne Marker, TTS |
| M `docs/setup.md` | Offlinebetrieb, Fallback und Paketbeschreibung |
| M `docs/testing.md` | Ausführbare JS-Tests und realistische Nachweisgrenzen |
| M `tests/test_api.py` | Ungültige LLM-Wurzeln und zehn Adapter-/Sprachfälle |
| M `tests/test_candidates.py` | Primärbedarf/Zeitplan M3 |
| M `tests/test_curation.py` | Vertauschte Quell-IDs M4 |
| M `tests/test_dialogue.py` | Altersfakten und vollständiger Dialog M2 |
| M `tests/test_drinking_fountains.py` | Acht defekte Geometrien M6 |
| M `tests/test_public_toilets.py` | Verkürzte CSV und präziser Recorddiff M6/M7 |
| M `tests/test_safety_policy.py` | Fünf Sprachen, gemischte Fragen, offene Safety H1 |
| M `tests/test_session_persistence.py` | Byteerhalt und unabhängige valide Sessions M5 |
| M `tests/test_speech_transcription.py` | Fünf ungültige JSON-Antworten M9 |
| M `tests/test_translation_quality.py` | Legacyfehler M8, konkrete Reviewassertion L3 |
| ?? `tests/frontend.test.cjs` | Sechs Offline-Verhaltenstests M1/M10 |
| ?? `docs/reviews/quality-review-2026-09.md` | Dieser Nachweisbericht |

Ignorierte lokale Konfiguration, Runtime, vorhandene aktuelle Buildoutputs und
Installationsmetadaten bleiben bewusst außerhalb des Git-Diffs erhalten.
