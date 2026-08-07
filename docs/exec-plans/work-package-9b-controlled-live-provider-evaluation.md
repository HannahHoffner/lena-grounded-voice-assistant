# Arbeitspaket 9B: kontrollierte Live-Provider-Evaluation

## Status

- State: Complete
- Status: preparation_only
- live_provider_calls_authorized: false
- Owner: Codex
- Created: 2026-08-03
- Last updated: 2026-08-03

## Objective

WP9B bereitet eine reproduzierbare, vierstufige Evaluation der real
konfigurierten Blablador-Modelle ausschließlich mit synthetischen Eingaben vor.
Dieser Vorbereitungsschritt erzeugt Schutzmechanismen, versionierte Erwartungen,
providerfreie Tests und einen vollständigen Dry-Run. Er startet keine Live-Stufe
und führt keine LLM-, STT-, TTS- oder Quelldatenprovideraufrufe aus.

## Acceptance contract

- [x] Reale LLM-, STT-, TTS-, WFS-, Toiletten- und Trinkbrunnenaufrufe bleiben null.
- [x] Vier Stufen sind versioniert und können einander niemals automatisch starten.
- [x] Stufe 1 enthält genau 15 Interpreterfälle: drei je Sprache, ohne Selector,
  Formulator, STT, TTS oder End-to-End-Pfad.
- [x] Jeder Live-Aufruf erfordert Unterbefehl, exakte Stufe, `--confirm-live`,
  `LENA_ALLOW_LIVE_SMOKE=true` und alle sieben expliziten Laufgrenzen vor dem
  Laden von Settings oder Initialisieren eines Providers.
- [x] Szenarien, Erwartungen und Bewertungsfelder sind vor einer Modellantwort
  versioniert, gehasht und als ausschließlich synthetisch gekennzeichnet.
- [x] Providerpayloads bleiben auf die vorhandenen positiven Transportmodelle
  für Interpreter, Selector und Formulator beschränkt.
- [x] Laufzähler, Zeitgrenze, Fehlergrenze und atomare Reportpersistenz verhindern
  unkontrollierte Fortsetzung und erzeugen keine Anwendungssessions oder
  Interaktionsprotokolle.
- [x] Der Dry-Run lädt keine normalen Settings, initialisiert keinen Provider/HTTP-Client,
  schreibt keine Laufdatei und verändert keine Runtimepointer.
- [x] Reports liegen ausschließlich unter dem ignorierten Pfad
  `runtime/live-evaluations/<opaque-run-id>/` und enthalten keine Secrets.
- [x] Pytest, Packaging und CI können keinen Live-Lauf implizit auslösen.
- [x] Technische, regelbasierte fachliche und menschlich-linguistische Bewertung
  bleiben getrennt; keine Produktiv-, SAFE-, klinische oder Sprachfreigabe wird behauptet.
- [x] WP9A, fachliche Runtime-Daten, Thesis und Präsentation bleiben unverändert;
  kein nachfolgendes Arbeitspaket wird begonnen.

## Scope

### In scope

- Bestandsaufnahme von Konfiguration, drei LLM-Verträgen, Prompts, Budgets,
  Providergrenzen, Szenarien, Logging und Datenschutz.
- Versionierter WP9B-Szenario-/Erwartungskatalog und Bewertungsvertrag.
- Vier strikt getrennte Stufenpläne, Call-/Zeitabschätzung und Abbruchkriterien.
- Dreifache Live-Freigabe plus stufenspezifische und explizite harte Limits.
- Atomare Zähler und lokale, ignorierte, redigierte Laufreports.
- Providerfreier Dry-Run, Payloadinventar aller aktuellen Runtimequellen und Tests.
- Unmittelbar betroffene Betriebs-, Test- und Architekturdokumentation.

### Out of scope

- Ausführung irgendeiner Live-Stufe oder Änderung der realen Modellkonfiguration.
- Reale Nutzereingaben, Sessions, Interaktionsprotokolle oder Sprachaufnahmen.
- Prompt-, Vertrags-, Grounding-, Candidate-, Safety- oder Fachregelverbesserungen.
- STT-/TTS-Evaluation, Hörprüfung, naturalistische Evaluation oder Produktivfreigabe.
- Thesis, Präsentation, WP10 oder andere nachfolgende Arbeitspakete.

## Repository review

### Current behavior

