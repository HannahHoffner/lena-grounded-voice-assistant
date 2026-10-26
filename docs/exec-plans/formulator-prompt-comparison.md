# Vergleich faktengebundener Formulator-Prompts

## Status

- Zustand: Complete (Vergleich abgeschlossen; keine produktive Übernahme)
- Erstellt: 2026-10-24; Verantwortlich: Codex
- Ausgangscommit: `15a912f`; Arbeitsbaum vor Beginn sauber.
- Skills: `review-first-coding` und `code-documentation` gelesen und angewandt.

## Ziel und Abnahmekriterien

Der beauftragte, begrenzte Vergleich soll feststellen, ob ein engerer
Formulierungsauftrag belegte, hilfreiche Antworten mit weniger unbelegten
Ergänzungen erzeugt. Erst danach über eine Übernahme entscheiden.

- [x] Vor Liveaufrufen Fragen, Belegpakete, Prüfkriterien und beide Prompts einfrieren.
- [x] Alle fünf Sprachen; richtige Information, fehlende Information, Widerspruch,
  Rollen, Angebotszuordnung, Bedingungen und Manipulationsversuche abdecken.
- [x] Gleiche Belegpakete und Parameter, ausgeglichene Aufrufreihenfolge,
  keine Wiederholung bis zum gewünschten Ergebnis.
- [x] Ungefilterte Antwortentwürfe, Provider-/Schemafehler und Grounding-Ergebnis
  getrennt sichern; keine ungeprüften Antworten im Anwendungsbetrieb ausliefern.
- [x] Semantische Einzelbewertung mit Begründung; kein LLM-Judge als menschliche
  Referenz deklarieren. Externe menschliche Bewertung bleibt offen.
- [x] Auswahlentscheidung einschließlich verbleibender Risiken dokumentieren.
- [x] Gezielte und vollständige Regression; bei produktiver Promptänderung
  Version aktualisieren, neu bauen und Runtime-Smoke durchführen.

## Umfang und Grenzen

Enthalten: reproduzierbares Vergleichswerkzeug, synthetischer Prüfsatz,
ein eingefrorener Kandidatenprompt, echte Blablador-Aufrufe, dokumentierte
Einzelbewertung und passende Ergebnis-/Thesishinweise. Keine Änderung von
Thesis, Datenbeständen, Fachregeln, Auswahl, Grounding-Gates oder Sitzungssystem.
Keine Abschwächung bestehender Tests. Kein zusätzlicher produktiver LLM-Judge.
Loggingreparatur und Browserprüfung sind eigene offene Arbeitspakete.

## Repositoryreview

`app/providers/llm.py:BlabladorProvider.formulate_answer` sendet Prompt und
`FormulatorEvidence`, parst den Vertrag und ruft `validate_formulation` auf.
Der aktuelle Prompt ist Version 22, Vertrag 5. Das Belegpaket enthält aktuelle
Frage, Bedarf und ausgewählte Angebotsfakten, keinen freien Gesprächsverlauf.
`app/llm_stages.py` führt begrenzte Retrys und Template-Rückfall aus.
Die Probleme N-01/N-02 betreffen die endliche semantische Wortprüfung;
sie darf weder als Goldstandard dienen noch im Betrieb still abgeschaltet werden.

Wiederverwendung: Providertransport einschließlich Timeout und Modellkennung,
bestehende Pydantic-Verträge, `validate_formulation`,
`live_evaluation_plan.collect_git_state` und `resources.checkout_root`.
Das Vergleichswerkzeug erweitert nicht die versionierten vier Live-Gates:
sein kontrollierter synthetischer Eingriff in den Systemprompt wird als eigene
diagnostische Studie mit Manifest und Quellhashes geführt.

Bestehende Tests: `test_formulation.py`, `test_grounding_content.py`,
`test_formulator_factual_freedom.py`, `test_live_evaluation*.py`.
Keine AGENTS-Anweisungen in den geprüften Verzeichnissen gefunden.

## Dead Ends und Entscheidungen

