# Notwendige Thesis-Anpassungen nach der Audit-Umsetzung

## Aktuelle notwendige Korrektur: Modellprosa wiederhergestellt

**Technisch belegt:** In `Chapters/5Solutionneu.tex` beim Formulator und der
Faktenprüfung (bisher Zeilen 502–503) das aktuelle Protokoll als Evidence 4,
Formulator 7, Prompt 25, Validator 7 ausweisen. Die Beschreibung einer selbst
formulierten LLM-Antwort mit Referenzen trifft wieder zu. Der Prompt verlangt
ein bis drei kurze Sätze in einfacher Sprache und Duzform. Akzeptierter Text
wird nicht durch Renderertexte ersetzt. Belege: `app/formulator_prose.py`,
`app/providers/llm.py`, `app/grounding.py`, `tests/test_formulator_prose.py`.
Nachfolgende Empfehlungen zur produktiven Plan-/Rendererarchitektur sind
historisch und dürfen nicht mehr als Beschreibung des finalen Systems dienen.

**Manuell zu prüfen:** Bedarfspassung, Verständlichkeit, Duzform und Kürze;
zwei erfolgreiche Live-Anfragen sind keine vollständige Evaluation. Ergebnisse
des früheren Planvertrags dürfen nicht als Messung dieses Freitextvertrags
übernommen werden. Code, Daten, Konfiguration und Messstand neu zuordnen.

**Systemgrenzen:** Endliche lexikalische und relationale Grounding-Prüfung,
mögliche falsche Ablehnung korrekter Paraphrasen sowie unerkannte Behauptungen;
kein allgemeiner Beweis von Faktentreue. Historischer strikter XFAIL bleibt offen.
Keine Änderung an der Thesis selbst in diesem Auftrag.

## Rendereränderung nach fb773e9, 26.10.2026

Technisch implementiert: Der geschlossene Formulatorplan bleibt unverändert;
der Server verbindet Fakten mit festen vollständigen Satzvorlagen statt
Feldlabels und Semikolonlisten (`app/answer_sentences.py`, Renderer 1,
`app/answer_plan.py._render_facts`). Äußere Markdown-Marker werden nur für die
Ausgabe normalisiert. Negationen, Zahlen und Pflichtbedingungen bleiben erhalten;
Hinweise werden nicht frei paraphrasiert. Regression einschließlich Screenshot-
Quellwerten und HTTP-Pfad: `tests/test_answer_sentences.py`.
In der Systembeschreibung (insbesondere `Chapters/5Solutionneu.tex`,
Formulator/Renderer, sowie R-04/R-08/R-20/R-21) entsprechend beschreiben.
Noch manuell zu prüfen: Verständlichkeit, Natürlichkeit und fachliche Nützlichkeit
je Sprache. Keine geprüfte Leichte Sprache oder vollständige Lokalisierung freier
Quellprosa behaupten. Vorige Live-Messungen nicht auf den neuen Renderer
übertragen; endgültigen Commit und anschließende Messungen neu zuordnen.

Fortschreibung nach vollständiger Live-Messung am Commit 2462e7d, 26.10.2026. Aktuelle neue Messergebnisse stehen in Abschnitt I, technische Blockerkorrekturen in H; Abschnitte A–G bleiben datierte Änderungshinweise und Messhistorie. Ausgangsstand dieses Dokuments: 24.10.2026, unabhängige Messungen vom 23.10.2026. Bezug: Umsetzung der Audit-Befunde im Repository `code/`
(Ausgangscommit `597e1f0`, Teilversuch `bd2c65f`, Details in
[IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md)). **Die Thesis wurde nicht
geändert.** Fundstellen beziehen sich auf den Arbeitsbaum `../thesis/` vom
22.10.2026; gedruckte Seiten laut Audit-Traceability.

Grundsatz: Alle bisherigen Mess- und Testergebnisse der Thesis sind an Commit
`597e1f0` und das dokumentierte Messprofil gebunden und bleiben als solche
korrekt. Sie dürfen **nicht** stillschweigend auf den neuen Codestand übertragen
werden. Die alten Live-Gates bleiben für ihren damaligen Stand gültig. Nach der Umsetzung wurden am 23.10.2026 **alle vier Stufen erneut ausgeführt**: nur die Interpreter-Gates bestanden, die übrigen nicht (Abschnitt E). Beschreibt die Thesis
den finalen Softwarestand, müssen die folgenden Stellen angepasst oder als
Stand `597e1f0` ausgewiesen werden.

## A. Historische inhaltliche Korrekturen für den Stand vom 23.10.2026

