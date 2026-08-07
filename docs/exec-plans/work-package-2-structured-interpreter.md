# Arbeitspaket 2: Strukturierter LLM-Interpreter

## Status

- [x] Repository, Arbeitsbaum und aktiver Anwendungspfad geprüft
- [x] Anforderungen aus `4Approachneu.tex` gegen den Code abgegrenzt
- [x] Versionierten Interpretervertrag und Prompt implementieren
- [x] Alten ID-selektierenden Router vollständig stilllegen
- [x] Übergangsadapter in den bestehenden Auswahlpfad integrieren
- [x] Tests, Dokumentation und Paketartefakte aktualisieren
- [x] Vollständige Verifikation und Diff-Review durchführen

## Ziel und Paketgrenze

Der erste LLM-Aufruf interpretiert ausschließlich die freie Anfrage. Er liefert eine strikt validierte, sprachunabhängige Bedarfsbeschreibung ohne Angebotsdaten oder Angebots-IDs. Die vorhandene Angebotsauswahl bleibt bis zu späteren Arbeitspaketen als ausdrücklich bezeichneter deterministischer Übergangsadapter erhalten.

Nicht Bestandteil dieses Pakets sind die vollständige deterministische Kandidatenfilterung, ein mehrstufiger Rückfragedialog, eine neue LLM-Kandidatenauswahl, eine neue Sicherheitspolitik oder Änderungen an Thesis- und Präsentationsdateien.

## Ausgangsstand und Schutz bestehender Änderungen

- Branch: `maintenance/repository-cleanup`
- Ausgangscommit der uncommitteten Arbeitspakete: `9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`
- Arbeitspaket 1 liegt als vom Nutzer freigegebener, noch nicht commitierter Arbeitsbaum vor.
- Vor Beginn von Arbeitspaket 2 waren folgende Pfade bereits geändert oder neu: `.env.example`, `README.md`, `app/config.py`, `app/curation.py`, `app/i18n.py`, `app/kb_loader.py`, `app/main.py`, `app/models.py`, `app/offer_roles.py`, `app/providers/__init__.py`, `app/providers/llm.py`, `app/resources.py`, `app/resources/bootstrap/curation/`, `app/retrieval.py`, `app/service.py`, `app/sessions.py`, `docs/architecture.md`, `docs/configuration.md`, `docs/data-flow.md`, `docs/testing.md`, `docs/exec-plans/work-package-1-curation-model.md`, `tests/test_api.py`, `tests/test_curation.py`, `tests/test_observability.py`, `tests/test_packaging.py`, `tests/test_runtime_loader.py`, `tests/test_session_persistence.py`, `tests/test_sessions.py`, `tests/test_wfs_releases.py`, `tests/test_wfs_sync.py`.
- Diese Änderungen werden nicht zurückgesetzt. Der Abschlussreview trennt die zusätzlich durch Arbeitspaket 2 berührten Pfade und prüft den Gesamtdiff gegen den genannten Commit.

## Review des aktuellen Kontrollflusses

Der aktive Pfad in `QueryService` führt derzeit vor dem LLM Vageheits-, Selbstbeschreibungs- und Aliasprüfungen aus. Anschließend erhält `BlabladorProvider.route()` einen Angebotsindex und kann Angebots-IDs auswählen. Diese Kopplung widerspricht dem neuen Vertrag. Ein positives Risikosignal führt danach bereits zu einem festen sofortigen Abbruch; diese Eigenschaft bleibt erhalten und wird so umgeordnet, dass potenziell akute Texte nicht durch frühe Vageheits- oder Selbstbeschreibungslogik am Interpreter vorbeilaufen.

Der bestehende Formulator bleibt unverändert in seiner Rolle und erhält weiterhin ausschließlich die in Arbeitspaket 1 positiv gelistete Runtime-Sicht. Sessiontexte werden nur bei passendem Wissensbasisfingerabdruck berücksichtigt. Für den Interpreter wird der Kontext zusätzlich auf aktuelle Nutzeräußerungen begrenzt; alte Assistentenantworten und darin enthaltene Angebotsfakten werden nicht übertragen.

## Entwurfsentscheidungen

1. Ein eigenes Modul `app/interpreter.py` enthält Vertrag, Prompt, Alias-Hinweise und den temporären Adapter. Dadurch wachsen die bereits großen Dateien `app/service.py` und `app/providers/llm.py` nicht um eine zweite Verantwortlichkeit.
2. Der Provider erhält ausschließlich `interpret_query()`. Der bisherige `route()`-Pfad, `ProviderRoute`, `LLMRoute` und Router-Index-Hilfen werden entfernt, statt als Kompatibilitätsschatten bestehen zu bleiben.
3. Modellantworten werden als reines JSON mit Pydantic `extra=forbid` und strikten Typen validiert. Markdown-Codeblöcke, Prosa, unbekannte Felder, fehlende Pflichtfelder, ungültige Werte und interne IDs sind Vertragsfehler.
4. Fehler werden in redigierte Kategorien aufgeteilt: Timeout, HTTP/Provider, ungültiges JSON, Schemafehler und Vertragsverletzung. Ein Fehler erzeugt nie eine erfolgreiche Interpretation; der bestehende deterministische Fehlerpfad bleibt als Übergang erhalten.
5. Alias-Hinweise enthalten nur Aliastext, Aliasart und Mehrdeutigkeit. Sie enthalten weder Angebots-IDs noch vollständige Angebote oder WFS-Felder.
6. Der temporäre Adapter bildet nur den erkannten Bedarf auf die bestehenden Kategorien und Retrievalfunktionen ab. Arbeitspaket 3 ersetzt dessen Auswahl-/Filteranteile; Arbeitspaket 5 entfernt die verbleibende Übergangskopplung zugunsten der vorgesehenen Kandidatenstufe.
7. `acute_risk_status=detected` bewahrt den vorhandenen festen positiven Risikoabbruch. `uncertain` bleibt ein Signal für die spätere Sicherheitspolitik und löst in diesem Paket keine neue autonome Entscheidung aus.

