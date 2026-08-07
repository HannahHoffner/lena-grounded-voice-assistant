# Implementierungsplan: Ergebnisliste vereinheitlichen, Hilfebus bei Beratung, Sprachausgabe pro Angebot

## Status

- State: Complete (Teile 0, 2, 3, 4 umgesetzt und verifiziert; Teil 1 bleibt bewusst Backlog)
- Owner: Claude
- Created: 2026-08-07
- Last updated: 2026-08-07

## Einordnung

Ausgangspunkt sind vier vom Nutzer gemeldete Punkte in einer Sitzung:

1. Warum antwortet LENA weiterhin manchmal nicht mit einer LLM-Formulierung?
2. Die Selbstauskunft ("Wer bist du?") ist nicht mehr erreichbar.
3. Der Hilfebus soll bei Beratungs-Anfragen mit einem Hinweis auf seine
   Einsatzzeiten erscheinen.
4. Die Ergebnisliste (Karten + Kartenansicht) soll vereinheitlicht werden:
   jedes Angebot soll per Klick (auf den Listeneintrag oder den Kartenpunkt)
   aufklappbar sein und volle Informationen zeigen, statt wie aktuell eine
   auf ca. 3 Einträge begrenzte Detailkarten-Liste parallel zu einer
   längeren, aber informationsarmen Kartenpunkt-Liste zu führen. Zusätzlich
   soll jedes aufgeklappte Angebot per Lautsprecher-Symbol vorlesbar sein.

Punkte 1 und 2 waren akute Fehlerdiagnosen und sind bereits behoben (Teil 0).
Punkte 3 und 4 sind Feature-Arbeit und werden hier als Arbeitspakete für die
weitere Umsetzung geplant, nicht in dieser Sitzung implementiert.

---

## Teil 0 — Bereits behoben (zur Nachvollziehbarkeit dokumentiert)

### 0.1 Selbstauskunft unerreichbar

**Ursache:** `SELF_PATTERNS`-Abgleich (`app/service.py`) lag *nach* dem
`ScopeStatus.OUT_OF_SCOPE`-Return. Sobald der Interpreter eine
Selbstbezug-Frage ("wer bist du") als `OUT_OF_SCOPE` einstufte — reproduzierbar
mit `alias-fast` **und** `alias-large`, also modellunabhängig —, griff der
`self_description`-Zweig nie. Der Code-Kommentar an dieser Stelle
("Kontrollierte Anwendungspolitik bleibt außerhalb des Interpretervertrags")
beschreibt explizit die *beabsichtigte* Unabhängigkeit vom Interpreter; die
Platzierung widersprach dem.

**Fix:** Prüfung vor den Interpreter-Aufruf gezogen, direkt nach dem
Akutgefahren-Preflight (`app/service.py`, vor der `interpretation`-Ermittlung).
Nebeneffekt: spart für diese Anfragen jetzt einen LLM-Roundtrip.

**Verifiziert:** Live gegen die konfigurierte Blablador-Instanz getestet
("wer bist du", "was ist lena", "was machst du" → `system_description`,
kein LLM-Aufruf mehr nötig). Volle Testsuite grün.

### 0.2 Klärungsfrage erscheint doppelt

**Ursache:** `app/service.py` baut den Antworttext bei jedem Dialogschritt
immer als `dialogue_text(prompts, dialog_type)` (+ optionaler Kontextsatz) —
die Frage steckt vollständig im Fließtext. Zusätzlich hängt
`app/service.py` (Zeile ~431) unabhängig davon *immer* ein
`clarification`-Objekt an die Antwort, dessen `prompt`-Feld
(`app/dialogue.py::clarification_block`) denselben Text erneut lädt. Das
Frontend zeigt beide Stellen an (`app.js` setzt `answerText`,
`dialogue.js` setzt zusätzlich `clarificationPrompt`) → jede Klärungsfrage
erschien zweimal. Betraf *jeden* Dialogtyp, nicht nur den Scharni/Alters-Fall.

**Fix:** `#clarificationPrompt` in `app/static/index.html` erhält die Klasse
`sr-only`. Bleibt für Screenreader wirksam (die `aria-labelledby`-Beziehung
des Panels ist unverändert), verschwindet aber aus der sichtbaren und
gesprochenen Ausgabe (Sprachausgabe liest ohnehin nur `answerText`, das
unverändert bleibt).

### 0.3 Falsche Altersgrenze im Fragetext (`dialogue.prompts.sleep_age`)

**Ursache:** Die Wahl-Buttons sagten korrekt "Ich bin unter 27"
(`dialogue.choices.under_27`, passend zu `AgeGroup.UNDER_27` /
`NOT_UNDER_27` in `app/interpreter.py`), der Fragetext selbst aber "zwischen
18 und 26 oder mindestens 27" — eine untere Grenze von 18, die im Datenmodell
gar nicht existiert.

**Fix:** Text in allen 5 Sprachen (DE/EN/PL/RO/RU) in
`app/resources/bootstrap/i18n/application_texts.json` auf "jünger als 27 /
under 27 / …" korrigiert, konsistent zur Choice-Beschriftung.

**Verifiziert:** Volle Testsuite grün nach beiden Textänderungen.

---

## Teil 1 — Diagnose: "Warum wird das LLM weiterhin nicht immer verwendet?"

Dies ist **kein offener Bug**, sondern eine dokumentierte Restunschärfe, die
hier als Analyse und Backlog-Empfehlung festgehalten wird.

### Befund

Mit Live-Tests gegen die echte Blablador-API (`alias-fast`, aktuell für alle
drei Stufen konfiguriert) reproduziert sich folgendes Bild:

