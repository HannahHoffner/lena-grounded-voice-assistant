# Execution Plan: Validator-Ablationstest (Formulator mit und ohne Faktenprüfung)

## Status
26.10.2026, freigegeben durch die Nutzerin, in Ausführung. Keine Änderung an
Anwendung, Tests, Daten, Prompts, Konfiguration oder Thesis.

## Fragestellung
Wie oft enthalten die Antworten des produktiven Formulators (Textvertrag 7,
Prompt 25) **ohne** inhaltliche Faktenprüfung falsche oder unbelegte Aussagen,
und wie viele davon fängt der Regelvalidator ab, übersieht er oder lehnt er
unnötig ab? Die Hypothese „die Formulatorantworten sind bereits richtig“ wird
damit geprüft, nicht vorausgesetzt.

## Verfahren
- **Ein Lauf, gepaarte Auswertung.** Der Validator verändert angenommene
  Antworten nicht. Deshalb liefert ein einziger Lauf beides:
  - „ohne Validator“ = erster geparster Formulatorversuch;
  - „mit Validator“ = tatsächlich angezeigte Antwort (angenommener Erst- oder
    Retryversuch bzw. kuratiertes Template).

  Zwei getrennte Läufe würden wegen nicht deterministischer Modellantworten
  unterschiedliche Texte vergleichen.
- **Erfassung ohne Codeänderung:** Ein externes Skript umschließt
  `app.providers.llm.validate_formulation` und
  `BlabladorProvider.formulate_answer` zur Laufzeit. Erfasst werden pro Versuch:
  Evidence-Paket, geparste Antwort, Validatorurteil und Diagnose. Pro Anfrage
  zusätzlich die angezeigte Antwort.
- **Fragen:** 24 synthetische Fragen × DE/EN/PL/RO/RU = 120 Einzelanfragen, je
  mit neuer Session. Abgedeckt sind Essen, Hygiene, Kleidung, Medizin, Beratung,
  Schlafen mit expliziten Angaben, Sucht, Toilette, Trinkwasser und Tagestreff,
  dazu zwei Manipulationsversuche. Der Katalog wird vor dem Lauf gehasht.
  Anfragen, die ohne Formulator enden (Dialog, Template, technischer Rückfall),
  werden gezählt, aber nicht bewertet.
- **Profil:** Commit `02a3612`, `alias-fast` in allen Stufen, 4096 Tokens,
  15/30/30 s, Budget 45 s, Temperatur 0. Höchstens zwei Anfragen parallel.
  Kein Wiederholen bis zu einem gewünschten Ergebnis. Abbruch bei mehr als
  20 % Transportfehlern in den ersten 20 Anfragen.
- **Bewertung:** allein durch die Nutzerin (kennt die Angebote), **blind** zum
  Validatorurteil, in zufälliger Reihenfolge. Codes:
  - `R` richtig;
  - `FK` falsch, kritisch (Aufnahme/Garantie, Zielgruppe/Alter, Zeit/Tag,
    Kontakt, falsches Angebot, Verfügbarkeit, Negation);
  - `FU` falsch, unkritisch;
  - `U` unklar.

  Für PL/RO/RU gibt es eine deutsche Hilfsübersetzung durch Claude. Sie ist
  ausdrücklich nicht maßgeblich. Bewertet werden auch angenommene Antworten,
  sonst bleiben übersehene Fehler unsichtbar. Angezeigte Retrytexte werden als
  eigene Items bewertet; kuratierte Templates werden nicht bewertet.
- **Auswertung:** Vierfeldertafel (Validator nimmt an/verwirft × richtig/falsch)
  mit Wilson-95-%-Intervallen für:
  - Formulatorfehlerquote ohne Validator;
  - abgefangene, übersehene und unnötig verworfene Antworten;
  - Korrektheit der angezeigten Antworten mit Validator;
  - Templatequote;
  - Aufschlüsselung nach Sprache und Fehlerart.

  Das Auswertungsskript wird vor der Bewertung festgehalten.

## Grenzen
- Eine einzige Bewerterin, die zugleich Autorin ist: keine Übereinstimmungsmessung.
- 120 Anfragen sind keine repräsentative Stichprobe. Null Fehler bedeuten keine
  Fehlerfreiheit (Rule of Three).
- Die Hilfsübersetzungen können Fehler verdecken oder erzeugen; markierte
  Unsicherheiten gehen als `U` in die Auswertung ein.
