# Execution Plan: Browser-STT-Audio vor Blablador normalisieren

## Status

- State: Completed
- Owner: Codex
- Created: 2026-08-20
- Last updated: 2026-08-20

## Objective

`POST /api/speech/transcribe` verarbeitet die von Firefox/Chromium erzeugten
WebM-/Opus-Aufnahmen zuverlässig, indem LENA unterstützte Browserformate lokal
in ein eng begrenztes PCM-WAV normalisiert und erst dieses an den real
konfigurierten Blablador-STT-Endpunkt sendet. Fehler bleiben redigiert, werden
aber technisch unterscheidbar protokolliert. Thesis und Präsentation bleiben
unverändert.

## Acceptance contract

- [ ] Gültiges WebM/Opus, Ogg, MP4, MP3 und WAV werden vor dem Provider in ein
  standardisiertes RIFF/WAV überführt; der Provider erhält Dateiname und MIME
  passend zum tatsächlichen Inhalt.
- [ ] `/api/speech/transcribe?language=de` liefert bei gültiger Aufnahme und
  gültiger Providerantwort HTTP 200 statt des bisherigen maskierten 503.
- [ ] Nicht dekodierbares Audio wird kontrolliert als Clientfehler behandelt;
  Timeout und Upstreamfehler bleiben sichere Servicefehler.
- [ ] Technische Logs enthalten redigierten Fehlercode, Dauer und – nur bei
  HTTP-Statusfehlern – den Statuscode, aber weder Audio, Providerbody, URL,
  Header, Token noch Transkript.
- [ ] Keine lokale Whisper-Modellinitialisierung, kein Modell-Download und
  keine Änderung der LLM-, TTS-, WFS- oder Wissensbasispfade.
- [ ] Bestehende Tests plus neue STT-Regressions-, API-, Timeout-, Packaging-
  und Clean-Install-Prüfungen bestehen.

## Scope

### In scope

- Browseraudio-Normalisierung im bestehenden `SpeechTranscriber`.
- Explizite PyAV-Laufzeitabhängigkeit und Python-3.11-Constraint.
- Strukturierte, redigierte STT-Fehlerklassen und API-Zuordnung.
- Providerfreie Tests mit synthetischen Audiodaten und HTTP-Test-Double.
- Unmittelbar betroffene Konfigurations-/Datenflussdokumentation.

### Out of scope

- Lokaler Betrieb von `faster-whisper`, Modell-Download oder GPU-Support.
- Änderungen an TTS, LLM-Prompts, Kandidaten, Safety oder Frontenddialog.
- Speicherung von Audio oder Transkripten in technischen Logs.
- Commit, Push, Branchwechsel, Pull Request, Thesis oder Präsentation.

## Repository review

### Current behavior

- Firefox zeichnet `audio/webm;codecs=opus` auf und sendet 55.750 Bytes an
  `/api/speech/transcribe?language=de`; LENA akzeptiert Medientyp und Größe,
  antwortet aber HTTP 503.
- `app/main.py::transcribe_speech()` kann genau im Catch von
  `SpeechTranscriptionError` einen 503 erzeugen. Der Endpoint selbst erzeugt
  daneben 413, 415 und 422, aber keinen weiteren 503.
- `app/speech.py::SpeechTranscriber.transcribe()` reicht Bytes, Dateiendung und
  MIME unverändert über multipart an
  `<Blablador-Basis>/audio/transcriptions` weiter. Timeout, HTTP-Fehler und
  leere Antwort werden sämtlich auf wenige generische Exceptions reduziert.
- Der laufende Prozess (`python -m app --port 8002`) meldet STT verfügbar und
  `faster-whisper-large-v3`. Die technische Ausgabe enthält nur `stt.failed`
  beziehungsweise `stt.timeout`; der behandelte Fehler erzeugt bei Uvicorn
  keinen Stacktrace. Es gibt keinen persistenten technischen Logstore.
- Kontrollierter Beleg mit rein synthetischem Satz „Ich brauche Hilfe in
  Leipzig.“: WAV → Erfolg in 1,559 s; derselbe Inhalt als WebM/Opus → Upstream
  HTTP 400 in 0,462 s, redigierte Providerursache
  `Could not decode audio: file does not start with RIFF id`.

### Relevant architecture and data flow

`app/static/app.js` → rohe Browseraufnahme →
`app.main.transcribe_speech()` → `SpeechTranscriber.transcribe()` → externer
OpenAI-kompatibler Blablador-Audioendpunkt → `{ "text": ... }` → Eingabefeld.
`SpeechTranscriber` wird synchron beim Appbau nur als leichter Settings-Adapter
erzeugt. Der Lifespan startet ausschließlich optionale Quellen-Sync-Tasks.

