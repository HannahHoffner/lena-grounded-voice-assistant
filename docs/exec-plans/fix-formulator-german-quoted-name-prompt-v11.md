# Formulator: deutsche Eigennamen in Anführungszeichen (Promptversion 11)

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-24
- Last updated: 2026-08-24

## Objective

Deutsche Referral-Antworten sollen den kuratierten Anzeigenamen durch deutsche
Anführungszeichen sichtbar als unveränderlichen Eigennamen behandeln. Das Modell
soll das feste Muster `Melde dich bei „<exakter Anzeigename>“` verwenden, ohne
den Namen grammatisch zu verändern.

## Acceptance contract

- [ ] Formulatorprompt auf Version 11 erhöhen.
- [ ] Für deutsche Referral-Sätze ein festes, knappes Satzmuster mit deutschen
  Anführungszeichen verlangen.
- [ ] Nur den tatsächlich gelieferten `display_name` einsetzen; keinen
  institutionsspezifischen Namen im Systemprompt hartcodieren.
- [ ] Vertrag, Evidence, Grounding, Payload, Fallback, Modelle und Limits
  unverändert lassen.
- [ ] Providerfreie Fokus- und Gesamttests bestehen; keine Live-Aufrufe.
- [ ] Keine Thesis- oder Präsentationsdatei ändern.

## Scope

### In scope

- `FORMULATOR_SYSTEM_PROMPT` und `FORMULATOR_PROMPT_VERSION`.
- Zugehörige Prompt-/Healthtests.
- Unmittelbar betroffene technische Evaluationsdokumentation.

### Out of scope

- Platzhalter- oder Nachbearbeitungslogik.
- Formulatorvertrag, Evidence und Groundingvalidatoren.
- Änderungen an anderen Sprachen oder fachlichen Fakten.
- Ein weiterer Live-Lauf oder WP9B-Stufe 3.

## Repository review

### Current behavior

Der saubere HEAD `c0e0c26aa2a39936378641c76965af2613bde1f3` verwendet
Formulatorprompt 10. Der vollständig abgeschlossene Stufe-2-Lauf
`run_9c5685d9ac784140bf0f759afbb0861b` bestand alle Selectorfälle und acht von
zehn Formulatorfällen. Polnisch, Englisch, Rumänisch und Russisch bestanden;
nur die beiden deutschen Referral-Szenarien für Angebot 7 wurden weiterhin mit
`proper_name_not_exact` verworfen. Prompt 10 verbietet Flexion bereits allgemein,
liefert für Deutsch aber kein konkretes syntaktisches Muster, das die Flexion
vermeidet.

### Relevant architecture and data flow

Der kanonische Systemprompt in `app/formulation.py` wird unverändert an den
Provider übergeben. Evidence liefert den freigegebenen `display_name` und dessen
opake Fakt-ID. `validate_formulation()` verlangt weiterhin die exakte wörtliche
Namensübernahme; Anführungszeichen um den Namen beeinträchtigen diese Prüfung
nicht. Health, Dry-Run und Live-Manifest lesen die Promptversion aus derselben
Konstante.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Kanonischer Systemprompt | `app/formulation.py` | Deutsche Referral-Regel ergänzen |
| Prompt-/Healthtests | `tests/test_formulation.py` | Version und Satzmuster absichern |
| WP9B-Dokumentation | `docs/live-provider-evaluation.md` | Promptversion und Grenze aktualisieren |

### Existing tests and commands

- `tests/test_formulation.py`: Prompt-, Vertrags-, Grounding- und Healthtests.
- `tests/test_api.py`: realer Formulatorpfad mit Test-Doubles.
- `tests/test_live_evaluation.py`: Runner und Versionsmanifest.
- Geplant: fokussiertes Pytest, vollständiges Pytest, Compileall,
  providerfreier Stufe-2-Dry-Run und `git diff --check`.

### Working tree considerations

Der Arbeitsbaum war vor Plananlage sauber. Lokale ignorierte Live-Reports bleiben
unverändert. Codex erstellt keinen Commit.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| „Rücke“ im Prompt hartcodieren | Prompt soll institutionsunabhängig bleiben | Spezialfall und doppelte Wissensbasis | generisches Muster mit Evidence-`display_name` | Test verbietet „Rücke“ weiterhin |
| Namen nachträglich korrigieren | Nutzer genehmigt ausdrücklich Prompt-only-Versuch | unkontrollierte Textmutation | keine Runtime-/Validatoränderung | Diffreview |
| Anführungszeichen als Garantie darstellen | Prompt 10 wurde trotz klarer Regel verletzt | reale Modellbefolgung bleibt empirisch offen | nur providerfreie Technikfreigabe behaupten | separater späterer Live-Lauf |
| Grounding lockern | Diagnose belegt fehlende exakte Namensform | falscher Name könnte sichtbar werden | Grounding unverändert | Groundingtests |

## Recommended approach

