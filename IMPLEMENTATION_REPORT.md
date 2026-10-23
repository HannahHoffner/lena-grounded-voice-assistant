# Umsetzung des LENA-Audits

Stand: 23.10.2026. Ausgangspunkt: Commit `597e1f0216c72eedd01b7b9e6d49be67ca8150f9` im kanonischen Repository `code`. Die vier Audit-Dokumente wurden vollständig gelesen. Bestehende Änderungen an der Thesis und Forschungsdaten bleiben unberührt.

## Arbeitsplan und Abgrenzung

1. **Faktenprüfung:** Aussagen unabhängig vom vom Modell vergebenen Claimtyp prüfen; vorhandene Evidence-, Fachregel- und Constraint-Module wiederverwenden. Unbekannte Leistungen dürfen nicht über `action` oder `fact` freigegeben werden. Positive Paraphrasen und negative Gegenbeispiele bilden den Regressionstest.
2. **Provider:** explizite Sprachdienst-Konfiguration, keine stillschweigende TTS-Vererbung des LLM-Zugangs; nachvollziehbare Konfigurationspriorität und datensparsame Statusinformationen. Textbetrieb bleibt ohne externe Dienste möglich.
3. **Orchestrierung/Persistenz/Logging:** gemeinsame Formulator-Aufrufsteuerung aus der fachlichen Orchestrierung lösen; Dialogreservierungen nur nach erfolgreicher Persistenz bestätigen; strukturierte technische Diagnose ohne Gesprächsinhalte oder Secrets.
4. **Reproduzierbarkeit:** alle 42 Anforderungen und 13 Fachregeln in der Traceability erhalten; README und vollständige Konfigurationsvorlage aktualisieren. Historische Retrieval-, Evaluations- und Datenartefakte erhalten und abgrenzen. Kein Compose ohne zusätzlichen notwendigen Dienst.
5. **Verifikation:** gezielte Tests, vollständige Python-/JavaScript-Suiten, unabhängiger Docker-Neubau und Laufzeitprüfungen einschließlich Volume/Neustart/Port/Health, fehlender Zugangsdaten und verfügbarer externer Dienste.

## Architektur und Wiederverwendung

Die bestehende Pipeline aus kuratierten Releases, deterministischer Kandidatenauswahl/Fachregeln, Evidence-Projektion, LLM-Formulierung und nachgelagerter Grounding-Prüfung bleibt erhalten. Änderungen erfolgen an den bestehenden Modulgrenzen; es wird keine zweite Datenbasis und kein zusätzlicher Modellanbieter eingeführt. `SessionStore` bleibt für den dokumentierten Einprozessbetrieb dateibasiert. Für die lokale Forschungsanwendung sind Datenbank, Ollama und GPU keine Voraussetzung.

Betroffene Bereiche: `app/grounding*`, `app/config.py`, `app/speech.py`, Provider-Aufrufsteuerung, `app/service.py`, `app/sessions.py`, `app/main.py`, technische Protokollierung, zugehörige Tests und die ausdrücklich beauftragten Ergebnisdokumente. Bei notwendigen Ergänzungen werden kleine, klar abgegrenzte Module verwendet.

## Schutz bestehender Artefakte und Rücknahme

Es werden keine historischen Daten, Evaluationen, Thesis-Dateien oder alten Implementierungen auf Verdacht gelöscht. Die vier Audit-Dateien sind Ausgangsbefunde, keine Behauptung über den späteren Umsetzungsstand. Laufzeitprüfungen verwenden eigene temporäre Verzeichnisse, Container und Volumes. Ein Rückbau erfolgt durch gezieltes Zurücknehmen des Implementierungsdiffs; vorhandene Nutzeränderungen werden niemals pauschal zurückgesetzt.

## Prüfprotokoll

Noch offen: gezielte und vollständige Tests sowie Docker-/Provider-Prüfungen nach den Änderungen. Bisher wurde in diesem Umsetzungsauftrag kein Erfolg eines geänderten Systems behauptet.

## Bewusste Grenzen

Eine endliche deterministische Grounding-Prüfung ist keine allgemeine semantische Wahrheitsgarantie. Datenrechte, fachliche Aktualität und empirische Wirksamkeit lassen sich nicht allein durch Codeänderungen belegen. Die bekannte, streng markierte sprachliche XFAIL-Regressionsstelle wird nicht verdeckt.
