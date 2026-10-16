# Execution Plan: Zitierte Zielgruppe vor einer zweiten Leistung abgrenzen

## Status

- State: Complete
- Owner: Codex
- Created: 2026-10-16
- Last updated: 2026-10-16

## Objective

Der Grounding-Prüfer akzeptiert die gespeicherte, belegte rumänische
CABL-Antwort aus dem synthetischen Lauf, ohne echte Leistungsnegationen oder
nicht zitierte Zusätze durchzulassen. Die Korrektur gilt für die bestehende
fünfsprachige Hilfsfunktion, nicht nur für eine Szenario-ID.

## Acceptance contract

- [x] Gespeicherten dreisätzigen Fall `f_ro_grounded` mit denselben Fakten
  providerfrei über den echten Validator und die Provider-Validierungsgrenze
  reproduzieren; Regression vor dem Fix rot, danach grün.
- [x] Eine vollständig zitierte Zielgruppenphrase darf vor einer koordinierten,
  separat zitierten positiven Leistungsphrase maskiert werden. Der nachfolgende
  Leistungstext bleibt für alle vorhandenen Prüfungen sichtbar.
- [x] Ohne unabhängigen zitierten Leistungsbeleg, bei abweichender Zielgruppe
  oder bei echter Leistungsnegation keine solche Präfixmaskierung.
- [x] Vollständige Zielgruppenphrasen mit mehreren fehlenden Dingen behalten
  Vorrang; `and`/`und`/entsprechende Konjunktionen allein sind keine Grenze.
- [x] Kontrollen für DE/EN/PL/RO/RU und den tatsächlichen negativen Leistungspfad.
- [x] Keine Änderung an Fakten, Szenarien, Prompts, Modellen, Gateformeln,
  Abbruchgrenzen, Dependencies oder alten Reports; kein Commit oder Live-Lauf.

## Scope

In scope: `service_text_without_cited_audience`, Regressionen und bestehende
Architekturdokumentation. Out of scope: allgemeine semantische Inferenz, neue
LLM-Stufen, Wissensbasiskorrekturen, finale Thesis-Ergebnisse und erneute Messung
auf dem ungecommitteten Stand. Die bisherigen Thesis-Änderungen bleiben erhalten.

## Repository review

Ausgangspunkt: `b82530fd43cdb6fa013725e55e5b5f038af9134e`, Branch
`maintenance/repository-cleanup`, sauberer Code-Arbeitsbaum. Thesis enthält die
vorhandenen Änderungen in `4Approachneu.tex` und `5Solutionneu.tex`. Keine
anwendbaren AGENTS-Dateien gefunden. Python >=3.11, FastAPI/Pydantic,
setuptools, pytest; keine zusätzlichen Werkzeuge erforderlich.

### Current behavior and data flow

`BlabladorProvider.formulate_answer` validiert strukturierte Antworten mit
`grounding.validate_formulation`. `_validate_sentence` übergibt ausschließlich
die angebotsgebundenen zitierten Fakten an
`grounding_constraints.service_text_without_cited_audience`. Dessen Regex
erfasst eine Zielgruppe bis zum Satzzeichen und maskiert nur bei vollständiger
Übereinstimmung mit einer zitierten Zielgruppenphrase.

Im Lauf `run_e9efd98a70594db9bd43fef3c6e9fe36` umfasst der Satz die zitierte
Zielgruppe und anschließend `și emitere de fișe de tratament anonime`. Der
Regex erfasst beides als Zielgruppe. Die Zeichenfolge stimmt dadurch nicht
mehr mit der ersten Quelle überein; `fără` bleibt sichtbar und löst in
`grounding.py:521` die Negationsabwehr aus. Die lokale Reproduktion auf dem
gebundenen Bestand liefert zuvor `ClaimSupport.SUPPORTED` für beide Leistungen.

### Existing structures to reuse

| Structure | Path | Decision |
| --- | --- | --- |
| Fünfsprachige Zielgruppenmaskierung | `app/grounding_constraints.py` | Kanonische Funktion begrenzt erweitern |
| Negationsprüfung und belegbare Faktentypen | `grounding_constraints.py`, `grounding_claims.py` | Bestehende Definitionen verwenden |
| Angebotsgebundener Zitierpool | `app/grounding.py` | Unverändert; keine Suche im ganzen Bestand |
| `_answer`, `_fact`, `_diagnostic`, `app` | `tests/test_grounding_claims.py` | Bestehende Fixtures/Builder wiederverwenden |
| Echter Provider mit gemocktem `_post` | `tests/test_grounding_constraints.py` | Muster für gespeicherten neuen Regressionstest |

