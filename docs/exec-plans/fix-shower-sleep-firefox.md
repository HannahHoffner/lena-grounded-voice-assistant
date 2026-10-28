# Execution Plan: Duschen, Schlafabschluss und Firefox-Spracheingabe

## Status

- State: Complete — lokale Fehler korrigiert und geprüft; Live-STT offen
- Arbeitsbereich: Repository-Wartung
- Created: 2026-09-16

## Objective / Acceptance contract

- [x] Explizites Duschen verwendet belegte Duschangebote statt Toiletten oder einer allgemeinen Bedarfsrückfrage.
- [x] Die Schlafantwort „Frau“ endet ohne weitere Pflichtfrage mit klar bedingtem Scharni-Hinweis und bestehendem Erstkontakt; keine Volljährigkeit erfinden.
- [x] Firefox-Aufnahme, Transkriptionsfehler und Mikrofonzustand lokal nachvollziehbar behandelt; Recorder-/Transport-Doubles geprüft.
- [x] Minderjährigenschutz, bestehende öffentliche Schnittstellen, fünf Sprachen und bisherige Änderungen erhalten.

## Scope und Repository review

Der vorherige Qualitätsreview liegt vollständig ungestagt vor (33 Änderungen,
zwei neue Dateien). Diese Änderungen werden erhalten; kein Reset/Commit/Push.
Keine produktiven Provideraufrufe, keine Änderungen an Zugangsdaten oder
Angebotskuration. Der Nutzer bestätigt „Frau“ als Schlafantwort und Firefox auf
`http://127.0.0.1:8002/` mit der Meldung „nicht verstanden“.

Lokales Interaktionslog bestätigt `wo kann ich duschen?` -> `public_toilets`
und die Korrektur `Ich suche keine Toilette, Dusche.` -> `dialog_general_need`.
Der Interpretervertrag kennt `shower`, aber keine eindeutige Abgrenzung zum
Toilettenbedarf. Der Toiletten-Sonderpfad ignoriert explizite Duschleistungen.
`choose_dialog` öffnet auch bei konkret genannten allgemeinen Leistungen eine
erneute Bedarfsfrage. `service.py` erzwingt bei weiblich/unbekanntem Alter einen
weiteren SLEEP_AGE-Dialog; bestehende Tests verlangen das alte Verhalten.

Firefox verwendet ohne SpeechRecognition die vorhandene MediaRecorder-/STT-
Kette. Aufnahme endet erst beim zweiten Klick. `updateVoiceStatusReady` ersetzt
den Aufnahmestatus sofort durch „bereit“. Alle HTTP-/Netzwerkfehler erscheinen
als „nicht verstanden“; fehlgeschlagener Recorderstart kann Mikrofontracks
offenlassen. Lokale STT-Konfiguration nennt `faster-whisper-large-v3`; tatsächliche
Providererreichbarkeit bleibt ohne erlaubten Live-Aufruf unbestätigt.

## Wiederverwendung und Dead-end analysis

| Risiko | Entscheidung / Verifikation |
|---|---|
| Lexikalischen Parallelklassifikator einführen | Bestehenden Interpreterprompt präzisieren und widersprüchliche strukturierte shower/hygiene/laundry+toilet-Angaben vor Routing korrigieren; API-Regression |
| Aus „Frau“ Volljährigkeit machen | Alter unbekannt lassen; vorhandenen lokalisierten bedingten Scharni-Text plus Erstkontakt verwenden, keine weitere Pflichtfrage |
| Tests durch bloßes Löschen grünen | Alte Rückfrage-Assertions durch explizite Abschluss-, Alters-, Angebots- und Safety-Assertions ersetzen |
| Firefox pauschal als inkompatibel erklären | Echte JS-Aufnahmekette mit Ogg-only-Recorderdouble und synthetisches Ogg/Opus durch echten Decoder prüfen |
| Technischen Dienstfehler als fehlendes Sprachverständnis ausgeben | HTTP-Fehlerklassen im UI unterscheiden, lokalisierte Ressourcen ergänzen; keine internen Providerdetails anzeigen |
| Neue Architektur / neue Speechabhängigkeit | Bestehende Funktionen/Fehlerpfade erweitern; große app.js/service.py hier gezielt bearbeiten, keine generische Aufteilung |

## File impact / Recommended approach

| Dateien | Änderung |
|---|---|
| `app/interpreter.py`, `app/service.py`, `app/dialogue_flow.py` | Duschroute präzisieren, unnötige Rückfragen entfernen, bedingten Schlafabschluss konsolidieren |
| `app/static/app.js` | Aufnahme-/Fehlerzustände und Mikrofonfreigabe korrigieren |
| `app/main.py` | Sicheren STT-Fehlercode und Upstream-Status im normalen Serverlog sichtbar machen, öffentliche Fehlerantwort unverändert |
| `app/application_texts.py`, paketierte `application_texts.json` | Neue Speechtexte in fünf Sprachen, Copyversion erhöhen; Safetytexte unverändert |
| Bestehende API-/Dialog-/Speechtests, `tests/frontend.test.cjs` | Reale Integrationspfade und Fehlersituationen reproduzieren |
| `docs/data-flow.md`, `docs/setup.md`, dieser Plan | Geändertes Verhalten und weiterhin offene Live-Evidenz beschreiben |