- Dieselbe Anfrage ("Ich brauche Beratung") lief 4/4 Wiederholungen im
  direkten Test sauber durch (`provider: blablador`).
- In den echten Logs (`runtime/logs/interactions.jsonl`) tauchen für
  vergleichbare, aber umfangreichere Angebotsmengen (4–5 Kandidaten statt 3)
  wiederholt `formulator_ungrounded_claim` und `formulator_schema_error` auf.

Das Muster ist **intermittierend**, nicht deterministisch — trotz
`temperature: 0`. Das ist ein bekanntes Phänomen bei über APIs bereitgestellten
Modellen (Batching, MoE-Routing, Serving-Stack) und kein Konfigurationsfehler:
`temperature: 0` garantiert bei den meisten gehosteten Inferenz-Backends keine
bitgenaue Reproduzierbarkeit.

Die Architektur behandelt jede Formulator-Antwort **atomar**: Ein einziger
nicht belegter Satz oder ein Schema-Fehler verwirft die *gesamte* Antwort und
fällt auf die Template-Antwort zurück (`app/service.py::_formulate_or_fallback`).
Das ist im Kern die richtige Sicherheitsentscheidung (siehe
`docs/safety-and-error-policy.md`), erhöht aber die beobachtbare
Fallback-Quote, weil auch ein einzelner, sonst korrekter, Satz die komplette
mehrsätzige Antwort mitreißt.

Zur Einordnung, was an diesem Tag bereits ausgeschlossen wurde (siehe
Sitzungsverlauf, alle live gegen die API verifiziert):

| Ursache | Status |
|---|---|
| `alias-large` reproduzierbar ~50s hängend, dann Verbindungsabbruch | Bestätigt, umgangen (Formulator läuft auf `alias-fast`) |
| `alias-huge` leakt `<think>`-Reasoning in `content`, bricht JSON-Parsing | Bestätigt, nicht verwendet |
| Gemeinsames 45s-Zeitbudget über alle LLM-Stufen | Bestätigt als Architekturrisiko, durch Modellwahl entschärft |
| Restliche `formulator_ungrounded_claim`/`schema_error`-Rate auf `alias-fast` | **Nicht behoben** — echte Modellgrenze, siehe unten |

### Empfehlung (Backlog, nicht in diesem Plan umgesetzt)

