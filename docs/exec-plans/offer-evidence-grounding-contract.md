# Execution Plan: Angebotsgebundener Groundingvertrag

## Status

- State: Complete
- Owner: Codex
- Created: 2026-10-20
- Last updated: 2026-10-20

## Objective / Acceptance contract

- [x] Inhaltlich belegte Antworten scheitern nicht allein an führenden Nullen
  einer eindeutig zuordenbaren Angebots-ID oder ausgelassenen Faktzitaten.
- [x] Gegenprobe ist ausschließlich das vollständige Evidence-Paket desselben
  ausgewählten Angebots, niemals die gesamte Wissensbasis oder andere Angebote.
- [x] Unbekannte/mehrdeutige IDs und vorhandene falsche/fremde Faktreferenzen
  bleiben Fehler. Keine Änderungen der semantischen Bedeutung dezimaler IDs.
- [x] Unbelegte Leistungen, falsche Leistungs-/Preispaare, falsche Zielgruppen,
  Zusagen, Safety-Verstöße und tatsächlich falsche Werte bleiben abgewiesen.
- [x] Deklarierte Referenzen und geprüfter Angebotspool werden getrennt als
  interner Evaluationsnachweis ausgewiesen; keine erfundenen Modellzitate.
- [x] Neue Vertrags-/Promptversion, lokale Regression, Dokumentation.

## Scope

Nutzer hat am 20.10.2026 ausdrücklich diese Vertragsänderung freigegeben.
Keine Live-Aufrufe, keine Gateumgehung, keine historischen Berichtänderungen,
keine Thesisänderung oder Migration, keine Daten-/Modell-/Dependencyänderung,
keine neuen Retrys, Commits, Installationen oder Formatierungen.

## Repository review

Code sauber auf `3d8489d27dfa77df32a14b3934aaa54164b87a89`.
Thesis enthält zwei vorbestehende Änderungen (Approach/Solution), nicht berühren.
Keine AGENTS-/Contribution-Datei im Workspace bzw. den Eltern gefunden.
Python/FastAPI/Pydantic, setuptools, pytest; Netz-/Runtime-Isolation aus
`tests/conftest.py`, Cache und Bytecode unterbinden. Packaging ausnehmen.

### Tatsächlicher Pfad

Provider parst `FormulatorResponse` (Vertrag 2 / Prompt 18), danach
`validate_formulation`: strikte Referenzen → antwortweite zitierte Faktpools
je Angebot → Wert-/Zielgruppen-/Zeit-/Safetyprüfungen → kanonische Karten.
Fakt-ID-Pools sind bereits angebotsgebunden, aber nur deklarierte IDs zählen.
`ValidatedFormulation`/`ProviderAnswer` tragen bisher keine Referenzbewertung.
Stage-2-Runner kann interne Providerresultate erfassen; E2E verwendet bereits
den `LimitedEvaluationProvider` für interne Formulatorbeobachtungen.

Das gespeicherte `f_de_grounded` enthält einen korrekten Preis 2,50 € für
Wäschewaschen, dessen Fakt im übergebenen Paket vorhanden ist, sowie `07`
statt `7`. Der Bestand hat denselben Fingerprint wie der Lauf. Die frühere
Verwerfung bleibt unter dem damaligen Vertrag korrekt und unverändert.

### Wiederverwendung / Größenprüfung

- Vorhandene Wertprüfungen und `grounding_constraints.py` wiederverwenden.
- Referenzprojektion kohäsiv nach `grounding_references.py` extrahieren,
  statt das bereits 681-zeilige Groundingmodul um eine zweite Logik zu vergrößern.
- Faktpreisbindung zusätzlich absichern: bloße Zahlenmengen desselben Angebots
  reichen nicht, um Wäschepreis als Übernachtungspreis freizugeben.
- Bestehende Negativtests müssen nach neuem Vertrag fehlende Evidenz aus dem
  Paket entfernen, statt nur Faktzitate zu löschen. Assertions nicht streichen;
  positive Tests belegen ausdrücklich die neu erlaubte unvollständige Zitation.

## Dead-end analysis / Alternatives rejected