Entgegen der Aufgabenannahme lädt LENA kein lokales `faster-whisper`-Modell:
Kein Anwendungscode importiert `faster_whisper`, `WhisperModel` oder
`ctranslate2`. Deshalb existieren keine lokale Modellgröße, Gerätewahl,
Ladezeit, Startup-/Lazy-Initialisierung, Readiness-Prüfung oder Start-Race.
Der Name `faster-whisper-large-v3` ist ein entfernter Provideralias.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| `SpeechTranscriber` | `app/speech.py` | als einzige STT-Transportgrenze erweitern |
| Requestgrößen-/MIME-Prüfung | `app/main.py` | unverändert vor der Dekodierung erhalten |
| redigiertes technisches Logging | `app/main.py` | um kontrollierten Fehlercode/Status ergänzen |
| STT API-/Timeouttests | `tests/test_api.py`, `tests/test_provider_timeouts.py` | aktualisieren und gezielt erweitern |
| Requestgrenztests | `tests/test_request_boundaries.py` | MIME-/Größenregression erhalten |

### Existing tests and commands

- `python -m pytest tests/test_api.py -k speech -q`
- `python -m pytest tests/test_provider_timeouts.py -k speech -q`
- `python -m pytest tests/test_request_boundaries.py -k stt -q`
- `python -m pytest tests/test_observability.py -k stt -q`
- Packaging und Clean-Install: `tests/test_packaging.py`

### Working tree considerations

Branch `maintenance/repository-cleanup`, HEAD
`fbcc85aa1d4c3eeca096d5a67e39f9df7580a5b2`. Der Arbeitsbaum enthält zahlreiche
Änderungen der Nutzerin. Insbesondere `app/config.py`, `app/speech.py`,
`app/static/app.js`, Tests und Dokumentation sind bereits geändert. Nur eng
begrenzte neue Hünks werden ergänzt; bestehende Änderungen werden nicht
zurückgesetzt oder breit formatiert.

## Step 1 – Analysis result

### Proven root cause

Der Blablador-STT-Backendpfad erwartet für diesen Modellalias RIFF/WAV. LENA
verspricht und akzeptiert dagegen mehrere Browserformate, reicht sie aber
unverändert weiter. Der Provider interpretiert WebM fälschlich als WAV und
antwortet 400; LENA maskiert diesen Status als generischen 503. Der Fehler ist
nicht sprachspezifisch – `language=de` ist nur das getestete Sprachhintfeld.

### Local dependency and resource findings

- Lokal vorhanden: `faster-whisper 1.2.1`, `ctranslate2 4.7.1`, `av 17.0.1`;
  Imports funktionieren, CUDA-Geräte: 0, CPU-Typen: `float32`, `int8`,
  `int8_float32`.
- Diese Pakete sind nicht in `pyproject.toml` deklariert und nicht im aktiven
  STT-Pfad. Eine zufällige Installation ist keine Anwendungsabhängigkeit.
- Default-Hugging-Face-Cache: ca. 0,906 GiB; keine explizite Cachevariable.
- Rechner: 13,86 GiB RAM, bei Prüfung nur 1,15 GiB frei; Systemlaufwerk ca.
  316,34 GiB frei. Disk ist unkritisch, ein lokales Large-v3-Modell wäre bei
  aktueller RAM-Lage dagegen riskant. Diese Ressourcen verursachen den
  belegten Remote-400 nicht.

### Remaining uncertainty

Keine Unsicherheit zur unmittelbaren 503-Ursache. Noch nicht real verifiziert
ist, ob jeder andere akzeptierte Container vom Provider abgelehnt wird; die
Lösung normalisiert deshalb alle akzeptierten Formate auf denselben belegten
WAV-Vertrag und testet sie lokal. Reale linguistische STT-Qualität bleibt
außerhalb dieses Fehlerpakets.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Timeout erhöhen | Fehler kommt reproduzierbar nach 0,462 s als HTTP 400 | keine Wirkung, längere echte Ausfälle | unverändert 45 s; Format beheben | synthetischer WebM-Test |
| 503 abfangen/Platzhalter liefern | verliert Transkript und Ursache | Spracheingabe bleibt defekt | keine Teil-/Leerantwort akzeptieren | API-Regressionsprüfung |
| Modell lokal mit `faster-whisper` laden | aktiver Pfad ist remote; kein GPU, nur 1,15 GiB RAM frei | neue Architektur, Download/OOM/Startlatenz | Remotevertrag erhalten, Audio lokal normalisieren | Import-/Lifespanreview |
| Browser ausschließlich WAV erzeugen lassen | `MediaRecorder` bietet Firefox WebM/Opus, Browser-WAV nicht portabel | browserabhängige Parallelpfade | Formatgrenze zentral im Backend | DE/Browserformat-Fixtures |
| externes `ffmpeg`-Binary voraussetzen | auf dem Zielsystem nicht vorhanden | Deployment bricht | PyAV als deklarierte Python-Abhängigkeit | Clean-Install-Test |
| WebM als `.wav` umbenennen | Provider prüft RIFF-Inhalt | identischer HTTP 400 | tatsächlich dekodieren und PCM-WAV schreiben | RIFF-/WAVE-Assertions |