| Risiko / Alternative | Entscheidung und Nachweis |
|---|---|
| Promptänderung ohne ungefilterte Messung | Beide Entwürfe vor Gate sichern; gleiche vorhandene Parser-/Groundingstrecke weiter ausführen |
| Eigener API-Client dupliziert Transport | Evaluations-Unterklasse ersetzt ausschließlich Systemprompt in `_post`; ruft bestehenden Transport auf |
| Referenzfälle an neues Modellverhalten anpassen | Feste erwartete Fakten/Verbote und Entwicklungs-/zurückgehaltener Teil vor erstem Aufruf hashen |
| Menschliche Goldbewertung vortäuschen | Erwartete Bedingungen synthetisch vorab festlegen; Bewertung durch Codex separat kennzeichnen, menschliche Reviewfelder offen lassen |
| Hohe Ablehnung mit hoher Halluzination verwechseln | Modellentwurf, Schema, Filter und Semantik getrennte Spalten |
| Prototyp durch neuen Prüfprovider verkomplizieren | Kein produktiver Judge; Entscheidung über einfachsten belegbaren Ansatz |
| Geheimnisse in Rohreports | Nur synthetische Eingaben, Antwortinhalt und ausgewählte Metadaten; keine Header, Envwerte oder freien Exceptiontexte; Secret-Gegenprüfung vor Archivierung |

## Messprotokoll vor Ausführung

12 Szenariofamilien × 5 Sprachen = 60 Belegpakete. 8 Familien Entwicklung,
4 Familien vorab zurückgehaltener Abschlussteil. Zwei Arme (`baseline`,
`candidate`), je ein Erstversuch pro Paket, keine Reparatur/Retrys.
Zusätzlich je Arm 5 vorab benannte Wiederholungen aus dem Abschlussteil
(eine Sprache pro Familie im Wechsel), maximal 130 Provideraufrufe.
Die Reihenfolge wechselt pro Paket; beide Arme desselben Pakets laufen
unmittelbar nacheinander. Höchstens 2 parallele Pakete; identische Modell-,
Token- und Timeoutparameter. Kein isolierter Performancebenchmark.

Vorab notwendige Freigabebedingung: keine neue schwerwiegende unbelegte
Leistungs-/Zugangs-/Verfügbarkeitsbehauptung im Kandidatenarm und keine
schlechtere belegte Antwortfähigkeit im Abschlussteil. Alle Ausfälle werden
mitgezählt. Ein kleiner Stichprobenvorsprung beweist keine allgemeine
Überlegenheit; bei uneindeutigem Ergebnis bleibt der produktive Prompt erhalten.
Ein produktiver Kandidat darf nur bei dokumentiert überzeugendem Befund
übernommen werden. Ein positives Resultat allein löst N-01/N-02 nicht.

## Dateiauswirkungen

| Pfad | Zweck |
|---|---|
| `app/prompt_comparison.py` | Abgegrenzter Evaluations-CLI, keine API-Route |
| `app/prompt_comparison_cases.py` | Deklarative synthetische Fragen, Fakten und Referenzkriterien, auch im Wheel verfügbar |
| `tests/test_prompt_comparison.py` | Kein Netzwerk: Datenkontrakt, Prompt-/Evidenzgleichheit, Grenzen, Fehler- und Reportverhalten |
| `docs/formulator-prompt-comparison.md` | Reproduktion, Auswertung, Entscheidung und Grenzen |
| `app/formulation.py`, `tests/test_formulation.py` | Nur bei begründeter Übernahme: Promptversion und dazugehöriger Vertragstest |
| `IMPLEMENTATION_REPORT.md`, `THESIS_UPDATE_NOTES.md`, `THESIS_CODE_TRACEABILITY.md`, `README.md` | Tatsächliches Ergebnis und Reichweite |

Keine neuen Abhängigkeiten, keine Secrets im Repository. Rohreports außerhalb
von Cloudsync unter `%LOCALAPPDATA%/LENA/verification/`.

## Meilensteine und Prüfplan

1. [x] Review, Wiederverwendung, Scope, persistenter Plan.
2. [x] Synthetische Belegpakete und Kandidatenprompt festlegen; Offlinewerkzeug
   und Tests; Dry-Run/Hashes vor Live.
3. [x] Entwicklungsteil durchführen, erste Bewertung; ohne Promptänderung
   Abschlussteil durchführen. Einzelbewertung, ausgeglichene Ergebniszählung.
4. [x] Auswahlentscheidung: keine produktive Übernahme; kein Gate abgeschaltet.
5. [x] `python -m pytest` vollständig; `node --test tests/frontend.test.cjs`;
   `git diff --check`; bei produktiver Änderung Dockerneubau, netzlose
   Container-Suite und Start/Health-Smoke.
6. [x] `code-documentation`: tatsächliche Architektur/Diff, Befehle und Links
   prüfen; Ergebnisdateien fortschreiben; abschließende Eigenreview.