## Geplante Dateien

- Neu: `app/interpreter.py`, `tests/test_interpreter.py`, dieser Ausführungsplan
- Erwartet geändert: `app/models.py`, `app/providers/llm.py`, `app/providers/__init__.py`, `app/service.py`, `app/main.py`
- Daten nur falls zur vollständigen Aliasabdeckung erforderlich: paketierter Kurationskatalog und dessen Manifestbindung
- Dokumentation: `README.md`, `docs/architecture.md`, `docs/data-flow.md`, `docs/testing.md` nur soweit das neue Laufzeitverhalten beschrieben werden muss
- Bestehende Tests: insbesondere API-, Provider-, Safety-, Observability- und Sessiontests

## Implementierungsmeilensteine

### 1. Vertrag, Prompt und Parser

- Geschlossene Enums und strikte Faktenmodelle definieren.
- Begrenzte unsichere Hinweise und fehlende Informationen modellieren.
- Prompt- und Vertragsversion exportieren.
- Reines JSON und semantische Vertragsverbote prüfen.
- Redigierte Providerfehler zuordnen.

### 2. Aktiven Kontrollfluss umstellen

- `interpret_query()` ohne Angebotsindex aufrufen.
- Positiven Risikoabbruch unmittelbar nach erfolgreicher Interpretation ausführen.
- Scope und bestehende feste Domänenantworten kontrolliert verbinden.
- Aliasauflösung und Retrieval ausschließlich nach dem Übergangsadapter ausführen.
- Alten Router und alle ID-selektierenden Aufrufstellen entfernen.

### 3. Kontext, Aliasdaten und Beobachtbarkeit

- Nur fingerprint-kompatible, begrenzte Nutzeräußerungen übertragen.
- Minimale Aliasliste aus der kuratierten Runtime-Projektion bilden.
- Health-Ausgabe um Interpreter-, Vertrags- und Promptversion ergänzen, ohne Prompts oder Nutzerdaten zu protokollieren.

### 4. Tests und Dokumentation

- Vertrag, Parserfehler, Injection, Mehrsprachigkeit, Korrekturen, Themenwechsel, Aliase, Scope und Risiko testen.
- Bestehende Router-Test-Doubles auf den Interpretervertrag umstellen.
- Kontrollieren, dass weder IDs 1–4 noch andere Angebots-IDs oder Rohfelder den Interpreter erreichen.
- Technische Dokumentation auf den tatsächlich aktiven Pfad aktualisieren.

## Verifikation

Geplant sind fokussierte Interpreter-, Provider-, Alias-, Session-, Scope-, Safety- und API-Tests, danach die vollständige Testsuite, Syntaxprüfung, Wheel- und Source-Distribution-Bau, Clean-Install außerhalb des Repositorys, Template-Smoke ohne Provider, `git diff --check` und ein Gesamtdiff-Review gegen `9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`.

Ausgeführt und erfolgreich:

- fokussierte Interpreter-, API-, Curation-, Safety-, Timeout- und Observability-Suite
- vollständige lokale Suite mit 276 Tests
- `python -m compileall -q app`
- `python -m build --no-isolation` einschließlich Wheel und Source Distribution
- `tests/test_packaging.py` einschließlich Clean-Wheel-Installation außerhalb des Checkouts
- Template-Smoke für Health und Query ohne externen Provider
- `git diff --check`

Es wurde kein realer Modell-, Speech- oder WFS-Provider aufgerufen. Die einzige
Warnung stammt aus der vorhandenen Starlette-TestClient-Kompatibilität mit der
installierten HTTPX-Version.

## Risiken und bewusste Grenzen

- Automatisierte mehrsprachige Test-Doubles belegen Schema und Kontrollfluss, nicht die reale linguistische Modellqualität.
- Die Übergangsauswahl besitzt weiterhin die bestehenden heuristischen Grenzen; sie wird nicht als Zielarchitektur ausgegeben.
- Die endgültige Rückfrage- und `uncertain`-Risikopolitik bleibt späteren Paketen vorbehalten.
- Ein Sprachwechsel kann wegen der bestehenden Sessionauflösung weiterhin Kontext verlieren; die Fingerprintprüfung wird nicht aufgeweicht.
- Es wird kein paralleler Legacy-Router als Fallback beibehalten. Bei Interpreterfehlern greift nur der klar abgegrenzte deterministische Altpfad.
