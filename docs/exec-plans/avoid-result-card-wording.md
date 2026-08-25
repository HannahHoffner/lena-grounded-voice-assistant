# Execution Plan: Verständliche Verweise auf weitere Informationen

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-25
- Last updated: 2026-08-25

## Objective

Nutzerseitige Antworten verweisen nicht mehr auf abstrakte Ergebnis-„Karten“
oder die Übersichtskarte als Informationscontainer. Stattdessen verwenden sie
in allen fünf Sprachen eine einfache räumliche Orientierung wie „Mehr Infos
stehen unten.“

## Acceptance contract

- [x] Allgemeiner, Organisations-, Toiletten- und Wasserfallback vermeiden
  sichtbare Card-/Karten-/Map-Verweise in allen fünf Sprachen.
- [x] Der deutsche allgemeine Fallback endet mit „Mehr Infos stehen unten.“
- [x] Dynamische Formulatorantworten dürfen nicht auf Ergebnis-Cards als Ort
  weiterer Angaben verweisen.
- [x] Die echte Kartenüberschrift, Karten-ARIA-Beschreibung und der operative
  Zahlungsfakt „mit Karte“ bleiben unverändert.
- [x] Textressourcen bleiben ehrlich `review_pending` beziehungsweise `machine`.
- [x] Providerfreie Fokus- und Gesamttests bestehen.

## Scope

### In scope

- versionierte UI-/Dialog-/Fallbackressource und Kopierversion
- Formulatorprompt und Promptversion
- unmittelbar zugehörige Ressourcen-, Prompt-, API- und Packagingtests
- bestehende technische Dokumentation

### Out of scope

- API-Felder `cards`/`card_ids`, Angebotsdarstellung und Mapfunktion
- operative Fakten wie Kartenzahlung
- fachliche Auswahl, Wissensbasis und Übersetzungsfreigabe
- reale Provideraufrufe, Thesis und Präsentation

## Repository review

### Current behavior

`fallback.found` sagt auf Deutsch „Die genauen Angaben stehen in den Karten.“;
die vier Zielsprachen verwenden dieselbe Card-Metapher. Drei weitere sichtbare
Ressourcen verweisen auf „Karte/Card/Map“: die bedingte Organisationsantwort
sowie zusätzliche Toiletten- und Wasserergebnisse. Formulatorprompt 14 verbietet
interne IDs, aber nicht den sprachlichen Verweis auf Ergebnis-Cards.

### Relevant architecture and data flow

`app/application_texts.py` lädt genau eine schema- und versionsvalidierte
Ressource für Backend und Frontend. `QueryService` verwendet die vier
betroffenen Resource-IDs in Template-, Dialog-, Toiletten- und Wasserpfaden.
Dynamische Antworten laufen getrennt über den Formulatorprompt und dessen
Groundingprüfung.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| zentrale Anwendungstexte | `app/resources/bootstrap/i18n/application_texts.json` | bestehende IDs aktualisieren |
| strikte Textversion | `app/application_texts.py` | Copyversion erhöhen |
| Formulatorprompt | `app/formulation.py` | UI-Metapher ausdrücklich vermeiden |
| Ressourceninventartests | `tests/test_translation_quality.py` | sichtbare Texte sprachübergreifend prüfen |
| API-/Packagingtests | `tests/test_api.py`, `tests/test_packaging.py` | Version und realen Fallbackpfad absichern |

### Existing tests and commands

- `python -m pytest -q tests/test_translation_quality.py tests/test_formulation.py tests/test_api.py tests/test_dialogue.py tests/test_packaging.py`
- `python -m pytest -q`
- `python -m compileall -q app tests`
- `git diff --check`

### Working tree considerations

Der Arbeitsbaum enthält die unmittelbar vorher freigegebenen, noch nicht
committeten Prompt-3/14-Änderungen. Sie werden erhalten und nur dort erweitert,
wo diese Aufgabe dieselben Prompt- und Dokumentationsstellen betrifft. HEAD ist
`e63ff4529a179fec8486db7b9e4ecb73c706fbfc` auf
`maintenance/repository-cleanup`.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| nur deutschen Fallback ändern | dieselben vier IDs existieren in fünf Sprachen | Sprachwechsel zeigt alte Metapher | alle Inventare gemeinsam versionieren | Ressourceninventartest |
| jedes Vorkommen von „Karte“ entfernen | UI bezeichnet eine echte Leaflet-Karte; Toiletten kennen Kartenzahlung | fachlich falsche oder unzugängliche Texte | nur Ergebniscontainer-Verweise ändern | gezieltes Inventar |
| nur Ressource ändern | LLM kann dieselbe UI-Metapher frei erzeugen | dynamischer Pfad bleibt inkonsistent | Formulatorprompt ergänzen | Prompttest |
| Begriff lexikalisch im Grounding sperren | „mit Karte zahlen“ ist ein belegter operativer Fakt | legitime Toiletteninformation würde verworfen | kontextbezogene Promptregel statt globalem Regex | Groundingregression |