1. **Ein automatischer Formulator-Retry innerhalb des Budgets.** Bei
   `formulator_ungrounded_claim`/`schema_error`/`invalid_json` einmal erneut
   versuchen (ggf. mit leicht verschärfter Systemprompt-Erinnerung "nutze
   ausschließlich die gegebenen fact_ids"), bevor auf Template zurückgefallen
   wird. Kleiner, klar abgegrenzter Eingriff in
   `app/service.py::_formulate_or_fallback`.
2. **`alias-large` regelmäßig neu testen** (z. B. wöchentlich per Skript) und
   zurückwechseln, sobald Blablador-seitig stabil — größere Modelle sollten
   tendenziell weniger ungrounded Claims produzieren.
3. **Formulator-Systemprompt schärfen** (`app/formulation.py`): explizite
   Wiederholung der Grounding-Regel unmittelbar vor der Evidence, da
   kleinere Modelle Instruktionen nahe am Ende des Kontexts zuverlässiger
   befolgen ("recency bias" in Prompt-Adherence).
4. **Monitoring statt Bauchgefühl:** `formulator_error_code`-Verteilung aus
   `runtime/logs/interactions.jsonl` als wiederkehrende Kennzahl beobachten,
   um zu erkennen, ob eine Änderung tatsächlich hilft oder nur verschiebt
   (das ist in dieser Sitzung mehrfach der Fallstrick gewesen).

Diese vier Punkte sind bewusst **nicht** Teil der Umsetzung in diesem
Dokument — sie gehören in ein eigenes, fokussiertes Arbeitspaket
"Formulator-Zuverlässigkeit", falls gewünscht.

---

## Teil 2 — Hilfebus bei Beratung mit Einsatzzeiten-Hinweis

### Bestandsaufnahme

Der Hilfebus (`OfferRecord.id == "21"`, `offer_type: mobile_basic_support`)
ist bereits fachlich für Beratung getaggt:

```
needs         = ["food", "drinking_water", "advice"]
capabilities  = ["food", "drinking_water", "clothing", "counselling", "referral", "mobile_outreach"]
target_groups = ["adults", "people_experiencing_homelessness"]
phone_numbers = ["0175 6758041 (Herr Neufert)",
                 "0152 33661087 (nur zu Einsatzzeiten des Busses)"]
opening_hours_raw = ["> Einsatz täglich 18:00 - 23:00 Uhr, stadtweit",
                      "> Jeden Sonntag: 20:00 -21:00 Uhr an der Westseite des Hauptbahnhofes ..."]
access_rules  = []   # aktuell leer
```

Er erscheint bereits in Beratungs-Ergebnislisten (siehe Screenshot des
Nutzers). Der Einsatzzeiten-Hinweis existiert nur unauffällig als Klammerzusatz
in einer von zwei Telefonnummern — er ist weder strukturell hervorgehoben
noch Teil der von der LLM-Formulierung zitierbaren Evidence.

### Zielbild

Bei jeder Nennung des Hilfebus (Karte, Kartenpunkt-Popup, LLM-Antworttext)
soll ein klar erkennbarer, eigenständiger Hinweis erscheinen, sinngemäß:
**"Rufe zu den Einsatzzeiten beim Hilfebus an."**

### Umsetzungsvorschlag

1. **Datenmodell:** `access_rules: list[str]` (bereits vorhandenes,
   aktuell ungenutztes Feld auf `OfferRecord`) für den Hilfebus in
   `app/resources/bootstrap/curation/social_offers.json` befüllen, z. B.
   `["phone_only_during_operating_hours"]` als stabiler, versionierter
   Regelcode — analog zum bestehenden Muster bei `priority_rules`
   (`general_help_referral_first`), nicht als Freitext, damit die Aussage
   testbar und über die i18n-Textquelle steuerbar bleibt.
2. **Text:** Neuer i18n-Schlüssel (z. B. `card.access_rule.phone_only_during_operating_hours`)
   in `application_texts.json`, alle 5 Sprachen, nach demselben Muster wie
   die bestehenden `fallback.*`/`dialogue.*`-Einträge.
3. **Card-Darstellung:** `OfferCard` um ein optionales `access_notes: list[str]`
   Feld erweitern (Projektion aus `access_rules` → lokalisierter Text,
   analog zu `_card()` in `app/service.py`), im Frontend als eigene,
   optisch hervorgehobene Zeile rendern (`addField` mit eigenem CSS-Akzent,
   z. B. `.card-field--notice`).
4. **Formulator-Evidence:** `access_rules` als eigener Fact-Typ in
   `build_formulator_evidence` (`app/formulation.py`) aufnehmen, damit die
   LLM-Formulierung den Hinweis *grounded* zitieren kann, statt ihn frei zu
   ergänzen (Konsistenz mit der bestehenden strikten Grounding-Architektur;
   kein Freitext im Prompt duplizieren, siehe bereits umgesetztes
   Arbeitspaket 10).
5. **Template-Fallback:** Bestehenden `_template_for_offers`/`_card`-Pfad so
   erweitern, dass der Hinweis auch bei Template-Antworten (ohne LLM)
   sichtbar ist — betrifft naturgemäß einen großen Teil der Antworten
   (siehe Teil 1).

### Akzeptanzkriterien

- [ ] Hilfebus-Karte zeigt den Einsatzzeiten-Hinweis als eigene, optisch
      abgesetzte Zeile — unabhängig davon, ob die Antwort per Template oder
      LLM formuliert wurde.
- [ ] Der Hinweistext ist in allen 5 Sprachen vorhanden und stammt aus
      `application_texts.json`, nicht aus Freitext im Prompt.
- [ ] Bestehende Tests zu `_card()`/`OfferCard` und Formulator-Evidence
      bleiben grün; neue Tests decken den neuen `access_notes`/`access_rules`-
      Pfad ab (mind. ein Test mit, ein Test ohne `access_rules`).
- [ ] Kein anderes Angebot erhält ungewollt denselben Hinweis (Regelcode ist
      offer-spezifisch in der Kuration gesetzt, nicht global).

### Aufwand/Risiko

Klein bis mittel. Reine Daten- und Darstellungs-Erweiterung, keine Änderung
an Kandidatenauswahl oder Interpreter/Selector-Logik. Geringes
Regressionsrisiko, sofern `access_rules` als rein additives, leeres-Default-
Feld eingeführt wird.

---

## Teil 3 — Ergebnisliste vereinheitlichen: aufklappbare "Tafeln" statt zwei parallele Listen

### Bestandsaufnahme (Ist-Architektur)

Aktuell existieren **zwei unabhängige, redundante Listen** unterhalb einer
Antwort:

| | `cardList` (`app.js::renderCards`) | `mapList` (`app.js::renderMap`) |
|---|---|---|
| Quelle | `response.cards` (`OfferCard[]`) | `response.map_data.destinations` (`MapDestination[]`) |
| Menge | faktisch auf 3 begrenzt (`order_social_results(...)[:3]` in `app/service.py`); Schema-Limit `max_length=4` (`app/models.py::QueryResponse.card_ids`/`spoken_result_ids`) | bis zu 4 Standard (`build_map_data(..., limit=4)`), Marker-IDs bis 500 (`map_marker_ids: max_length=500`) |
| Inhalt | vollständig: Beschreibung, Dienste, Adresse, Telefon, Öffnungszeiten, Standzeiten, Notizen | schmal: Name, Adresse, Distanz, Beschreibung, Telefon, Öffnungszeiten — **keine** `services`/`standzeiten_raw`/`notes` |
| Interaktivität | keine (immer vollständig sichtbar) | keine (statischer Text, kein Klick-Handler) |
| Kartenmarker-Klick | – | öffnet nur ein Leaflet-Popup, keine Verbindung zur Liste |

Der vom Nutzer gezeigte Screenshot stammt aus `mapList`: dort können
**mehr** Angebote auftauchen als in `cardList` je gezeigt werden — für diese
zusätzlichen Einträge (z. B. "SZL Suchtzentrum gGmbH Tagestreff Insel" in
Position 6) sendet das Backend aktuell **keine** Detaildaten (Telefon,
Öffnungszeiten, Dienste) an das Frontend. Ein reines Frontend-Aufklappen
würde für diese Einträge nichts anzuzeigen haben — die Lücke liegt im
Datenvertrag, nicht nur in der Darstellung.

### Zielbild

Eine einzige Liste ("Tafeln"), synchron mit den Kartenmarkern:

- Jede Tafel zeigt kollabiert Name + Adresse + Distanz (wie heute `mapList`).
- Klick auf eine Tafel klappt sie auf und zeigt alle Details (wie heute
  `cardList`).
- Klick auf einen Kartenmarker klappt die zugehörige Tafel in der Liste auf
  (scrollt sie in den sichtbaren Bereich) — und umgekehrt hebt das
  Aufklappen einer Tafel den zugehörigen Marker hervor.
- Nicht mehr auf 3–4 Einträge begrenzt für die reine Anzeige (die
  LLM-Kernaussage/`answer`-Text bleibt weiterhin nur auf die engere,
  streng gegroundete Teilmenge gestützt — diese Trennung ist bewusst und
  bleibt erhalten, siehe unten).

### Entscheidung: Datenvertrag

**Empfohlener Ansatz — Anzeige- und Aussage-Menge entkoppeln:**

`response.answer` (Fließtext) bleibt weiterhin nur auf die eng gegroundete
Teilmenge gestützt (aktuell ≤3 Angebote) — daran ändert dieser Plan nichts,
das ist Kern der bestehenden Sicherheitsarchitektur (Grounding-Zwang,
`app/grounding.py`). Getrennt davon wird die **Anzeigemenge** vergrößert:

1. `app/service.py`: `response.cards` nicht mehr nur aus `final_offers`
   (≤3, LLM/Selector-eingeschränkt) befüllen, sondern aus der vollständigen,
   bereits deterministisch sortierten Kandidatenliste
   (`order_social_results(...)`, ohne `[:3]`-Kappung, ggf. mit sinnvoller
   Obergrenze — z. B. 10 — statt 3/4).
2. `app/models.py`: `card_ids`/`spoken_result_ids` `max_length` entsprechend
   anheben (aktuell `4`); `map_marker_ids` (`max_length=500`) ist bereits
   ausreichend dimensioniert.
3. `MapDestination` bleibt wie heute schlank (für Kartenperformance), aber
   die Verknüpfung Marker ↔ Tafel läuft über die bereits vorhandene
   `id`-Übereinstimmung zwischen `map_data.destinations[].id` und
   `response.cards[].id` — Frontend braucht dafür **keine** neuen
   Backend-Felder, nur konsequente Nutzung der vorhandenen IDs.
4. `spoken_result_ids` (max. 3, unverändert) bestimmt weiterhin, welche
   Karten in die *gesprochene* Zusammenfassung eingehen — unabhängig von der
   Gesamtzahl angezeigter Tafeln.

Diese Trennung ("was wird behauptet" vs. "was wird angezeigt") ist die
sauberere Lösung gegenüber der Alternative, `MapDestination` um `services`/
`notes`/`standzeiten_raw` zu duplizieren — sie vermeidet zwei parallele
Datenquellen für dieselbe Information und nutzt die ohnehin schon
deterministische, ungegroundete Natur von Kartendaten (Karten sind bereits
heute Template-Projektionen, keine LLM-Ausgabe, siehe `_card()`).

### Frontend-Umsetzung (`app/static/app.js`, `dialogue.js`-Pattern als Vorbild)

1. Neue Komponente `renderResultList(cards, mapData)` ersetzt die separaten
   `renderCards`/den Listenteil von `renderMap` (Karten-Rendering selbst
   bleibt in `renderMap`, nur die Text-Liste wandert in die neue,
   gemeinsame Komponente).
2. Jede Tafel: `<article class="offer-tile" aria-expanded="false">` mit
   Header (Name, Adresse, Distanz, klickbar) + Detailbereich
   (`hidden`-Attribut, per Klick umgeschaltet) — analog zum bestehenden
   `<details>`-Element-Muster, das die App schon für `historyPanel`
   verwendet (`app/static/index.html`), oder nativ mit `<details>`/`<summary>`
   für kostenlose Tastatur-/Screenreader-Semantik statt eigenem
   ARIA-Handling.
3. Marker-Klick (`marker.on("click", ...)` in `renderMap`) ruft eine neue
   Funktion `expandResultTile(id)` auf: setzt `open`/`aria-expanded` der
   passenden Tafel, scrollt sie in den sichtbaren Bereich
   (`scrollIntoView({behavior:"smooth", block:"nearest"})`).
4. Tafel-Klick hebt umgekehrt den zugehörigen Marker hervor (z. B. Leaflet
   `marker.openPopup()` plus kurzzeitige CSS-Hervorhebung).
5. CSS: neue Klassen `.offer-tile`, `.offer-tile[open] .offer-tile-summary`
   etc., angelehnt an bestehende `.clarification-panel`-Ästhetik für
   visuelle Konsistenz.

### Akzeptanzkriterien

- [ ] Alle vom Backend gelieferten Angebote (nicht nur die bisherigen 3)
      erscheinen als eigene, initial kollabierte Tafel mit Name/Adresse/
      Distanz.
- [ ] Klick auf eine Tafel zeigt alle Detailfelder, die heute in `cardList`
      erscheinen (Beschreibung, Dienste, Telefon, Öffnungszeiten,
      Standzeiten, Notizen).
- [ ] Klick auf einen Kartenmarker klappt die zugehörige Tafel auf und
      scrollt sie sichtbar.
- [ ] Die gesprochene Kurz-Zusammenfassung (`answer`, `speakText`) bleibt
      unverändert auf die engere, gegroundete Teilmenge beschränkt.
- [ ] Tastaturbedienung und Screenreader-Ankündigung funktionieren
      (`<details>`/`<summary>` oder gleichwertiges ARIA-Pattern).
- [ ] Bestehende Tests zu `renderCards`/`build_map_data`/`card_ids`-Limits
      angepasst statt gebrochen; neue Tests für die erhöhte Card-Anzahl und
      für Marker→Tafel-Synchronisation (Playwright/DOM-Test oder
      vorhandenes Frontend-Test-Setup, siehe `tests/test_dialogue_frontend.py`
      als Vorbild für HTML-Struktur-Assertions).

### Aufwand/Risiko

Mittel bis groß — größtes Teilstück dieses Plans. Berührt Backend-Datenvertrag
(`QueryResponse`-Schema-Limits), Service-Logik (`app/service.py`) und
größere Teile des Frontends. Empfehlung: als eigenes Arbeitspaket mit
eigenem Feature-Branch und eigener Testrunde umsetzen, nicht zusammen mit
Teil 2/4 in einem Schritt.

---

## Teil 4 — Sprachausgabe pro Angebot (Lautsprecher-Symbol je Tafel)

### Bestandsaufnahme

Die App hat bereits eine voll funktionsfähige, wiederverwendbare
Sprachausgabe: `speakText(message)` (`app/static/app.js`) ruft
`/api/speech/synthesize` mit beliebigem Text auf, spielt das Ergebnis ab und
ist bereits an einer Stelle verdrahtet (`replayAnswerButton` für den
Haupt-Antworttext). `stopSpeechOutput()` existiert ebenfalls und stoppt
laufende Wiedergabe sauber.

**Kein neuer Backend-Endpunkt nötig** — dies ist überwiegend eine
Frontend-Erweiterung.

### Umsetzungsvorschlag

1. Pro Tafel (aus Teil 3, oder unabhängig auch schon auf die heutige
   `cardList` anwendbar, falls Teil 3 später kommt) einen
   Lautsprecher-Button einfügen, analog zu `replayAnswerButton`.
2. Neue Hilfsfunktion `buildSpokenTextForOffer(offer)`: setzt aus den
   bereits im Frontend vorhandenen, lokalisierten Feldern (Name,
   Beschreibung, Adresse, Telefon, Öffnungszeiten, Standzeiten, Notizen,
   inkl. des neuen Hinweisfeldes aus Teil 2) einen zusammenhängenden,
   sprechbaren Text zusammen — rein deterministisch aus bereits
   angezeigtem Text, keine neue Datenquelle, kein LLM.
3. Klick-Handler: `stopSpeechOutput()` (falls eine andere Tafel gerade
   vorgelesen wird) → `speakText(buildSpokenTextForOffer(offer))`, Button
   während der Wiedergabe visuell als "aktiv" markieren (`aria-pressed`),
   Zustand zurücksetzen bei `audio.onended`.
4. i18n: neuer Schlüssel `ui.listen_to_offer` (aria-label/title) in
   `application_texts.json`, alle 5 Sprachen.

### Akzeptanzkriterien

- [ ] Jede Tafel hat ein Lautsprecher-Symbol mit sprechendem `aria-label`.
- [ ] Klick liest genau die Inhalte dieser Tafel vor, keine anderen.
- [ ] Wiedergabe einer Tafel unterbricht eine laufende Wiedergabe (eigene
      oder Haupt-Antwort) sauber, statt zu überlappen.
- [ ] Funktioniert unabhängig davon, ob Server-Sprachsynthese verfügbar ist
      (`state.serverSynthesisAvailable`-Check wie in `speakText` bereits
      vorhanden) — Button ausblenden/deaktivieren, wenn nicht verfügbar.
- [ ] Kein neuer Netzwerk-Call-Typ, nur Wiederverwendung von
      `/api/speech/synthesize`.

### Aufwand/Risiko

Klein. Reine Frontend-Wiederverwendung bestehender, bereits produktiv
laufender Funktionen. Geringstes Risiko der vier Arbeitspakete — guter
Kandidat, um zuerst umgesetzt zu werden.

---

## Empfohlene Reihenfolge

1. **Teil 4** (Sprachausgabe pro Tafel) — kleinster, isoliertester Schritt,
   unabhängig von Teil 3 sofort auf die heutige `cardList` anwendbar.
2. **Teil 2** (Hilfebus-Hinweis) — klein, unabhängig, guter zweiter Schritt.
3. **Teil 3** (Listen-Vereinheitlichung) — größter Umbau, sollte die
   Datenvertragsänderung (`card_ids`-Limit, `response.cards`-Befüllung)
   zuerst in einem Review absichern, bevor das Frontend darauf aufbaut.
   Teil 4 sollte danach auf die neuen, vollständigen Tafeln übertragen
   werden (Lautsprecher-Button wandert von `cardList`-Karten zu
   `offer-tile`-Elementen).
4. **Formulator-Zuverlässigkeit** (Teil 1, Backlog) — unabhängig von den
   UI-Arbeitspaketen, eigenes Vorhaben.

Jedes Arbeitspaket erhält beim Start eine eigene Umsetzung mit: Diff,
Testlauf (`python -m pytest -q`), und — bei Frontend-Änderungen — manueller
Verifikation im Browser, da UI-Interaktion nicht vollständig durch die
bestehende Python-Testsuite abgedeckt ist.

---

## Umsetzung (2026-08-07)

Reihenfolge wie oben empfohlen: Teil 4 → Teil 2 → Teil 3. Alle vier Teile
wurden in dieser Sitzung umgesetzt; Teil 1 bleibt bewusst offenes Backlog
(siehe dortige Empfehlung).

### Teil 4 — Sprachausgabe pro Angebot

Wie geplant, rein im Frontend, ohne neuen Endpunkt:

- `app/static/app.js`: `createListenButton()` (Lautsprecher-Button, gleiche
  SVG-Vorlage wie `replayAnswerButton`) und `speakText()` erweitert um einen
  optionalen `button`-Parameter (`setSpeechButtonActive`/
  `clearSpeechButtonActive`), damit der visuelle "spricht gerade"-Zustand
  zentral an einer Stelle verwaltet wird — verhindert, dass ein Button aktiv
  hängen bleibt, wenn eine andere Wiedergabe ihn unterbricht (kein `await`
  auf die unterbrochene alte Wiedergabe nötig).
- `addField()` sammelt beim Rendern jedes Feldes den sichtbaren Text in ein
  `speech`-Array ein; der Lautsprecher-Button liest exakt das vor, was auch
  angezeigt wird — keine zweite, separat zu pflegende Text-Quelle.
- `app/resources/bootstrap/i18n/application_texts.json`: neuer Schlüssel
  `ui.listenToOffer` in allen 5 Sprachen.
- `app/static/styles.css`: `.card-listen-button`, `.replay-button.is-speaking`.

### Teil 2 — Hilfebus-Einsatzzeiten-Hinweis

**Abweichung vom ursprünglichen Plan:** Der Plan sah einen neuen
`access_rules`-Code plus neues `OfferCard.access_notes`-Feld vor. Bei der
Umsetzung zeigte sich, dass `access_rules` bereits ein **maschinenlesbares
Feld für die deterministische Kandidatenauswahl** ist (exakter String-
Vergleich in `app/candidates.py:192`, z. B. für Helenes Zugangsregel) — ein
neuer Code dort hätte nur einen unlesbaren Rohstring in die LLM-Evidence
eingeschleust, ohne echten Anzeige- oder Zitier-Nutzen. Stattdessen wurde das
bereits vollständig verdrahtete `notes`-Feld verwendet:

- `app/resources/bootstrap/curation/social_offers.json`: `runtime_overrides.notes`
  für den Hilfebus (Angebot-ID `21`) um "Rufe während der Einsatzzeiten
  (täglich 18:00–23:00 Uhr) direkt beim Hilfebus an." ergänzt (neben dem
  bestehenden Instagram-Hinweis). `notes` ist ein regulär in
  `ALLOWED_OVERRIDE_FIELDS` gelistetes, kuratierbares Feld
  (`app/curation.py:232-245`).
