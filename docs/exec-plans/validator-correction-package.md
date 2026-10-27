# Exec-Plan: gezielte Validator-Korrekturen nach Blindbewertung

## Status

Technisch abgeschlossen, Codex, 27.10.2026. Basis `5f9ddd8`, Arbeitsbaum beim Start sauber.
Skills: review-first-coding und code-documentation. Kein Commit/Tag/Push.

## Ziel und Abnahmevertrag

Mehr belegte Antworten freigeben, ohne Schutzprüfungen pauschal abzuschalten.
Die 30 als R bewerteten und verworfenen Ersttexte werden unverändert offline
erneut geprüft. 25 aufgeklärte Heuristik-/Formatfälle sind Verbesserungsziele,
keine garantierte Freigabequote: hinter der ersten Diagnose können weitere
Fehler stehen. Fünf tatsächliche Vertragsabweichungen (zwei E-Mail-Zeichen,
Eigenname, Fakt-ID, Primärreihenfolge) bleiben abgelehnt. Menschliche Urteile
werden nicht umkodiert. Ungeprüfte offene Leistungsprosa bleibt eine Grenze;
keine Garantie, dass alle wirklichen Falschaussagen erkannt werden.

- [x] Telefon-/Betragsdarstellung normalisieren, Werte und Angebotsbindung erhalten.
- [x] Ortsnamen von Sprache unterscheiden, echte Sprachmischung weiterhin ablehnen.
- [x] NOT_CHECKED-Zeitgate durch beleggebundene Zeit-/Tages-/Ortsprüfung ersetzen.
- [x] Kontaktzahlen nicht als Alter lesen; vollständige Altersintervalle prüfen.
- [x] Belegte Zielgruppen-/Barrierefreiheitsqualifier von Leistungsnegation trennen.
- [x] Gleichwertige Policyablehnungen/Ungewissheit und belegte Kooperationsorte erkennen.
- [x] Gegenbeispiele, bestehende Negativtests, vollständige Python-/JS-Suite bestehen.
- [x] Versionen/Belege/Thesisnotizen fortschreiben; Containerbuild/Runtime prüfen.

## Umfang und Grenzen

Nur Validator, unmittelbar widersprüchliche Promptanweisung, gezielte Tests und
Dokumentation. Kein Safety-/Akutpfad, keine Auswahl-/Kurations-/Queldatenänderung,
keine Thesisänderung, keine neue Konfiguration/Abhängigkeit. Keine neue Live-
oder vollständige Vierstufen-Evaluation; nur Replay gespeicherter synthetischer
Antworten. Frühere Messungen bleiben unverändert standgebunden.

## Repositoryreview und Datenfluss

Produktiver Vertrag 7: Provider parst GroundedFormulatorResponse; grounding.py
löst Referenzen gegen ausgewählte Evidence auf und prüft atomar, sonst Retry/
Template. Validator 8, Prompt 26, Evidence 5, Copy 10. Alle 30 Erstdiagnosen am
identischen App-Hash offline reproduziert; Befunde außerhalb des Repositorys
unter `%LOCALAPPDATA%/LENA/verification/2026-10-27-validator-ablation/`.
Kein AGENTS.md im Repository/Projektstamm vorhanden.

Wiederverwenden: normalize_name_typography, Decimal aus Standardbibliothek,
schedule_matches/stated_weekdays, typisierte Facts/Policies, vorhandene
Groundingtest-Fixtures und Paket-/Runtimeprüfungen. Keine zweite KB und kein
LLM-Judge. Bestehende Module über 400 Zeilen nur gezielt ändern; kohäsive
Wert-/Sprach-/Zeithelfer bei Bedarf extrahieren, keine parallelen Validatoren.

## Sackgassen und Gegenmaßnahmen

| Risiko | Beleg | Entscheidung und Prüfung |
|---|---|---|
| Alle 30 R pauschal freigeben | fünf echte Vertragsabweichungen | unveränderte Replayfälle getrennt ausweisen; keine ID-/E-Mail-Reparatur |
| Nur erste Diagnose beheben | atomarer Abbruch | alle 134 bewerteten Texte plus 30er-Gruppe offline durch realen Validator |
| Wörter ersetzen statt Zeitbindung | NOT_CHECKED-Zeitgate trotz belegter Zeiten | echte Fenster/Reihenfolge/Ort binden; manipulierte Tage/Zeiten bleiben negativ |
| Telefonlabels entfernen und Betriebsbedingung verlieren | Hilfebuslabel deutsch im PHONE-Wert | Nummer getrennt prüfen, Einsatzzeitbedingung weiterhin mehrsprachig verlangen |
| Sprache nur anhand Umlauten feststellen | vier belegte Straßen; akzeptierter DE-Satz in EN-Retry | belegte Ortsliterale maskieren, zusätzliche eng begrenzte Fremdsprachenmuster |
| Unbekannt als Freifahrtschein | bestehende Unknown-Bypass-Negativtests | nur eng gebundene reine Statusunsicherheit zulassen, positive Echtzeitzusage ablehnen |
| Quellen/Messungen überschreiben | neue fachliche Bewertung | neue Prüfarbelege, Originale mit Hash schützen |
| Docker-Snapshotserver weiter gestört | drei HTTP-502/503-Fehler zuvor | erneut sauber bauen; externen Blocker ehrlich ausweisen, keine Pinänderung |

Abgelehnt: Validator abschalten, allgemeine semantische Wahrheitsgarantie,
automatische Umwertung der Nutzerbewertungen, Testlöschung, Retry auf Grün,
unbelegte Namens-/Adress-/Fakt-ID-Korrektur, Änderungen an FR-01–FR-13.