Die neue kohäsive Testdatei betrifft nur Zielgruppenkoordination; die bestehende
Constraint-Datei würde mit der zusätzlichen Sprach-/Negativmatrix zu groß.
Kein zweiter Validator oder paralleler Anwendungspfad wird eingeführt.

## Dead-end analysis

| Potential dead end | Evidence / impact | Mitigation / verification |
| --- | --- | --- |
| Bei jeder Konjunktion abschneiden | Kann zwei Dinge trennen, die der Zielgruppe fehlen | Nur vollständigen, separat zitierten positiven Leistungssuffix erkennen; Gegenfälle |
| Zitiertes Präfix überall entfernen | Würde unbelegte Fortsetzungen verdecken | Unabhängige vollständige Suffixübereinstimmung und Wortgrenze verlangen |
| Negative Fakten als Suffixbeleg nutzen | Könnte Negation aus dem Leistungsnachweis entfernen | Positive Leistungsfakten prüfen; Gegenkontrolle mit negativer Quelle |
| Aus ganzen KB statt Zitierpool belegen | Würde fehlende Fakt-IDs verbergen | Unveränderter Aufrufvertrag; Entzug eines Zitats muss zur Verwerfung führen |
| Rumänisches Einzelwort aus Negationsliste löschen | Würde echte Verneinung zulassen | Negationsliste und abschließende Abwehr unverändert lassen |
| Gates lockern oder sofort live wiederholen | Messstand wäre verändert, nicht eingefroren | Nur lokale Regression; neuer Commit durch Nutzer vor neuer Messreihe |

## Recommended approach

Vollständige exakte Zielgruppenübereinstimmung zuerst beibehalten. Zusätzlich
ein bekanntes Zielgruppenpräfix nur dann abgrenzen, wenn die gesamte restliche
Phrase aus einer sprachpassenden Konjunktion und einem unabhängig zitierten,
nicht negierten Leistungswert besteht. Nur das Präfix maskieren. Die
Leistungsfortsetzung und jede übrige Negation bleiben sichtbar. Listenmarker
werden ausschließlich beim Vergleich des separaten Leistungswerts entfernt.

## Alternatives rejected

| Alternative | Reason |
| --- | --- |
| Szenario-, Angebots- oder Wortlautausnahme | Würde nur den beobachteten Fall überanpassen |
| Allgemeines Satzparser-/LLM-System | Unverhältnismäßig; zusätzliche Inferenz und Abhängigkeit |
| Promptänderung, damit das Modell anders formuliert | Behebt nicht die Fehlklassifikation einer bereits belegten Ausgabe |

## File impact

| File | Action / reason | Risk |
| --- | --- | --- |
| `app/grounding_constraints.py` | Begrenzte Ergänzung der vorhandenen Maskierung | Mittel; Negationsschutz erhalten |
| `tests/test_grounding_audience.py` | Gespeicherter Fall und Sprach-/Negativmatrix | Klein |
| `docs/architecture.md` | Tatsächliche Abgrenzungsregel dokumentieren | Klein |
| Dieser Plan | Nachweise und Restgrenzen | Klein |

## Milestones

1. [x] Aufrufpfad, gespeicherten Fall, Helper, Tests und Risiken prüfen.
2. [x] Regressionen hinzufügen und rote Fälle nachweisen.
3. [x] Kleine Implementierung, gezielte und breitere Regressionen.
4. [x] `code-documentation` auf finalen Diff anwenden; bestehende Doku ergänzen.
5. [x] Selbstreview, Syntax und Git-Diff; Hand-off zur erneuten Versionierung.

## Validation plan