- Branch `maintenance/repository-cleanup`, HEAD
  `9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`; der vollständige uncommittete
  WP1–WP9A-Stand gehört der Nutzerin. Es existiert keine `AGENTS.md`.
- `app.multilingual_review` besitzt `export` und `live-smoke`. Live erfordert
  bereits Unterbefehl, `--confirm-live` und `LENA_ALLOW_LIVE_SMOKE=true` vor
  `load_settings()`, startet danach aber alle Szenarien End-to-End. Stufen,
  explizite Calllimits, Fehlerlimit, dauerhafter atomarer Report und
  Abbruchmanifest fehlen.
- `tests/conftest.py` entfernt Providerumgebung, deaktiviert `.env`-Ladung und
  blockiert nichtlokale HTTP-/Sockettransporte suiteweit.
- Alle drei LLM-Stufen verwenden `Settings.blablador_model` und damit aktuell
  dasselbe Modell `alias-fast`; getrennte Modellfelder existieren nicht.
  Die sichere Allowlist-Prüfung liest nur Provider-, Modell-, Basis-URL-, Timeout-
  und Tokenlimitnamen; von der URL wird ausschließlich der Hostname
  `api.blablador.fz-juelich.de` ausgegeben. Keys, Header, Pfade, Queryparameter
  und sonstiger `.env`-Inhalt bleiben ungelesen beziehungsweise unveröffentlicht.
- Aktiv sind Interpreter Vertrag/Prompt `3/4`, Selector `1/1`, Evidence `3`,
  Formulator Vertrag/Prompt `2/4`, Candidatevertrag `2` und Safety-Policy `1`.
- Providerparameter: `temperature=0`, `response_format=json_object`, maximal
  700/300/800 Tokens mit der aktuellen `BLABLADOR_MAX_TOKENS=800`-Konfiguration.
- Stufentimeouts sind mangels abweichender sicher gelesener Konfiguration
  15/10/30 Sekunden; das monotone End-to-End-Budget beträgt 45 Sekunden.
- Der vorhandene dynamische Katalog enthält 16 Szenarien in fünf Sprachen; der
  Safety-Katalog enthält 19 fünfsprachige Gruppen. Beide sind synthetisch, aber
  noch kein stufenspezifischer WP9B-Erwartungs- und Abbruchvertrag.
- Laufzeitdaten unter `runtime/` sind bereits vollständig durch `.gitignore`
  ausgeschlossen. Der bisherige Live-Smoke nutzt ein temporäres Runtimeverzeichnis
  und deaktiviert Interaktionslogging, schreibt aber nur einen einzelnen Export.

### Relevant architecture and data flow

`python -m app.multilingual_review` parst derzeit den Unterbefehl, prüft beim
Live-Smoke die zwei Freigaben, ruft `load_settings()` auf, lädt die kuratierte
Runtime-KB und erstellt `QueryService`. `BlabladorProvider` baut drei strikt
getrennte JSON-Payloads und validiert die Antworten durch Pydantic plus ID- und
Groundingregeln. `QueryService` erzwingt für End-to-End-Anfragen das monotone
45-Sekunden-Budget. WP9B setzt vor Settings/Provider eine zusätzliche
stufenspezifische Plan- und Limitgrenze und persistiert ausschließlich
synthetische Evaluationsergebnisse in einem separaten Store.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| CLI und bestehendes Live-Gate | `app/multilingual_review.py` | Unterbefehl erhalten, um Stufe, Dry-Run und explizite Limits erweitern |
| Drei Providerverträge | `app/providers/llm.py` | unverändert ausführen; keine tolerantere Testparserlogik |
| Positivlisten | `InterpreterUserPayload`, `SelectorUserPayload`, `FormulatorEvidence` | Feldinventar direkt aus Modellen ableiten und vollständig prüfen |
| Runtime-KB/Fingerprint | `app/kb_loader.py` | read-only für Manifestidentität und kuratierte Fixtures verwenden |
| Globales Budget | `app/llm_budget.py` | im End-to-End-Pfad unverändert erzwingen |
| Atomarer JSON-Write | `app/i18n.py::write_json` | für einzelne JSON-Dateien wiederverwenden; JSONL atomar ersetzen |
| Szenariokataloge | `dynamic_scenarios.json`, `safety/scenarios.json` | Erwartungen referenzieren, nicht nach Modellantwort mutieren |
| Netzwerksperre | `tests/conftest.py` | beibehalten und um WP9B-Umgebungsnamen erweitern |

