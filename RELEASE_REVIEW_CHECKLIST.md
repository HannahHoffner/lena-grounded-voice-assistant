# Manueller Release-Review – LENA, Stand 26.10.2026

**Aktueller Status: Commit 2462e7d versioniert, vierstufige Messung abgeschlossen; menschlicher Release-Review und manuelle Evaluation ausstehend.**
Keine uneingeschränkte Abgabe- oder Veröffentlichungsempfehlung. Diese Liste
ist ein Reviewinstrument; offene Punkte sind keine bereits erteilten Freigaben.
In diesem Dokumentationsauftrag wurden keine neuen Tests, Builds, Liveaufrufe,
Commits, Tags oder Pushes ausgeführt. Anwendung, Daten und Konfiguration bleiben
auf dem geprüften technischen Stand.

## Aktuelles Messergebnis vom 26.10.2026

Die folgende Vorabcheckliste bleibt als Reviewinstrument erhalten; ihre offenen
Rechte-/Sprach-/Bedien-/Aufbewahrungspunkte sind nicht automatisch abgehakt.
Commit und einmalige vierstufige Messung sind technisch erledigt. Ergebnis:

| Stufe / Run-ID | Anfragen / Provideraufrufe | Fehlerfälle | Inhaltsabweichungen / kritisch | Vertragsgate / Inhaltsgate |
|---|---|---|---|---|
| Interpreter `run_7d26ad94463c490fbdbb8f02122e4c28` | 15 / 15 | 0 | 1 / 0 | bestanden / nicht bestanden |
| Selector/Formulator `run_4a90aba53e164c4593d14cd2d39f0237` | 16 / 18 | 0 terminale | 0 / 0 | bestanden / bestanden |
| E2E `run_f61552f6c5fc4e4daaa83024b4163a7d` | 34 / 52 | 2 | 0 / 0 | nicht bestanden / nicht bestanden |
| Stabilität `run_642870f9c3c746e999acba1c094ca81f` | 18 / 37 | 1 | 0 / 0 | nicht bestanden / nicht bestanden |