## Rücknahme und Wiederaufnahme

Produktiver Prompt bleibt bis zur Entscheidung unverändert. Alle Rohantworten
werden nach jedem Aufruf geschrieben; Teilerhebungen als unvollständig
kennzeichnen und nicht still ergänzen oder überschreiben. Bei Fehlern keine
Secrets oder Providerantworten in Exceptionausgaben. Alte Messungen bleiben
unverändert standgebunden gültig; diese Studie ersetzt keine vierstufige E2E.

## Fortschritt / Entdeckungen / Abschluss

- 2026-10-24: Ausgangsstand und Prompt 22 geprüft. Erst ein Vergleich,
  keine vorweggenommene Entfernung der Faktenprüfung.
- 2026-10-24: 60 Pakete und beide Prompts eingefroren; externe Studie
  `%LOCALAPPDATA%/LENA/verification/2026-10-24-formulator-prompts`.
  Manifest: Fragen/Fakten/Kriterien SHA256
  `d0cfe65dee9b18c64777674238cbb42fed4fc004c5f8064f346f019f1d55d48d`;
  Baseline `d41ec435…ca536`, Kandidat `6438cd66…5b04`.
  Alle App-Pythondateien vor Aufruf gehasht. 9 neue Offlineprüfungen bestanden;
  bestehende Formulator-/Grounding-Teil-Suite ebenfalls erfolgreich (ein
  bekannter XFAIL). Keine Änderung produktiver Prompts oder Gates.
- Vorläufige Beobachtung: richtige Unbekanntheits-/Altersformulierungen werden
  auch vom bestehenden Gate verworfen; Schema- und Transportfehler getrennt
  erfasst. Das synthetische Altersbeispiel prüft den Formulatorvertrag und
  beschreibt keinen Nachweis, dass der reguläre Dialogpfad diesen Fall an
  den Formulator weitergibt. Keine Änderung des Kandidaten nach Sichtung.
- Abschluss: 130 ursprünglich registrierte Aufrufe vollständig; nach
  Providerfehlern ein ausdrücklich separat registrierter Ergänzungsdurchgang
  mit 30 Aufrufen. Originaldaten unverändert. Keine Promptanpassung nach Sichtung.
- Originaler Abschluss (25 je Arm inkl. Wiederholungen): Gateakzeptanz 3/10,
  nach Codex belegte hilfreiche Entwürfe 23/25 (Baseline/Kandidat).
  Alle 50 HTTP-Statuswerte 200. Im ursprünglichen Entwicklungsteil je 15
  Providerfehler; genaue Upstreamursache nicht erhoben, kein Rate-Limit behaupten.
- Entscheidung: Kandidat günstiger, aber kein Nachweis ausreichender
  Gesamtfunktion. Ein ausdrücklich modellierter Antwortakt für fehlende
  Information und die Grenzen der semantischen Wortprüfung müssen strukturell
  behandelt werden. Keine Wortlistenergänzung, kein zusätzlicher produktiver
  LLM-Judge und keine Abschwächung bestehender Tests in diesem Auftrag.
- Fach-/Sprachreview durch unabhängige Menschen bleibt offen. Einzelurteile
  sind ausdrücklich von Codex. Synthetische Zeitbedingungen sind nicht im
  kanonischen Runtime-Builderformat; Ergebnisse nicht auf sämtliche echten
  Hilfebus-Belegpakete verallgemeinern.
- Vollständige native Suite 1355 bestanden / 1 bekannter XFAIL, 4795,88 s;
  JS 19/19, beide Syntaxprüfungen erfolgreich. Zwölf neue Offlinefälle.
  Kein neuer Dockerlauf: produktive Verarbeitung/Dependencies unverändert.
- `code-documentation` angewandt: Versuchs-/Ergebnisdokument,
  Implementierungsbericht, Thesishinweise, Traceability und README aktualisiert.
  README korrigiert auch die durch die Nachprüfung widerlegten Aussagen zur
  umfassenden Claimtypunabhängigkeit, PL/RO-Fakten und Logging.
- Abschlusskontrolle: alle gemessenen App-Quellhashes weiterhin identisch;
  42 Anforderungen/13 Fachregeln vollständig im Register, interne Links und
  `git diff --check` geprüft. Kein Treffer tatsächlich konfigurierter Secrets
  in den externen Studienbelegen. Keine Thesisänderung und kein Commit.