| Risiko / Alternative | Maßnahme / Nachweis |
|---|---|
| Nur Gate lockern | Laufzeitvertrag ändern; Gates bleiben gleich |
| Alle IDs numerisch parsen | nur ASCII-Ganzzahlstrings mit führenden Nullen, eindeutige Paketzuordnung; Kollisionen ablehnen |
| `7.10` zu `7.1` normalisieren | ausgeschlossen, IDs keine Fließkommazahlen |
| Ganze KB statt ausgewähltem Paket | Pools nur aus `selected_offers`, Cross-Offer-Tests |
| Unbekannte/fremde Fakt-IDs ignorieren | bestehende Referenzprüfung beibehalten |
| Gleicher Betrag bei anderer Leistung | relationaler Preisgegencheck; vertauschte Preise als Negativfälle |
| Nachträglich alle Fakten als Modellzitate ausgeben | deklarierte IDs und verfügbarer Prüfumfang getrennt ausweisen |
| Alte Berichte grün erklären | neue Semantik versionieren, alte Artefakte unverändert |

## Recommended approach / File impact

| Datei | Änderung |
|---|---|
| `app/grounding_references.py` | eindeutige ID-Projektion, Angebots-Faktpools, interne Referenzbewertung |
| `app/grounding.py` | bestehende Wertprüfung mit neuen Pools und kanonischer Antwort verdrahten |
| `app/grounding_constraints.py` | begrenzte Leistungs-/Preisbindung |
| `app/grounding_claims.py` | Modulbeschreibung auf übergebene statt nur zitierte Werte präzisieren; keine Logikänderung |
| `app/formulation.py` | Vertrag 3 / Prompt 19, neue Evidenzsemantik erläutern |
| `app/providers/llm.py` | interne Referenzbewertung an Ergebnis weitergeben |
| `app/live_evaluation_runner.py`, `app/live_evaluation_runtime.py` | Referenzbewertung in synthetischen Reports, turngebunden |
| betroffene Tests + `tests/test_offer_evidence_contract.py` | alte negative Fälle auf fehlende Paketevidenz umstellen; neue Positiv-/Negativfälle |
| bestehende Architektur-/Evaluationsdokumentation | aktuellen Vertrag und Grenzen beschreiben |

Keine öffentliche QueryResponse-/Interaktionsschemaerweiterung. Interne
Referenzbewertung nennt deklarierte IDs, kanonische Angebote und verfügbare
Fakt-IDs, nicht vermeintlich vollständig nachgewiesene semantische Quellen.

## Milestones / Validation plan

- [x] Review, Wiederverwendung, Risiken, Scope und Vertrag festlegen.
- [x] Regression/Altvalidator-Gegenprobe und neue Positiv-/Negativtests.
- [x] Implementieren und betroffene Tests mit beibehaltenen Assertions anpassen.
- [x] Gezielte Tests, breite Suite ohne Packaging, AST und Diffreview.
- [x] `code-documentation` anwenden; Pfade/Versionen und Grenzen abgleichen.

