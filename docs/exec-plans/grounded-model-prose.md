# Execution Plan: Fragebezogene LLM-Formulierung wiederherstellen

## Status
Implemented / verified, 26.10.2026, Codex.

## Auftrag und Scope
Der Nutzer korrigiert ausdrücklich das Ziel: Die sichtbare Antwort muss vom LLM formuliert werden, ausschließlich auf Basis der ausgewählten freigegebenen KB-Fakten und der aktuellen Frage als Relevanzkontext. Die MA beschreibt in Chapters/5Solutionneu.tex:502–503 freie Textblöcke mit Claimtyp und Referenzen, keine Ausgabe durch Satzschablonen. Keine Thesisänderung, keine Commits/Tags/Pushes; Fachregeln, Daten und Providerkonfiguration unverändert.

## Review / Ausgangsstand
Code-HEAD fb773e9 plus eigene uncommittierte Rendereränderungen aus dem vorherigen Auftrag; diese nicht pauschal zurücksetzen. Provider akzeptiert derzeit ausschließlich Planvertrag 6. Historischer Vertrag 5, FormulatedSentence und Freitext-Grounding sind vorhanden und mit zahlreichen Positiv-/Negativtests abgesichert. Die Faktenprüfung bleibt endlich und lexikalisch, mit dokumentierten Fehlannahmen und Fehlalarmen. Kein allgemeines Wahrheitsversprechen. Transport, Budget, ein Retry und atomarer Templatefallback werden wiederverwendet.

## Entscheidung und Dead Ends
- Neuer produktiver Freitextvertrag 7 / Prompt 25 statt Umdeutung von Vertrag 6. Historische Typen/Prompts 5 und 6 ausdrücklich erhalten.
- JSON-Schema aus dem tatsächlichen Parser im Prompt. Ausgegeben wird akzeptierter Modelltext, kein nachträgliches Überschreiben durch Renderer.
- Referenz-, Zahlen-, Kontakt-, Zeit-, Rollen-, Claim- und Policyprüfung wiederverwenden. Unbelegte Garantien, falsche Leistungen/Angebotszuordnungen, Prompt-Injection und ungültige Referenzen gezielt testen.
- Kein zusätzlicher LLM-Judge in diesem Auftrag: Er würde Budget, Aufrufzählung und wissenschaftliche Messverträge verändern und wäre ebenfalls keine Wahrheitsgarantie. Beschränkungen der vorhandenen Prüfung offen dokumentieren; kein ungeprüftes Abschalten von Gates.
- Alte Plan-Runtime-Tests auf den neuen Protokollvertrag migrieren, ihren Prüfanlass (Fehlerschema, ungültige Nummern, Zielgruppe, Rolle, Primärreihenfolge) erhalten. Historische Renderer-/Planprüfungen nicht löschen.
- Produktiver Evidenzfilter darf keine internen Codes als Modellprosa nahelegen; aktuelle Frage bleibt untrusted und ist kein Faktenbeleg.

## Dateien / Umsetzung
formulation.py: Versionen und aktueller Freitextprompt; neuer kohäsiver formulator_prose.py: Parser/Schema und Kontext. answer_plan.py: historische Konstanten fixieren. providers/llm.py: produktiver Parser/Prompt. grounding.py: Typ und Assessment der neuen Freitextantwort, kein Text-Rendering. Tests an betroffenen Laufzeitgrenzen und neue Prosa-/Relevanzregressionen. README, docs und Ergebnis-/Traceabilitydateien gezielt aktualisieren.

## Prüfung
Nach Änderungen gezielte Tests. Abschließend vollständige Python-/JS-Suiten, sauberer Docker-Neubau und netzloser Containerlauf sowie Runtimeprüfung. Begrenzte synthetische Live-Diagnose für Beratung/Essen/Folgefragen und Negativfälle, keine vollständige Vierstufen-Evaluation vor neuem finalem Commit. Eigene Belege außerhalb des Repositorys unter LOCALAPPDATA/LENA/verification/2026-10-26-model-prose. Vorherkopie betroffener Dateien sichern. Keine Erfolgssimulation bei fehlendem Provider.

## Offene Grenzen
Freie Formulierung stellt endliche Faktenprüfung erneut vor semantische Grenzen. Fachlich hilfreiche und sprachlich geeignete Antworten müssen zusätzlich manuell beurteilt werden. Der alte finale Messstand und die vorbereitete manuelle Baseline werden durch diese Änderung nicht automatisch gültig. Abschließender gemeinsamer Codecommit und Messung bleiben erforderlich.

## Fortschritt
- Review und Plan abgeschlossen.
- Produktiver Textvertrag und atomare Textvalidierung umgesetzt. 388 gezielte Tests bestanden, 1 bekannter XFAIL. Zwei echte synthetische Anfragen erfolgreich mit Modelltext; Hunger benötigte Retry. Vollständige Suiten nativ und im netzlosen Container: 1521 bestanden, 1 strikter XFAIL, 1 bekannte Warning; JavaScript jeweils 19/19. Sauberer Neubau, Runtime, Healthcheck und Persistenz geprüft. Eigener Runtimecontainer samt Prüfvolume entfernt. Quell-/Testhashes stimmen mit Docker-Export überein. Historische Messungen erhalten; Diff und verification.json extern bereitgestellt. Selbstreview: keine Änderung an geschützten Routing-, Safety-, Fachregel-, Budget- oder Konfigurationsdateien; keine Secrets ergänzt. Code-documentation angewendet, lokale Dateilinks geprüft. Keine Routing-/Fachregeländerung.