## Step 2 – Options evaluation

| Option | Vorteile | Nachteile | Bewertung |
|---|---|---|---|
| Backendnormalisierung mit PyAV | eine kanonische Grenze; alle Browser; kein externes Binary; Provider erhält belegtes Format | zusätzliche binäre Python-Abhängigkeit; lokale CPU-Arbeit | **empfohlen** |
| WAV-Encoding im Browser | kein Backenddecoder | duplizierte Browserlogik, Speicher-/Kompatibilitätsrisiko, umgehbar durch API-Clients | nicht nachhaltig |
| lokales `faster-whisper` | unabhängig vom Remoteformat | grundlegender Architekturwechsel, Modellcache, hohe RAM-/CPU-Last, kein GPU | außerhalb Umfang/riskant |
| Providerwechsel oder Timeout | geringe Codeänderung | behebt den nachgewiesenen Formatvertragsbruch nicht | verworfen |

## Recommended approach

`SpeechTranscriber` dekodiert jedes zugelassene Eingabeformat in einem Worker-
Thread über PyAV, resampelt auf mono PCM16/16 kHz und sendet ausschließlich
`speech.wav` mit `audio/wav`. Die dekodierte Dauer wird begrenzt, damit kleine
komprimierte Dateien keine unbegrenzte CPU-/RAM-Last erzeugen. Dekodierfehler
werden vor dem Provider als kontrollierter 422 behandelt. Provider-HTTP- und
Timeoutfehler bleiben 503, erhalten aber redigierte maschinenlesbare Codes und
ggf. den numerischen Upstreamstatus im technischen Log.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Nur WebM konvertieren | andere bereits öffentlich akzeptierte Container könnten denselben Providerfehler erzeugen |
| WAV ungeprüft durchreichen | inkonsistente/defekte WAVs würden wieder als Provider-503 erscheinen |
| Providerbody loggen | unnötiges Datenschutz-/Secretrisiko; Status und eigener Fehlercode genügen |
| Retry mit Originalformat | wiederholt deterministisch denselben 400 und erhöht Last |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/speech.py` | Modify | zentrale Dekodierung, Begrenzung und Fehlervertrag | mittel |
| `app/main.py` | Modify | 422-/503-Zuordnung und redigierte Diagnose | klein |
| `pyproject.toml` | Modify | PyAV als echte direkte Laufzeitabhängigkeit | klein |
| `requirements/constraints-py311.txt` | Modify | reproduzierbare Python-3.11-Auflösung | klein |
| `tests/test_api.py` | Modify | Endpoint-200 und ungültiges Audio | klein |
| `tests/test_provider_timeouts.py` | Modify | Provider-/Timeoutregression | klein |
| `tests/test_request_boundaries.py` | Modify | tatsächlicher Browserformatvertrag | klein |
| `tests/test_observability.py` | Modify | keine Secrets/Audio/Providerbody im Log | klein |
| `docs/configuration.md`, `docs/data-flow.md` | Modify | Formatnormalisierung und Fehlersemantik | klein |
| dieser Plan | Update | Ursache, Entscheidung und Abschlussnachweis | klein |

## Milestones

### Milestone 1: Review and design

- [x] Anweisungen, Status, Diff, Einstiegspunkte und aktiven STT-Pfad geprüft.
- [x] 503-Stellen, Logging, Konfiguration, Lifespan und Readiness verfolgt.
- [x] Abhängigkeiten, Geräte, Cache, RAM und Disk geprüft.
- [x] Ursache mit synthetischem WAV/WebM-Vergleich und redigiertem Upstream-400 belegt.
- [x] Dead Ends und Lösungsoptionen bewertet.

Evidence: Review- und Analyseabschnitte dieses Plans.

### Milestone 2: Implementation

- [x] Audio-Normalisierung und begrenzten Fehlervertrag implementieren.
- [x] Abhängigkeit explizit deklarieren.
- [x] Tests für WebM→WAV, HTTP 200, Dekodierfehler und Providerfehler ergänzen.

### Milestone 3: Verification

- [x] Fokussierte STT-/API-/Loggingtests ausführen.
- [x] Vollständige Suite und Syntaxprüfung ausführen.
- [x] Wheel/sdist, sdist→Wheel und Clean-Install prüfen.
- [x] Finalen Diff und `git diff --check` prüfen.

### Milestone 4: Documentation

- [x] `code-documentation` auf finalen Diff und STT-Pfad anwenden.
- [x] Dokumentationsänderungen prüfen und betroffene Tests wiederholen.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Audiovertrag | neue providerfreie PyAV-/MockTransporttests | Browser-WebM wird RIFF/WAV; Transkript erfolgreich |
| API | `pytest tests/test_api.py -k speech` | gültig 200, ungültig kontrolliert, kein generischer Format-503 |
| Grenzen/Timeout | `pytest tests/test_request_boundaries.py tests/test_provider_timeouts.py -k 'stt or speech'` | Limits und 503-Timeout erhalten |
| Logging | `pytest tests/test_observability.py -k stt` | nur Codes/Status/Dauer, keine Payload/Secrets |
| Regression | `python -m pytest -q` | vollständig grün |
| Syntax/Build | `compileall`, `python -m build`, Packagingtests | Wheel/sdist/Clean-Install erfolgreich |
| Diff | `git diff --check` und Reviewtemplate | keine Fremdhünks oder Whitespacefehler |

## Rollback and recovery

Die Änderung hat keine Datenmigration und persistiert kein Audio. Rücknahme
beschränkt sich auf die neuen Hünks in Transcriber, Endpoint, Abhängigkeiten,
Tests und Dokumentation. Ein Dekodierfehler verändert weder Sessions noch das
Interaktionsprotokoll. Die ursprünglichen Audiodaten verbleiben weiterhin nur
im Requestspeicher.

## Progress log

- 2026-08-20 — Review abgeschlossen; Ursache durch zwei synthetische,
  nichtpersonenbezogene Providerdiagnosen belegt. Noch keine Quellcodeänderung.
- 2026-08-20 — Plan als erste Repositoryänderung dieses Arbeitspakets erstellt.
- 2026-08-20 — Browseraudio zentral zu PCM16/16-kHz-WAV normalisiert,
  dekodierte Dauer begrenzt und redigierte Fehlerklassifikation ergänzt.
- 2026-08-20 — 702 Tests, Build aus Checkout und sdist sowie Clean-Install
  erfolgreich; integrierter synthetischer WebM-Smoke liefert HTTP 200.

## Decision log

- Decision: Formatnormalisierung an der zentralen Backendgrenze.
  - Context: Browser liefert WebM/Opus, Remote-STT erwartet RIFF/WAV.
  - Options: Browser-WAV, Backend-PyAV, lokales Whisper, Providerwechsel.
  - Choice: Backend-PyAV mit PCM16/mono/16 kHz und Dauergrenze.
  - Consequences: reproduzierbarer Providervertrag; neue explizite binäre
    Python-Abhängigkeit; keine lokale Modellinitialisierung.

## Discoveries

- Die Aufgabenannahme „FastAPI mit lokalem faster-whisper“ ist für den aktiven
  Codepfad widerlegt; der Modellname bezeichnet einen Remotealias.
- Der bisherige technische Log kann die Ursache eines behandelten 503 nicht
  rekonstruieren, weil Exceptionklasse/Upstreamstatus nicht erfasst werden.

## Final verification summary

- Acceptance requirements: erfüllt; Firefox-WebM wird nicht mehr unverändert
  an den RIFF/WAV erwartenden Provider gesendet.
- Tests: 17 fokussierte STT-/Speech-Tests und 702 Tests der Gesamtsuite
  bestanden; `compileall` und `git diff --check` bestanden.
- Build: Wheel und sdist aus dem Checkout, Wheel aus der sdist und
  Clean-Install-Smoke bestanden; Wheel-Metadaten enthalten `av>=14,<18`.
- Manual verification: vor der Änderung synthetisches WAV erfolgreich und
  synthetisches WebM mit Upstream-400; nach der Änderung derselbe synthetische
  WebM-Inhalt über den FastAPI-Endpunkt mit HTTP 200 und nichtleerem Transkript.
  Es wurden keine Nutzeraufnahme, Session- oder Interaktionsdaten übertragen.
- Documentation: Plan enthält Analyse und Entscheidung; Betriebsdoku ausstehend.
- Residual risks: reale Browseraufnahme nach Implementierung noch zu prüfen.
