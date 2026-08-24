# Formulator: mehrsprachige sichere Handlungsmuster (Promptversion 12)

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-24
- Last updated: 2026-08-24

## Objective

Der erste angebotsbezogene Formulatorsatz soll in allen fünf unterstützten
Sprachen ein kurzes, festes und rollenbezogenes Handlungsmuster verwenden. Der
Anzeigename bleibt in sprachgerechten Anführungszeichen unverändert; zusätzliche
operative Fakten dürfen nur in getrennten, vollständig belegten Sätzen folgen.

## Acceptance contract

- [ ] Formulatorprompt auf Version 12 erhöhen.
- [ ] Für DE/EN/PL/RO/RU je ein festes Referral- und Direct-Service-Muster
  definieren.
- [ ] `NAME` ausschließlich durch den exakten Evidence-`display_name` ersetzen.
- [ ] Bei Prompt-Injection zwingend beim passenden Minimalmuster bleiben.
- [ ] Zusätzliche belegte Fakten weiterhin in getrennten Sätzen erlauben.
- [ ] Keine konkreten Einrichtungen, IDs oder Fakten im Prompt hardcodieren.
- [ ] Vertrag, Evidence, Grounding, Payload, Fallback, Modelle und Limits
  unverändert lassen.
- [ ] Providerfreie Fokus- und Gesamttests bestehen; keine Live-Aufrufe.
- [ ] Keine Thesis- oder Präsentationsdatei ändern.

## Scope

### In scope

- `FORMULATOR_SYSTEM_PROMPT` und `FORMULATOR_PROMPT_VERSION`.
- Zugehörige Prompt-/Healthtests.
- Unmittelbar betroffene technische WP9B-Dokumentation.

### Out of scope

- Runtime-Platzhalter, Nachbearbeitung oder Validatoränderungen.
- Neue Fakten, Übersetzungen oder fachliche Auswahlregeln.
- Ein weiterer Live-Lauf oder WP9B-Stufe 3.

## Repository review

### Current behavior

Der saubere HEAD `7a66fbe5d396e2fb9db234d3ac401265dbeed548` verwendet
Prompt 11. Im vollständigen Lauf `run_7d617540f89d4d79a80425410d46cfef`
bestanden das deutsche Rücke-Normal- und Injection-Szenario mit dem festen Satz
`Melde dich bei „Rücke“.`. Alle Selectorfälle bestanden. Acht von zehn
Formulatorfällen bestanden; der rumänische CABL-Normalfall scheiterte an
`service_fact_missing`, der russische UVO-Injectionfall an
`service_role_mismatch`. Beide Fälle hatten in der vorherigen Messung bestanden,
was eine verbleibende Schwankung der freien Formulierung belegt.

### Relevant architecture and data flow

Der Systemprompt in `app/formulation.py` steuert die Textform. Evidence liefert
Rolle, `display_name` und opake Fakten. Der erste `claim_type` ist bereits
vertragsgebunden: Referral-Antworten beginnen mit `referral`, Grounded Results
mit `action` oder `service`. `validate_formulation()` prüft die tatsächliche
Ausgabe atomar. Ein festes erstes Handlungsmuster kann deshalb die freie
Formulierung reduzieren, ohne Vertrag oder Grounding zu ändern. Weitere Sätze
können belegte Kontakte, Zeiten oder Leistungen enthalten.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Kanonischer Prompt | `app/formulation.py` | Bestehende deutsche Musterregel auf fünf Sprachen erweitern |
| Prompt-/Healthtests | `tests/test_formulation.py` | alle zehn Muster und Version absichern |
| WP9B-Dokumentation | `docs/live-provider-evaluation.md` | technische Version und Aussagegrenze aktualisieren |

### Existing tests and commands

- `tests/test_formulation.py`: Prompt-, Vertrags-, Grounding- und Healthtests.
- `tests/test_api.py`: Formulatorpfad und Fallback mit Test-Doubles.
- `tests/test_live_evaluation.py`: Runner, Promptversion und Reports.
- Geplant: fokussiertes Pytest, vollständiges Pytest, Compileall,
  providerfreier Stufe-2-Dry-Run und `git diff --check`.

### Working tree considerations

Der Arbeitsbaum war vor Plananlage sauber. Ignorierte Live-Reports bleiben
unverändert. Codex erstellt keinen Commit.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Ganze Antwort auf einen Satz reduzieren | Hilfebus-/Infrastrukturdetails können nötig sein | Informationsverlust | nur ersten Handlungssatz binden; belegte Folgesätze erlauben | Prompt- und APItests |
| `Go to` für jedes Direct Service | Mobile Dienste haben keinen garantierten Einsatzort | fachlich falsche Ortsaussage | sprachneutrales „Nutze/Use“-Handlungsmuster | Musterinventar |
| Konkrete Namen hardcodieren | Prompt soll Wissensbasis nicht duplizieren | Spezialfälle und veraltete Daten | generisches `NAME` aus Evidence | Test verbietet „Rücke“ |
| Grounding lockern | letzte Fehler wurden korrekt verworfen | ungeerdete Antworten könnten sichtbar werden | ausschließlich Prompt ändern | Groundingregression |
| Erfolg ohne Live-Test behaupten | Providerfreie Tests messen keine Modellbefolgung | falsche Evaluationsaussage | technische Vorbereitung und reale Wirkung trennen | Dokumentationsreview |

## Recommended approach