## Dateiauswirkung

| Datei | Änderung / Zweck |
|---|---|
| app/grounding.py | Validatorversion, Aufruf präziser Wert-/Sprach-/Zeit-/Ortprüfungen |
| app/grounding_constraints.py, app/grounding_claims.py | Geld, Alter, Qualifier, Ungewissheit; bestehende Schnittstellen erhalten |
| ggf. app/grounding_values.py / Sprach-/Zeithelfer | kohäsive Standardbibliotheksfunktionen ohne Importzyklen |
| app/formulation.py | aktuelle Promptanweisung zu Telefonlabels anpassen, Promptversion erhöhen |
| tests/test_grounding_corrections*.py | Paare gültiger Varianten und echter Manipulationen |
| bestehende betroffene Tests | nur bewusst geänderte Telefonformat-/Versionsverträge begründet anpassen |
| IMPLEMENTATION_REPORT, THESIS_UPDATE_NOTES, Traceability, README, docs | tatsächlicher Prüfumfang, neue Versionen, Replay statt neuer Livemessung |

## Meilensteine und Validierung

- [x] Review und persistenter Plan vor Codeänderung.
- [x] 1: Werte/Telefon/Betrag und gezielte positive/negative Tests.
- [x] 2: Sprache/Policy/Ort, Alter/Negation/Ungewissheit, relationale Zeitprüfung.
- [x] 3: 30er- und 134er-Replay mit Originalhashschutz; gezielte Groundingtests.
- [x] 4: volle Python-Suite, `node --test tests/frontend.test.cjs`, Paket-/Docker-/Runtimeprüfung.
- [x] 5: Selbstreview, code-documentation, Ergebnis/Abgabegrenzen dokumentieren.

Belege separat unter `%LOCALAPPDATA%/LENA/verification/2026-10-27-validator-corrections/`.
Neue enge Gegenbeispiele für falsche Ziffern, E-Mail/Name/ID, Preis-/Zeit-/
Leistungsvertauschung, Altersausweitung, echte Negation, Echtzeit-/Aufnahme-
Zusage, Fremdsprachenprosa und unbelegte Kooperationsorte. Bestehende
Negativtests bleiben erhalten. Kein Browser-/Sprachreview als automatisiert
erledigt ausgeben. Abgabereife erst anhand tatsächlicher Nachweise einordnen.

## Rücknahme und Fortschritt

Nur eigene Änderungen dieses Pakets reversieren; keine Migration, kein neues
Datenformat. Rohbelege und menschliche Bewertungen bleiben unverändert.

- 27.10.: Ausgangsstand/sauberen Baum bestätigt; 30er-Befunde geprüft, Plan angelegt.
- Validator 9/Prompt 27 implementiert; Evidence 5/Copy 10/Kuration unverändert.
  Drei kohäsive Helfer für Werte, Sprach-/Policyoberfläche und Zeitbeziehungen;
  constraints bleibt unter 400 Zeilen, bestehender größerer atomarer Orchestrator
  nur gezielt erweitert. Keine neue Abhängigkeit oder Konfiguration.
- Gezielter letzter Lauf: 209 bestanden (targeted-complete.log). Neue Testdateien
  mit korrekten Varianten und falschen Ziffern/Beträgen/Tagen/Negationen/Zusagen;
  historische Promptprüfung unverändert. Nur absichtliche Telefon-/Betragsformat-
  und Versions-Erwartungen migriert, nicht fachliche Negativtests gelöscht.
- 134er-Replay: 23/30 R-Ersttexte zusätzlich akzeptiert, sieben weiter gesperrt
  (fünf ursprüngliche Vertragsabweichungen plus zwei dahinterliegende E-Mail-
  Zeichenabweichungen). Kein zuvor akzeptierter R-Text neu verworfen; kritischer
  DE-Sprachwechsel im EN-Retry jetzt abgelehnt. Zwei FU bleiben bzw. werden
  akzeptiert: Handlungsorientierung/Explizitheit der Anfrageabgrenzung, keine
  automatische Umwertung zu R. Originaldateien unverändert; kein Liveaufruf.
- Vollständige native Suite und No-Cache-Dockerprüfung gestartet; Snapshotserver
  wieder erreichbar, sauberer Testimage-Neubau bereits erfolgreich.
- Im letzten Replay zunächst ein zusätzlicher R-Fall gesperrt: englische
  Antwort auf deutsche Quell-Wochentage. Quellen-Sprachfallback mit vollständigen
  Wochentagen ergänzt (keine unkontrollierte Deutung fremder Kurzformen), eigene
  positive/negative Regression. Danach erneut vollständige native Suite,
  sauberer No-Cache-Build und netzlose Suite am `source-reviewed/`-Export.
- Endgültig je 1637 Python bestanden + historischer XFAIL, bekannte Warning;
  je 19 JS. Runtime healthy, ohne Schlüssel, read-only/Loopback und Persistenz
  nach Neustart und Containerersatz bestanden. `native.xml`,
  `docker-verification.json`, `runtime-smoke.json`; Bericht 15.5. Source-/Test-
  und installierte Modulhashes gegen Export geprüft; Änderungen danach nur Docs.

## Abschluss

Implementierung, vollständige technische Prüfungen, Dokumentationsabgleich und
Selbstreview abgeschlossen. Menschlich offen: 15 U/Sprachreview, sichtbare
Bedienprüfung und fachliche Hilfebus-Akutentscheidung (bis dahin unverändert).
R-20/R-21 bleiben begrenzte Prüfungen, kein vollständiger Wahrheitsnachweis.
Kein neuer Live-Lauf, kein Commit/Tag/Push, keine Thesis-/Quelldatenänderung.