| # | Fundstelle | Bisherige Aussage | Korrekte Aussage (Vorschlag) | Code-/Testbeleg |
|---|---|---|---|---|
| 1 | `Chapters/AppendixLenaDesign.tex:113`, R-21, gedr. S. 149 | „Keine erfundenen Fakten … must / implementiert“ | Status „must / begrenzt implementiert“: endliche regelbasierte Prüfung. Das zusätzliche Inhaltswort-Gate läuft unabhängig vom Claimtyp **nur für erkannte Satzformen**; andere unbelegte Leistungsaussagen werden weiterhin als `action`/`fact` akzeptiert. Keine allgemeine semantische Garantie. | `app/grounding_content.py:189–195,251–252`; `app/grounding.py:494–505,565–571`; Nachprüfung N-01, `independent-grounding-probe.json` |
| 2 | `Chapters/5Solutionneu.tex:508` | „Ohne erkanntes Konzept bleibt die Aussage als `not_checked` außerhalb dieser Konzeptprüfung“ | Ergänzen: Validator 4 prüft bei erkannten Leistungs-/Identitätsformen offene Inhaltswörter gegen Fakten desselben Angebots und eigens geprüften Wortschatz; sonst `content_not_covered`. Diese Mustererkennung ist unabhängig vom deklarierten Claimtyp, aber nicht vollständig. Für andere Formen kann `not_checked` weiter zur Annahme als `action`/`fact` führen, während `service` abgelehnt wird. | `app/grounding_content.py:asserts_provision`, `unsupported_content_words`; `GROUNDING_VALIDATOR_VERSION = "4"`; N-01 |
| 3 | `Chapters/5Solutionneu.tex:504–508` (Grounding) und Diskussion `Chapters/7Discussion.tex` (Grenzen) | – | Der ursprüngliche synthetische Satz „Scharni bietet eine Fahrradreparatur an.“ und „nimmt dich heute garantiert auf“ werden nun abgelehnt. Aber „Scharni repariert Fahrräder.“ / „Bei Scharni ist Fahrradreparatur möglich.“ werden als `action`/`fact` weiterhin akzeptiert. Keine im Live-Lauf beobachteten Halluzinationen, sondern eingespeiste Gegenbeispiele. Umgekehrt verwirft der echte Live-Fall `f_en_grounded` das belegte Zeitwort `weekends`. Die geprüften PL-/RO-Evidence-Pakete enthalten lokalisierte Leistungstexte; Rückfälle nicht pauschal mit deutschen Fakten erklären. Keine kausal gemessene Veränderung der Rückfallquote. | `tests/test_grounding_content.py`; `app/grounding_claims.py` `ADMISSION_REGEXES`, `GUARANTEE_STEMS`; `independent-grounding-probe.json`, `stage2-rejection-diagnosis.json`, `english-scharni-evidence.json` (Nachweisverzeichnis, Abschnitt E) |
| 4 | `Chapters/AppendixLenaDesign.tex:112`, R-20 | „implementiert“ | Präzisieren wie R-21; Schichtentrennung jetzt als Test gesichert. | `tests/test_architecture_boundaries.py` |
| 5 | `Chapters/AppendixLenaDesign.tex:104`, R-12 Sprachausgabe | „prototypisch implementiert … Konfigurationspfade technisch geprüft“ | Ergänzen: Standard ist `SPEECH_SYNTHESIS_PROVIDER=disabled`; Edge-TTS oder ein kompatibler Endpunkt wird ausdrücklich gewählt. Der früher aus dem Blablador-Zugang geerbte Default (`gpt-4o-mini-tts`) lieferte im Audit HTTP 404 und wurde entfernt. Kein Hörtest. | `app/config.py` (`SYNTHESIS_PROVIDERS`, keine Vererbung); `tests/test_configuration_profiles.py::test_llm_access_does_not_silently_enable_speech_services`, `::test_missing_tts_model_on_endpoint_is_a_controlled_503_not_a_crash` |
| 6 | `Chapters/5Solutionneu.tex:450` | „Sprachausgabe … über Edge-TTS beziehungsweise alternativ über eine kompatible Provider-Schnittstelle“ | „… optional über ausdrücklich gewähltes Edge-TTS oder einen kompatiblen Endpunkt; ohne Wahl deaktiviert.“ | wie 5 |
| 7 | `Chapters/5Solutionneu.tex:212` (Abbildung) und Datenflussmatrix `:795–800` | STT/TTS als externe Dienste | Unverändert korrekt; ergänzen, dass Server-STT nur über `SPEECH_TRANSCRIPTION_PROVIDER` (`blablador` ausdrücklich oder `openai`) aktiv ist und Kartenkacheln mit `MAP_PROVIDER=disabled` abschaltbar sind. | `app/config.py`, `app/main.py` `/api/client-config`, `app/static/app.js` `applyClientConfig`; `tests/frontend.test.cjs` |
| 8 | `Chapters/5Solutionneu.tex:773` | „Interaktionsprotokollierung ist im kanonischen Konfigurationsstand standardmäßig aktiviert“ | „… ist standardmäßig deaktiviert (nativ, Docker und `.env.example` einheitlich) und wird für Evaluationen ausdrücklich mit `INTERACTION_LOGGING_ENABLED=true` eingeschaltet; keine automatische Löschfrist.“ | `app/config.py` (Default `False`); `tests/test_configuration_profiles.py::test_native_defaults_match_the_safe_container_profile` |
| 9 | `Chapters/5Solutionneu.tex:767`, Dialogannahme „genau einmal beansprucht“ | uneingeschränkt | „… genau einmal, sofern die Reservierung gespeichert werden konnte; scheitert das Schreiben, wird die Anfrage mit HTTP 503 `session_persistence_unavailable` abgelehnt und der Dialog bleibt beantwortbar. Ein neu angebotener Dialog wird nur nach erfolgreicher Speicherung angezeigt.“ | `app/sessions.py` `claim_dialog`, `set_dialog`; `tests/test_session_persistence.py::test_failed_dialog_reservation_is_reported_and_leaves_dialog_answerable`, `::test_api_refuses_an_unpersistable_clarification_with_a_controlled_503` |
| 10 | `Chapters/5Solutionneu.tex:769–770` (TTL, Reset) | TTL bei Zugriff | Ergänzen: beschädigte Sessiondateien werden in Quarantäne verschoben, höchstens drei bleiben erhalten. | `app/sessions.py` `max_quarantine_files`; `tests/test_session_persistence.py::test_quarantine_files_are_retained_only_up_to_the_limit` |
| 11 | Loggingbeschreibung `Chapters/5Solutionneu.tex:762–807` | technische Ereignisse mit Diagnosefeldern | Ergänzen: Zusätzliche Diagnosefelder werden nach Erlaubnisliste gerendert. Das verhindert nicht jeden Freitexteintrag: App-Logs enthalten Rohpfade, Uvicorn-Accesslogs auch Query-Strings; Grundnachrichten/Exceptions sind nicht entsprechend bereinigt. Synthetische URL-Marker wurden tatsächlich protokolliert. Kein nachgewiesenes Leck normaler Frage-POST-Bodies, aber auch kein allgemeiner Ausschluss von Nutzertexten/Secrets. Korrektur vor Eingaben personenbezogener Daten erforderlich. | `app/main.py:246,254,266`; `app/logging_setup.py:27,86`; `app/__main__.py:56–62`; N-03, `url-logging-probe.txt` |

## B. Ergänzungen zu Betrieb und Reproduktion (bisher fehlend)

| # | Fundstelle | Ergänzung | Beleg |
|---|---|---|---|
| 12 | Kap. 5.2.9 `Chapters/5Solutionneu.tex:709–741` | Das Messprofil (alias-fast, 4096 Tokens, 15/30/30 s, Budget 45 s) ist kein Installationsdefault; die Defaults lauten 2000 Tokens (Vorlage) bzw. 1200 (Code), Selector 10 s. Das Messprofil steht kommentiert in `.env.example`. | `.env.example` Abschnitt 1 |
| 13 | Kap. 5.2.12 `Chapters/5Solutionneu.tex:810–816` | Konfigurationspriorität: Defaults < `.env` < `.env.local` < Prozessumgebung (früher überschrieb `.env.local` die Prozessumgebung); Envdateien nur im Checkout; ungültige Werte und nicht unterstützte Namen (`LENA_LLM_TEMPERATURE`, `LENA_LLM_FALLBACK_PROVIDER`) werden nur namentlich gemeldet. | `app/config.py`; `tests/test_configuration_profiles.py::test_process_environment_overrides_local_files_without_mutating_it`, `::test_invalid_profiles_fall_back_safely_and_are_reported_by_name` |
| 14 | Kap. 5.2.6 API, `Chapters/5Solutionneu.tex:472–486` | `/api/health` enthält `external_services` (Profil, `configured`, fehlende Variablennamen, `availability: not_checked`) und `configuration_warnings`; neuer Endpunkt `/api/client-config`; aktive Prüfung `python -m app.service_check`. Konfiguriertheit ist ausdrücklich keine Verfügbarkeitsprüfung. | `app/external_services.py`, `app/service_check.py`; `tests/test_configuration_profiles.py::test_service_check_separates_configuration_from_model_availability` |
| 15 | Anhang Reproduktion `Chapters/AppendixLenaDesign.tex:14–56` | Dockerfile setzt kein TTS-Profil mehr; persistentes Volume ist dokumentiert (Vorbereitung für UID 10001). Neue Prüfergebnisse vom 23.10.2026 nur als zusätzlichen, an den neuen Commit gebundenen Nachweis aufnehmen. | `Dockerfile`; README „Schnellstart mit Docker“; IMPLEMENTATION_REPORT Abschnitt Docker |
| 16 | Kap. 5.2.3 Architektur `Chapters/5Solutionneu.tex:63–286` | Orchestrierung: LLM-Stufensteuerung liegt in `app/llm_stages.py` (gemeinsamer Formulator-Rückfall für soziale Angebote, Toiletten und Trinkwasser); Safety-Entscheidung und formulatorfreie Fachregelabschlüsse sind eigene Methoden. Fachliches Verhalten unverändert. | `app/llm_stages.py`; `app/service.py` `_apply_safety_decision`, `_resolve_conditional_or_dialog_answer` |
| 17 | Ergänzung zu Kap. 5.2.7 | Historischer Retrievalbaseline (`app/retrieval.py`) ist nur Test-/Forschungsartefakt; die aktive Normalisierung liegt getrennt in `app/text_normalization.py`. | `app/retrieval.py` Moduldocstring |

## C. Historische Zahlen des Umsetzungsstands vom 23.10.2026

