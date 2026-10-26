# Aus Fakten gebildete Antworten und gebundene Unbekanntheitsaussagen

## Status, Ziel und Vertrag

2026-10-25, implementiert und geprüft; Live-Gates teilweise negativ. Ausgangscommit `15a912f`; uncommittierte
Werkzeuge und Dokumentation des Promptvergleichs bleiben erhalten.
Skills `review-first-coding` und `code-documentation` werden angewandt.

Ziel: Richtige Fakten und fehlende Angaben ohne lexikalische Bedeutungsprüfung
ausgeben, unbelegten Modelltext strukturell von der produktiven Ausgabe trennen.
Interpreter → Fachregeln/Kandidaten → Selector → Formulator → Prüfung/Renderer
bleibt erhalten. Kein zusätzlicher produktiver LLM, keine Änderung an Thesis,
Kuration, Quellen, Auswahl-, Safety-, Session- oder Persistenzregeln.

- [x] Neuer Antwortplanvertrag 6: nur erlaubte Akte, Angebots-/Faktenkennungen,
  Unbekanntheitsgründe oder passende Policies; kein frei generierter Ausgabetext.
- [x] Fakten werden unverändert aus demselben Evidence-Angebot eingesetzt.
  Zugang, Zielgruppe, Alter und Leistungszeitbedingungen können nicht durch
  Weglassen im Plan verschwinden. Namen/Kontakte/Zahlen bleiben quellgebunden.
- [x] Unbekanntheitsakte bei expliziten bekannten Preis-/Zeit-/Zugangsfakten
  ablehnen. Keine globale Abwesenheit aus fehlenden typisierten Feldern ableiten;
  stattdessen begrenzte Nicht-Zusage. Aktuelle Verfügbarkeit ist
  durch statische Daten nie garantiert. Sonstige Details erhalten ausdrücklich
  eine begrenzte Nicht-Zusage statt einer Behauptung, eine Leistung existiere nicht.
- [x] Alle fünf Sprachen, soziale Angebote, Toiletten und Trinkwasser.
- [x] Ausschluss beliebigen Textes, fremder Fakten, erfundener Kennungen,
  fehlender Bedingungen und ungeeigneter Policies durch Negativtests.
- [x] Legacy-Vertrag 5 und Wortvalidator als klar benanntes Forschungsartefakt
  erhalten. Produktiver Provider akzeptiert ausschließlich Vertrag 6.
- [x] Vollständige Python-/JS-Regression, unabhängiger Dockerneubau mit Tests,
  Start/Health/Volume, fehlender Zugang und begrenzte neue synthetische Liveprüfung.
- [x] Berichte, README, Konfiguration-/Architekturdokumentation und Traceability
  fortschreiben; keine menschliche Evaluation behaupten.

## Review und Wiederverwendung

`formulation.py` definiert Evidence 4, freien Antwortvertrag 5 und Prompt 22.
`providers/llm.py.formulate_answer` parst den Vertrag, ruft `validate_formulation`
auf und gibt erst danach `ProviderAnswer` zurück. `llm_stages.py` enthält Budget,
Retry und atomaren Template-Rückfall; die Live-Evaluation verwendet denselben
Einstieg. `grounding_references.py` prüft Faktenzugehörigkeit; `grounding*` prüft
Freitext mit endlichen Wortlisten. Die Vergleichsdaten belegen Fehlablehnungen
korrekter Unbekanntheits-/Negationsaussagen und Lücken unbekannter Prädikate.

Wiederverwendet werden Evidence-Angebote, Faktenkennungen, Providertransport,
Ausgabebegrenzung, Kartenordnung, Retry-/Diagnosevertrag und bestehende Tests.
Der neue Renderer kennt ausschließlich das vorgelegte Evidence-Paket, keinen
Provider, KB-/Sessionzugriff oder Fachregeln. Der historische Freitextvalidator
bleibt getrennt und wird im produktiven Provider nicht als Alternative aufgerufen.

Keine AGENTS-Dateien im Repository und übergeordneten Workspace gefunden.
Der bestehende Arbeitsbaum des Promptvergleichs wird nicht überschrieben.
Plan und Belege vom 24.10. bleiben historische Nachweise.

## Entscheidung und Dead Ends