- Ergebnis gilt nur für diesen Commit, dieses Modellprofil und diesen Zeitpunkt.
  Fachliche Hilfsqualität und Verständlichkeit werden nicht bewertet.

## Ablage
Extern unter `%LOCALAPPDATA%/LENA/verification/2026-10-26-validator-ablation/`:
- `queries.json`, `manifest.json`
- `run.py`, `results.jsonl`
- `bewertung.csv`, `evidenz.md`
- `schluessel.json` (erst nach der Bewertung öffnen)
- `auswertung.py`, `ergebnis.md`

Im Repository nur dieser Plan.

## Fortschritt
- Plan erstellt.
- Lauf am 26.10.2026 abgeschlossen: Commit `02a3612` (Anwendungsquelle vor und
  nach dem Lauf unverändert), KB-Fingerprint `9471e705…`. 120/120 Anfragen, kein
  Abbruch. Davon 113 mit geparstem Erstversuch, 7 ohne Formulatoraufruf;
  3 Interpreter-Schemafehler. Keine Zugangsdaten in Ergebnissen oder Logs.
- Blindes Bewertungspaket erzeugt: 127 Items (113 Erstversuche, 14 angezeigte
  Retrytexte), 72 Hilfsübersetzungen. `auswertung.py` vor der Bewertung per
  Prüfsumme festgeschrieben (`pruefsummen.txt`).
- Bewertung durch die Nutzerin am 27.10.2026 abgeschlossen (127 Items: 111 R,
  4 FK, 1 FU, 11 U), Auswertung mit unverändertem Skript (Prüfsumme bestätigt).
  Ergebnis extern in `ergebnis.md`.

## Ergebnis (Erstversuche, n = 103 ohne U)

| | richtig | falsch |
|---|---:|---:|
| Validator nimmt an | 12 | 2 (1 kritisch) |
| Validator verwirft | 86 | 3 (3 kritisch) |

- **Fehlerquote ohne Validator:** 4,9 % [2,1–10,9 %]; kritisch 3,9 % [1,5–9,6 %].
- **Unnötig verworfen:** 86 von 98 richtigen Antworten (87,8 % [79,8–92,9 %]).
  Templatequote mit Validator 72,8 %.
- **Ablehnungsgründe:** `content_not_covered` (53×) und `service_fact_missing`
  (19×) betrafen ausschließlich richtige Antworten.
- **Kein beobachteter Fehler war eine Formulator-Halluzination.** Alle fünf
  Fehler stammen aus der Datenauswahl bzw. den Daten:
  - **Wundfrage (4× FK, alle Sprachen):** Die Kandidatenregel verlangt exakt
    `wound_care`; diese Fähigkeit hat nur das an Drogenkonsum gebundene A1 –
    Kontaktcafé. Ergebnis: „kein Angebot“, obwohl UVO (Medibus, u. a. sonntags
    20:00 Hbf), Oase, Helene, Rücke und das mobile Zentrum für Drogenhilfe
    `medical_care` anbieten.
  - **Hilfebus mit Büroadresse Demmeringstr. 32 (1× FU):** die Adresse stammt
    aus der Evidence.
- **Die drei „abgefangenen“ Fehler sind nur zufällig abgefangen.** Der
  Validator verwarf sie wegen einer fehlenden Formulierung
  (`no_result_boundary_missing`). Das angezeigte Template sagte inhaltlich
  dasselbe („kein passendes Angebot“). Den einzigen Datenfehler im Text
  (Demmeringstr.) ließ er durch, weil die Adresse belegt war. Ein Validator kann
  Fehler, die mit der Evidence übereinstimmen, grundsätzlich nicht erkennen.
- **Weitere Kommentare der Bewerterin (Darstellung, keine Faktenfehler):**
  - „geprüft“ bei Trinkbrunnen weglassen;
  - keine Telefonnummern bei Toiletten;
  - Hilfebus mit Einsatznummer statt Mitarbeiternummer;
  - „flexibel nach Bedarf“ nicht als Zusage;
  - in Antworten ohne Treffer nicht „Datenbank/Wissensbasis“ sagen;
  - Sonntagsessen: Hilfebus-Standzeit nennen;
  - Namen: Tagestreff Insel, Tagestreff Oase, Übernachtungshaus für wohnungslose Frauen.

**Grenzen:** eine Bewerterin, synthetische Anfragen, ein Lauf. 0 Halluzinationen
bei 103 Antworten schließen eine Rate bis ca. 3,6 % nicht aus. Die 11 U-Bewertungen
betreffen überwiegend fremdsprachige Manipulationsfragen.