### Existing tests and commands

- `tests/test_provider_isolation.py`: `.env`-Isolation, Transportblock und
  bisherige Freigabekombination.
- `tests/test_translation_quality.py`: synthetischer Export, Katalog und alter Live-Smoke.
- `tests/test_interpreter.py`, `tests/test_llm_selection.py`,
  `tests/test_formulation.py`, `tests/test_safety_policy.py`: Einzelverträge.
- `tests/test_packaging.py`: Wheel/sdist, sdist→Wheel, Clean-Install und Template-Smoke.
- Vor WP9B sind 616 Tests grün; WP9A dokumentiert null Provideraufrufe.

### Working tree considerations

Der Git-Diff gegen HEAD kombiniert WP1–WP9A mit 44 bereits getrackten
Änderungen sowie zahlreichen neuen Dateien. Er ist kein isolierter WP9B-Baseline-
Diff. WP9B führt deshalb ein eigenes Datei-/Hunkinventar im Progress Log; keine
vorhandene Änderung wird zurückgesetzt, gelöscht oder breit formatiert.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Alten End-to-End-Live-Smoke nur um `--stage` ergänzen | `run_live_smoke()` iteriert immer `QueryService.query()` | Stufe 1 könnte Selector/Formulator starten | eigener stufenspezifischer Runner; Interpreter direkt aufrufen | Fake zählt je Stufe exakt |
| Dry-Run über `load_settings()` | Funktion lädt `.env` und `.env.local` | Secrets werden unnötig eingelesen, Provider könnte initialisiert werden | reine allowlistbasierte redigierte Plankonfiguration ohne Settings | Monkeypatch lässt `load_settings`/Provider hart scheitern |
| Nur `--confirm-live` plus Env behalten | vorhandenes Gate kennt keine Stufe/Limits | Tippfehler oder zu großer Lauf startet unkontrolliert | Stage-Enum und sieben zwingende Limitflags vor Settings | Parser-/Gate-Tests |
| Kumulativen Zähler erst nach Aufruf erhöhen | Providertransport kann vor Limitprüfung beginnen | Calllimit wird überschritten | atomare Reservierung vor jedem Request/Providerawait | Parallel-/Grenztest |
| Szenarioerwartungen aus Modellantwort ableiten | bisheriger Export enthält nur grobe Erwartungen | Ground Truth wird nachträglich angepasst | versionierter, gehashter Katalog mit required/allowed/forbidden | Hash-/Immutabilitätstest |
| Modellrohausgaben in normale Logs schreiben | QueryService hat Interaktionslogging | synthetische Runs vermischen sich mit Forschungspfad | eigener Laufstore, eigene Runtime, Interaktionslogging aus | Pfad-/Dateiinventartest |
| Alle Stufen mit einer Freigabe ausführen | alter Smoke hat nur einen Live-Modus | automatische Eskalation von Kosten/Datenumfang | jede CLI-Ausführung akzeptiert exakt eine Stufe und endet danach | Dispatchtest |
| Kosten schätzen ohne Preisquelle | Repository enthält keine belastbare Preistabelle | erfundene Kostenaussage | Calls/Tokens/Zeiten ausweisen, Kosten als nicht bestimmbar markieren | Dry-Run-Snapshot |
| Automatische Kriterien als Sprachfreigabe ausgeben | bisherige Reviewmodelle trennen manuell/technisch | methodisch falsche Aussage | `technically_valid` und `linguistic_review_pending` getrennt | Schema-/Reporttest |

## Recommended approach

Vier kohäsive Module trennen deklarative Verträge/Katalog, providerfreie
Planung/Manifest, atomare Laufzeitgrenzen/Reports und den isolierten Stufe-1-
Runner. Sie laden einen paketierten WP9B-Katalog und erstellen ohne normale
Settings einen redigierten Dry-Run. `app.multilingual_review`
bleibt der einzige öffentliche CLI-Einstieg und prüft alle Freigaben und Limits,
bevor Settings oder Provider erreichbar sind. Stufe 1 ruft ausschließlich
`interpret_query()` auf; weitere Stufen besitzen eigene Dispatchgrenzen und
können niemals aus einer vorigen Stufe heraus gestartet werden.

## Fixed evaluation plan

