# Execution Plan: Belegte Zeitliterale ohne Darstellungsmarker

## Status

- State: Complete
- Owner: Codex
- Created: 2026-10-19
- Last updated: 2026-10-19

## Objective / Acceptance contract

- [x] Gespeicherte russische UVO-Antwort mit `18:30 ч. Hauptbahnhof`
  besteht die reale Validierung ohne Textänderung.
- [x] Bei Öffnungs-/Standzeiten darf ausschließlich der führende Marker `> `
  des Evidence-Werts entfallen; der verbleibende Text muss vollständig passen.
- [x] Echte zusätzliche Sätze sowie abweichende/unbelegte Zeit-/Ortsangaben
  bleiben verworfen. Keine globale Abkürzungsausnahme.
- [x] Providerpfad mit gemocktem Transport sowie lokale Regression geprüft.
- [x] Prompts, Modelle, Verträge, Gates, Fallbacks und Quellbestände unverändert.

## Scope

Nur freigegebene Korrektur des nachgewiesenen False Positive und ihre Tests/
Dokumentation. Keine Live-Aufrufe, keine Messwiederholung, keine Thesisänderung,
keine Abhängigkeiten, Installation, Paketierung, Commits oder Formatierungen.

## Repository review

Stand `8ea4f3750cc88879bc862fae44e9111660ac7951`, Code sauber.
Thesis hat zwei vorhandene Änderungen (Approach/Solution); nicht berühren.
Keine AGENTS-/Contribution-Anweisung im Workspace oder den Eltern gefunden.
Python/FastAPI/Pydantic, setuptools; pytest mit vorhandener Netz-/Runtime-
Isolation aus `tests/conftest.py`. Keine zusätzlichen Tools erforderlich.

### Datenfluss und bestätigte Ursache

`BlabladorProvider.formulate_answer` → `validate_formulation` →
`_validate_sentence` → `_strip_evidence_literals` und `_contains_sentence_break`.
Die Literalprojektion wird auch von der Sprachprüfung verwendet. Sie entfernt
Namen/Kontakte/Zeitliterale nur für interne Proseprüfungen, nicht aus der Ausgabe.
Grounding-/Referenzprüfungen sehen weiterhin den unveränderten Antworttext.

Lauf `run_16e1cc0d11a44b27ab6cf3e728148922`, Fall `f_ru_grounded`:
Der belegte Wert `> Среда: 18:30 ч. Hauptbahnhof` enthält schon das Stundenkürzel.
Die Antwort `Среда: 18:30 ч. Hauptbahnhof.` lässt nur den Präsentationsmarker weg.
Die bisherige Literalmaske verlangt ihn, danach zählt die lateinisch begrenzte
Abkürzungsheuristik `ч.` als Satzbruch. Ein Provider-freier Evidence-Aufbau mit
dem aktuellen Bootstrap bestätigt genau diesen Wert und dieselben Fakt-IDs.
Es ist keine neue russische Abkürzungsgrammatik nötig: das vollständige Literal
ist bereits vertrauenswürdig belegt.

### Wiederverwendung

| Struktur | Entscheidung |
|---|---|
| `app/grounding.py::_strip_evidence_literals` | vorhandene exakte Maske für Zeitliterale ergänzen |
| `_contains_sentence_break`, Grounding-/Referenzprüfungen | unverändert lassen |
| Testfixture `_settings`, `_answer`, `app` aus bestehenden Tests | wiederverwenden |
| bestehender UVO-Bestand und Übersetzungskatalog | Originalpfad für Regression, keine Datenänderung |

## Dead-end analysis / Alternatives rejected

| Ansatz / Risiko | Auswirkung | Entscheidung / Nachweis |
|---|---|---|
| `ч` global in Abkürzungsliste aufnehmen | mögliche echte Satzgrenze hinter Stundenangabe verborgen | verworfen; vollständiger Evidence-Text nötig |
| Alle kurzen Wörter/alle Punkte erlauben | Mehrsatzvertrag wirkungslos | verworfen; bestehende Satzprüfung erhalten |
| Marker oder Kürzel im Output/Bestand entfernen | Mess-/Quelltext manipuliert, nur Fall kaschiert | verworfen; interne Projektion korrigieren |
| Beliebige Satzteile/Marker streichen | unbelegte Fortsetzung könnte verschwinden | nur `> ` am Anfang von opening_time/stand_time; exakter Rest |
| Nur isolierte Regex testen | echter Provider-/Validatorpfad ungeprüft | gespeicherte Antwort vollständig und Provider mit Mocktransport prüfen |

## File impact / Recommended approach

| Datei | Aktion / Grund |
|---|---|
| `app/grounding.py` | ergänzende Literale nur für markierte Öffnungs-/Standzeiten |
| `tests/test_grounding_schedule_literals.py` | positive, negative und gespeicherte vollständige Regression |
| `docs/architecture.md` | genaue Reichweite der beleggebundenen Maske dokumentieren |
| dieser Plan | Review, Fortschritt, Prüfnachweise |