## Milestones / Validation plan

1. [x] Relevante Quellen, Tests, Ressourcen, Konfiguration und konkrete Logs prüfen.
2. [x] Regressionen zunächst fehlschlagen lassen, gezielte Änderungen umsetzen.
3. [x] Betroffene Python-/JS-Tests, Syntax, Paketbau und Diff prüfen.
4. [x] `code-documentation` anwenden; Ursachen, Korrekturen und Grenzen berichten.

Prüfbefehle: `python -m pytest tests/test_dialogue.py tests/test_api.py
tests/test_candidates.py tests/test_speech_transcription.py tests/test_safety_policy.py
tests/test_translation_quality.py -q`; Node-Test des bestehenden CJS-Harness;
Syntaxchecks und `python -m build --no-isolation` in temporären Outputpfad.
Keine vollständige Wiederholung unabhängiger Testgruppen ohne Anlass.

## Rollback and recovery

Nur Änderungen dieses Plans gezielt zurücknehmen; vorherige Reviewhunks erhalten.
Keine Datenmigration, Löschungen oder neue Dependencies. Anwendungsressource und
Copyversion gemeinsam ändern. Alte SLEEP_AGE-Sessionverträge bleiben lesbar.

## Discoveries / Final verification summary

- Vor dem Fix scheiterten alle 15 neuen Dusch-/Schlaf-API-Fälle, drei neue
  Frontendfälle und die neue Prüfung der sichtbaren STT-Fehlerdiagnose.
- Danach erfolgreich: 412 unterschiedliche Python-Fälle aus den Gruppen
  `test_dialogue`, `test_api`, `test_candidates`, `test_speech_transcription`,
  `test_safety_policy`, `test_translation_quality`, `test_interpreter`,
  `test_packaging`, `test_dialogue_frontend`, `test_frontend_security`,
  `test_provider_timeouts`, `test_observability`. Wiederholte STT-Fälle wurden
  in dieser Summe nicht doppelt gezählt. Bestehende Starlette-Warnung unverändert.
- Neun Node-Verhaltenstests bestanden. Ogg-only-Aufnahme prüft Mikrofonfreigabe,
  Aufnahmehinweis, Upload und Transkriptübernahme. Synthetisches Ogg/Opus und
  WebM/Opus laufen zusätzlich durch echten API-Endpunkt und PyAV-Decoder;
  nur der externe STT-Transport ist ersetzt.
- Pakettests prüfen Wheel/Source-Archiv, isolierte Installation und Offline-
  Start. Python-/JS-Syntax und Diffprüfung erfolgreich. Keine neuen Dependencies.
- Interpreterprompt 9 präzisiert Duschen; Vertragsversion 4 bleibt gleich.
  Sprachcopy 9 ergänzt drei Hinweise in allen fünf Sprachen; alte Textinhalte
  einschließlich Safety sind unverändert. Neue Sprachfassungen sind nicht
  als menschlich freigegeben ausgewiesen.
- Der Schlafabschluss verwendet die bereits vorhandenen bedingten Texte direkt;
  auf „Frau“ per Button folgen weder zusätzliche Frage noch weitere Modellaufrufe.
  Freitext wird weiterhin sicher interpretiert. Minderjährige werden separat
  behandelt; „Frau“ wird nicht in „volljährig“ umgedeutet.
- Die abschließende Eigenprüfung hat zusätzlich einen Vorrangfehler gegenüber
  ausdrücklich genannten Organisationen reproduziert. Der bedingte allgemeine
  Schlafabschluss greift deshalb nur ohne Aliasbindung; die neue Schoppi-
  Regression schützt den bisherigen direkten Organisationspfad.
- Reale Firefox-/STT-Erreichbarkeit und Wirkung des geänderten Prompts auf das
  Live-Modell bleiben ohne produktiven Aufruf unbestätigt. Die frühere generische
  Fehlermeldung erlaubt keine sichere retrospektive Diagnose. Zukünftige Fehler
  unterscheiden Audio-/Transport-/Providerprobleme im UI bzw. redigierten Log.
- Für die manuelle Abnahme: Server mit neuem Code starten, Firefox neu laden,
  Mikrofon starten/stoppen, Transkript prüfen; Duschfrage und Schlafantwort „Frau“
  durchspielen. Kein öffentliches Deployment und keine Live-Freigabe behauptet.