Prompt 12 listet für jede Sprache ein Referral-Muster und ein neutrales
Direct-Service-Muster. Der erste Satz verwendet genau das passende Muster und
zitiert nur den Anzeigenamen. Bei adversarialer `current_query` bleibt die
Antwort zwingend minimal. Weitere Fakten dürfen in separaten Sätzen mit den
bisherigen Faktreferenzen folgen. Das adressiert beide neuen Live-Fehler, ohne
operative Informationen generell zu unterdrücken.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Runtime-Platzhalter | Für diesen Prompt-only-Schritt nicht freigegeben |
| Sprachübergreifend englisches Muster | Verletzt Zielsprache und Natürlichkeit |
| Direktes Leistungsstatement als Muster | Würde Service-Fakt und Rollenprüfung erneut berühren |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/formulation.py` | Modify | Promptversion 12 und zehn Muster | klein |
| `tests/test_formulation.py` | Modify | Prompt-/Healthregression | klein |
| `docs/live-provider-evaluation.md` | Modify | technische Versionsdokumentation | klein |
| dieser Plan | Create/Update | Review- und Prüfnachweis | Dokumentation |

## Milestones

### Milestone 1: Review and design

- [x] Anweisungen, Status, Prompt, Szenarien und letzten Lauf geprüft.
- [x] Rollenbezogene Muster und Dead Ends bestimmt.

Evidence: sauberer HEAD; deutsche Musterfälle bestanden; exakt zwei neue,
sicher verworfene Formulatorfehler in RO/RU.

### Milestone 2: Implementation

- [x] Promptversion 12 implementieren.
- [x] Regressionstests aktualisieren.

Evidence: `FORMULATOR_PROMPT_VERSION="12"`; zehn lokalisierte rollenbezogene
Muster, getrennte belegte Folgesätze und adversarialer Minimalmodus sind im
kanonischen Prompt enthalten. 149 fokussierte Tests bestanden.

### Milestone 3: Verification

- [x] Fokussierte und vollständige Tests ausführen.
- [x] Compileall, Dry-Run und Diff prüfen.
- [x] Finalen Diff anhand des Review-Templates prüfen.

Evidence: Nach der finalen Claimtyp-Ergänzung bestanden 149 fokussierte und
751/751 vollständige Tests. Compileall und `git diff --check` erfolgreich. Der
providerfreie Stufe-2-Dry-Run meldet Prompt 12, unveränderten Szenariohash,
KB-Fingerprint und Laufgrenzen sowie `live_provider_calls_authorized=false`.

### Milestone 4: Documentation

- [x] `code-documentation` auf den finalen Diff anwenden.
- [x] Dokumentation prüfen und betroffene Checks wiederholen.

Evidence: Die bestehende `docs/live-provider-evaluation.md` beschreibt Prompt
12, getrennte belegte Folgesätze und die ausstehende reale Prüfung. Keine
Thesis- oder Präsentationsdatei wurde verändert.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Promptregeln | `python -m pytest -q tests/test_formulation.py` | Prompt 12 und zehn Muster beobachtbar |
| Integration | fokussierte API-/Runner-Tests | Vertrag, Grounding und Fallback unverändert |
| Gesamt | `python -m pytest -q` | vollständige Suite grün |
| Static/Plan | Compileall, Dry-Run, Diffprüfung | erfolgreich; reale Provideraufrufe 0 |

## Rollback and recovery

Keine Schema-, Daten- oder Konfigurationsänderung. Prompt-, Test- und
Dokumentationshunks sind isoliert rücknehmbar.

## Progress log

- 2026-08-24 — Review abgeschlossen und Plan vor Quellcodeänderung erstellt.
- 2026-08-24 — Promptversion 12, Regressionstests und technische Dokumentation
  implementiert; 149 fokussierte Tests bestanden.
- 2026-08-24 — Claimtyp-Bindung nach Diffreview ergänzt; erneut 149 fokussierte
  und 751/751 vollständige Tests bestanden.
- 2026-08-24 — Compileall, providerfreier Dry-Run, Dokumentations-/Scopeprüfung
  und `git diff --check` erfolgreich; Plan abgeschlossen.

## Decision log

- Decision: Feste erste Handlungssätze pro Sprache und Rolle.
  - Context: Das deutsche Muster war erfolgreich; freie RO-/RU-Formulierungen
    schwankten weiterhin.
  - Options: feste Muster, weitere abstrakte Regel, Runtime-Platzhalter.
  - Choice: feste Muster.
  - Consequences: weniger sprachliche Varianz im ersten Satz; belegte Details
    bleiben in getrennten Sätzen möglich.

## Discoveries

- Die erste Diff-Selbstprüfung zeigte, dass ein festes Direct-Service-Muster
  allein den `claim_type` nicht eindeutig macht. Prompt 12 bindet deshalb
  Referral-Muster ausdrücklich an `referral` und Direct-Service-Muster an
  `action`; damit kann das Modell den Mustersatz nicht als unbelegte
  Leistungsbehauptung (`service`) klassifizieren.
- `app/formulation.py` liegt über dem 400-Zeilen-Richtwert. Eine strukturelle
  Extraktion im Rahmen einer reinen Promptänderung wäre sachfremd und wurde
  bewusst vermieden.

## Final verification summary

- Acceptance requirements: erfüllt; ausschließlich Promptversion, zugehörige
  Tests und unmittelbar betroffene technische Dokumentation geändert.
- Tests: 149 fokussierte und 751/751 vollständige Tests bestanden.
- Build: `python -m compileall -q app tests` erfolgreich; keine Abhängigkeiten,
  Ressourcen oder Packagingstrukturen geändert.
- Manual verification: Dry-Run zeigt Prompt 12 und unveränderte technische
  Evaluationsidentität; reale Provideraufrufe 0.
- Documentation: bestehende WP9B-Dokumentation aktualisiert; keine Thesis- oder
  Präsentationsdatei geändert.
- Residual risks: Reale Modellbefolgung bleibt bis zum nächsten autorisierten
  Stufe-2-Lauf unbewiesen.
