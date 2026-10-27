# Execution Plan: Lokales Audio aktivieren und pruefen

## Status

- State: Complete; Audiofunktion in Firefox durch Nutzerin bestaetigt
- Owner: Codex
- Created: 2026-10-27
- Last updated: 2026-10-27

## Objective and acceptance contract

Die native LENA-Instanz auf `http://127.0.0.1:8002` soll in Firefox
Server-Spracherkennung und Vorlesen anbieten.

- [x] Lokale Profile `blablador` (STT) und `edge` (TTS) aktivieren.
- [x] Externe Dienste mit ausschliesslich synthetischen Inhalten pruefen.
- [x] Laufende Instanz neu starten; reale HTTP-Audioendpunkte pruefen.
- [x] Pruefergebnis und verbleibenden manuellen Hoertest ehrlich dokumentieren.
- [x] Keine Secrets, Thesis-, Quelldaten-, Safety- oder Validatoraenderung.

## Scope and repository review

Ausgangsstand: sauberer Commit `209edfa`. Keine zusaetzlichen AGENTS-Dateien
gefunden. `app/config.py:load_settings` liest Defaults < `.env` < `.env.local`
< Prozessumgebung. Beide lokalen Dateien enthielten keine Audio-Profile;
`GET /api/speech/config` meldete beide Serverfunktionen als `false`.
Firefox zeigte den Nichtverfuegbarkeits-Hinweis. `app/static/app.js` verwendet
bei fehlender Browser-Spracherkennung Server-STT mit MediaRecorder und
getUserMedia; TTS ruft ausschliesslich den Server auf.

Wiederverwendung: `app/service_check.py`, `app/speech.py` (WAV-Normalisierung,
SpeechSynthesizer, SpeechTranscriber), bestehende Audio- und Frontendtests.
Edge-Client ist bereits installiert. `.env.local` ist explizit Git-ignoriert.
Das Aendern der Defaults oder ein neuer Audioadapter ist nicht erforderlich.

## Dead-end analysis and approach

| Risiko / Alternative | Evidenz und Behandlung |
|---|---|
| Nur auf konfiguriert pruefen | Belegt keine Erreichbarkeit. Synthetisches Audio ueber echte Dienste und HTTP pruefen. |
| Firefox auf Browsererkennung verweisen | Aktuell nicht verfuegbar. Bestehendes Server-STT aktivieren. |
| TTS mit Blablador erzwingen | Vorhandener separater Edge-Adapter ist vorgesehen; vorhandene explizite Profile verwenden. |
| Geheimnisse in Ausgabe oder Git | Nur Profilnamen und redigierte Ergebnisse ausgeben; lokale Datei nie als Diff anzeigen. |
| Tests als Hoer-/Mikrofonnachweis ausgeben | Synthetische Tests getrennt vom ausstehenden echten Firefox-Aufnahme-/Hoertest dokumentieren. |
| Laufenden Prozess mit falschen Optionen ersetzen | Prozessidentitaet und Startoptionen vor Neustart pruefen. Nur Instanz an Port 8002 ersetzen. |

## File impact

| Datei | Aenderung |
|---|---|
| `.env.local` (ignoriert) | Nur zwei Audio-Profile setzen; sonstige Werte erhalten. |
| `docs/exec-plans/audio-activation.md` | Plan und Nachweis. |
| `README.md` | Konkretes Audio-Profil und Firefox-Aufnahmebedienung ergaenzen. |
| `IMPLEMENTATION_REPORT.md`, `THESIS_UPDATE_NOTES.md` | Datierten Audio-Pruefstand ergaenzen. |
| `%LOCALAPPDATA%/LENA/verification/2026-10-27-audio-activation/` | Secretfreie Pruefergebnisse und synthetisches Audio ausserhalb des Repositorys. |

Anwendungscode, Daten, Versionsvertraege und allgemeine Defaults bleiben unveraendert.
Nur wenn die reale Pruefung einen Fehler zeigt, wird der Plan vor einer gezielten
Codeaenderung ergaenzt. Keine komplette Vier-Stufen-Live-Evaluation.

## Milestones and validation

1. [x] Repository, Konfiguration, HTTP-Endpunkte und bestehende Tests pruefen.
2. [x] Lokale Profile setzen; `python -m app.service_check --synthesize` pruefen.
3. [x] Instanz neu starten und `/api/speech/config` kontrollieren.
4. [x] Synthetischen TTS/STT-Durchlauf ueber echte HTTP-Endpunkte pruefen.
5. [x] Relevante bestehende Audio-/Konfigurationstests und `node --test tests/frontend.test.cjs` ausfuehren.
6. [x] Dokumentation nach Skill code-documentation aktualisieren und Diff pruefen.