- Dadurch automatisch abgedeckt, ohne weiteren Code: Kartenanzeige
  (`addField(..., text().notes, offer.notes, ...)`), Sprachausgabe (Teil 4,
  da `notes` bereits Teil des `speech`-Arrays ist) und LLM-Grounding
  (`FactType.NOTE` in `app/formulation.py::_facts_for_offer`, bereits
  bestehender, generischer Pfad).
- Neuer Test: `tests/test_curation.py::test_hilfebus_runtime_notes_include_operating_hours_call_reminder`
  — prüft Quell- vs. Runtime-Notes, dass `access_rules` weiterhin leer bleibt
  (also nicht zweckentfremdet wurde), und dass der Hinweis als zitierbarer
  `FactType.NOTE`-Fact in der Formulator-Evidence ankommt.

**Wichtige Nebenwirkung, die dabei entdeckt und behoben wurde:**
`curation_catalog_hash` (`app/curation.py::load_curation_catalog`) ist ein
SHA-256 über die **gesamten Rohbytes** von `social_offers.json` — jede
Änderung an der Datei, egal wo, invalidiert den `curation_catalog_hash` für
**alle** Angebote im gespeicherten Übersetzungsstand
(`data/i18n/offer_translations.json`), nicht nur für das geänderte Angebot.
Direkt nach der Notes-Änderung schlugen deshalb ~104 Prüfungen in
`tests/test_translation_quality.py` fehl (u. a. auch für unveränderte
Angebote wie Scharni). Vor jedem `generate`-Lauf wurde per
`python -m app.translate_offers status` verifiziert, dass keine
`reviewed`-Übersetzungen betroffen sind (Ergebnis: ausschließlich
`machine`/`stale`, keine einzige `reviewed` im gesamten Bestand) — erst
danach wurde `python -m app.translate_offers generate --provider blablador
--languages en,pl,ro,ru` ausgeführt, um den Übersetzungsstand neu zu
erzeugen und den Hash wieder zu synchronisieren. **Merke für künftige
Kurations-Änderungen:** Jede Änderung an `social_offers.json` erfordert
danach einen `generate`-Lauf (oder mindestens `status`, um den Umfang zu
prüfen), bevor die Testsuite wieder grün ist.