| Fundstelle | Bisher (Commit `597e1f0`) | Neuer Stand (Arbeitsbaum nach Umsetzung) |
|---|---|---|
| `Chapters/6Resultsneu.tex:26,75`; `AppendixLenaDesign.tex:54,447`; `FrontBackmatter/Summary.tex:23` | 41 Module, 1.220 Fälle, 1.219 bestanden, 1 xfail; 17 JS-Tests | 45 Module, 1.344 Fälle, 1.343 bestanden, 1 xfail (unverändert „minor injuries“); 19 JS-Tests. Siehe IMPLEMENTATION_REPORT für Containerlauf. |
| Grounding-Validatorversion (Live-Manifeste) | 3 | 4 |

Die vier Live-Läufe vom 22.10.2026 wurden mit Validator 3 erzeugt. Ihre Ergebnisse dürfen nicht als Messung des Validators 4 ausgegeben werden. Die vier neuen Läufe vom 23.10.2026 messen Validator 4 (Abschnitt E). Ein kausaler Vorher-/Nachhervergleich auf identischen Modellantworten wurde nicht durchgeführt; daraus ist keine quantitative Erhöhung der Rückfallquote allein durch den Validator ableitbar.

## D. Unverändert offene Thesis-Punkte (nicht durch Code lösbar)

- Manuelle qualitative Bewertung und sichtbare Platzhalter (`FrontBackmatter/Summary.tex:25`, `Chapters/6Resultsneu.tex:235–243`, `Chapters/7Discussion.tex:49–54`): weiterhin erheben oder ausdrücklich als nicht durchgeführt deklarieren; keine Ergebnisse aus automatischen Tests ableiten.
- Lizenz-/Weitergabestatus Trinkbrunnen und WFS-Endpunkt (`Chapters/4Approachneu.tex:291–294`): im Repository nicht geändert; Widerspruch zu `THIRD_PARTY_NOTICES.md:15–17` und `app/static/index.html:148–150` bleibt bis zur Rechteklärung bestehen.
- Versionierung des Thesis-Evidenzstands (`Evaluation/technische-evaluation-2026-10-22/`).

## E. Unabhängige Nachprüfung: neue Ergebnisse und Zuordnung zum Abgabestand

Die folgenden Ergänzungen betreffen den unveränderlichen externen Prüfsnapshot `70ed1dfd32230726cd111669bd761f27b705bc08`, Manifest-SHA256 `458e647c843c401af648999385970961854afafc10e1751f6faa4c1e874a54ba`. Der kanonische HEAD `bd2c65f` enthält diese uncommittierten Verbesserungen **nicht vollständig**. Thesis-HEAD bei Prüfung: `a99d743`; keine Thesis-Datei wurde geändert.

