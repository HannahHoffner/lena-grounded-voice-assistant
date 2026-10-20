# Execution Plan: Begrenzte Grounding-Fehlalarme

## Status

- State: Complete
- Owner: Codex
- Created / Last updated: 2026-10-20

## Objective / acceptance contract

- [x] Belegtes Imbiss-/Mittagessen wird als Essenskonzept erkannt.
- [x] Russische фонтан-Formen werden im belegten Trinkbrunnenpaket geprüft,
  ohne dekorative Brunnen oder bloße Namen zu Trinkwasserbelegen zu machen.
- [x] Die belegte polnische Facility „bez barier“ negiert nicht die Toilettenleistung;
  fehlende Facilitybelege, echte Leistungsverneinungen und mehrdeutige Koordination bleiben sichtbar.
- [x] „tel.“ vor einer Telefonnummer ist kein Satzbruch; echte Mehrsatztexte bleiben ungültig.
- [x] Lokale Positiv-/Negativtests und vollständige Regression; kein Live-Aufruf.

## Scope

Vier nachgewiesene lexikalische Groundingprobleme; keine Prompt-, Enum-, Safety-,
Retrieval-, Daten-, Preis-, Karten- oder Gateänderung, keine Thesis, kein Commit.
Hilfebus-Claimtyp und nicht akute Domänenabweisung bleiben getrennte Folgethemen.
Nach lokalem Replay zusätzlich in scope: rein typografische Klammer-/Komma-
Äquivalenz des verpflichtenden Gebührenliterals. Keine Änderung von Betrag,
Zahlungsbedingungen oder Leistungs-/Preiszuordnung.

## Repository review

Python/FastAPI/Pydantic, setuptools, pytest (pyproject.toml); Netzwerksperre und
Runtimeisolation in tests/conftest.py. Keine AGENTS-Dateien im Workspace/code.
Arbeitsbaum bereits mit neun Dateien der freigegebenen Runnerkorrektur dirty;
alle diese Änderungen erhalten. Thesis nur vorbestehende Approach-/Solutionänderungen.

Provider → FormulatorResponse → grounding.validate_formulation → pro Angebot
gebundene Evidence → grounding_claims/grounding_constraints → Antwort/Fallback.
Servicewörter werden am Wortanfang gesucht; Imbiss und Mittagessen fehlen.
Russisch фонтан fehlt, bezeichnet aber ohne Datenkontext nicht zwingend Trinkwasser.
has_negation erkennt jedes „bez“; facility „bez barier“ hat einen anderen Bezug.
_contains_sentence_break kennt tel. nicht. Die gespeicherten E2E-Verwerfungen
aus run_2cba16fac8834b18a206d1dabe9ffaba belegen diese Pfade.

### Reuse / affected files

| Pfad | Vorhaben / Risiko |
|---|---|
| app/grounding_claims.py | Essensstämme und kontextgebundene russische Brunnenprüfung; begrenzt |
| app/grounding_constraints.py | vorhandene Audience-Maskierung um gemeinsame, beleggebundene Qualifier-Projektion ergänzen; begrenzter Gebührenliteral-Vergleich |
| app/grounding.py | Projektion in Claim und Beleg anwenden; Telefonabkürzung; Validatorversion |
| app/live_evaluation_plan.py | Validatorversion in Dry-Run und Manifest ausweisen |
| tests/test_grounding_lexical_boundaries.py | neue fokussierte Positiv-/Negativtests mit realem Validator |
| tests/test_live_evaluation.py | Manifest-Versionsnachweis, vorhandene Runneränderung erhalten |
| docs/live-provider-evaluation.md | aktuelle Grenzen/Fixes dokumentieren, historische Diagnose erhalten |

Große bestehende Groundingdateien werden nur an kanonischen Prüfstellen erweitert;
kein Parallelvalidator, keine sachfremde Dateiaufteilung. Bestehende Hilfsfunktionen
und Fixtures in tests/test_grounding_claims.py werden genutzt.

## Dead ends / alternatives rejected

| Ansatz | Problem | Gewählter Nachweis |
|---|---|---|
| Negationsprüfung abschalten | Unbelegte Verneinungen akzeptiert | nur vollständig belegtes Facility-Literal maskieren |
| Jede фонтан-Nennung als Trinkwasserbeleg | Zierbrunnen werden potable | nur Claim erkennen; typed potable_water_status=verified und vorhandener Leistungsbeleg erforderlich |
| Essen als beliebigen Teilstring finden | ungewollte Treffer | begrenzte zusätzliche Wortanfangsstämme |
| tel. generell von Satzprüfung ausnehmen | Mehrsatzumgehung | nur vor Ziffer / internationaler Nummer |
| Alte Messung nachträglich grün rechnen | Evidenzverlust | historische Reports unverändert; neue Validatorversion im Manifest |

## Milestones

- [x] Review, Risiken und Plan vor Codeänderung.
- [x] Reproduzierende Tests zunächst gegen alten Validator ausführen.
- [x] Begrenzte Umsetzung und Gegenproben.
- [x] Vollständige Regression, AST / git diff --check und Selbstreview.
- [x] code-documentation nach Implementierung anwenden.

## Validation plan

python -B -m pytest -p no:cacheprovider tests/test_grounding_lexical_boundaries.py
und bestehende Grounding-/Formulator-/Live-Evaluationsprüfungen, danach gesamte
pytest-Suite, JUnit extern. Kein Cache/Bytecode oder produktiver Transport.
Bestehende ID-/Fakten-/Preis-/Zielgruppen-/Zeit-/Safety-Negativtests müssen bestehen.
Lokale Wiedergabe ist keine neue Live- oder vollständige semantische Evaluation.