### Teil 3 — Ergebnisliste vereinheitlichen

**Korrektur einer Plan-Annahme:** Der Plan ging davon aus, dass
`response.cards` (und damit die volle Detailtiefe) technisch auf die enge,
LLM-formulierte Teilmenge (≤3) begrenzt sei und `card_ids`/`spoken_result_ids`
(`max_length=4`) angehoben werden müssten. Ein Live-Test zeigte: Das Backend
baut `map_data` an der zentralen Stelle in `app/service.py`
(`eligible_map_offers = order_social_results(decision.candidates, ...)`,
`build_map_data(eligible_map_offers, limit=None, ...)`) bereits **aus der
vollständigen, ungekappten Kandidatenmenge** — unabhängig von den ≤3 Karten
der Antwort. Ein Beispiel-Query lieferte 3 `cards`, aber 5
`map_data.destinations` inklusive Adresse/Telefon/Öffnungszeiten. Der
tatsächliche Fehlbestand war viel kleiner als angenommen: `MapDestination`
hatte schlicht drei Felder nicht, die `OfferCard` bereits hatte. Entsprechend
kleiner blieb der Backend-Eingriff — **keine** Änderung an
`card_ids`/`spoken_result_ids`-Limits oder an der `response.cards`-Befüllung
nötig:

- `app/models.py`: `MapDestination` um `services`, `standzeiten_raw`, `notes`
  erweitert (Default: leere Liste, rückwärtskompatibel).
- `app/maps.py`: `build_map_data()` und `_stand_destination()` (Hilfebus-/
  Medibus-/Schwanenteich-Standzeiten) befüllen die drei neuen Felder aus dem
  `OfferRecord`.
- `app/infrastructure_results.py`: `toilet_map_data()` setzt jetzt zusätzlich
  `source_attribution="Stadt Leipzig"` (fehlte bisher auf `MapDestination`,
  war aber auf `PublicToiletCard` immer per Modell-Default gesetzt —
  Detailparität zwischen Karte und Kartenpunkt-Tafel).

Frontend (`app/static/app.js`, `index.html`, `styles.css`):

- `#mapList` (kompakte, nur-Name/Adresse/Distanz-Zeilen) entfernt;
  `#cardList` ist jetzt der alleinige Listen-Container, strukturell
  unabhängig von der Kartensichtbarkeit positioniert (Geschwister von statt
  verschachtelt in `#mapPanel`) — zeigt die Liste auch, wenn kein Angebot
  gültige Koordinaten hat.
- `renderCards()` ersetzt durch `renderResultList(cards, mapData)` +
  `buildOfferTile(item, {highlighted})`: baut aus `mapData.destinations`
  (bevorzugt, vollständige Menge) oder `cards` (Fallback ohne Kartendaten)
  je ein natives `<details class="offer-tile">`-Element — kollabiert zeigt
  Name/Adresse/Distanz, aufgeklappt alle Detailfelder. Native
  `<details>`/`<summary>`-Semantik statt eigenem ARIA-Handling (Tastatur- und
  Screenreader-Unterstützung kostenlos).