| Check | Method | Expected result |
| --- | --- | --- |
| Rote Regression | Neue Audience-Tests vor dem Fix | Positiver kombinierter Fall scheitert |
| Gezielte Prüfung | Audience-, Constraint-, Claims- und Formulation-Tests | Keine neuen Fehler; bekannten strict xfail separat benennen |
| Breiter Lauf | `python -B -m pytest -p no:cacheprovider --ignore=tests/test_packaging.py` | Keine Regression, keine produktiven Aufrufe |
| Statisch | AST-Parse ohne Imports; `git diff --check` | Erfolgreich |
| Isolation | `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, Env-Datei deaktiviert, Live-Flag false | Bestehende Transportblockade und temporäre Test-Runtime |

Packaging/Installationen werden nicht ausgeführt. Keine JUnit-/Cache-/Bytecode-
Artefakte im Repository erforderlich. Keine automatischen Reparaturen.

## Rollback and recovery

Keine Datenmigration, Löschung, Umbenennung oder öffentliche API-Änderung.
Der begrenzte uncommittete Diff bleibt einzeln prüfbar; kein automatisches
Zurücksetzen fremder Änderungen. Alte Messberichte bleiben unverändert.

## Progress and decisions

- 2026-10-16 — Review abgeschlossen, Plan vor der Codeänderung angelegt.
- 2026-10-16 — Vor dem Fix: 7 rote Positivregressionen und 16 bestandene
  Negativ-/Grenzkontrollen. Danach zusätzliche direkte Validatorprüfungen für
  alle fünf Sprachen ergänzt. Gezielter Lauf: 217 bestanden, 1 bekannter
  strict xfail, 1 vorhandene StarletteDeprecationWarning (2,48 s).
- 2026-10-16 — Breiter providerfreier Lauf ohne Packaging: 1040 bestanden,
  1 bekannter strict xfail (`minor injuries`), 1 vorhandene
  StarletteDeprecationWarning, 215,29 s. Keine neuen Fehler.
- 2026-10-16 — `code-documentation` auf Implementierung und Prüfnachweise
  angewandt; bestehende Regelbeschreibung in `docs/architecture.md` ergänzt.
  Gegen Implementierung, Aufrufpfad und negative Kontrollen abgeglichen.
- 2026-10-16 — Alle 94 Pythondateien unter `app`/`tests` per AST ohne
  Anwendungsimporte erfolgreich geprüft; `git diff --check` erfolgreich.
- Die Fortsetzung ist nur über zitierte Fakten entscheidbar. Grammatik außerhalb
  dieser engen Regel bleibt eine ausdrücklich begrenzte Heuristik.

## Final verification summary

- Akzeptanzvertrag: erfüllt. Der gespeicherte dreisätzige Fall besteht direkt
  und über die echte Provider-Validierungsgrenze mit lokal gemocktem Transport.
  Die neue Testdatei umfasst 28 Fälle; sprachübergreifende Kontrollen prüfen
  echte Negation, fehlende/unpassende Belege und koordinierte Mangelangaben.
- Regressionen: 217 gezielt beziehungsweise 1040 im breiten Lauf bestanden;
  jeweils der unveränderte strict xfail und die vorhandene Warnung separat.
- Statisch: Syntaxprüfung und Whitespace-Diff erfolgreich. Kein Linter oder
  Typechecker konfiguriert/ausgeführt, keine Dependencies installiert.
- Selbstreview: kanonischer Aufrufpfad beibehalten, keine parallele
  Implementierung, keine öffentliche API-Änderung. Die Constraint-Datei bleibt
  deutlich unter 400 Zeilen. Negationsliste und weitere Grounding-Schritte
  unverändert; keine Ausnahme für Sprache, Angebot oder Szenario-ID.
- Dokumentation: Endzustand und Grenzen in bestehender Architekturdatei
  beschrieben, keine spekulativen Fähigkeiten ergänzt.
- Restgrenzen: weiterhin eine lexikalisch begrenzte Heuristik, kein allgemeiner
  semantischer Wahrheitsbeweis. Keine Packaging-/Installationsprüfung und keine
  neuen Live-Aufrufe. Änderungen uncommitted auf Basis `b82530f`; erneute
  Versionierung durch den Nutzer vor der nächsten Messreihe erforderlich.
- Thesis: keine Änderungen in diesem Korrekturpaket. Die zwei bereits
  vorhandenen geänderten Kapitel bleiben unberührt. Frühere Live-Reports
  behalten ihre Commitbindung und ihr gescheitertes Gate.
