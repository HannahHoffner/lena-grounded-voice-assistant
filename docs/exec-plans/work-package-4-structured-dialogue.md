# Arbeitspaket 4: Strukturierter Rueckfrage- und Dialogpfad

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-01
- Last updated: 2026-08-01

## Objective

Nach Interpreter und deterministischem `CandidateSelector` kann LENA eine einzige kurze, fachlich begruendete Rueckfrage stellen, deren Zustand atomar in der bestehenden Session gespeichert ist. Antworten per validiertem Button, Freitext oder Sprache aktualisieren ausschliesslich ausdrueckliche Fakten und fuehren erneut durch den Selector. Ungeklaerte Faelle enden kontrolliert beim kuratierten Hilfebus-Verweis.

## Acceptance contract

- [x] Ein versionierter, strikt validierter Dialogzustand ersetzt `pending_clarification` in der bestehenden Sessionverwaltung.
- [x] Die API liefert einen optionalen strukturierten Klaerungsblock und validiert Dialog-ID sowie technische Choice-Werte serverseitig und nebenlaeufigkeitssicher.
- [x] Schlaf-, A1/Schoppi-, Mobile/Kuebel- und allgemeine Hilfedialoge folgen den freigegebenen fachlichen Grenzen.
- [x] Freitext und STT-Transkripte durchlaufen mit offenem Dialog weiterhin denselben LLM-Interpreter; Buttons erzeugen keine kuenstliche Freitextanfrage.
- [x] Themenwechsel schliessen den alten Dialog; ein Sprachwechsel allein erhaelt Dialog und strukturierte Fakten bei identischem KB-Fingerprint.
- [x] Rueckfragen, Choice-Labels, Fehler und Hilfebus-Fallbacks kommen aus einer paketierten, versionierten Ressource fuer de/en/pl/ro/ru.
- [x] Akutrisiko und Out-of-Scope beenden einen offenen Dialog ohne Angebote oder Hilfebus; Interpreterfehler uebernehmen keine Fakten.
- [x] Das Frontend zeigt barrierearme Buttons mit Fokus, Doppelklickschutz und paralleler Text-/Spracheingabe; technische Werte bleiben unsichtbar.
- [x] Forschunglogging speichert nur redigierte Dialogmetadaten, keine sensitiven Choice-Werte oder zusaetzlichen Personenmerkmale.
- [x] Arbeitspakete 5 bis 7 sowie Infrastruktur-, Distanz- und abschliessende Safety-Arbeiten bleiben unberuehrt.

## Scope

### In scope

- Dialogvertrag, lokalisierte Dialogressource und Dialogpolitik.
- Erweiterung der bestehenden Sessionpersistenz um atomare Dialogoperationen und KB-/TTL-Bindung.
- Begrenzter Interpreter-Dialogkontext sowie explizites Altersgruppenfaktum fuer die Aussage `unter 27`, ohne ein Alter zu erfinden.
- Erneuter deterministischer Selector-Aufruf nach validierter Dialogantwort.
- Strukturierte API-Antwort und Frontend-Buttons.
- Redigierte Interaktionsmetadaten, Tests und bestehende technische Dokumentation.

### Out of scope

- LLM-Kandidatenauswahl, neuer Formulator, Uebersetzungsfreigabeverfahren.
- Allgemeine Stadtteilvalidierung, Zuständigkeits- oder Entfernungsranking.
- Toiletten-/Trinkbrunnenimporte und neue Runtime-Angebote.
- Endgueltige Policy fuer `acute_risk_status=uncertain` oder Providerfehler.
- Thesis- und Praesentationsdateien.

## Repository review

### Current behavior

`QueryService.query()` laedt eine fingerprintfaehige `ConversationSession`, uebergibt deren Freitextturns an den Interpreter und setzt nach jeder Antwort nur `pending_clarification: bool`. `SessionStore.resolve()` verwirft die gesamte Session bei einem Sprachwechsel. `_query_core()` formuliert Rueckfragen als verstreute Konstanten, kann aber weder einen Dialog binden noch Buttonwerte oder Mehrfachangaben validieren. Mehrdeutige Aliase und allgemeine Hilfe enden in statischen Texten; eine erneute strukturierte Kandidatenbegrenzung aus einem gespeicherten Klaerungskontext existiert nicht. Das Frontend sendet nur Freitext und kennt keinen Klaerungsblock.