E2E/Stabilität zählen 2/1 erholte Formulatorfehler; kein katalogseitig kritischer
Fehler, sechs Antworttypen dreimal stabil. 54/51 Kriterien und menschliches
Review offen. Empfehlung für formative manuelle Evaluation mit dokumentierten
Grenzen, keine vollständige Freigabekette. [Bericht 12](IMPLEMENTATION_REPORT.md#12-abschließende-vierstufige-live-messung-am-commit-2462e7d).
Die älteren Aussagen „noch nicht gemessen/versioniert“ unten beschreiben den
Vorbereitungsstand und werden nicht als heutiger Messstatus gelesen.

## 1. Vorhandene technische Nachweise prüfen

- [ ] [Bericht 11](IMPLEMENTATION_REPORT.md#11-technisch-geprüfter-stand-für-den-manuellen-release-review-26102026)
  mit der externen `HANDOVER.md` und den Rohbelegen abgleichen. Kanonischer
  Basis-HEAD `15a912f657a3e47e2c0d96a6a9201a693ea134db` enthält die späteren
  uncommittierten Korrekturen allein noch nicht.
- [ ] Prüfidentität festhalten: `source-final/`, 220 Dateien;
  `final-source-manifest.json` SHA-256
  `a393b01071b7c70f0dd1a6a0c6db523bae811006a742ad22853314377aab6917`.
  Heutige reine Dokumentationsfortschreibung separat zuordnen. Der alte
  Gesamthash ist kein Hash eines künftigen vollständigen Releasecommits.
- [ ] Je **1476 bestandene Python-Tests**, ein bekannter **strikter XFAIL**,
  null Fehler nativ und im netzlosen Container sowie je **19/19 JS** richtig
  übernehmen. XFAIL `minor injuries` betrifft den historischen Wortvalidator;
  die bekannte Starlette-TestClient-DeprecationWarning bleibt sichtbar.
- [ ] Clean-Room-Build, Runtime, Health, Loopback-Port, read-only Root-FS,
  Start ohne Schlüssel, Blablador und Sessions nach Neustart/Containerersatz
  anhand der vorhandenen Logs prüfen. Zwei externe Snapshotserverfehler vor
  dem erfolgreichen dritten No-Cache-Build nicht unterschlagen. Nachgewiesen
  ist Linux/AMD64, keine allgemeine Plattform-/Mindesthardwaregarantie.
- [ ] Die [zehn direkten Formulatorfälle](docs/live-provider-evaluation.md#zehn-fälle-stichprobe-vom-26102026)
  korrekt einordnen: neun gültige Pläne, ein korrekt abgelehnter Plan, null
  Schemafehler. Einmalproben, kein regulärer Stufe-2-Retry, kein vollständiger
  Vierstufenlauf und kein unabhängiges menschliches Qualitätsurteil.

Lokales Belegarchiv:
`C:/Users/User/AppData/Local/LENA/verification/2026-10-25-blockers/`.
Es ist noch kein veröffentlichtes Evidenzpaket. Tests/Builds vom 23.–25.10.
behalten ihre ursprünglichen Identitäten und werden nicht auf neue Stände
umetikettiert.

## 2. Historische Ausgangsgates und Reviewmaßstab

Vorherige vollständige Reihe vom 25.10., vor der Blockerkorrektur.
Sie wurde am 26.10. am Commit 2462e7d neu erhoben (Ergebnisse oben); die
folgenden Zahlen bleiben historische Ausgangswerte. Ein historisch bestandenes Gate ist keine neue Messung des
korrigierten Stands. Stufenfehler zählen auch bei anschließend erholtem Retry.

| Stufe | Historisch Anfragen / Provideraufrufe | Fehlerfälle / Inhaltsabweichungen | Reviewauftrag am finalen Stand |
|---|---|---|---|
| Interpreter | 15 / 15 | 0 / 0; beide Gates bestanden | erneut messen: heutiger Prompt 12 und begrenzter Namenslookup |
| Selector/Formulator | 16 / 21 | 4 / 0; beide Gates negativ | vollständige sechs Selector- und zehn Formulatorfälle mit tatsächlicher Anwendungs-Retrypolitik |
| E2E | 34 / 59 | 6 / 1; beide Gates negativ | alle 27 Abläufe / 34 Requests, Dialog-/Safety-/Sprachwechsel-/Zeitpfade prüfen |
| Stabilität | 18 / 40 | 8 / 0; beide Gates negativ | sechs Abläufe je dreimal, technische und inhaltliche Stabilität getrennt |

- [ ] Den vollständigen Lauf erst nach unten beschriebenem Review/Commit und
  bewusster Livefreigabe durchführen. Dieser Auftrag startet ihn nicht.
- [ ] Unveränderten kataloggebundenen Messplan und Limits verwenden; jedes
  Stadium einzeln starten. Bei negativem Gate kein bestandenes Freigabepaket
  behaupten. Etwaige Folgestufen ausdrücklich nur als Diagnose kennzeichnen.
- [ ] Alle Rohreports, einschließlich Fehlschlägen, Timeouts und erholten
  Retrys, erhalten. `completed` oder CLI-Exit 0 bedeutet abgeschlossene
  Erhebung, kein bestandenes Gate. Kein Wiederholen auf Grün oder nachträgliches
  Lockern von Erwartungen/Enums/Gates.
- [ ] Vorhandene negative Befunde vom 23.10. einschließlich kritischem
  Interpreterausfall bei Akutunsicherheit in die fachliche Bewertung aufnehmen;
  nicht als durch den neuen Renderer gelöst behandeln.
- [ ] Ungeprüfte Kriterien ausdrücklich bearbeiten: in der alten Reihe 54 E2E-
  und 51 Stabilitätskriterien. Für neue Läufe deren eigene offenen Kriterien
  berichten. Metadatensprache ist kein Sprachqualitätsnachweis.
- [ ] Falls Code/Regeln/Prompts nach Review geändert werden müssen: neue
  Prüfidentität, passende Regression/Buildprüfung und neue relevante Messung;
  vorherige Ergebnisse unverändert bewahren.

Verträge aktuell: Interpreter 4/12, Selector 1/3, Evidence 4, Formulator 6/24,
Groundingvalidator 6. [Live-Verfahren](docs/live-provider-evaluation.md) und
[Testdokumentation](docs/testing.md) erklären Grenzen und historische Läufe.

## 3. Fachliche, sprachliche und Bedienprüfung

- [ ] Verantwortliche fachkundige Person bestätigt den eingefrorenen Datenstand
  mit Datum/Prüfumfang: Zuständigkeit, Zielgruppen, Zugang, Kontakt, Zeiten,
  Orte und eingeschränkte Leistungen. Hashgleichheit ist keine Sachprüfung.
- [ ] Kurationsstatus `reviewed_for_prototype` von formaler institutioneller
  Freigabe unterscheiden; offenen Reviewturnus und Quelländerungen dokumentieren.
  Frischer Container nutzt den paketierten Bootstrap; `degraded`/`pointer_error`
  ist hier dokumentierter Fallbackstatus, kein Nachweis aktueller externer Daten.
- [ ] Deutsch, Englisch, Polnisch, Rumänisch und Russisch menschlich prüfen:
  feste Antwort-/Safety-/Dialogtexte, neue kurze Unbekanntheitsakte, ausgewählte
  Quellwerte und Kartenübersetzungen. Maschinenstatus nicht in „reviewed“
  umdeuten; Reviewperson, Datum, Beispiele und Urteile festhalten.
- [ ] Sichtbare Bedienung auf dem vorgesehenen Evaluationsrechner prüfen:
  Texteingabe, Transkript, Antworten/Karten, Rückfragen, Sprachwechsel, Reset
  während Requests, Inaktivitätsreset, optional Mikrofon, Vorlesen/Stoppen und
  tatsächliches Kachelladen. HTTP-/JS-Doubles ersetzen diesen Nachweis nicht.
- [ ] Verbleibende Risiken in die Bewertung aufnehmen: fehlerhafte LLM-
  Interpretation oder Auswahl, zurückgewiesene ungültige Pläne, informationsarme
  Kontaktantworten bei langen Bedingungen, zu allgemeine Ausschlussantworten.
- [ ] Konkrete Grenzen prüfen: Kübel/Grünau ist begrenzte kuratierte Zuordnung
  mit Zuständigkeitsvorbehalt. Scharni ist als Schlafangebot kuratiert;
  Grundversorgung belegt keinen eigenständigen Essenszugang. Keine Aufnahme-
  oder Verfügbarkeitsgarantie aus statischen Daten ableiten.

## 4. Datenrechte und Logginggrenzen

- [ ] Vor öffentlicher Daten-/Imageweitergabe Rechte für Trinkbrunnen-KML und
  ergänzende Betreiberangaben klären. `not_explicitly_specified` ist keine Lizenz.
- [ ] Konkrete Lizenzzuordnung des WFS-Endpunkts klären. Vorhandene pauschale
  Zuordnung in `THIRD_PARTY_NOTICES.md` und UI ist keine unabhängige Bestätigung;
  Attributionen/Notices nach Rechteklärung konsistent machen. Eigene GPL deckt
  fremde Daten nicht automatisch ab.
- [ ] N-03 ausdrücklich bewerten: erlaubte Diagnosefelder begrenzen zusätzliche
  Felder; rohe URL-Pfade, Uvicorn-Queries und Grundnachrichten/Exceptions können
  trotzdem sensible Inhalte enthalten. Ein POST-Smoke ohne Texttreffer beweist
  keine allgemeine Secret-/Personendatenfreiheit. Kein Nachweis, dass normale
  Query-POST-Bodies tatsächlich geleakt sind.
- [ ] Für die geplante synthetische Evaluation isolierte Runtime außerhalb
  Cloudsync, Zugriff, Aufbewahrung und anschließende Löschung festlegen. Auch
  bei ausgeschaltetem Interaktionslog speichern Sessions nicht-akute Texte.
  UI-Reset löscht keine Serverdaten; TTL wird bei Zugriff bereinigt,
  Interaktionslogs haben keine automatische Löschfrist.
- [ ] Vor personenbezogenen Eingaben die Logginggrenzen technisch und
  organisatorisch behandeln; diese Liste und technische Tests erteilen dafür
  keine Einsatzfreigabe. Nur synthetische Daten in den nächsten Live-Lauf geben.
- [ ] Externe Empfänger/Verbindungen benennen: LLM, optional STT/TTS bzw.
  Browser-Spracherkennung, OSM-Kacheln; Docker Hub/Ubuntu/PyPI beim Neubau.
  Edge ist ein veränderlicher externer Dienst, kein lokales Sprachmodell.

## 5. Voraussetzungen für Commit, Lauf und Einfrieren

1. **Manueller Review vor Commit:** Vollständigen beabsichtigten Diff prüfen,
   einschließlich bereits vorhandener uncommittierter Implementierung und aller
   nötigen neuen Dateien. Gegen Exportmanifest zuordnen, Dokumentationsänderungen
   separat benennen. Keine Secrets, `.env`/`.env.local`, Sessions oder Rohlogs
   versehentlich übernehmen. 42 Anforderungen und 13 Fachregeln anhand der
   [Traceability](THESIS_CODE_TRACEABILITY.md) prüfen. Dieser Dokumentationsauftrag
   führt weder `git add` noch Commit/Tag/Push aus.
2. **Versionierung durch verantwortliche Person:** Den reviewed Stand gezielt
   committen und Identität dokumentieren. Der offizielle `live-smoke`-CLI
   verlangt sauberen Git-Arbeitsbaum (`live_smoke_dirty_worktree` andernfalls).
   Kein Umgehen dieser Bedingung oder nachträgliches Zuweisen alter Läufe zum
   neuen Commit.
3. **Vierstufiger vollständiger Live-Lauf:** Erreichbaren Blabladorzugang und
   bewusst gewähltes Messprofil vorab prüfen/festhalten; Schlüssel außerhalb
   Repository/Reports. `live-smoke`, Stufe, `--confirm-live`,
   `LENA_ALLOW_LIVE_SMOKE=true`, erwartete Modell-/Domainidentität und sieben
   exakte Limits je Stufe erforderlich. Während der Reihe nichts nachjustieren.
   Alle technischen Gates und menschlich offenen Kriterien dokumentieren.
4. **Gemeinsam einfrieren:** Nach bewerteten Resultaten Commit, vollständiges
   Dateimanifest, Datenreleases/Quellen-/Kurations-/Übersetzungshashes,
   Runtimefingerprint, tatsächliche Provider-Modellkennung und gesendete Aliase,
   Vertrags-/Prompt-/Validator-/Safety-/Katalog-/Assessmentversionen,
   Konfiguration ohne Secrets, Datum/Uhrzeit/Europe-Berlin, Dockerimage-ID und
   Logs/XML/JSONL als zusammengehöriges Evidenzpaket sichern. Veränderlicher
   Modellalias bedeutet keine Zusage bytegleicher künftiger Antworten.
5. **Anschließend manuell evaluieren:** Festen Szenariokatalog, Bewertungsmaßstab,
   Reviewpersonen, Sprach-/Fachprüfumfang und Umgang mit Fallbacks festlegen.
   Jeden unabhängigen Fall mit frischer Sitzung starten, relative Zeitbezüge
   protokollieren. Die Evaluation am eingefrorenen Stand durchführen; neue
   Codeänderungen schaffen einen neuen Stand. Negative technische Gates dürfen
   Gegenstand einer formativen Untersuchung sein, müssen dabei sichtbar bleiben.

## 6. Thesis und Releaseabschluss

- [ ] [THESIS_UPDATE_NOTES.md, Abschnitt H](THESIS_UPDATE_NOTES.md#h-notwendige-thesis-anpassungen-für-den-reviewstand-vom-26102026)
  in die tatsächliche Thesis übernehmen: technisch belegte Aussagen,
  ausstehende manuelle Evaluation und Systemgrenzen getrennt. Platzhalter erst
  mit echten Ergebnissen ersetzen oder Durchführung ausdrücklich verneinen.
- [ ] Alte Messungen standgebunden erhalten. Neuen vollständigen Lauf samt
  negativen Resultaten und offenen Kriterien getrennt aufnehmen; die Zehn-Fälle-
  Stichprobe bleibt Diagnose, kein Ersatz für menschliche Evaluation.
- [ ] Lokale Belegpfade vor Abgabe in ein zugängliches, geprüftes Archiv mit
  Manifest/Zuordnung überführen. Rohantworten/Belege vor öffentlicher Weitergabe
  auf Inhalte, Secrets und Datenrechte prüfen. Eine lokale Datei ist keine DOI.
- [ ] Erst nach diesem Review Umfang und Vertretbarkeit einer Forschungs-
  veröffentlichung entscheiden. Keine Produktions-, allgemeine Fakten-,
  fachliche Wirksamkeits- oder uneingeschränkte Abgabefreigabe aus Tests ableiten.

Reviewperson: __________  Datum: __________  beabsichtigter Commit: __________

Entscheidung / akzeptierte Grenzen / offene Punkte: _________________________

## Nächster Abschluss für die manuelle Erhebung

- [x] Geprüften Code versionieren: Commit 2462e7d; Arbeitsbaum während Messung sauber.
- [x] Alle vier offiziellen Stufen genau einmal mit unveränderten Limits durchführen;
  Gates/Fehler/ungeprüfte Kriterien erhalten. Negative Gates bleiben sichtbar.
- [x] Einzelergebnisse technisch sichten und als Codex-Analyse dokumentieren;
  dies ist kein menschliches Sprach-/Fachreview.
- [ ] Menschliche Entscheidung zur formativen Evaluation mit L-01-Scopegrenze,
  erholten Formulatorfehlern, Relevanz-/Kontakt-/Ausschlussgrenzen dokumentieren.
- [ ] Zielrechner-Browsercheck durchführen, manuelle Fälle/Kriterien/Reviewer
  festlegen, Daten/Profil/Evidenz gemeinsam einfrieren und dann erheben.
- [ ] Thesis mit neuer Messung und anschließend tatsächlich erhobenen manuellen
  Ergebnissen finalisieren; Rechte/Logginggrenzen unverändert berücksichtigen.

Dieser Auftrag änderte nur Ergebnisdokumentation nach allen Messungen, keine
Anwendung/Tests/Daten/Providerkonfiguration und keine Gates. Kein Commit/Tag/Push.