| Stufe | Szenarien/Requests | geplante Calls | Providerwartezeit | harte Gesamtlaufzeit | Fehlerabbruch |
|---|---:|---:|---:|---:|---:|
| `interpreter` | 15 / 15 | exakt 15 Interpreter | 225 s | 300 s | beim 3. technischen/vertraglichen Fehler; Erfolg nur bei 0 |
| `selector-formulator` | 16 / 16 | 6 Selector + 10 Formulator | 360 s | 480 s | beim 3. Fehler; Erfolg nur bei 0 Vertragsfehlern |
| `end-to-end` | 27 Abläufe / höchstens 33 Requests | mindestens 30 I + 4 S + 10 F = 44; höchstens 99 | höchstens 1.485 s | 1.900 s | beim 4. kritischen Fehler |
| `stability` | 6 Abläufe × 3 Wiederholungen = 18 Requests | mindestens 18 I + 6 S + 15 F = 39; höchstens 54 | höchstens 810 s | 1.050 s | beim 3. kritischen Fehler |

Die maximale Providerwartezeit nutzt je isoliertem Call das Stufentimeout und je
End-to-End-Request höchstens das globale 45-Sekunden-Budget. Deterministische
Verarbeitung kommt zur realen Wandzeit hinzu und wird durch die separate harte
Gesamtlaufzeit begrenzt. Kosten sind ohne belastbare Providerpreisdaten nicht
bestimmbar; WP9B erfindet keinen Preis.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Neue eigenständige CLI | würde den vorhandenen Review-/Live-Einstieg duplizieren |
| Stufenspezifische Modellkonfiguration ergänzen | Vorbereitung darf reale Konfiguration nicht verändern; aktuell nutzen alle Stufen dasselbe Modell |
| Live-Gate nur dokumentieren | technische Fehlbedienung bliebe möglich |
| Vollständige Rohantwort immer speichern | für valide strukturierte Resultate unnötig und erhöht Datenumfang |
| Zusätzlicher „Test“-Hinweis im Systemprompt | verfälscht das zu evaluierende reale Verhalten |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/live_evaluation.py` | Create | Stage-, Limit-, Szenario- und Bewertungsverträge | mittel |
| `app/live_evaluation_plan.py` | Create | redigierte Konfigurationssicht, Payloadinventar, Dry-Run und Manifest | mittel |
| `app/live_evaluation_runtime.py` | Create | atomare Laufzähler und getrennter Reportstore | klein |
| `app/live_evaluation_runner.py` | Create | ausschließlich isoliertes Interpreter-Vertragsgate | mittel |
| `app/multilingual_review.py` | Modify | einziger CLI-Dispatch, Gate vor Settings, keine automatische Folgestufe | mittel |
| `app/resources/bootstrap/evaluation/live_scenarios.json` | Create | versionierte synthetische Erwartungen aller vier Stufen | deklarativ |
| `tests/test_live_evaluation.py` | Create | Plan, Limits, Store, Manifest, Dry-Run, Payloadinventar, Fake-Runner | hoch |
| `tests/test_provider_isolation.py`, `tests/conftest.py` | Modify | dreifache/stufenspezifische Freigabe und Netzwerksperre | mittel |
| `tests/test_packaging.py` | Modify | neue Paketressource und providerfreier CLI-Smoke | klein |
| `README.md`, `docs/setup.md`, `docs/testing.md`, `docs/configuration.md` | Modify | WP9B-Grenzen, Befehle, Reports und keine Produktivfreigabe | mittel |
| `docs/live-provider-evaluation.md` | Create | vollständige technische Betriebs- und Freigabeanleitung | mittel |
| dieser Plan | Create/Update | Reviewnachweis und Abschlussstatus | Dokumentation |

## Milestones

### Milestone 1: Review and design

- [x] Skills, Templates, Repository, Status, Diff, Dokumentation und Anweisungen prüfen.
- [x] Verträge, Prompts, Budgets, Providerinitialisierung und `.env`-Semantik verfolgen.
- [x] Bestehende Live-Gates, Netzwerksperre, Szenarien, Reviews, Logging und Datenschutz prüfen.
- [x] Dead Ends, feste Stufen und Dateiauswirkung dokumentieren.

Evidence: Tabellen und Pfade oben; ausschließlich allowlistbasierte Ausgabe
nicht geheimer Konfigurationsfelder, keine Providerinitialisierung.

### Milestone 2: Implementation

- [x] Versionierte Evaluationsmodelle, Katalog und Bewertungen implementieren.
- [x] Gate, Limits, atomare Zähler, getrennten Store und Redaktion implementieren.
- [x] Vollständigen providerfreien Dry-Run und Payloadinventar implementieren.
- [x] Providerfreie Tests ergänzen und Plan mit tatsächlichen Werten aktualisieren.

### Milestone 3: Verification

- [x] Fokussierte Live-Runner-, Gate-, Netzwerk-, Manifest- und Dry-Run-Tests ausführen.
- [x] Vollständige Suite und `compileall` ausführen.
- [x] Wheel/sdist, sdist→Wheel, Clean-Install und Template-Smoke prüfen.
- [x] Vollständigen Dry-Run ausführen und Dateibaum/Nebenwirkungsfreiheit prüfen.
- [x] Finalen Diff nach `REVIEW_TEMPLATE.md` und `git diff --check` prüfen.

### Milestone 4: Documentation

- [x] `code-documentation` auf den finalen WP9B-Diff anwenden.
- [x] Befehle, Limits, Datenschutz und Bewertungsgrenzen gegen Code und Tests prüfen.
- [x] Betroffene Prüfungen nach Dokumentation wiederholen.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Gate/Runner | `python -m pytest tests/test_live_evaluation.py tests/test_provider_isolation.py -q` | jede Stufe isoliert; fehlende Freigabe/Limit stoppt vor Settings |
| Verträge/Payloads | fokussierte Interpreter-/Selector-/Formulator-/KB-Tests | nur positive Transportfelder, keine Roh-/Excluded-Daten |
| Dry-Run | `python -m app.multilingual_review live-dry-run --stage all` | vier Pläne, null Writes, null Provider/HTTP |
| Full suite | `python -m pytest -q` | vollständig grün, null externe Transporte |
| Syntax | `python -m compileall -q app tests` | Exit 0 |
| Packaging | `python -m build`; `tests/test_packaging.py` | Ressource in sdist/Wheel, sdist→Wheel/Clean-Install grün |
| Diff | `git diff --check` plus Hunkreview | keine Fremdhunks oder Whitespacefehler |

## Rollback and recovery

Die Vorbereitung verändert keine fachlichen Runtime-, Quellen- oder
Providerdaten. Der Live-Store wird erst nach vollständiger Autorisierung unter
dem bereits ignorierten Runtimepfad erzeugt und schreibt Manifest/Resultate
atomar. Ein Abbruch erhält einen abgeschlossenen redigierten Report; keine Stufe
wird fortgesetzt. WP9B kann durch Rücknahme ausschließlich der hier
inventarisierten Hunk-/Dateimenge entfernt werden, ohne WP1–WP9A zu berühren.

## Progress log

- 2026-08-03 — Skills und Reviewtemplates vollständig gelesen; Arbeitsbaum,
  Branch, HEAD, vollständiger Diff und fehlende `AGENTS.md` geprüft.
- 2026-08-03 — Drei Verträge/Prompts, Providerpayloads, Timeouts/Budget,
  `.env`-Ladung, Live-Gate, Netzwerksperre, 16 dynamische und 19 Safety-Szenarien
  sowie Review-/Loggingpfade read-only rekonstruiert.
- 2026-08-03 — Nicht geheime Allowlistkonfiguration ergibt Provider Blablador,
  effektives gemeinsames Modell `alias-fast`, maximal 800 Tokens; keine Secrets gelesen.
- 2026-08-03 — Plan als erste WP9B-Datei mit `preparation_only` und
  `live_provider_calls_authorized: false` angelegt.
- 2026-08-03 — Vier Stufen, 58 synthetische Szenarien, vorab gebundene
  Erwartungen, Positivlisteninventar, Gate, atomare Grenzen, redigierter
  Reportstore und isolierter Interpreterrunner implementiert. Die 27
  End-to-End-Fälle enthalten die vollständige neun Klassen umfassende
  Safety-Matrix.
- 2026-08-03 — Vollständiger Dry-Run ausgeführt: Status
  `prepared_not_executed`, Szenariohash
  `4e0c9de9e8877086b7c93b68ac3c2a5e9e98ffe0d1aaa29db4cf58b3ce383fe2`,
  26 soziale Angebote, 21 Toiletten und 21 Trinkbrunnen; Runtime- und
  Arbeitsdateibaum davor/danach identisch; Provideraufrufe 0.
- 2026-08-03 — Fokussierte Gate-/Runner-/Providerisolations-/Packagingtests
  sowie die vollständige Suite mit 640 Tests bestanden. `compileall`, Wheel,
  sdist, Wheel-Neubau aus sdist, Clean-Install, providerfreier Template-Smoke
  und `git diff --check` bestanden. Node.js war nicht verfügbar; deshalb keine
  zusätzliche `node --check`-Ausführung.
- 2026-08-03 — Technische Betriebsdokumentation mit `code-documentation`
  erstellt; alter pauschaler Live-Smoke durch stufen- und limitgebundene
  Anleitung ersetzt. WP9B bleibt `prepared_not_executed`.

## Decision log

- Decision: Stufe 1 läuft direkt gegen `interpret_query()`, nicht über `QueryService`.
  - Context: QueryService kann bei normalen Ergebnissen Selector und Formulator starten.
  - Choice: isolierter Interpreterrunner mit demselben Providervertrag und Prompt.
  - Consequences: exakt 15 Calls sind technisch erzwingbar; keine End-to-End-Aussage.
- Decision: Live-Limits sind zwingende CLI-Werte und kataloggebundene Obergrenzen.
  - Context: implizite Defaults können bei Fehlbedienung einen größeren Lauf erlauben.
  - Choice: alle sieben Limits vor Settings verlangen und gegen den Stufenplan prüfen.
  - Consequences: der spätere Freigabebefehl ist länger, aber vollständig auditierbar.
- Decision: Dry-Run verwendet eine reine redigierte Allowlistkonfiguration.
  - Context: Modellkennung, Timeouts und die erwartete Ziel-Domain sind für den
    Schutz gegen Konfigurationsabweichung relevant; API-Key und URLdetails nicht.
  - Choice: nur erlaubte Namen lesen, von der URL ausschließlich den Hostnamen
    ableiten und nie `load_settings()` oder Provider aufrufen.
  - Consequences: Live-Gate kann Modell und Zielhost vor Providerinitialisierung
    binden, ohne Secrets, Pfade oder Queryparameter offenzulegen.

## Discoveries

- `BLABLADOR_MODEL` hat im bestehenden Loader Vorrang vor `LENA_LLM_MODEL`;
  damit ist trotz beider vorhandener Namen effektiv `alias-fast` aktiv.
- Der globale Budgetpfad misst kumulierte tatsächliche Providerwartezeit, nicht
  deterministische Verarbeitung; WP9B benötigt deshalb zusätzlich eine harte
  Wandzeitgrenze je Lauf.
- Der vorhandene Export speichert synthetische Inputs und Modelloutputs, besitzt
  aber keine opake Run-ID oder getrennte Manifest-/Result-/Fehlerdateien.
- `.gitignore` deckt `runtime/live-evaluations/` bereits über `runtime/` ab;
  eine zusätzliche Ignore-Regel wäre redundant.
- Der vollständige Dry-Run inventarisiert 26 soziale Angebote, 21 Toiletten und
  21 Trinkbrunnen beim Runtime-Fingerprint
  `3883c64cc74d24433ccdef191f29c0233de3c95237101d982d92abb1947e05f0`.

## Final verification summary

- Acceptance requirements: erfüllt; Status bleibt `preparation_only`, Live
  bleibt nicht autorisiert und keine spätere Stufe ist automatisch erreichbar.
- Tests: 640 vollständig grün; fokussierte Gate-, Limit-, Netzwerk-, Manifest-,
  Redaktions-, Dry-Run-, Packaging- und Clean-Install-Prüfungen enthalten.
- Build: Wheel und Source Distribution erfolgreich; Wheel aus sdist neu gebaut
  und außerhalb des Checkouts installiert; Template-Smoke erfolgreich.
- Manual verification: vollständiger providerfreier Dry-Run und finaler
  Diff-/Hunkreview abgeschlossen; Provideraufrufe 0; keine Thesis- oder
  Präsentationsdatei verändert.
- Documentation: Betriebsanleitung, Setup, Test- und Konfigurationshinweise auf
  dem finalen Code-/Katalogstand; Status `prepared_not_executed`.
- Residual risks: reale Modell-, Klassifikations- und Sprachqualität bleibt
  absichtlich ungeprüft; Stufen 2–4 sind nur geplant und technisch gesperrt;
  Kosten sind mangels belastbarer Preisquelle nicht bestimmbar; Node.js war
  nicht verfügbar und die tatsächliche linguistische Qualität erfordert
  weiterhin menschliche Prüfung.