### Relevant architecture and data flow

- HTTP: `app/main.py:answer_query()` -> `app/service.py:QueryService.query()`.
- Session: `app/sessions.py:SessionStore.resolve()` und `add_turn()` mit atomarer JSON-Dateipersistenz, TTL und Groessenlimit.
- Interpreter: `app/providers/llm.py:BlabladorProvider.interpret_query()` -> `app/interpreter.py:QueryInterpretation`.
- Auswahl: `app/candidates.py:CandidateSelector.select()` aus der einzigen kuratierten Runtime-KB.
- Ausgabe: bestehender geerdeter Formulator oder Templates; Karten und Marker entstehen nur aus ausgegebenen Runtime-Angeboten.
- Frontend: `app/static/index.html` und `app/static/app.js`; Browser-/Server-STT setzt normalen Text und nutzt anschliessend `/api/query`.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Strikte Pydantic-Vertraege | `app/interpreter.py`, `app/candidate_contract.py`, `app/models.py` | Fuer Dialog-, API- und Ressourcenmodelle fortfuehren |
| Einzige Sessionverwaltung | `app/sessions.py` | Erweitern; keinen zweiten Store und keinen parallelen `pending_clarification`-Pfad behalten |
| CandidateSelector | `app/candidates.py` | Nach Faktenauflösung erneut aufrufen; keine neue Auswahlengine |
| Kuratierte Aliasbindung | `app/candidate_context.py`, `app/curation.py` | Dialog nur bei explizit definierten Mehrdeutigkeiten oeffnen |
| Runtime-KB-Fingerprint | `app/kb_loader.py` | Dialog und Fakten daran binden und bei Wechsel verwerfen |
| Paketressourcen | `app/resources/bootstrap/` und `pyproject.toml` | Versionierte Dialogtexte als JSON paketieren |
| Bestehende Karten-/Formulatorpfade | `app/service.py`, `app/maps.py`, `app/providers/llm.py` | Unveraendert aus sicheren Kandidaten speisen |

### Existing tests and commands

- `python -m pytest tests/test_sessions.py tests/test_session_persistence.py tests/test_api.py tests/test_candidates.py tests/test_interpreter.py tests/test_safety.py`
- `python -m pytest`
- Frontend-Sicherheitspruefung: `tests/test_frontend_security.py`.
- Packaging: `tests/test_packaging.py` und `python -m build --no-isolation`.

### Working tree considerations

Branch `maintenance/repository-cleanup`, Ausgangscommit `9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`. Der Arbeitsbaum enthaelt die freigegebenen, nicht committeten Aenderungen aus Arbeitspaket 1 bis 3. Sie werden weder zurueckgesetzt noch bereinigt. WP4-Hunks bleiben auf Dialog, Session, API, Interpreterkontext, Frontend, Lokalisierungsressourcen, redigierte Beobachtbarkeit, Tests und passende bestehende Dokumentation begrenzt.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Zweiter Dialogzustand neben `pending_clarification` | Boolesches Feld liegt bereits in `ConversationSession` | Widerspruechliche offene Dialoge | Feld vollstaendig durch genau ein `DialogState` ersetzen | Referenzsuche und Persistenztests |
| Button erzeugt kuenstlichen Nutzertext | API akzeptiert aktuell nur `query` | Technischer Wert koennte sichtbar/logged oder fehlinterpretiert werden | Eigene `dialog_id`/`choice_values`-Felder; sichtbaren Text serverseitig aus lokalisiertem Label bilden | API-, Logging- und Frontendtests |
| Parallele Antwortversuche loesen zweimal aus | Persistenz sperrt nur einzelne Schreibvorgaenge | Doppelantwort und inkonsistente Fakten | Atomare Claim-/Complete-/Reopen-Operationen unter bestehendem Lock | Nebenlaeufigkeitstest |
| Sprachwechsel loescht Dialog | `SessionStore.resolve()` vergleicht Sprache auf Gleichheit | Mehrsprachiger Dialog bricht ab | Sprache aktualisieren, Zustand bei gleichem Fingerprint erhalten | de->ro, en->ru und Neustarttests |
| Freie LLM-Antwort `unter 27` erzwingt erfundenes Alter | Interpreter kennt nur numerisches `age` | U27-Button waere nicht ausdrueckbar | Striktes `age_group`-Faktum mit Konsistenzpruefung; kein Zahlenwert erfinden | Vertrags- und Selectorregression |
| Allgemeine Rueckfrage fuer jedes Conditional | Selector weist viele moegliche Luecken aus | Belastende Endlosschleifen | Nur vier explizite Dialogtypen; harte Versuchslimits | Dialogmatrix |
| Hilfebusdaten werden in Strings dupliziert | Aktuelle Texte nennen teils Hilfebus ohne strukturierte Dialogantwort | Veraltete Kontakte/Zeiten | Fakten ausschliesslich aus Runtime-Angebot, nur Satzschablone in Ressource | Datenherkunftstest |
| UI wird ohne Backendbindung implementiert | `app.js` kennt kein Klaerungsschema | Tote Buttons | API-Contract zuerst; DOM-Rendering und Submit gegen exakt denselben Contract | API-/Frontend-Smoke |
| `service.py` waechst weiter ueber 500 Zeilen | Datei hat bereits 531 Zeilen | Unwartbare Policy | Dialogpolitik kohesiv in eigenem Modul; Service nur orchestriert | Zeilen- und Importreview |
| Maschinelle Texte erscheinen geprueft | Fuenfsprachige Ressource ist neu | Falscher Qualitaetsstatus | Pro Sprache expliziter Reviewstatus; kein `reviewed` fuer ungepruefte Fassungen | Ressourcen-/Health-Test |