| Risiko / Alternative | Entscheidung, Begründung, Prüfung |
|---|---|
| Mehr Wörter/RegEx ergänzen | Verworfen: keine semantische Vollständigkeit. Stattdessen Faktenauswahl/Antwortakt ohne freie Faktensätze |
| Beliebigen Text als uncertainty deklarieren | Verboten: Grund ist geschlossener Enum, Text wird ausschließlich serverseitig formuliert |
| Fakten aus anderem Angebot | Jede Referenz gegen genau das gebundene Angebot prüfen; keine globalen Faktenpools |
| Einschränkungen verschwinden durch Auswahl | Relevante Zugang-/Alter-/Zielgruppen-/Zeitbedingungen serverseitig mitführen; bei Überschreitung kontrolliert abbrechen, nicht kürzen |
| Rohcodes werden sichtbare Sprache | Interne Capability-/Typkennungen nicht als auswählbare Prosa; strukturierte Einschränkungen lokalisiert darstellen |
| Alte Freitextantwort wird still weiter akzeptiert | Liveadapter parst nur neuen Planvertrag. Historische Modelle/Tests behalten explizit Vertrag 5 |
| Tests werden auf grün getrimmt | Alte Wortvalidator-Regression bleibt unverändert; notwendige Wire-/Versionsanpassungen separat ausweisen und neue tatsächliche Provider-/API-Negativfälle hinzufügen |
| Vier-Stufen-Evaluation misst alten Adapter | Gleicher produktiver Einstieg `formulate_answer`, nur strikter neuer Parser; Manifest-/Prompt-/Validatorversionen fortschreiben |
| Sichere Faktenausgabe wird Wahrheitsgarantie | Nur Treue zu freigegebenen Fakten. Datenaktualität, Interpreter-/Auswahlqualität und Sprachprüfung bleiben eigene Grenzen |
| Neue Legacy-Brücke / Konfigurationsschalter | Kein runtimefähiger Umschalter zum alten freien Vertrag |

## Dateiauswirkungen

| Datei | Änderung |
|---|---|
| `app/answer_plan.py` | Neuer strikter Planvertrag, Referenz-/Akteprüfung und deterministischer Renderer, unter 400 Zeilen angestrebt |
| `app/answer_act_texts.py` | Geschlossene, fünfsprachige Ausgabeakte und Labels, maschinell erstellt, nicht als sprachlich reviewed markieren |
| `app/formulation.py` | Produktive Versionen/Prompt; Legacy-Konstanten ausdrücklich erhalten; Evidence bleibt Datenquelle |
| `app/grounding.py`, `app/providers/llm.py` | Produktiven Plan prüfen/rendern; Legacy-Wortvalidator nur historisch |
| `app/live_evaluation*.py`, `app/prompt_comparison.py` | Nur erforderliche Protokoll-/Messkompatibilität, keine Gateabschwächung |
| `tests/test_answer_plan.py`, bestehende Wire-/Versionsprüfungen | Neue Pfade und Angriffsflächen; historische Tests explizit kennzeichnen |
| README, docs, Ergebnis-/Thesishinweise und Traceability | Korrekte Architektur, Freiheitsgrad und tatsächliche neue Prüfungen |

## Meilensteine / Prüfplan

1. [x] Ausgangsstand und betroffene Aufrufketten geprüft, Plan vor Codeänderung.
2. [x] Planvertrag/Renderer, fehlende Information, Bindungen und fünf Sprachen.
3. [x] Providerintegration, Legacyabgrenzung, positive/negative gezielte Tests.
4. [x] Vollständige native Suite/JS; Testlaufzeit der vorigen 80-Minuten-Suite
  beobachten und tatsächliche Dauer protokollieren. Keine Tests entfernen.
5. [x] Clean-Room-Dockerbuild/-Tests und Runtimeprüfungen, echte synthetische
  Blablador-Prüfung mit festgehaltenem Code-/Daten-/Modellstand.
6. [x] Eigenreview nach Skillvorlage, `code-documentation`, Berichte, offene
  Grenzen und notwendige Thesisänderungen (Thesis selbst unverändert).

## Rücknahme / Risiken / Fortschritt

Keine Datenmigration und keine Löschung. Der alte produktive Stand ist in
`15a912f` und den Nachweisarchiven gesichert. Neue Verträge müssen an allen
Provider-/Live-Messstellen erkennbar sein. Die neue Ausgabe ist kontrollierter
und weniger frei formuliert; diese bewusst geänderte Eigenschaft muss in der
Thesis erklärt und qualitativ bewertet werden. Nicht mit besserer allgemeiner
semantischer Erkennung gleichsetzen: freie Faktensätze werden strukturell
verhindert, nicht durch einen perfekten Bedeutungsprüfer erkannt.

2026-10-25: Eigenreview und Prüfungen abgeschlossen. 1419 Python + 1 XFAIL
und 19 JS nativ sowie im neuen netzlosen Testcontainer. HTTP-/Volume-/TTS-Smoke
bestanden; vier Live-Stufen erhoben, nur Interpreter-Gates bestanden. Siehe
`docs/controlled-answer-acts.md` und IMPLEMENTATION_REPORT.md Abschnitt 10.
