# Execution Plan: Formulator mit belegtem Angebotsdetail (Promptversion 13)

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-25
- Last updated: 2026-08-25

## Objective

Normale angebotsbezogene Antworten behalten den stabilen ersten Handlungssatz
mit unverändertem Anzeigenamen, erklären danach aber in einem zweiten kurzen
Satz mindestens eine für die Anfrage hilfreiche, zitierte Angebotsinformation.

## Acceptance contract

- [x] Promptversion 13 ist in Runtime, Health und Evaluation nachvollziehbar.
- [x] `grounded_result`, `grounded_referral` und `ambiguous_help_fallback`
  erzeugen regulär zwei bis drei Sätze statt eines bloßen Namenssatzes.
- [x] Der zweite Satz verwendet genau ein ausgewähltes Angebot und mindestens
  einen passenden Description-, Service-, Capability- oder operativen Fakt.
- [x] Direct-Service- und Referral-Rollen bleiben korrekt getrennt.
- [x] Der feste erste Satz und die zeichengetreue Namensbehandlung bleiben
  unverändert.
- [x] Der adversariale Prompt-Injection-Pfad bleibt absichtlich einsätzig.
- [x] Vertrag, Evidence, Grounding, Auswahl, Karten, Fallbacks und Modelle
  bleiben unverändert.
- [x] Providerfreie Fokus- und Gesamttests bestehen.

## Scope

### In scope

- `FORMULATOR_SYSTEM_PROMPT` und `FORMULATOR_PROMPT_VERSION`
- unmittelbar zugehörige Prompt-, Health- und Regressionstests
- bestehende Architektur-, Datenfluss- und Live-Evaluationsdokumentation

### Out of scope

- Änderungen an Formulatorvertrag, Evidence oder Groundingvalidatoren
- neue Wissensbasisdaten, Übersetzungen oder fachliche Auswahlregeln
- Änderungen am Templatefallback
- reale Provideraufrufe oder eine neue Live-Evaluation
- Thesis- und Präsentationsdateien

## Repository review

### Current behavior

Prompt 12 erlaubt ein bis drei Sätze, fordert zugleich die kleinstmögliche
Antwort und erklärt den bloßen ersten Namenssatz ausdrücklich für ausreichend.
Für `direct_service` lautet das feste deutsche Muster `Nutze „NAME“.`, für
`referral_contact` `Melde dich bei „NAME“.`; das Modell darf danach aufhören.

### Relevant architecture and data flow

`app.formulation.build_formulator_evidence()` übergibt bereits pro finalem
Angebot Anzeigename, Beschreibung, Leistungen, Fähigkeiten, Zielgruppe,
Adresse, Kontakte, Zeiten und Hinweise als opake Fakten. Der Provider verwendet
den Systemprompt; `app.grounding.validate_formulation()` prüft anschließend
jeden Satz atomar gegen Rolle, Fakt-IDs, operative Tokens und Sprache. Eine
Promptpräzisierung erreicht daher den aktiven Pfad ohne parallele Logik.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| kanonischer Formulatorprompt | `app/formulation.py` | ausschließlich Regeln präzisieren und Version erhöhen |
| Evidence-Fakteninventar | `app/formulation.py::_facts_for_offer` | unverändert verwenden |
| atomare Groundingprüfung | `app/grounding.py::validate_formulation` | unverändert beibehalten |
| Prompt-/Healthtests | `tests/test_formulation.py` | neue Detailpflicht und Version absichern |
| Provider-Test-Doubles | `tests/test_formulation.py`, `tests/test_api.py` | gültige Zwei-Satz-Antwort ohne Netzwerk prüfen |

### Existing tests and commands

- `python -m pytest -q tests/test_formulation.py tests/test_api.py tests/test_live_evaluation.py`
- `python -m pytest -q`
- `python -m compileall -q app tests`
- `git diff --check`

### Working tree considerations

Der Arbeitsbaum enthält die bereits abgeschlossenen, uncommitteten Safety- und
VKKJ-Kartenänderungen der Nutzerin/Codex. Diese werden nicht zurückgesetzt,
umformatiert oder inhaltlich verändert. `app/formulation.py` ist derzeit nicht
lokal verändert und bildet eine klar isolierbare neue Difffläche.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Grounding lockern | Detailfakten sind bereits vorhanden | ungeerdete Aussagen würden sichtbar | nur Prompt ändern | bestehende Groundingtests |
| Ersten Satz freigeben | frühere Live-Läufe veränderten Eigennamen und Rollen | erneute Vertragsfehler | festes Muster unverändert lassen | Promptregression |
| Adresse/Telefon immer verlangen | nicht jedes Angebot besitzt dieselben operativen Fakten | Modell könnte Fakten erfinden oder scheitern | bevorzugt Beschreibung/Leistung; operative Details nur bei vorhandener Relevanz | Evidence- und APItests |
| Auch Injection ausführlich beantworten | adversariale Eingabe kann Faktwahl beeinflussen | größere Angriffsfläche | bestehender Eins-Satz-Modus bleibt | Injectiontests |
| Templatefallback parallel ausbauen | Nutzer beobachtet das feste LLM-Muster; Templates sind bereits informativer | sachfremde doppelte Logik | Templatepfad unverändert | Provider-/Fallbacktests |