## Rollback and recovery

Die beiden gesetzten Profilzeilen aus `.env.local` entfernen und dieselbe native
Instanz neu starten stellt den vorherigen Zustand wieder her. Sonstige lokale
Werte bleiben erhalten. Ein Neustart darf keine Runtime-/Sessiondaten loeschen.

## Progress and decisions

- 2026-10-27: Ursache auf explizit deaktivierte Audio-Profile eingegrenzt.
  Nutzerin hat deren Aktivierung und Pruefung beauftragt.
- Profile in `.env.local` gesetzt; Git-Ignore und effektive Konfiguration
  bestaetigt. Modellinventar fuer LLM und STT erfolgreich abgefragt.
- Live-TTS scheiterte zunaechst mit HTTP 403: Der tatsaechlich verwendete native
  Python-3.14-Interpreter hatte noch `edge-tts 7.2.8`, waehrend beide Constraints
  und der Docker-Lock bereits `7.3.1` festlegen. Zusaetzlicher Umsetzungsschritt:
  nur dieses lokale Paket an die bestehende Pin-Version angleichen; keine
  Aenderung der Repository-Abhaengigkeiten. Danach erneut live pruefen.
- 25 bestehende Audio-/Konfigurationstests bestanden. `node` ist nicht im PATH;
  fuer den bestehenden Frontendtest den vorhandenen Node-Pfad ermitteln.
- Die Nutzerin bestaetigte anschliessend am 27.10.2026: "jetzt funktioniert es".
  Das dokumentiert die Audiofunktion in ihrem Firefox, keine unabhaengige
  sprachliche oder akustische Qualitaetspruefung aller fuenf Sprachen.

## Final verification summary

- Alle technischen Akzeptanzkriterien erfuellt. Native Instanz mit denselben
  Host-/Portoptionen neu gestartet; HTTP meldet beide Speech-Funktionen aktiv.
- Lokaler Edge-Client an bestehenden Pin 7.3.1 angeglichen; pip check erfolgreich.
- Fuenf vorab festgelegte synthetische Saetze DE/EN/PL/RO/RU als Ogg/Opus ueber
  `/api/speech/transcribe`: jeweils HTTP 200 und exakt erwartetes Transkript.
- Fuenf sessiongebundene Policytexte ueber `/api/speech/synthesize`: jeweils
  HTTP 200 und dekodierbares MP3. Keine LLM-Stufen aufgerufen.
- 38 bestehende gezielte Python-Tests, 19 Frontendtests erfolgreich;
  keine Tests geaendert. Bekannte TestClient-Warnung bleibt.
- Externes Pruefskript: nach fuenf erfolgreichen Durchlaeufen verschachteltes
  asyncio.run im abschliessenden Servicecheck korrigiert; diesen Servicecheck
  separat erfolgreich wiederholt. Anwendungscode war davon nicht betroffen.
- Skill code-documentation angewandt: README um explizites lokales Audio-Profil,
  Firefox-Bedienung und Datentransfers ergaenzt; Bericht 16 und Thesisnotiz L
  binden die technischen Ergebnisse an den unveraenderten Anwendungscode 209edfa.
- Review: nur ignorierte lokale Konfiguration und Markdown geaendert;
  keine Pins, Daten, Safety, Prompt-/Validatorvertraege oder Secrets hinzugefuegt.
  git diff --check erfolgreich. Kein Build erforderlich: installierter
  Anwendungs-/Imagecode unveraendert; Runtime-Lock enthielt 7.3.1 bereits.
- Belege: `live-audio-results.json`, `live_audio_check.py`, `restart.json`,
  `python-tests.log`, `javascript-tests.log`, `pip-check.log`,
  `regression-results.json` unter dem oben genannten externen Pruefordner.
- Manueller Funktionscheck: Nutzerin bestaetigt funktionierende Ein-/Ausgabe
  in Firefox am 27.10.2026; separat in `user-confirmation.json` festgehalten.
  Allgemeine Hoer-/Sprachqualitaet aller fuenf Sprachen wird nicht behauptet.
  Externe Dienste bleiben abhaengig von Netz und Anbieter. Keine vollstaendige Live-Evaluation,
  kein Commit, Tag oder Push und keine Thesis-Aenderung.