Umgebung: `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
`LENA_ENV_FILE_MODE=disabled`, `LENA_ALLOW_LIVE_SMOKE=false`.
`python -B -m pytest -p no:cacheprovider tests/test_offer_evidence_contract.py`
danach Grounding/Formulation/API/Live-Evaluation und gesamte Suite mit
`--ignore=tests/test_packaging.py`. Keine Installation, kein Live-Smoke.

## Rollback and recovery

Keine Datenmigration; inverse gezielte Patches nach Freigabe möglich.
Keine destruktiven Git-Befehle. Vor neuer Messung Nutzercommit erforderlich.

## Progress / Decision log / Discoveries

- 2026-10-20: Plan vor Quelländerung erstellt. Bewusste neue Anforderung,
  nicht rückwirkende Korrektur der Bewertung unter dem alten Vertrag.
- Referenzprojektion implementiert; neue Preisgegenproben zeigten zunächst
  falsche Freigaben vertauschter Beträge. Relationale Europreisprüfung vor
  breitem Testlauf ergänzt. Neue Datei mit 22 Fällen bestanden (3,47 s).
- Gezielte Grounding-/Formulationssuite: 258 bestanden, ein bekannter strict
  xfail, eine vorhandene Starlette-Deprecationwarnung (7,00 s).
- Erste breite Suite auf Zwischenstand: 1103 bestanden, ein Fehler durch eine
  verbliebene wörtliche Versionsassertion `2`, ein bekannter xfail (246,99 s).
  Assertion auf aktuelle Vertragskonstante umgestellt, nicht entfernt.
- Betroffener Berichtstest und finale Formulations-/Vertragstests erneut:
  155 bestanden, ein bekannter xfail, eine vorhandene Warnung (8,55 s).
  Finale breite Suite auf fertigem Code-/Teststand gestartet.
- Read-only Altvalidator-Gegenprobe: Kern aus `git show HEAD:app/grounding.py`
  nur im Arbeitsspeicher geladen. Bei denselben geparsten synthetischen
  Objekten verwirft er fehlendes Faktzitat mit `formulator_ungrounded_claim`
  und führende Null mit `formulator_invalid_fact`; neuer Kern akzeptiert beide.
  Zwei vorbereitende Probeaufrufe scheiterten vor der Validierung an einem
  unvollständig konstruierten Test-Evidence-Objekt; anschließend mit gültigem
  Policybaustein ausgeführt. Keine Datei- oder Providerwirkung.
- `code-documentation` angewendet: Architektur, Datenfluss und Evaluations-
  dokumentation auf Vertrag 3 / Prompt 19 und Referenzbewertung abgeglichen;
  historische Berichte/Pläne nicht umgedeutet. Retryhinweise konsistent auf
  bereitgestellte Evidenz ausgerichtet. Keine neue reguläre Log-/API-Persistenz.
- AST aller 98 Pythondateien und `git diff --check` bestanden. Neue
  Referenzprojektion 47 Zeilen, Preis-/Relationsmodul 223, neue Tests 187;
  bestehendes Groundingmodul durch kohäsive Extraktion auf 640 Zeilen reduziert.
  Große Provider-/Runnerdateien nur am vorhandenen Ergebnisweg ergänzt.
- Finale breite Suite: 1112 bestanden, ein bekannter strict xfail, eine
  vorhandene Starlette-Deprecationwarnung, 266,45 s. Keine unerwarteten Fehler.
  Abschlussstatus: 21 beabsichtigte Code-/Test-/Dokumentationsdateien geändert
  oder neu; keine Commits. Die zwei vorbestehenden Thesisänderungen unberührt.

## Final verification summary

Selbstreview gemäß `REVIEW_TEMPLATE.md`: korrekter realer Provider-/Validator-
Pfad, keine KB-Ausweitung, keine toten Helfer oder Dependencyänderungen.
Interne Antwortkopie wahrt Originalzitate. Referenzqualität wird als Prüfumfang
ausgewiesen, nicht als nachträglich erfundene tatsächliche Zitation. Die
vorhandenen Referenz-, Rollen-, Namen-, Restriktions-, Safety- und Grenztests
bleiben erhalten; geänderte negative Fixtures entfernen Evidenz statt nur
Zitate. Neue kanonische Karten-IDs gelangen bis zum Providerergebnis; beide
synthetischen Berichtspfade auf Metadaten geprüft. Keine Gate-/Retryänderung.
Dokumentationspfade und Versionswerte gegen Konstanten geprüft.

Alle lokalen Akzeptanzpunkte belegt. Finale breite Suite 1112 bestanden,
ein bekannter strict xfail, eine vorhandene Warnung. Packaging wegen Build-/Installations-
artefakten ausgenommen. Kein Linter/Typechecker in pyproject eingerichtet;
keine Nachinstallation oder Formatierung. Thesis unverändert.
Restrisiko: heuristisches Grounding ist kein allgemeiner Entailmentnachweis;
Preisbindung ist auf erkannte Euro-/Leistungsrelationen begrenzt. Vollständige
Verfügbarkeit aller Evidenzfakten ist nicht dasselbe wie vollständig belegte
semantische Ableitung. Kein Erfolg einer Live-Evaluation aus lokalen Tests
ableiten; neue versionierte Messung erst nach Nutzercommit.