Das große bestehende Groundingmodul wird nur im kohäsiven vorhandenen Helper
ergänzt. Keine neue konkurrierende Sprach-/Satzsegmentierung oder breite
Aufteilung kurz vor der Messung.

## Milestones

- [x] Review, tatsächlichen Fehlerpfad und Wiederverwendung prüfen.
- [x] Regression vor Änderung reproduzieren.
- [x] Kleine Implementierung und gezielte Tests.
- [x] Breite Tests ohne Packaging, AST und Diffreview.
- [x] `code-documentation` auf finalen Diff anwenden; bestehende Doku abgleichen.

## Validation plan

Umgebung: `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
`LENA_ENV_FILE_MODE=disabled`, `LENA_ALLOW_LIVE_SMOKE=false`.

- `python -B -m pytest -p no:cacheprovider tests/test_grounding_schedule_literals.py --tb=short`
- `python -B -m pytest -p no:cacheprovider tests/test_grounding_schedule_literals.py tests/test_formulation.py tests/test_grounding_claims.py tests/test_grounding_constraints.py tests/test_grounding_audience.py --tb=short`
- `python -B -m pytest -p no:cacheprovider --ignore=tests/test_packaging.py --tb=short`
- AST aller Pythondateien, `git diff --check`, abschließender Status.

## Rollback and recovery

Keine Migration oder Quell-/Konfigurationsänderung; gezielter inverser Patch
nach Freigabe möglich. Keine destruktiven Git-Befehle. Historische Berichte
bleiben unverändert und das gescheiterte Gate wird nicht umgedeutet.

## Progress / Decision log

- 2026-10-19: Plan vor Implementierung erstellt. Die zusätzliche Untersuchung
  präzisiert die frühere Diagnose: fehlende Marker-Normalisierung belegter
  Zeitliterale, nicht das Fehlen einer globalen russischen Kürzelliste.
- Vor Änderung: neues Testmodul 12 fehlgeschlagen / 14 bestanden; darunter
  tatsächliche gespeicherte Antwort im Validator und im Providerpfad.
- Nach Änderung: gezielte Suite 243 bestanden, ein bekannter strict xfail,
  eine vorhandene Starlette-Deprecationwarnung, 2,83 s. Neue Datei: 26 Fälle.
- AST aller 96 Pythondateien erfolgreich. AST-Diff der Groundingfunktionen
  bestätigt ausschließlich `_strip_evidence_literals` als geändert.
  Groundingmodul 681 Zeilen, nur neun Ergänzungszeilen im vorhandenen Helper;
  Testmodul 132 Zeilen. Keine zusätzliche Segmentierungsabstraktion nötig.
- `code-documentation` angewendet: bestehende Architektur um genaue interne
  Projektion, vollständigen Literalabgleich und Grenzen ergänzt. Keine neue
  Konfiguration, öffentlichen Schnittstellen oder spekulativen Funktionen.
  Testpfad, FactType-Namen und konkrete Beispiele geprüft.
- `git diff --check` bestanden; breite Tests laufen noch. Nutzeränderungen
  in der Thesis unverändert. Keine Live-Aufrufe oder Commits.
- Breite Suite abgeschlossen: 1089 bestanden, ein bekannter strict xfail,
  eine vorhandene Starlette-Deprecationwarnung, 225,56 s. Finales neues
  Testmodul nach Assertion-Review erneut geprüft: 26 bestanden (0,90 s).
  Abschlussstatus: ausschließlich vier geplante Dateien geändert/neugefügt;
  Thesis weiterhin nur mit den beiden vorbestehenden Änderungen.

## Discoveries / Final verification summary

Finaler Selbstreview anhand `REVIEW_TEMPLATE.md`: keine parallele
Implementierung, neun Codezeilen im realen Provider-/Validatorpfad, keine
neue API/Abhängigkeit oder ungenutzte Symbole. Positive Fälle in fünf Sprachen
für beide Faktarten; negative Fälle für andere Faktarten/Marker, fehlende
Referenz, geänderten Ort/Zeit und tatsächliche Zusatzsätze. Satzsegmentierer
selbst unverändert. Keine Lockerung der Gateformeln. Die vollständige
Originalantwort bleibt in der Ausgabe erhalten; keine Rohdatenkorrektur.

Alle lokalen Akzeptanzpunkte belegt; breite Suite 1089 bestanden / ein
bekannter strict xfail, keine unerwarteten Fehler. Packaging wegen Build-/
Installationsartefakten nicht ausgeführt. Kein Linter/Typechecker in pyproject konfiguriert; keine
Installation und keine Formatierung. Grenze: nur vollständige Zeitliterale
werden geschützt; abweichende Paraphrasen/andere unbelegte Abkürzungen bleiben
unberücksichtigt. Lokale Tests beweisen keinen erfolgreichen neuen Live-Lauf.