## Recommended approach

Prompt 13 ersetzt die widersprüchliche Minimalregel durch eine klare
Zwei-Satz-Vorgabe für normale angebotsbezogene Antworten. Satz 1 bleibt das
sprach- und rollenfeste Muster. Satz 2 nennt genau eine hilfreiche, zitierte
Information des primären Angebots; Satz 3 darf eine weitere relevante operative
Angabe enthalten. Der bestehende Injectionfall bleibt die einzige explizite
Ausnahme.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| neues Antwortschema mit Pflichtfeld | unnötige Vertragsmigration; Satzvertrag reicht aus |
| serverseitig Text an Modellantwort anhängen | würde einen zweiten Formulierungs- und Groundingpfad schaffen |
| vollständige Karteninhalte im Antworttext wiederholen | widerspricht kurzer Sprache und TTS-Nutzbarkeit |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/formulation.py` | Modify | Prompt 13 und Angebotsdetailpflicht | klein |
| `tests/test_formulation.py` | Modify | Promptversion und Zwei-Satz-Regeln | klein |
| `docs/architecture.md` | Modify | tatsächliche Formulatorausgabe beschreiben | klein |
| `docs/data-flow.md` | Modify | Satzaufbau im aktiven Pfad aktualisieren | klein |
| `docs/live-provider-evaluation.md` | Modify | aktive Promptidentität und ausstehendes Live-Gate korrigieren | klein |
| dieser Plan | Create/Update | Review- und Prüfnachweis | klein |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: Prompt 12 verlangt explizit `Prefer the smallest grounded answer`,
`name-only ... is enough` und die festen Muster; `_facts_for_offer()` liefert
bereits alle benötigten freigegebenen Detailklassen.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

Evidence: Nur Promptkonstante und Prompttext wurden im Runtimecode geändert;
Vertrag, Evidence und Validator blieben unverändert. Ein neuer Regressionstest
validiert den festen Handlungssatz plus einen getrennten, belegten Servicesatz.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run integration/build checks where relevant.
- [x] Verify Promptversion in Health und providerfreiem Evaluationsplan.
- [x] Review final diff.

Evidence: Fokussierte Formulator-, API- und Live-Evaluationstests bestanden;
die vollständige Suite bestand mit 749 Tests. `compileall` und
`git diff --check` waren erfolgreich. `live-dry-run --stage
selector-formulator` meldete Formulatorvertrag `2`, Prompt `13` und
`live_provider_calls_authorized=false`.

### Milestone 4: Documentation

- [x] Apply the `code-documentation` checklist to the final diff.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: Architektur, Datenfluss und Live-Evaluationsidentität dokumentieren
die Zwei-Satz-Regel, die einsätzige Injection-Ausnahme und den ausstehenden
realen Modellnachweis.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Promptvertrag | `python -m pytest -q tests/test_formulation.py` | Version 13, fester erster und belegter zweiter Satz |
| Integration | `python -m pytest -q tests/test_api.py tests/test_live_evaluation.py` | aktiver Provider-/Health-/Evaluationspfad konsistent |
| Regression | `python -m pytest -q` | vollständige Suite grün |
| Static quality | `python -m compileall -q app tests`; `git diff --check` | erfolgreich |

## Rollback and recovery

Die Änderung migriert weder Daten noch Schemas. Die isolierten Prompt-, Test-
und Dokumentationshunks können zurückgenommen werden; die vorherigen
uncommitteten Änderungen bleiben davon unberührt.

## Progress log

- 2026-08-25 — Review abgeschlossen und Plan vor Quellcodeänderung erstellt.
- 2026-08-25 — Prompt 13, Regressionstest und technische Dokumentation
  umgesetzt; vollständige providerfreie Verifikation erfolgreich abgeschlossen.

## Decision log

- Decision: verpflichtender zweiter, belegter Satz nur bei normalen
  angebotsbezogenen Antworten.
  - Context: Der sichere erste Mustersatz verhindert Namens- und Rollenfehler,
    ist allein aber für Nutzende zu informationsarm.
  - Options: Promptpräzisierung, Vertragsänderung, serverseitige Ergänzung.
  - Choice: Promptpräzisierung.
  - Consequences: bessere Information ohne Lockerung der atomaren Validierung;
    reale Modellbefolgung bleibt separat zu evaluieren.

## Discoveries

- `docs/live-provider-evaluation.md` weist in der Tabelle der aktiven
  technischen Identität noch Formulatorprompt 9 aus, obwohl Runtime und Health
  bereits Prompt 12 verwenden. Diese unmittelbar betroffene veraltete Angabe
  wird im selben Dokument auf Prompt 13 korrigiert.

## Final verification summary

- Acceptance requirements: erfüllt
- Tests: 749 bestanden; fokussierte Tests ebenfalls bestanden
- Build: Python-Syntaxprüfung erfolgreich; keine Paketstruktur geändert
- Manual verification: Prompt- und Dokumentationsdiff geprüft; Dry-Run zeigt Version 13
- Documentation: Architektur, Datenfluss und Live-Evaluation aktualisiert
- Residual risks: reale Providerbefolgung erst nach gesonderter Freigabe messbar