Dauerhafte Rohbelege: `C:/Users/User/AppData/Local/LENA/verification/2026-10-23-70ed1dfd/`. Dort liegen die vier vollständigen Live-Reportverzeichnisse, `verification-summary.json`, Quellmanifest und verifiziertes Git-Bundle sowie die unten genannten Gegenproben. Details und vollständige Lauf-IDs: [IMPLEMENTATION_REPORT.md, Abschnitt 8](IMPLEMENTATION_REPORT.md#8-unabhängige-nachprüfung-und-live-e2e-am-23102026).

| Thesis-Stelle | Notwendige korrekte Aussage | Beleg |
|---|---|---|
| `Chapters/6Resultsneu.tex:173–233`, Kap. 5.3.7 | Neue Messreihe vom 23.10. getrennt von 22.10. berichten: Interpreter 15 Anfragen/15 Provideraufrufe, 0 technische Fehlerfälle, beide Gates bestanden. Selector/Formulator 16/24, 8 Fehlerfälle; E2E 34/58, 10 Fehlerfälle; Stabilität 18/47, 13 Fehlerfälle. Die letzten drei Stufen bestehen beide Gates nicht. `completed` bedeutet erhoben, nicht bestanden. Technische Fehlerfälle schließen erholte Retrys ein und sind keine Halluzinationsquote. | vier `summary.json` und `stage-results.jsonl`; Bericht 8.3 |
| `Chapters/6Resultsneu.tex:201–233`; `Chapters/7Discussion.tex:7–113` | E2E: zwei Szenarien mit Inhaltsabweichung, keine katalogseitig kritische; Stabilität: eine Inhaltsabweichung, zugleich kritisch. Unsichere Akutgefahr, Wiederholung 2: Interpreter-Timeout → technischer Hilfebuspfad mit bedingtem 112-Hinweis statt Sicherheitsrückfrage. Fachlich zu entscheidender Ausfallvertrag, keine rückwirkende Umwertung des gemessenen Gates. | `e_acute_uncertain` im Stabilitätslauf; N-04 |
| `Chapters/6Resultsneu.tex:224–233` | Antwortart bei 4/6 dreifach geprüften Szenarien stabil; unklare Akutgefahr und Prompt-Injection instabil. E2E 54, Stabilität 51 noch ungeprüfte Einzelkriterien; menschliches Sprachreview ausstehend. | Stabilitäts-/E2E-Summary, `content_evaluation_complete=false` |
| `Chapters/AppendixLenaDesign.tex:14–70`; `Chapters/6Resultsneu.tex:69–89` | Unabhängig bestätigt: nativ und netzlos im frisch gebauten Testcontainer je 1343 Python-Tests bestanden, 1 bekannter XFAIL; je 19 JS-Tests. Neubau, Start ohne Secrets, Volume-Neustart/-Ersatz und Portbindung geprüft. Linux/AMD64-Docker und nativer Windows-Testlauf; keine allgemeine Plattform-/Mindesthardwaregarantie. | `native-pytest.xml`, `native-javascript.log`, `container-tests.log`, Buildlogs, `runtime-smoke.json`; Bericht 8.2 |
| `Chapters/5Solutionneu.tex:450,795–800`; R-10/R-12 | Live-HTTP-TTS erzeugt 147888 Bytes MPEG; serverseitige STT transkribiert dieses synthetisch erzeugte Audio. Fremder TTS-Text → 409, unkonfiguriertes TTS → 503. Kein Mikrofon-/Hör-/menschlicher Qualitätsnachweis. | `http-live-smoke.json`, `synthetic-toilet-answer.mp3` |
| `Chapters/5Solutionneu.tex:423–470`; R-05/R-07/R-08/R-09 | Sichtbare Browserbedienung, echte Mikrofonaufnahme und Kartenkacheln nicht unabhängig geprüft: Computer-Use-Kontrolle stoppte wegen nicht sicher bestimmbarer Browser-URL. Frontendtests/HTTP-Smokes ersetzen diesen Nachweis nicht. | Bericht 8.5; dokumentierte Werkzeuggrenze |
| `Chapters/AppendixLenaDesign.tex:54–70`; Summary/Ergebnisplatzhalter | Erst kanonischen Commit samt nötigen neuen Dateien sichern, Messsnapshot eindeutig zuordnen und den vorgesehenen Evaluationsstand festlegen. Spätere reine Dokumentations-/Loggingänderungen separat benennen; fachliche Äquivalenz muss begründet werden. Neue fachliche Änderungen benötigen neue relevante Messungen. Die alten Messungen bleiben für ihren jeweiligen Stand gültig. | Quellmanifest, Git-Bundle; Bericht 8.1 und 8.6 |

Eine formative manuelle Untersuchung mit synthetischen Fällen ist auch bei negativen Gates sinnvoll. Sie darf deren Ergebnisse nicht als bestanden voraussetzen und ersetzt keine personenbezogene Einsatzfreigabe. Ob die Thesis diese Grenzen wissenschaftlich angemessen behandelt, entscheidet sich an ihrer tatsächlichen Überarbeitung und der transparenten Ergebnisdarstellung; eine technische Prüfung erteilt keine akademische Abgabefreigabe.

## F. Diagnostischer Promptvergleich vom 24.10.2026

Ausgangspunkt nun kanonischer Commit `15a912f` („Grounding“). Der Nutzer hat den
zuvor uncommittierten Stand gesichert. Der Vergleich selbst ergänzt nur
Evaluationswerkzeuge und Dokumentation; produktiv weiterhin Prompt 22,
Formulatorvertrag 5, Groundingvalidator 4. Keine Thesisänderung.

| Thesis-Stelle | Korrekte Ergänzung bei Aufnahme des neuen Vergleichs | Beleg |
|---|---|---|
| `Chapters/5Solutionneu.tex:488–508`; R-20/R-21 | Einen experimentellen Kandidatenprompt von der produktiven Konfiguration unterscheiden. Der Kandidat wurde nicht übernommen; der Vergleich beweist weder allgemeine Faktentreue noch die Entbehrlichkeit der Prüfung. | `app/prompt_comparison.py`, `app/prompt_comparison_cases.py`; `docs/formulator-prompt-comparison.md` |
| `Chapters/6Resultsneu.tex:173–233` | Gesonderte Moduldiagnose: 130 ursprüngliche Aufrufe auf 60 fünfsprachigen Paketen inklusive Wiederholungen, zusätzlich 30 separat registrierte Ergänzungsaufrufe nach Providerfehlern. Keine neue reguläre Vier-Stufen-E2E und keine manuelle Fachbewertung. | eingefrorenes Manifest, originale JSONL-Dateien, `supplement-plan.json`, getrennte Summaries |
| `Chapters/7Discussion.tex:7–113` | In der ursprünglichen Reihe wurden 13/65 bisherige bzw. 22/65 Kandidatenantworten akzeptiert. Codex bewertet 48 bzw. 50 Entwürfe als belegt und hilfreich; 28 bzw. 22 belegte Entwürfe wurden vom Grounding abgelehnt. Je 15 Providerfehler ohne Entwurf. Die absichtlich schwierigen synthetischen Fälle erlauben keine repräsentative Fehlerquote. | `complete-summary.json`, begründete Einzelurteile; Bericht Abschnitt 9 |
| `Chapters/5Solutionneu.tex:504–508`; Diskussion | Fehlende Preis-/Leistungsinformation wird von den Modellen häufig richtig beschrieben, besitzt aber keine explizite Policybindung im Vertrag; 14 ursprüngliche Schemafehler `non-offer sentence requires policy`. Schema nicht einfach lockern. Zum Studienzeitpunkt waren strukturelle Antwortakte noch nicht implementiert; Umsetzung am 25.10. siehe G. | `app/formulation.py:FormulatedSentence.validate_references`; `schema-diagnosis.json` |
| `Chapters/6Resultsneu.tex:235–243`; manuelle Ergebnisplatzhalter | Einzelbewertungen stammen von Codex; unabhängiges menschliches Sprach-/Fachreview steht weiter aus. Die neuen Zahlen dürfen die geplante manuelle Evaluation nicht ersetzen. | `reviews.json`, `reviews-supplement.json`: `reviewer=codex` |
| Automatisierte Regression, `Chapters/6Resultsneu.tex:69–89` | Nach Ergänzung von 12 Evaluationswerkzeugtests nativ 1355 bestanden und 1 bekannter XFAIL; 19 JS-Tests. Für diese neuen Werkzeuge kein neuer Docker-/Vier-Stufen-Lauf behaupten. | neue JUnit und JS-Lauf; Bericht Abschnitt 9 |

Ausführliche Einschränkungen, Modell-/Prompthashes und Reproduktionsbefehle:
[docs/formulator-prompt-comparison.md](docs/formulator-prompt-comparison.md).
Rohbelege außerhalb Cloudsync:
`C:/Users/User/AppData/Local/LENA/verification/2026-10-24-formulator-prompts/`.

## G. Geschlossener Antwortplan vom 25.10.2026

Die Thesis wurde nicht bearbeitet. Diese Ergänzung ersetzt Gegenwartsaussagen
über den alten freien Formulator; frühere Studien bleiben standgebunden.

| Fundstelle | Korrekte Aussage für den neuen Stand | Code-/Testbeleg |
|---|---|---|
| `Chapters/5Solutionneu.tex:488–508`, Architektur und Grounding | Die bestehende Pipeline bleibt. Der Formulator wählt Fakten und geschlossene Akte, statt sichtbare Sätze frei zu formulieren. Kein zusätzlicher LLM-Prüfer. Vertrag 6, Prompt 23, Evidence 4, Validator 5 | `app/formulation.py`, `app/providers/llm.py.formulate_answer`, `app/answer_plan.py.FormulatorPlan`; `tests/test_answer_plan.py` |
| Gleicher Abschnitt, Faktenprüfung | Der Renderer sichert Paket-/Angebots-/Faktenbindung, Pflichtbedingungen und atomare Länge. Keine allgemeine semantische Prüfung beliebiger Modelltexte; diese sind im produktiven Format ausgeschlossen. Historischer Wortvalidator bleibt nur für Forschung | `render_answer_plan`, produktive Ablehnung von Freitext auch mit Version 6; Legacy-Replays über `ComparisonProvider` |
| R-04/R-08/R-20/R-21, Systemgrenzen und Diskussion | Weniger freie, teilweise aufzählende Sprache. Unbekanntheitsakte sind begrenzte Nicht-Zusagen, keine Behauptung vollständiger Datenabwesenheit. Bekannte explizite Felder sperren entsprechende Unbekanntheitsakte. Quellwerte können sprachlich unvollständig lokalisiert sein; lange Bedingungen können Rückfälle auslösen | `app/answer_act_texts.py`, `_unknown`, `_render_facts`; fünfsprachige Positiv-/Negativtests und Längenprüfung |
| `Chapters/6Resultsneu.tex:69–89`, Engineeringtests | Neue Reihe: 1419 passed + 1 historischer XFAIL, JS 19/19, nativ und im neuen netzlosen Container. Der erste Übergangslauf hatte sechs behobene Testprotokollfehler. Historische Worttests und produktive Plantests unterscheiden | `native-pytest.xml`, `container-tests.log`, `tests/test_answer_plan.py`; Bericht 10.2 |
| `Chapters/6Resultsneu.tex:173–233`, Liveevaluation | Neue getrennte Reihe vom 25.10.: 83 Anfragen, 135 Provideraufrufe; Fehlerfälle Interpreter/Selector-Formulator/E2E/Stabilität 0/4/6/8; Inhaltsabweichungen 0/0/1/0. Nur Interpreter-Gates bestanden; CLI exit 0 bedeutet abgeschlossene Erhebung. Keine kausale Verbesserung gegenüber der alten Messung beweisen | Vier neue Manifeste und Summaries, Bericht 10.3 |
| Gleicher Abschnitt, Stabilität | Sechs Antworttypen bei dreifacher Wiederholung stabil. 54/51 Inhaltskriterien ungeprüft, unabhängiges Sprachreview offen. `e_mobile` verfehlt erwartetes Hauptresultat; Schema-/Vertragsrückfälle bleiben | `stage-results.jsonl`, `summary.json` vom 25.10. |
| Packaging/Reproduzierbarkeit und Grenzen | Read-only Docker mit Runtimevolume, Health, Loopback, Sessionerhalt nach Neustart/Containerwechsel, echte Blablador-Textantworten und Edge-Audio geprüft. Frische Volumeinitialisierung verwendet identifizierten packaged Bootstrap; kein aktueller externer Datenrelease behauptet. Browser/Mikrofon/STT/Hör-/Kartenprüfung nicht erneut erfolgt | `runtime-smoke.json`, `controlled-answer.mp3`, Build-/Testlogs; Bericht 10.2 |
| `Chapters/6Resultsneu.tex:235–243` und Diskussion | Manuelle Evaluation und unabhängiges Sprachreview bleiben ausstehend. Der neue Stand darf nicht mit Messungen vom 22.–24.10. als validiert bezeichnet werden. Commit und Evidenzpaket vor endgültiger Evaluation festhalten | Snapshot `e8b5181e5d913d55b4fd36dde9f056c7aadced7c`, Manifest; noch kein kanonischer Commit dieses Auftrags |

Architekturbeschreibung und vollständige Einschränkungen:
[docs/controlled-answer-acts.md](docs/controlled-answer-acts.md).
Die Rechte-/Logging-/Interpretationsgrenzen aus früheren Hinweisen bleiben
offen; der kontrollierte Ausgabeplan hebt sie nicht auf.

## H. Notwendige Thesis-Anpassungen für den Reviewstand vom 26.10.2026

Diese Aussagen ersetzen bei Beschreibung des heutigen Systems die älteren
Gegenwartsformulierungen aus A–G. Historische Ergebnisse bleiben unter ihrer
ursprünglichen Version bestehen. Die Thesis wird in diesem Auftrag nicht
bearbeitet. Fundstellen: bisherige TeX-Abschnitte des Abgleichs; aktuelle
Code-/Testfundstellen stehen vollständig in
[THESIS_CODE_TRACEABILITY.md](THESIS_CODE_TRACEABILITY.md). Messbelege und
Identität: [Bericht 11](IMPLEMENTATION_REPORT.md#11-technisch-geprüfter-stand-für-den-manuellen-release-review-26102026).

### H.1 Technisch belegt: notwendige Beschreibungs- und Ergebniskorrekturen

| Thesis-Fundstelle | Notwendige korrekte Aussage | Code-/Test-/Messbeleg |
|---|---|---|
| `Chapters/5Solutionneu.tex:488–508`; Anhang R-20/R-21 | Pipeline bleibt Interpreter → Fachregeln/Kandidaten → Selector → Formulator → Prüfung/Renderer. LLM wählt geschlossene Akte und Faktreferenzen; der Server erzeugt sichtbaren Text. Kein zusätzlicher LLM-Judge. Interpreter 4/12, Selector 1/3, Evidence 4, Formulator 6/24, Validator 6. Beschreibungen von Claimwort-/Prosa-Grounding ausdrücklich als historischen Stand kennzeichnen | `app/providers/llm.py:356`, `app/grounding.py:576`, `app/answer_plan.py:24,51,64,192`; `tests/test_answer_plan.py:63,121,148,212` |
| Gleicher Abschnitt, Vertrag und Datenflussmatrix `:748–800` | Tatsächliches Pydantic-Schema steht im Prompt; interne Capability-/Typfakten sind nicht als Ausgabefakten auswählbar. Originale Evidence bleibt Referenzautorität; Frage ist Relevanzkontext, keine zusätzliche Faktenquelle | `app/answer_plan.py:64,81`, `app/providers/llm.py:356`; `tests/test_answer_plan.py:121` |
| `Chapters/5Solutionneu.tex:502`; R-04/R-08/R-21 | Ein bis drei Antwortakte, höchstens 600 Zeichen. Zuerst vollständige Validierung, danach ganze Fakten samt Bedingungen in Prioritätsreihenfolge einpassen. Kein Abschneiden; wenn nichts passt Kontaktakt, für Unbekanntheit feste Kurzformen. Karten bleiben erhalten; `length_limited` und tatsächlich ausgegebene Referenzen unterscheiden | `app/answer_plan.py:131,151,170,192`; `tests/test_answer_plan.py:97,163,182,200` |
| Alias-/Dialog-/Fachregeln `Chapters/5Solutionneu.tex:639–703,762–807`; FR-01/04/08/11 | Eng begrenzte vollständige Namenssuche gegen kuratierte Aliase kann nach Safety eine falsche Scopeentscheidung korrigieren. Sie belegt weder persönlichen Zugang noch Leistungsbedarf. Kontakt ist ggf. Verweisung; ausdrückliche Dienste bleiben im offenen Dialog erhalten. Kübel → Stadtteilfrage → Grünau ergibt nur Team 19.2 mit Zuständigkeitsvorbehalt; A1-Kontaktdienst bleibt spezifisch | `app/interpreter.py:334`, `app/candidates.py:66`, `app/dialogue_flow.py:49,162`, `app/service.py`; `tests/test_interpreter.py:755,769,777`, `tests/test_dialogue.py:79,104,344` |
| `Chapters/6Resultsneu.tex:26,69–89`; Summary und Anhang Testzahlen | Neue getrennte Messung: nativ und im netzlosen Container je 1476 bestanden, 1 bekannter strikter XFAIL, 0 Fehler; je JS 19/19. XFAIL `minor injuries` betrifft den historischen Wortvalidator und zählt nicht als bestanden. Bekannte Starlette-TestClient-DeprecationWarning transparent nennen. Keine neue Modulzahl erfinden | `native-pytest.xml`, `native-tests.log`, `docker-final-tests.log`, `native-js-tests.log` im Archiv `2026-10-25-blockers`; `tests/test_formulation.py:1018` |
| Reproduktion `Chapters/AppendixLenaDesign.tex:14–70` | Sauberer No-Cache-Testbuild aus Export; zwei externe Snapshotserverfehler vor Erfolg beim dritten Versuch. Runtime aus derselben frischen Buildkette; read-only, Loopback, Health, Volume, Neustart/Containerersatz und Blablador-HTTP geprüft. Nur Linux/AMD64 nachgewiesen. Exportmanifest statt HEAD allein bezeichnet den uncommittierten Prüfstand; heutige Dokumentänderungen separat zuordnen | Bericht 11.1–11.4; Buildlogs, `runtime-final-results.json`, `final-source-manifest.json`, `final-checks.json` |
| Liveergebnisse `Chapters/6Resultsneu.tex:173–233` | Zehn direkte synthetische Formulatorfälle: neun gültige Pläne, ein korrekt abgelehnter Plan, null Schemafehler. Je ein direkter Versuch, kein vollständiger Stufe-2-/Vierstufenlauf. Kein repräsentativer Erfolgsanteil und kein neues bestandenes Gate. Frühere negative Gates bleiben offen | `verified/results.json`, `verified/calls.json`; [Zehn-Fälle-Stichprobe](docs/live-provider-evaluation.md#zehn-fälle-stichprobe-vom-26102026) |
| TTS-/Betriebsbeschreibung `Chapters/5Solutionneu.tex:450,795–816`; R-10/R-12 | Explizite optionale TTS-Profile; Client 7.3.1 in den Constraints/Lock. Erfolgreicher Edge-Audiotransport stammt aus früherer Prüfung, kein neuer Hör- oder Akustiknachweis am 26.10. Ohne LLM nur technischer Hilfepfad, keine lokale Modellabhängigkeit | `app/config.py`, `app/speech.py`, `requirements/runtime-py312.lock`; Bericht 10.2 und 11.4; README und `.env.example` |

### H.2 Noch durch manuelle Evaluation zu prüfen

| Thesis-Fundstelle | Offener Nachweis / zulässige Formulierung | Beleg für offenen Status |
|---|---|---|
| `FrontBackmatter/Summary.tex:25`, `Chapters/6Resultsneu.tex:235–243`, `Chapters/7Discussion.tex:49–54` | Ergebnisplatzhalter erst nach tatsächlicher manueller Erhebung ersetzen; bis dahin „noch nicht durchgeführt“. Keine Nutzerwirksamkeit oder Facheignung aus Unit-Tests ableiten | Keine manuellen Ergebnisse in Übergabe; technische Suite und Stichprobe haben ausdrücklich begrenzten Zweck |
| R-04/R-05/R-07/R-08/R-09/R-12; UI-/Sprachbeschreibung `Chapters/5Solutionneu.tex:423–470` | Verständlichkeit, Natürlichkeit, angemessene Kürze und fachliche Brauchbarkeit einschließlich informationsarmer Kontakt- und allgemeiner Ausschlussantworten prüfen. Sichtbare Browserbedienung, Mikrofon/Hören, Karten und Assistenztechnik separat dokumentieren | `app/answer_act_texts.py`; `tests/frontend.test.cjs` verwendet Doubles, kein echter Browser; Bericht 11.4 |
| `Chapters/6Resultsneu.tex:173–233`; Auswahl-/Safety-/Stabilitätsaussagen | Vollständigen Vierstufenlauf nach Review/Versionierung erneut erheben; menschlich offene Kriterien und kritische Ausfälle bewerten. Frühere negative Gates dürfen weder gelöscht noch aufgrund der Stichprobe auf „bestanden“ gesetzt werden | Bericht 10.3/11.5; letzte vollständige Reihe nur Interpreter positiv, keine erneute volle Reihe nach Korrektur |
| Datenbeschreibung Kap. 4.4 und R-42 | Aktualität, Zuständigkeit, Zugangsvoraussetzungen und operative Daten fachkundig bestätigen; alle fünf Sprachen einschließlich neuer Kurzakte menschlich bewerten | Kurations-/Übersetzungsstatus: `app/resources/bootstrap/curation/social_offers.json`, `app/resources/bootstrap/i18n/`; Fingerprint ist Integrität, keine Sachprüfung |

### H.3 Bekannte Systemgrenzen, die in der Thesis bleiben müssen

| Thesis-Fundstelle | Notwendige Grenze | Code-/Test-/Nachweisbeleg |
|---|---|---|
| R-18/R-20/R-21/R-22/FR-11; Diskussion `Chapters/7Discussion.tex:7–113` | Pakettreue ist keine allgemeine Wahrheitsgarantie. Fehlerhafte LLM-Interpretation/Auswahl und falsche/veraltete Quellen bleiben möglich; statische Daten belegen keine freie Kapazität. Ungültige Pläne werden weiter verworfen | `app/answer_plan.py:192`, `app/interpreter.py:232`; RU-Injection in `verified/results.json` |
| R-04/R-08; Diskussion | Sichere Längenbehandlung kann nur Kontaktauftrag übrig lassen. Fehlende typisierte Felder beweisen keine globale Datenabwesenheit. Die allgemeine Kein-Treffer-Antwort erklärt konkrete Ausschlüsse noch unzureichend | `_fit_facts`, `_fit_answer`, `_unknown`; `runtime-final-results.json` (Scharni); `time-diagnostic/alias-replay.json` |
| Logging/Sitzungen `Chapters/5Solutionneu.tex:762–807`; R-37 | Interaktionslog standardmäßig aus, Sessions enthalten trotzdem nicht-akute Texte. Diagnose-Erlaubnisliste verhindert keine sensiblen Roh-URL-/Query-/Exceptioninhalte; kein allgemeiner Ausschluss personenbezogener Daten oder Secrets. Einzelprozess, TTL bei Zugriff, keine automatische Interaktionslog-Löschfrist | `app/logging_setup.py:25,86`, `app/main.py:244`, `app/__main__.py:45`, `app/sessions.py`, N-03 |
| Datenrechte `Chapters/4Approachneu.tex:291–294`; Reproduktion/Veröffentlichung | Trinkbrunnen-Weitergaberecht und konkrete WFS-Lizenzzuordnung ungeklärt; widersprüchliche Notices/UI-Attribution sind keine Rechteklärung. Paket-Bootstrap ist eingefrorener Quellenstand, kein aktueller externer Release | `THIRD_PARTY_NOTICES.md`, `app/static/index.html`, Trinkbrunnenmanifest; Bericht 11.5 |
| Reproduktion/Validität und R-38/R-41 | Normale Suche braucht externes LLM; Sprache/Kacheln weitere optionale Dienste. Modellaliase/Edge und Buildserver können sich ändern. Keine zugesicherte Providerinteroperabilität, Mindesthardware, Remote-CI- oder Plattformbreite | README, `.env.example`, Dockerfile; zwei Snapshotserverausfälle; Bericht 11.3/11.5 |

Vor Übernahme neuer Zahlen den geprüften Code-/Daten-/Modellstand und die
historische Evidenz eindeutig zuordnen. Nach Review versionieren, vollständige
Live-Gates getrennt messen, Code/Daten/Modellkonfiguration/Evidenz einfrieren
und anschließend manuell evaluieren. Noch keine uneingeschränkte akademische
Abgabe- oder Veröffentlichungsempfehlung; siehe
[RELEASE_REVIEW_CHECKLIST.md](RELEASE_REVIEW_CHECKLIST.md).

## I. Neue vollständige Live-Messung am Commit 2462e7d, 26.10.2026

Die in H noch ausstehende Vierstufenmessung wurde jetzt genau einmal am
sauberen Commit ausgeführt. H bleibt der technische Vorabstand; manuelle
Evaluation und menschliches Sprach-/Fachreview sind weiterhin nicht durchgeführt.

| Thesis-Fundstelle | Notwendige korrekte Ergänzung | Beleg |
|---|---|---|
| `Chapters/6Resultsneu.tex:173–233`, technische Liveevaluation | Neue getrennte Reihe: 83 Anfragen/122 Provideraufrufe. Interpreter 15/15, 0 technische Fehler, 1 Scopeabweichung: Vertragsgate ja/Inhaltsgate nein. Selector/Formulator 16/18, 0 terminale Fehler: beide Gates ja. E2E 34/52, 2 erholte Fehler: beide Gates nein. Stabilität 18/37, 1 erholter Fehler: beide Gates nein. Null katalogseitig kritische Fehler in dieser Reihe | Vier neue `manifest.json`/`summary.json` unter `2026-10-26-final-live/runtime/live-evaluations/`; Bericht 12 |
| Gleicher Abschnitt und Diskussion | Stufe 2 enthält zwei erfolgreiche Formulatorretrys (12 Aufrufe für 10 Fälle), zählt aber nur terminale Fehler. E2E/Stabilität zählen auch erholte Fehler. Keine einheitliche Halluzinations-/Erstversuchsfehlerquote aus den Zählern bilden | `_run_formulator_scenario`, `_run_e2e_scenario` in `app/live_evaluation_runner.py`; stdout/stderr und JSONL |
| Interpretation/Safety, R-18/R-34 | `i_pl_acute`: Risiko detected, Scope out_of_scope statt in_scope. Nicht-kritische Katalogabweichung; Safety wird in der Anwendung vor Scope verarbeitet. Kein gemessener unterlassener Stopp auf genau diesen Satz | Interpreter-JSONL; `app/service.py` `_apply_safety_decision`/`_query_core` |
| E2E-/Groundinggrenzen | Toilettenschemafehler und zwei Wasser-Primärreihenfolgefehler werden je durch regulären Retry erholt. Fremde Wasserfakten hier nicht nachgewiesen; erster Wasserakt ließ Primärangebot 22 aus. Schemafehlerfeld Toilette mangels gespeichertem Erstplan nicht rekonstruierbar | E2E `e_toilet`, `e_water`; Stabilität `e_water` Wiederholung 2; `formulator_rejections`; `app/answer_plan.py:230–232` |
| Stabilität, `Chapters/6Resultsneu.tex:224–233` | Sechs Antworttypen innerhalb der dreifachen Reihe stabil; Details/Wortlaut variieren. Injection wird zwischen E2E und Stabilität unterschiedlich, jeweils erlaubt, geroutet. Keine globale Deterministik. 54/51 Inhaltskriterien ungeprüft | Stabilitäts-Summary/JSONL, E2E-JSONL; `content_evaluation_complete=false` |
| Anhang Reproduktion/Messidentität | Commit 2462e7d, sauberer Arbeitsbaum bei jeder Stufe, source-manifest SHA256 2259d32533a8cddfba240f69c0489e87ae9e00c9216a1fdcac593e4dbf75a3f4; gleicher Datenfingerprint/Modellprofil. Dokumentation erst nach Messung ergänzt, keine Codeänderung | `source-manifest.json`, `source-2462e7d.zip`, `*-process.json`, `measurement-profile.json`; Bericht 12 |
| Manuelle Ergebnisplatzhalter und Diskussion | Menschliche Fach-/Sprachbewertung und sichtbare Bedienprüfung bleiben offen. Codex-Sichtung zu Relevanz, langen Hinweisen, Kontakt-/Ausschlussantworten nicht als manuelle Evaluation ausgeben. Formative Evaluation dieses Standes mit dokumentierten Grenzen sinnvoll; keine vollständige Freigabe | Externe `RESULT_ASSESSMENT.md`, Bericht 12.2; Release-Checkliste |

Frühere negative Messungen bleiben standgebunden gültig. Neuer Lauf ist eine
abschließende Providerregression im bereits verwendeten Katalog, keine unabhängige
Generalisierungsstudie oder kausale Vorher-/Nachhermessung. Datenrechte,
N-03-Logging und organisatorische Grenzen bleiben offen. Keine Thesisänderung.

## J. Fachentscheidungen aus der Validator-Ablation, 27.10.2026

Die Thesis bleibt unverändert. Diese Hinweise beschreiben den neuen
Arbeitsstand auf `02a3612`, keinen neuen Commit. Sämtliche bisherigen
Messungen dieses Ablationsvergleichs sind an `02a3612` gebunden und dürfen
nicht als Evaluation der nachstehenden Änderungen ausgegeben werden. Ältere
archivierte Messreihen behalten ihre jeweils dokumentierten Commitbezüge.

| Fundstelle | Neue korrekte Aussage | Code-/Testbeleg |
|---|---|---|
| `Chapters/5Solutionneu.tex:488–508`, Anhang R-20/R-21 | Freie Modellprosa (Vertrag 7, Prompt 26) wird mit Evidence 5 durch Validator 8 geprüft. Die Inhaltswortabdeckung und lexikalische NOT_CHECKED-/UNDECIDABLE-Leistungsprüfung verwerfen keine Antworten mehr. R-20/R-21 bleiben nur begrenzt abgesichert; Literal-, Referenz-, Zielgruppen-, Garantie-, Zeit-/Preis- und Policyprüfungen bestehen fort. | `app/grounding.py`, `tests/test_grounding_content.py`, `tests/test_grounding_constraints.py`, `tests/test_formulator_prose.py`; Bericht 14 |
| `Chapters/6Resultsneu.tex`, technische/manuelle Evaluation und Diskussion; bisherige Ergebnisplatzhalter | Formative manuelle Prüfung: 127 Texte, eine Bewerterin; Erstversuche ohne U n=103: 5 Fehler (4,9 %), keine beobachtete Formulator-Erfindung, 86 von 98 richtigen Antworten unnötig verworfen. Fehler stammten aus Auswahl/Daten. Datengetreue Fehler sind mit Evidenceprüfung grundsätzlich nicht erkennbar. Grenzen: synthetischer Katalog, eine Bewerterin, ein Modellprofil/ein Lauf. Neue Antworten werden erneut blind von der Nutzerin bewertet, nicht von Codex als richtig eingestuft. | `docs/exec-plans/validator-ablation.md`, externes unverändertes `auswertung.py`/`ergebnis.md` vom 27.10.; neuer Lauf und Blindpaket getrennt im Bericht |
| `Chapters/5Solutionneu.tex:488–508,639–655`, R-27; Bedarfsauswahl Medizin | Ausdrückliche Wunde/Verletzung ist ein medizinischer Bedarf und findet medical_care/medical_access, keine exklusive Forderung nach dem Label wound_care. Persönliche Zugangsregeln bleiben bestehen, insbesondere FR-04. | `app/candidates.py._requested_capabilities`, `tests/test_candidates.py.test_wound_care_includes_medical_care_and_access_without_inferring_drug_use`, `tests/test_validator_ablation_decisions.py.test_wound_query_reaches_medical_results_and_regular_contact_tile` |
| `Chapters/5Solutionneu.tex:488–508`, Safetyabgrenzung R-22/R-34 | Bei sehr starken Beschwerden/Gefahr verlangt der Formulatorprompt zusätzlich die zentral gebundene Nummer 112; sonst nicht. Keine feste Formulierung im medizinischen Modellpfad. Der deterministische Akutgefahrpfad und Preflight bleiben unverändert. | `app/formulation.py` medical_emergency, `app/policy_facts.py`, medizinische Policy- und unveränderte Akutgefahrtests in `tests/test_validator_ablation_decisions.py` |
| `Chapters/5Solutionneu.tex:423–470,639–655,762–807`, R-12/R-25/R-26/FR-09 | Lokalisierter Hilfebuskontakt wird bei unklarer/ungelöster Hilfe, keinem Treffer, Fachfremdheit und technischem Rückfall deterministisch vor der Session-/TTS-Freigabe ergänzt, wenn Hilfebus noch nicht im Text steht. Gesamtlimit 600 Zeichen berücksichtigt den Zusatz. Zusatzkachel in jeder Antwort mit Kacheln und diesen Fällen; ohne Ort, außer beim konkreten Sonntagsstand. Die Kachel ist kein zusätzlicher Bedarfstreffer. | `app/hilfebus.py`, `app/service.py.query`, Copy 10; fünfsprachige Hint-/TTS-/Sonntagstests in `tests/test_validator_ablation_decisions.py` |
| Datenkuration `Chapters/5Solutionneu.tex:288–421`, Anhang FR-03/FR-08/FR-09 | Hilfebus ohne Büroanschrift/Geometrie; Einsatztelefon allein in Evidence und Kontaktprosa, Mitarbeitertelefon nur auf Kachel. Team Konsum/Wohnen behalten Büroanschrift Demmeringstr. 32. Namensänderungen ausschließlich Kuration: Tagestreff Insel (9), Tagestreff Oase (10), Übernachtungshaus für wohnungslose Frauen (8), quellbelegte Teamnamen (12/13); alte Aliasse bleiben. Neuer KB-Fingerprint verwirft alte Sessions. | Kurationskatalog mit sechs Entscheidungen und erhöhtem Katalogstand; `tests/test_curation.py`, Alias-/Evidence-/Kacheltests; Übersetzungsintegrität ohne neue menschliche Reviewfreigabe |
| Antwortdarstellung `Chapters/5Solutionneu.tex:488–508`, R-04/R-08 | Brunnenprüfstatus nicht in Modellprosa, öffentliche Toiletten ohne Telefonfakten im Formulatorpaket (Kachel behält Kontakt), keine Zusage aus „nach Bedarf“, Postadresse als Leistung beschreiben, Ausschlussantwort ohne Datenbank-/Wissensbasiswortlaut. | Prompt 26, `app/formulator_prose.py`, `app/formulation.py`, Policyanker in `app/grounding.py`, `tests/test_validator_ablation_decisions.py` |
| Reproduktion `Chapters/AppendixLenaDesign.tex:14–70`; technische Tests `Chapters/6Resultsneu.tex:69–89` | Neuer Arbeitsstand ohne Commit: nativ und im netzlosen Testcontainer je 1585 bestanden, 1 bekannter XFAIL und je 19 JS. Runtime ohne Schlüssel, Health und Persistenz nach Neustart/Containerersatz geprüft. Containerbuild mit vorhandenen Basis-Layern; kein erfolgreicher No-Cache-Neubau behaupten, da drei Versuche am Ubuntu-Snapshotserver (HTTP 502/503) scheitern. | Bericht 14.4; `native-complete.xml`, `docker-tests-cached.log`, `runtime-smoke-cached.json`, `source-manifest-complete.json`, Buildfehlerlogs |

Offen bleibt allein die Fachentscheidung zum Hilfebus bei Akutgefahr; derzeit
keine Ergänzung. Die Streetwork-Namen sind durch die Quellen geklärt.
Ein neuer Commit bedarf einer gesonderten Anweisung. Der erneute Ablationslauf
ist keine freigegebene vollständige Vierstufen-Live-Evaluation und kein
Korrektheitsnachweis ohne die neue menschliche Bewertung.

## K. Validator-Korrekturpaket auf 5f9ddd8, 27.10.2026

Keine Thesisänderung. Der bereits vorliegende 120er-Live-Lauf bleibt Prompt 26 /
Validator 8 zugeordnet; die folgenden Zahlen sind ein **Offline-Replay** seiner
gespeicherten Modelltexte gegen Validator 9, keine neue Anwendungsmessung.

| Fundstelle | Neue korrekte Aussage | Code-/Testbeleg |
|---|---|---|
| `Chapters/5Solutionneu.tex:488–508`, R-20/R-21 | Prompt 27, Validator 9, Textvertrag 7/Evidence 5. Telefonziffern unabhängig von Personenlabels; Betriebsbedingung bleibt erforderlich. Eurobeträge numerisch und leistungsgebunden. Belegte Orte von Sprache, Kontaktzahlen von Alter, Zielgruppen-/Ausstattungsqualifier von Leistungsnegation getrennt. Das NOT_CHECKED-Zeitgate ist durch begrenzte Uhrzeit-/Tages-/Ortsprüfung ersetzt. Keine vollständige Entailment-/Falschheitsprüfung. | `app/grounding.py`, drei neue Groundinghelfer, `grounding_constraints.py`; neue Korrektur-/Gegenprobentests, Bericht 15 |
| `Chapters/6Resultsneu.tex`, formative manuelle Evaluation | Zweites Blindpaket: 134 Texte = 113 Ersttexte + 21 angezeigte Retrys; Nutzerin bewertete 116 R, 2 FU, 1 FK, 15 U. Ersttexte ohne U: 98 R/2 FU bei n=100; 30 von 98 R wurden von Validator 8 verworfen. Ein kritischer Sprachwechsel trat in einem akzeptierten EN-Retry auf. Labels FU betreffen hier auch Handlungsorientierung/Anfrageabgrenzung, daher nicht alle als erfundene Angebotsfakten zählen. | unveränderte `bewertung_ausgefüllt.csv`, Schlüsseldatei und gespeicherte Versuche im externen Ablationsordner; Bericht 15 |
| Gleicher Abschnitt, diagnostische Weiterentwicklung/Diskussion | Validator 9 akzeptiert im Offline-Replay 23 der 30 R-Ersttexte zusätzlich; sieben bleiben wegen echter Namens-/E-Mail-/ID-/Primärvertragsabweichungen gesperrt. Zwei E-Mail-Abweichungen lagen hinter der ursprünglichen Altersdiagnose. Kein zuvor akzeptierter R-Text wird neu verworfen; der FK-Sprachwechsel wird erkannt. Die beiden FU-Texte werden akzeptiert; menschliche Bewertung wird nicht umgeschrieben. | externes `2026-10-27-validator-corrections/replay.json`, Originalhashschutz; gezielte echte Negativfälle in `test_grounding_correction_controls.py` |
| Diskussion/Validität und Abgabestand | Auf denselben Beispielen entwickelt und geprüft; Verbesserung ist Diagnose/Regression, kein unabhängiger Generalisierungsnachweis. Kein neuer Templateanteil aus Replay ableiten, da Retrys und Prompt 27 nicht neu ausgeführt wurden. 15 U, unabhängiges Sprachreview und sichtbare Bedienprüfung bleiben von technischen Tests getrennt. Datengetreue Fehler und ungeprüfte offene Leistungsaussagen bleiben Grenzen. | Bericht 15; dokumentierte Charakterisierungstests; Release-Review-Checkliste |

Hilfebus bei Akutgefahr bleibt fachlich unentschieden und technisch unverändert.
Bestehende Live-/Baseline-Messungen werden nicht auf Validator 9 umetikettiert.

Technische Reproduktion (`Chapters/AppendixLenaDesign.tex:14–70`,
`Chapters/6Resultsneu.tex:69–89`): am endgültigen Korrekturexport je **1637
bestandene Python-Tests + 1 bekannter strikter XFAIL**, je **19 JS** nativ und
im netzlosen Container. Erfolgreicher No-Cache-Neubau, Runtime-Health, Start
ohne Zugangsdaten und Sitzungserhalt nach Neustart/Containerersatz. Belege:
Bericht 15.5; `native.xml`, `docker-tests.log`, `docker-verification.json`,
`runtime-smoke.json`, `source-manifest-reviewed.json` und `verification.json`
im externen Korrekturordner. Diese Tests sind kein neuer Live-Qualitätsanteil.

## L. Audio-Konfiguration und aktueller technischer Nachweis, 27.10.2026

Keine Thesisänderung. Ausgangsstand dieses lokalen Audio-Checks ist `209edfa`;
Anwendungscode und Prompt-/Validatorverträge wurden dabei nicht verändert.

| Fundstelle | Neue korrekte Aussage | Code-/Testbeleg |
|---|---|---|
| `Chapters/AppendixLenaDesign.tex:14–70`, Betriebs-/Installationsbeschreibung | Audio ist optional und standardmäßig deaktiviert. Das geprüfte lokale Profil verwendet explizit Blablador-STT und Edge-TTS; Serverneustart und Browser-Neuladen sind erforderlich. Lokale Profile gehören nicht ins Git-Archiv, Zugangsdaten nicht in die Thesis. | `app/config.py`, `.env.example`, README „Lokales Audio-Profil“; effektive HTTP-Speech-Konfiguration im Audio-Prüfordner |
| `Chapters/6Resultsneu.tex:69–89`, technische Evaluation | Am 27.10. wurden je fünf echte HTTP-STT-/TTS-Durchläufe mit synthetischen Daten erfolgreich geprüft: Ogg/Opus in DE/EN/PL/RO/RU transkribiert, sessiongebundene Policytexte als dekodierbares MP3 erzeugt. Native Umgebung CPython 3.14, Edge-Client 7.3.1 nach Angleichung an bestehenden Repository-Pin. 38 gezielte Python- und 19 Frontendtests bestanden. | Bericht 16; externes `2026-10-27-audio-activation/live-audio-results.json`, Prüfskript und Testlogs |
| Diskussion, Sprach-/Bedienqualität | Fünf festgelegte synthetische Sätze sind ein technischer Smoke-Test, kein Nachweis allgemeiner Erkennungsqualität. Anschließend bestätigte die Nutzerin funktionierende Ein-/Ausgabe in Firefox („jetzt funktioniert es“, 27.10.2026). Das bestätigt die Bedienfunktion, keine unabhängige Aussprache-/Verständlichkeitsbewertung aller fünf Sprachen. Externe Dienste bleiben erforderlich; STT empfängt Audio, Microsoft-TTS Vorlesetext. | Bericht 16; ursprünglicher technischer Prüfbericht mit damals ausstehendem manuellem Check bleibt erhalten; nachfolgendes `user-confirmation.json` dokumentiert die Bestätigung; README und bestehende Datenschutz-/Betriebsgrenzen |