## Rollback / recovery

Nur reviewbare Quelldiffs; keine Migration oder Datenänderung. Neue Hunks getrennt
von vorbestehender Runnerkorrektur rücknehmbar; nichts automatisch zurücksetzen.

## Progress / decisions / discoveries

- Plan nach Review gespeichert; konkrete Negationsausnahme bleibt evidenzgebunden.
- Red-Nachweis vor Codeänderung: nach Korrektur zunächst unvollständiger
  Testreferenzen 17 fehlgeschlagene / sieben bestandene neue Fälle auf altem
  Validator. Danach vier Fixes zunächst mit 24 bestandenen Fällen bestätigt.
- Voller Satzpfad benötigt Telefonnummer vor Satzgrenzprüfung: sonst wird
  belegtes „tel. 0800 ... .“ durch Literalentfernung zu „tel. .“. Sprachprüfung
  entfernt bekannte Literale weiterhin vollständig; Zahlenprüfung bleibt aktiv.
- Nach 400 bestandenen Zieltests / einem bekannten xfail zeigt gespeicherter
  Toilettenversuch 2 nun REQUIRED_FEE_MISSING statt Satzgrenzenfehler:
  „50 centów, gotówka lub karta“ statt „50 centów (gotówka lub karta)“.
  Das ist ein zusätzlicher Darstellungsfehler; begrenzte Normalisierung nur von
  Klammern und nicht dezimalen Kommas, mit vollständigem Wort-/Betragserhalt.
- Schema und Prompt unverändert. Neue Grounding-Validatorversion 1 bezeichnet
  erstmals explizit diesen im Manifest ausgewiesenen Prüfstand; alte Manifeste
  ohne dieses Feld werden nicht umgeschrieben.
- Zielprüfung nach allen Korrekturen: 409 bestanden, ein bekannter strict xfail,
  eine bestehende Deprecationwarnung in 28,99 s. Neuer Testumfang: 37 Fälle.
- Erneute providerfreie Wiedergabe der zwei Wasser- und zwei Toilettenoutputs
  im echten QueryService-Evidencepfad: alle vier Validatorprüfungen bestehen.
  Die ursprünglichen Reports unverändert; keine neue Live-Messung oder Aussage
  über vollständige semantische Validität dieser Modelltexte.
- code-documentation nach Implementierung angewandt: vorhandene
  docs/live-provider-evaluation.md um die fünf begrenzten Regeln und separate
  Validatorversion ergänzt. Historische Diagnose und Runnerkorrektur erhalten.

## Final verification summary

- Zielprüfung: 409 bestanden, ein bekannter strict xfail, eine bestehende
  Starlette-Deprecationwarnung in 28,99 s. 37 neue Positiv-/Negativfälle.
- Gesamtsuite: `python -B -m pytest -p no:cacheprovider
  --junitxml=C:/Users/User/AppData/Local/LENA/evaluations/20261020-fa670f4/grounding-lexical-engineering-results.xml`:
  1178 bestanden, ein bekannter strict xfail, eine vorhandene Warnung, 250,67 s.
  Testtransporte gesperrt; Bytecode-/pytest-Cacheerzeugung unterbunden.
- AST aller 59 app-Pythondateien gültig; git diff --check bestanden mit den
  vorhandenen Git-LF/CRLF-Hinweisen. Keine Formatter/Installationen ausgeführt.
- Dry-Run providerfrei ausgeführt: versions.grounding_validator=1; Manifestfeld
  durch Test bestätigt. Unveränderter Formulatorvertrag 3 / Prompt 19.
- Lokaler Replay der vier gespeicherten Wasser-/Toilettenoutputs bestanden;
  kein Provideraufruf und keine Neubewertung des historischen Runs.
- Selbstreview nach REVIEW_TEMPLATE: Begrenzung auf canonical Groundingpfad,
  vorhandene Strukturen erweitert, neue Helfer tatsächlich aufgerufen, keine
  neue Datenquelle oder globale Freigabe von Fakten. Gegenproben zu fehlender
  Evidenz, Status, Negation, Koordination, Telefonnummer, Zweitsatz, Betrag und
  Zahlungsbedingungen bestehen. Bisherige ID-/Preis-/Safetytests bestehen.
- Bestehende große Dateien grounding.py (653) / grounding_claims.py (645) nur
  an ihren zentralen Prüfstellen erweitert; gemeinsame Projektion/Formatprüfung
  in grounding_constraints.py (253). Keine sachfremde Modulaufteilung.
- Dokumentation: code-documentation angewandt, vorhandene
  docs/live-provider-evaluation.md erweitert und gegen tatsächliche Bedingungen
  geprüft. Historische Reports und vorbestehende Runnerkorrektur erhalten.
- Kein Build/Packaging oder Browser-/Sprach-Livelauf; keine Paket-/Schemaänderung.
- Thesis unverändert, code enthält noch die vorbestehenden Runneränderungen
  sowie diese Groundingkorrektur; keine Commits erstellt.
- Grenzen: begrenzte lexikalische Prüfung, kein vollständiges semantisches
  Entailment. Zusätzliche Aussagen wie kostenloser Kaffee sind durch einen
  akzeptierten Replay nicht als wahr oder vollständig belegt nachgewiesen.
  Hilfebus-Claimtyp, fehlende Domänenpflichtinhalte, nonacute-Routing und
  Interpreter-Enumfehler bleiben getrennte offene Aufgaben. Kein neues
  bestandenes Live-E2E-Gate behauptet.