- Tafeln, deren ID auch in `data.cards` vorkommt (die engere, im Fließtext
  zitierte Teilmenge), erhalten ein Abzeichen `ui.mentionedInAnswer` ("Wird
  in der Antwort genannt") — macht die bewusste Trennung "was wird gezeigt"
  vs. "was wird behauptet" für Nutzer sichtbar, statt sie zu verstecken.
- `renderMap()`: Listen-Aufbau entfernt (jetzt exklusiv in
  `renderResultList()`), Marker erhalten stattdessen einen Klick-Handler
  (`marker.on("click", () => expandResultTile(destination.id))`).
  `expandResultTile(id)` öffnet die passende Tafel (`tile.open = true`) und
  scrollt sie in den sichtbaren Bereich.
- `state.resultTiles` (Map von Angebots-ID auf DOM-Element) verbindet Marker
  und Tafeln; wird bei jedem `renderResultList()`-Aufruf sowie in
  `resetView()`/`backToSearch()` zurückgesetzt.
- Tote CSS-Regeln (`.map-list`, `.map-list-item`, alte `.offer-card*`) durch
  `.offer-tile*`-Regeln ersetzt.

### Nachtrag — TTS-Sicherheitslücke bei Teil 4, gefunden in der Browser-Verifikation

Die Browser-Verifikation (Playwright, headless Chromium) deckte auf, dass der
Vorlese-Button aus Teil 4 in der Praxis mit **409 Conflict** scheiterte:
`/api/speech/synthesize` (`app/main.py`) akzeptiert ausschließlich Text, der
exakt `session.turns[-1].answer` entspricht — eine bewusste Anti-Injection-
Schranke, damit der Client dem TTS-Endpunkt niemals beliebigen Text unterschieben
kann. Der clientseitig aus Kartenfeldern zusammengesetzte Tafel-Text (Teil 4)
konnte diese Prüfung naturgemäß nie bestehen.

**Fix, nicht Umgehung:** Der Server ist jetzt die alleinige Quelle des
vorlesbaren Texts:

- Neues Modul `app/spoken_text.py`: `offer_spoken_text()`,
  `toilet_spoken_text()`, `fountain_spoken_text()` bauen aus denselben
  Feldern, die auch angezeigt werden, einen Text nach demselben Muster wie
  vorher im Frontend (Label aus `application_texts.json`, "> "-Aufzählungen
  entfernt).
- `OfferCard`, `PublicToiletCard`, `DrinkingFountainCard`, `MapDestination`
  (`app/models.py`) erhalten ein neues Feld `spoken_text: str`, befüllt an
  der jeweiligen Konstruktionsstelle (`app/i18n.py::localize_offer_card`,
  `app/infrastructure_results.py`, `app/maps.py`).
- `ConversationSession` (`app/sessions.py`) merkt sich zusätzlich
  `speakable_texts: list[str]` — die Menge der für den *aktuellen* Turn
  gültigen Kartentexte (bewusst nicht Teil von `ChatTurn`/`response.history`,
  damit die sichtbare Verlaufsanzeige nicht wächst). `add_turn()` erhält
  dafür einen neuen optionalen Parameter.
- `/api/speech/synthesize` (`app/main.py::synthesize_speech`) akzeptiert
  jetzt `payload.text`, wenn es entweder der letzten Antwort **oder** einem
  Eintrag in `session.speakable_texts` entspricht — weiterhin keine
  Freitext-Synthese.
- Frontend: `buildOfferTile()`/`createListenButton()` senden `item.spoken_text`
  unverändert weiter, statt selbst Text zusammenzusetzen; `addField()` verlor
  dadurch die zwischenzeitliche `speech`-Sammel-Option wieder (nicht mehr
  gebraucht — eine echte Vereinfachung, kein Kompromiss).
- `build_map_data()`/`offer_stand_destinations()` mussten dafür einen
  `language`-Parameter erhalten; `result_ordering.py::social_result_distance`
  ruft `offer_stand_destinations()` weiterhin ohne Sprache auf
  (`language=None`), da dort nur die Distanz gebraucht wird und der
  Text-Aufbau pro Sortiervergleich sonst unnötig wiederholt würde.

Live gegen die neu gestartete App verifiziert (Playwright): `SPEECH_SYNTH_STATUS`
vorher `409`, nachher `200`, keine Konsolenfehler mehr.

**Lehre:** Ein neues Frontend-Feature, das einen bestehenden Endpunkt
wiederverwendet, muss dessen tatsächliche Vertragsbedingungen prüfen (hier:
serverseitige Content-Allowlist), nicht nur seine Aufruf-Signatur. Das wäre
ohne den Playwright-Lauf erst in Produktion aufgefallen.

### Simplify-Pass (4 parallele Review-Agenten: Reuse/Simplification/Efficiency/Altitude)

**Angewendet:**
- `app/i18n.py::localize_offer_card` auf einen einzigen Rückgabepunkt reduziert
  (baute vorher an vier Exit-Punkten `spoken_text` separat auf, mit doppeltem
  `model_copy` im Übersetzungs-Zweig).
- `app/main.py::synthesize_speech`: `known_texts`-Aufbau lesbarer geschrieben.
- `app/sessions.py`: `speakable_texts` ist jetzt auf `max_speakable_texts = 40`
  begrenzt (wie `turns`/`max_turns` bereits begrenzt sind) — ohne Deckel hätte
  eine Toiletten-/Trinkbrunnen-Anfrage mit bis zu 500 Kartenpunkten ebenso viele
  volle Sätze in die Session-Datei geschrieben, bei jedem Turn und für die
  gesamte Session-Datei (nicht nur die eine Session) neu serialisiert und
  ge-fsynct.
- `app/service.py`: neuer Helfer `_adopt_card_spoken_text()` lässt Kartenpunkte
  bei Toiletten/Trinkbrunnen den `spoken_text` der zugehörigen Karte
  übernehmen (Konsistenz-Absicherung, analog zum bestehenden Muster für
  soziale Angebote).
- `app/service.py`: `nearest_distance` für Toiletten baut nicht mehr eine
  komplette `PublicToiletCard` (inkl. `spoken_text`-Aufbau) nur um ein
  Distanz-Feld zu lesen, sondern ruft `distance_from_hbf()` direkt auf.
- `app/spoken_text.py`: `offer_spoken_text`/`toilet_spoken_text`/
  `fountain_spoken_text` nutzen jetzt einheitlich denselben `_spoken_text()`-
  Kern statt zweier verschiedener Idiome.
- `app/static/app.js::buildOfferTile`: tote `item.short_description ||`/
  `item.opening_hours_raw ||`-Fallback-Hälften entfernt (nach der
  Normalisierung in `offerCardAsDestination`/`MapDestination` nie belegt).

**Bewusst nicht angewendet (dokumentierter Verzicht, kein übersehener Fund):**
- *Eliminierung* der doppelten `toilet_spoken_text`/`fountain_spoken_text`-
  Berechnung (Karte und Kartenpunkt bauen den String weiterhin unabhängig,
  `_adopt_card_spoken_text` behebt nur das Konsistenzrisiko danach). Eine
  echte Deduplizierung hätte die Signaturen von `toilet_map_data`/
  `drinking_water_map_data` erneut ändern müssen für einen bei den aktuellen
  Datensatzgrößen (wenige Toiletten/Brunnen pro Antwort) marginalen Gewinn.
- `language: Language | None = None` an `offer_stand_destinations`/
  `_stand_destination`/`build_map_data`, nur damit
  `result_ordering.py::social_result_distance` (reine Distanzsortierung) ohne
  Sprache aufrufen kann. Der sauberere Schnitt (eigene, von `MapDestination`
  unabhängige Distanz-Hilfsfunktion) griffe in bereits bestehende,
  gut getestete Sortierlogik ein, die nicht Teil dieses Feature-Umfangs ist.
- Vereinheitlichung der Feldauswahl/-reihenfolge zwischen `app/spoken_text.py`
  (Python) und `buildOfferTile` (JS) über eine gemeinsame deklarative
  Spezifikation. Beide Listen stimmen heute Feld für Feld überein, sind aber
  weiterhin von Hand parallel zu pflegen. Bei einem stabilen, kleinen
  Feldkatalog wie hier ist das vertretbar; bei künftigen Erweiterungen lohnt
  sich eine gemeinsame Spezifikation.
- Semantische Vereinheitlichung von `MapDestination.address` (trägt je nach
  `record_type` Straßenadresse, Ortsteil oder Standortbeschreibung) in
  eigene Felder. Betrifft nur, dass Toiletten-Tafeln ihren Ortsteil nicht
  zusätzlich als eigene Zeile im aufgeklappten Bereich zeigen — er steht
  bereits sichtbar in der Kopfzeile jeder Tafel.

Volle Testsuite und Playwright-Verifikation nach dem Simplify-Pass erneut
grün (`SPEECH_SYNTH_STATUS=200`, keine Konsolenfehler).

### Offene Nacharbeit / bekannte Grenzen

- **Übersetzungen für den neuen Hilfebus-Hinweis**: Die `generate`-Ausführung
  lief mit `--provider blablador` (echte Maschinenübersetzung), nicht mit dem
  Test-Double `--provider copy`. Die neuen EN/PL/RO/RU-Texte sind damit
  Maschinenübersetzungen ohne menschliches Review (`linguistic_review_status:
  machine`) — konsistent mit dem Rest des Bestands (aktuell keine einzige
  `reviewed`-Übersetzung im System), aber vor einem echten Rollout an
  Endnutzer:innen wäre ein Review-Durchlauf (`export-review`/`import-review`)
  sinnvoll.
- **Barrierefreiheit der Tafeln**: manuell im Browser mit Tastatur und
  mindestens einem Screenreader gegenzuprüfen (native `<details>`-Semantik
  sollte tragen, wurde aber nicht mit echter AT verifiziert).
- **Teil 1 (Formulator-Zuverlässigkeit)** bleibt wie geplant unangetastet.