Promptversion 11 ergänzt ausschließlich für deutsche Referral-Sätze ein festes
Muster: Kontaktaufforderung, `bei`, deutscher öffnender und schließender
Anführungsstrich und der unveränderte `display_name`. Das vermeidet die
grammatische Notwendigkeit, den Namen zu flektieren, ohne einen konkreten
Angebotsnamen in den Prompt zu schreiben.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Opake Runtime-Platzhalter | Vom Nutzer für diesen Versuch ausdrücklich nicht gewünscht |
| `zur` plus Name | Kann das Modell eher zur grammatischen Anpassung verleiten; `bei` lässt den Eigennamen unverändert |
| Mehrsprachige feste Templates | Beobachteter Fehler betrifft ausschließlich Deutsch |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/formulation.py` | Modify | Promptversion 11 und deutsches Referral-Muster | klein |
| `tests/test_formulation.py` | Modify | Prompt-/Healthregression | klein |
| `docs/live-provider-evaluation.md` | Modify | technische Version und Aussagegrenze | klein |
| dieser Plan | Create/Update | Review- und Prüfnachweis | Dokumentation |

## Milestones

### Milestone 1: Review and design

- [x] Anweisungen, Status, Promptpfad, Tests und letzten Lauf geprüft.
- [x] Datenunabhängiges Satzmuster und Dead Ends bestimmt.

Evidence: sauberer HEAD; zwei redigierte `proper_name_not_exact`-Fehler im
vollständigen Stufe-2-Lauf; keine anderen offenen Formulatorfehler.

### Milestone 2: Implementation

- [x] Promptversion 11 implementieren.
- [x] Regressionstests aktualisieren.

Evidence: `FORMULATOR_PROMPT_VERSION="11"`; deutsches Referral-Muster und
Anführungszeichenregel sind im kanonischen Prompt enthalten. Health- und
Prompttests erwarten Version 11; 149 fokussierte Tests bestanden.

### Milestone 3: Verification

- [x] Fokussierte und vollständige Tests ausführen.
- [x] Compileall, Dry-Run und Diff prüfen.
- [x] Finalen Diff anhand des Review-Templates prüfen.

Evidence: 149 fokussierte und 751/751 vollständige Tests bestanden. Compileall
und `git diff --check` erfolgreich. Der providerfreie Stufe-2-Dry-Run meldet
Prompt 11, unveränderten Szenariohash, KB-Fingerprint und Laufgrenzen sowie
`live_provider_calls_authorized=false`.

### Milestone 4: Documentation

- [x] `code-documentation` auf den finalen Diff anwenden.
- [x] Dokumentation prüfen und betroffene Checks wiederholen.

Evidence: `docs/live-provider-evaluation.md` dokumentiert Prompt 11 im
bestehenden WP9B-Kontext, ohne reale Konformität zu behaupten. Keine Thesis- oder
Präsentationsdatei wurde verändert.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Promptregeln | `python -m pytest -q tests/test_formulation.py` | Prompt 11 und Satzmuster beobachtbar |
| Integration | fokussierte API-/Runner-Tests | Verträge und Fallback unverändert |
| Gesamt | `python -m pytest -q` | vollständige Suite grün |
| Static/Plan | Compileall, Dry-Run, Diffprüfung | erfolgreich; reale Provideraufrufe 0 |

## Rollback and recovery

Keine Schema- oder Datenänderung. Prompt-, Test- und Dokumentationshunks können
isoliert zurückgenommen werden; Runtime-KB und Providerkonfiguration bleiben
unberührt.

## Progress log

- 2026-08-24 — Review abgeschlossen und Plan vor Quellcodeänderung erstellt.
- 2026-08-24 — Promptversion 11, Regressionstest und technische
  Versionsdokumentation implementiert; 149 fokussierte Tests bestanden.
- 2026-08-24 — 751/751 vollständige Tests, Compileall, providerfreier Dry-Run,
  Scope-/Diffreview und `git diff --check` bestanden; Plan abgeschlossen.

## Decision log

- Decision: Deutsches Referral-Muster mit Anführungszeichen, ohne konkreten Namen.
  - Context: Prompt 10 löste alle nichtdeutschen Fehler, aber nicht die Flexion
    des deutschen Anzeigenamens.
  - Options: generisches Satzmuster, harter Name, Runtime-Platzhalter.
  - Choice: generisches Satzmuster.
  - Consequences: reine Promptänderung; tatsächliche Modellwirkung bleibt erst
    in einem gesondert freigegebenen Live-Lauf messbar.

## Discoveries

- `app/formulation.py` liegt mit 571 Zeilen über dem 400-Zeilen-Richtwert. Eine
  Extraktion für eine einzelne Promptzeile wäre sachfremd; die Modulstruktur
  blieb deshalb bewusst unverändert.

## Final verification summary

- Acceptance requirements: erfüllt; reine Promptversion-/Test-/Dokumentationsänderung.
- Tests: 149 fokussierte und 751/751 vollständige Tests bestanden.
- Build: `python -m compileall -q app tests` erfolgreich; keine Abhängigkeit,
  Ressource oder Packagingstruktur geändert.
- Manual verification: providerfreier Dry-Run zeigt Prompt 11 und unveränderte
  technische Identität; reale Provideraufrufe 0.
- Documentation: bestehende technische WP9B-Dokumentation aktualisiert; keine
  Thesis- oder Präsentationsdatei geändert.
- Residual risks: Reale Einhaltung ist durch providerfreie Tests nicht belegbar.