## Recommended approach

Ein neues kohesives Modul definiert Dialogvertrag, erlaubte Choices, Faktenzusammenfuehrung und die begrenzte Dialogpolitik. `SessionStore` bleibt alleinige Persistenz und erhaelt atomare Operationen fuer Oeffnen, Beanspruchen, Wiedereroeffnen und Abschliessen. `QueryService` interpretiert zuerst, beendet bei Safety/Scope, erkennt klare Themenwechsel, fuehrt den Selector mit ausdruecklichen Fakten aus und delegiert ausschliesslich explizite Klaerungsfaelle an die Dialogpolitik. Buttonantworten werden deterministisch aus dem gebundenen Dialog abgeleitet; Freitext und STT nutzen einen minimalen strukturierten Dialogkontext im Interpreter. Texte und Labels werden aus einer paketierten Ressource geladen.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Dialogzustand nur im Browser halten | Nicht manipulationssicher, nicht sprach-/session-/fingerprintgebunden und nicht fuer STT/API ausreichend |
| Choice-Wert in `query` kopieren | Technische Werte wuerden zu Nutzersprache und koennten als sensitive Angaben geloggt werden |
| Alle Antwortvarianten deterministisch parsen | Wuerde einen konkurrierenden sprachspezifischen Interpreterpfad schaffen |
| Kandidatenauswahl in die Dialogkomponente verschieben | Dupliziert den freigegebenen `CandidateSelector` und nimmt WP5 vorweg |
| Vollstaendige Angebotsdaten im Dialog speichern | Verletzt Datenminimierung und erzeugt veraltete Sessiondaten |
| Beliebig viele Rueckfragen aus `missing_information` generieren | Fachlich nicht freigegeben und belastend |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/dialogue.py` | Create | Strikte Dialogmodelle, Ressourcenbindung und begrenzte Policy | Mittel; zentraler neuer Zustand |
| `app/resources/bootstrap/dialogue/messages.json` | Create | Versionierte Texte/Labels fuer fuenf Sprachen mit Reviewstatus | Mittel; paketiert |
| `app/sessions.py` | Modify | Boolesches Feld ersetzen, Sprachwechsel erhalten, atomare Dialogoperationen | Hoch; Persistenz/Concurrency |
| `app/models.py` | Modify | Query-/Response-Klaerungsvertrag und redigierte Metadaten | Mittel; oeffentliche API |
| `app/interpreter.py`, `app/providers/llm.py` | Modify | Minimaler Dialogkontext und `age_group`, Prompt-/Vertragsversion | Mittel; strikte Providergrenze |
| `app/candidate_contract.py`, `app/candidates.py` | Modify | Ausdrueckliches Altersgruppenfaktum auswerten | Klein; Regression U27 |
| `app/service.py` | Modify | Dialogorchestrierung und Hilfebus-Fallback | Hoch; aktiver Kontrollfluss |
| `app/main.py`, `app/interactions.py` | Modify | Redigierte API-Fehler/Metadaten und Versionen | Klein |
| `app/static/index.html`, `app/static/app.js`, `app/static/styles.css` | Modify | Barrierearme Choice-UI und Submitpfad | Mittel; Browserzustand |
| `app/static/dialogue.js` | Create | Kohesives Rendering/Choice-State, um `app.js` nicht weiter aufzublaehen | Klein bis mittel |
| `tests/test_dialogue.py`, `tests/test_dialogue_frontend.py` | Create | Dialog-, API-, I18n-, Concurrency- und Frontendvertrag | Hoch, aber isoliert |
| bestehende Session/API/Interpreter/Candidate/Safety/Packagingtests | Modify | Vertrags- und Regressionserwartungen | Mittel |
| `README.md`, `docs/architecture.md`, `docs/data-flow.md`, `docs/testing.md` | Modify | Nur implementierten WP4-Stand dokumentieren | Klein; nach Implementierung |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: API-, Session-, Interpreter-, Selector-, Service-, Frontend-, Packaging- und Testpfade wurden vor der ersten Quellcodeaenderung verfolgt.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep new source files cohesive; retain the pre-existing oversized service orchestrator without an out-of-scope refactor.
- [x] Update this plan with discoveries.

Evidence: Dialogvertrag und -ressource liegen in `app/dialogue.py`, die begrenzte Politik in `app/dialogue_flow.py`; `SessionStore`, API, Service, Interpreter, Selector und Frontend verwenden diesen einen Zustand.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run syntax and JavaScript checks to the extent supported by the environment.
- [x] Run integration/build/clean-install checks.
- [x] Verify registration, runtime path, packaging and data minimization.
- [x] Review final diff.

Evidence: Dialog-/Kurations-/Selector-Fokussuite, komplette Pytest-Suite, `compileall`, Packagingtests, sdist/Wheel-Neubau, Clean-Install, lokaler Template-Smoke und `git diff --check` waren erfolgreich. Eine JavaScript-Laufzeit war nicht installiert; die statischen Frontend-Vertragstests liefen erfolgreich.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

Evidence: `README.md`, `docs/architecture.md`, `docs/data-flow.md` und `docs/testing.md` dokumentieren nur den implementierten WP4-Stand; die komplette Suite wurde danach erneut ausgefuehrt.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Dialog/API/Session | `python -m pytest tests/test_dialogue.py tests/test_sessions.py tests/test_session_persistence.py tests/test_api.py` | Alle Dialogtypen, Fehler und Persistenzfaelle korrekt |
| Interpreter/Selector/Safety | `python -m pytest tests/test_interpreter.py tests/test_candidates.py tests/test_safety.py` | Neuer Kontext ohne Auswahl-/Safetyregression |
| Frontend/I18n | `python -m pytest tests/test_dialogue_frontend.py tests/test_frontend_security.py` und `node --check` | Zugaengliche Buttons, keine technischen Werte, gueltiges JS |
| Vollstaendige Regression | `python -m pytest` | Gesamte Suite erfolgreich |
| Syntax | `python -m compileall -q app` | Keine Fehler |
| Build | `python -m build --no-isolation` | Wheel und sdist erfolgreich |
| Clean install | Wheel aus sdist neu bauen und in temporaerer Umgebung installieren/testen | Ressource und Laufzeit ausserhalb Checkout funktionieren |
| Template smoke | Lokale Anfrage/Choice ohne Provider | Kein externer Aufruf; Dialog und Hilfebus sicher |
| Diff | `git diff --check` und Review gegen Stand nach WP3 | Keine Whitespace-/Scopefehler |

## Rollback and recovery

Es gibt keine externe Mutation oder Datenmigration. Bestehende Sessiondateien werden beim Laden kontrolliert als Legacy behandelt und duerfen keinen alten Klärungszustand reaktivieren. Wegen der uncommitteten Nutzerarbeit waere ein Rollback ausschliesslich durch gezieltes Rueckgaengigmachen der in dieser Datei ausgewiesenen WP4-Hunks zulaessig; Reset-/Checkout-Befehle bleiben ausgeschlossen.

## Progress log

- 2026-08-01 — Review-First- und Code-Dokumentations-Skills sowie Vorlagen gelesen.
- 2026-08-01 — Vollstaendigen aktiven Session-, Interpreter-, Selector-, Service-, API-, STT- und Frontendpfad verfolgt.
- 2026-08-01 — Dead Ends, API-Grenzen, Persistenz- und Mehrsprachigkeitsrisiken vor Codeaenderungen dokumentiert.
- 2026-08-01 — Plan vor der ersten Quellcodeaenderung angelegt.

## Decision log

Implementation completion:

- 2026-08-01 - Strikten Dialogvertrag, atomare Sessionoperationen, Dialogpolitik, API und fuenfsprachige Ressourcen implementiert.
- 2026-08-01 - Button-, Freitext- und STT-Aufloesung sowie Themen-/Sprachwechsel, Safety-/Scope-Abbruch und kuratierten Hilfebus-Fallback integriert.
- 2026-08-01 - Barrierearme Frontend-Buttons, redigiertes Forschungslogging und Health-/Ressourcenbeobachtbarkeit ergaenzt.
- 2026-08-01 - Fokussierte und vollstaendige Tests, Build, Clean-Install, Template-Smoke, Syntax- und Diff-Pruefungen erfolgreich abgeschlossen.

- Decision: `age_group` ergaenzt das numerische Alter als ausdrueckliches, dreiwertiges Faktum.
  - Context: `unter 27` ist fachlich entscheidend, nennt aber kein exaktes Alter.
  - Options: Alter erfinden, Freitextheuristik im Selector, eigenes strikt validiertes Faktum.
  - Choice: Eigenes Faktum mit Konsistenzregeln zum numerischen Alter.
  - Consequences: U27 kann sicher erkannt werden; Volljaehrigkeit bleibt ohne Zahl ungeklärt.
- Decision: Buttonantworten umgehen nur den LLM-Interpreter, nicht den CandidateSelector.
  - Context: Der technische Wert besitzt bereits eine serverseitig gebundene, geschlossene Bedeutung.
  - Choice: Fakten/Bedarf deterministisch ableiten und danach denselben Selector aufrufen.
  - Consequences: Keine kuenstliche Nutzeranfrage und keine zweite Auswahlengine.
- Decision: Ein Sprachwechsel aktualisiert die Interface-Sprache und behaelt den strukturierten Dialog bei identischem Fingerprint.
  - Context: Aktuell wird die ganze Session geloescht.
  - Choice: Turns und Dialog erhalten; fuer Dialogauflösung nur strukturierte Fakten als Fachkontext verwenden.
  - Consequences: Mehrsprachige Antworten funktionieren, alte Assistententexte werden nicht als neue Fakten interpretiert.

## Discoveries

- `service.py` ist bereits deutlich ueber dem 400-Zeilen-Ziel; neue Dialogpolitik muss extrahiert werden.
- Browser- und Server-STT erzeugen bereits normalen Text, sodass kein sprachspezifischer Backendpfad erforderlich ist.
- Die paketierte Ressourcen-Glob umfasst neue JSON-Dateien unter `app/resources/bootstrap/**` ohne Packaging-Konfigurationsaenderung.

## Final verification summary

Additional discoveries:

- Eindeutige, aber nur bedingt passende A1- und Mobile-Angebote werden als bedingte Kontakte formuliert; eine Karte allein behauptet keine garantierte Eignung.
- `node`, `deno` und `bun` stehen in der Arbeitsumgebung nicht zur Verfuegung; JavaScript wurde daher durch statische Vertrags- und Sicherheitstests statt durch `node --check` geprueft.

- Acceptance requirements: erfuellt; kein paralleles `pending_clarification` und keine Arbeiten aus WP5 begonnen.
- Tests: komplette Suite mit 335 Tests erfolgreich; fokussierte Dialog-, Session-, API-, Selector-, Interpreter-, Safety-, I18n- und Frontendtests erfolgreich.
- Build: Wheel und sdist sowie Wheel-Neubau aus der sdist und Clean-Install ausserhalb des Checkouts erfolgreich.
- Manual verification: lokaler Template-Smoke ohne Provider fuer Schlafdialog und U27-Aufloesung erfolgreich; Runtime- und Ressourceninventar geprueft.
- Documentation: bestehende technische Dokumentation mit dem `code-documentation`-Verfahren aktualisiert und nachgetestet.
- Residual risks: keine echte Modellqualitaet oder Browserlaufzeit getestet; vier nichtdeutsche Dialogfassungen bleiben als maschinell entworfen und sprachlich ungeprueft gekennzeichnet; `acute_risk_status=uncertain` bleibt bewusst dem spaeteren Sicherheitspaket vorbehalten.