## Recommended approach

Anwendungstextversion 8 ersetzt die vier sichtbaren Containerverweise durch
kurze lokalisierte „unten“-Formulierungen und lässt Reviewstatus unverändert.
Formulatorprompt 15 untersagt Verweise auf result cards beziehungsweise UI-
Container, erlaubt aber belegte operative Bedeutungen wie Kartenzahlung.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Frontendtext nachträglich ersetzen | würde TTS, Sessiontext und API-Antwort auseinanderlaufen lassen |
| neue Resource-ID | bestehende IDs bilden bereits exakt die vier Pfade ab |
| globaler Wortfilter | kann fachlich richtige Kartenzahlung nicht unterscheiden |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/resources/bootstrap/i18n/application_texts.json` | Modify | fünfsprachige Texte und Version 8 | klein |
| `app/application_texts.py` | Modify | Copyversion 8 | klein |
| `app/formulation.py` | Modify | Prompt 15 | klein |
| relevante Tests | Modify | Versions-, Inventar- und Fallbackregression | klein |
| bestehende Architektur-/Datenfluss-/Evaluationdocs | Modify | aktive Versionen und Wortwahl | klein |
| dieser Plan | Create/Update | Review- und Prüfnachweis | klein |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Vier zentrale Resource-IDs decken alle sichtbaren problematischen
Fallback-/Dialogverweise ab; echte Map- und Zahlungsbedeutungen sind getrennt.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

Evidence: Copyversion 8, Formulatorprompt 15 und vier lokalisierte Resource-IDs
sind begrenzt geändert. Die Vollsuite deckte einen zunächst entfallenen
Zugangshinweis auf; dieser wurde vor Abschluss in allen Sprachen erhalten.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run integration/build checks where relevant.
- [x] Verify providerfreien Versionspfad.
- [x] Review final diff.

Evidence: 173 fokussierte Tests sowie die vollständige Suite bestanden;
`compileall` und `git diff --check` waren erfolgreich. Der providerfreie
Selector-/Formulator-Dry-Run meldete Prompt 15 und Anwendungstextversion 8 bei
null Live-Aufrufen.

### Milestone 4: Documentation

- [x] Apply the `code-documentation` checklist.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: Architektur, Datenfluss und Live-Evaluationsdokumentation weisen die
neuen Versionen und die Abgrenzung zwischen sichtbarem Containerverweis,
echter Kartenansicht und Kartenzahlung aus.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Ressourcen | fünfsprachiger Inventartest | keine Card-/Map-Containerverweise in vier IDs |
| Prompt | Formulatortest | dynamische Antworten verweisen nicht auf Ergebnis-Cards |
| API | Templatefallbacktest | deutscher sichtbarer Text „Mehr Infos stehen unten.“ |
| Regression | `python -m pytest -q` | vollständige Suite grün |
| Static quality | `compileall`; `git diff --check` | erfolgreich |

## Rollback and recovery

Keine Daten- oder Schemamigration. Text-, Versions-, Prompt-, Test- und
Dokumentationshunks können isoliert zurückgenommen werden.

## Progress log

- 2026-08-25 — Sichtbare Textpfade, Abgrenzungen und Versionierung geprüft; Plan
  vor Quellcodeänderung erstellt.
- 2026-08-25 — Ressourcen und Prompt aktualisiert; fokussierte Tests bestanden.
- 2026-08-25 — Vollsuite fand den entfallenen A1/Schoppi-Zugangshinweis; Text
  minimal korrigiert und gesamte Suite anschließend erfolgreich wiederholt.

## Decision log

- Decision: zentrale Ressourcen plus Prompt, kein globaler Wortfilter.
  - Context: „Karte“ kann UI-Container, echte Map oder Zahlungsart bedeuten.
  - Options: Textressource, Frontendersetzung, Validatorregex, Ressource plus Prompt.
  - Choice: Ressource plus Prompt.
  - Consequences: verständliche Texte ohne Beschädigung operativer Fakten; reale Modellbefolgung bleibt separat evaluierbar.

## Discoveries

- Der bedingte A1/Schoppi-Pfad benötigt weiterhin den ausdrücklichen Hinweis
  auf Zugangsbedingungen. Nur der nachgelagerte Containerverweis durfte
  entfallen.

## Final verification summary

- Acceptance requirements: erfüllt
- Tests: 173 fokussierte Tests und vollständige Suite erfolgreich
- Build: für reine Text-/Promptänderung nicht erforderlich; Syntaxprüfung erfolgreich
- Manual verification: fünfsprachiges gezieltes Ressourceninventar geprüft
- Documentation: Architektur, Datenfluss und Live-Evaluation aktualisiert
- Residual risks: reale Providerbefolgung nur durch gesonderten Live-Lauf messbar
