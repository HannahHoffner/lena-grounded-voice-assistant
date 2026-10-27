# Implementierungsentscheidungen am eingefrorenen Anwendungsstand

Bezugsstand: `482f1f9` und anschließende begrenzte Validator-10-Präzisierung
(noch uncommittiert), Anwendungsversion 0.2.0. Dieser Überblick dient der
Übernahme in Methodik, Implementierung und Diskussion der Thesis; die Thesis
wird in diesem Auftrag nicht geändert. Einzelmessungen behalten ihren Commit.

| Entscheidung | Fachliche/technische Begründung | Umsetzung und Belege | Aussagegrenze |
|---|---|---|---|
| LLM-Stufen mit getrennten Rollen | Interpretation, Auswahl und Formulierung sind verschiedene Fehlerquellen; feste Verträge begrenzen ihre Befugnisse. | `app/interpreter.py`, `app/candidates.py`, `app/llm_stages.py`, `app/service.py`; Vierstufenmessung | Stufentrennung ist keine Garantie korrekter Interpretation oder hilfreicher Auswahl. |
| Deterministische Kandidaten vor Modellselektion | Persönliche Voraussetzungen, Angebotsfähigkeiten und Fachregeln sollen nicht frei vom Modell erfunden werden. | `app/candidates.py`, `candidate_contract.py`; `tests/test_candidates.py`, R-01–R-42/FR-01–FR-13 | Unbekannte Zielgruppen bleiben bedingt; nicht alle persönlichen Lebenslagen sind modelliert. |
| Freie, referenzierte Prosa statt starrer Antwortakte | Natürlichere, fragebezogene Antworten bei weiterhin beleggebundenem Format. | `app/formulation.py`, `formulator_prose.py`; Textvertrag 7, Prompt 27, Evidence 5 | Formale Referenzierung beweist keine vollständige semantische Entsprechung. |
| Zwei lexikalische Gates abschalten | In der ersten formativen Blindbewertung wurden 86/98 richtige Ersttexte unnötig verworfen; 5/103 beurteilbare Ersttexte fehlerhaft, keine beobachtete Formulator-Erfindung. | `grounding_content.py`, `grounding.py`; Bericht 14, ursprünglicher Ablationsplan und Charakterisierungstests | Stichprobe, eine Bewerterin und bekannte Fälle; 4,9 % ist eine historische beobachtete Quote, keine aktuelle allgemeine Fehlerrate. |
| Gezielte harte Groundingprüfungen beibehalten | Operative Literale, Namen, Angebot-/Fakt-/Kartenbindung, Zielgruppe, Alter, Zusage, Zeit-/Preis-/Leistungsbezug bleiben prüfbare Risiken. | `grounding.py`, `grounding_constraints.py`, neue Werte-/Sprach-/Zeithelfer; bestehende Negativtests | R-20/R-21 begrenzt; datengetreue Falschaussagen und offene Leistungsprosa sind nicht vollständig erkennbar. |
| Formate von Werten trennen | Gleiche Telefonziffern/Beträge und belegte Straßennamen sollen keine Fehlablehnung allein durch Darstellung auslösen. | Validator 9 / Prompt 27; `test_grounding_corrections.py`, `test_grounding_correction_controls.py`; Bericht 15 | Keine Freigabe geänderter Nummern, anderer Leistungen, zu weiter Altersgrenzen oder erfundener Zeiten; Sprache wird nur begrenzt erkannt. |
| Atomare Prüfung mit begrenztem Retry und Templatefallback | Ein abgelehnter Modelltext soll nicht teilweise ungeprüft angezeigt werden; bei Fehlern bleibt ein kontrollierter Ausgabepfad. | `app/service.py`, `app/providers/llm.py`, `app/llm_budget.py`; Retry-/Budgettests | Rückfallvorlagen und erholte Fehler bleiben Qualitäts-/Messbefunde; sie verschwinden nicht durch einen erfolgreichen Retry. |
| Wundversorgung als medizinische Unterart | Ein vorhandenes medizinisches Angebot soll bei ausdrücklicher Wunde nicht allein am fehlenden Capabilitywort wound_care scheitern. | `app/candidates.py`; fünfsprachige Wundtests; Bericht 14 | A1/Schoppi bleiben an belegten Drogenkonsum gebunden; kein Diagnose-/Eignungs-/Aufnahmeversprechen. |
| Notruf als gebundene medizinische Policy | 112 soll bei schweren Beschwerden im freien Modelltext möglich sein, aber aus einer zentralen verlässlichen Policy stammen. | `app/policy_facts.py`, Evidence-Projektion und Prompt; `test_medical_emergency_number_is_a_binding_policy_and_literal_allowance` | Safety-Preflight und Akutgefahrantwort bleiben unverändert; Hilfebus bei Akutgefahr ist weiterhin nicht ergänzt. |
| Hilfebuskontakt deterministisch ergänzen | Kontakt bleibt bei unklaren, fachfremden, erfolglosen oder technischen Antworten verfügbar und geht nicht durch LLM-Variation verloren. | `app/hilfebus.py`, `app/service.py`, lokalisierte Application Copy 10; R-12/FR-09 und Ablationstests | Keine Echtzeiterreichbarkeitszusage; genaue Nummer/Zeiten aus Kuration, nicht im freien Text erfunden. |
| Mobiler Kontakt und Einsatzort trennen | Büroadresse ist kein Busstandort; nur die belegte Sonntagstandzeit rechtfertigt Ort/Marker. | Hilfebus-Kachel/Evidence/TTS-Projektion; Sonntag- und Adressausschlusstests | Mitarbeitertelefon nur Kachel, Einsatznummer in Prosa; Teams 12/13 behalten ihre eigene belegte Büroanschrift. |
| Kanonische Namen ausschließlich kuratieren | Namen sind fachlich entschieden; Rohdaten bleiben unverändert, alte Bezeichnungen bleiben als Suchalias erhalten. | `app/resources/bootstrap/curation/social_offers.json`, curation_decisions und erhöhte Version; Alias-/Fingerprinttests | Neuer KB-Fingerprint entwertet Sessions; Teamnamen stammen aus Quellen, keine erfundenen Teams. |
| Evidenz für Prosa begrenzen | Interne Prüfstatus und Toilettentelefone sind keine hilfreichen Antwortfakten; fehlende Treffer sollen ohne Datenbankjargon verständlich benannt werden. | `app/formulation.py`, Prompt, Policyanker; Tests in `test_validator_ablation_decisions.py` | Toilettenkachel behält Kontaktdaten; kuratierte flexible Angaben bleiben ohne Zusagecharakter. |
| Getrennte technische und menschliche Evaluation | Verträge und ausgewählte Regeln sind automatisch prüfbar; Relevanz, Risiko und sprachliche Gestaltung benötigen eigene Urteile. | Vierstufenkatalog, manuelles 16-Einheiten-Protokoll; `THESIS_UPDATE_NOTES.md` | Keine LLM-as-a-Judge-Korrektheitsbewertung, kein Zielgruppen-/Usabilitynachweis aus Eigenbewertung. |
| Explizite externe Dienstprofile und lokale Datenspeicherung | Dienste sollen nicht still Zugangsdaten übernehmen; Kernstart ohne Zugang muss kontrolliert funktionieren. | `app/config.py`, `external_services.py`, Dockerfile, Sessions; neue Runtimeprüfungen | Sessions/Logs können Personenbezug haben; kein öffentlicher Mehrprozessbetrieb oder Konformitätsnachweis. |
| Blablador-STT und separate Edge-TTS | Firefox benötigt hier Server-STT; lokales TTS-Paket wurde an vorhandenen Pin 7.3.1 angeglichen, nachdem 7.2.8 HTTP 403 erzeugte. | lokale ignorierte Profile, `app/speech.py`, fünfsprachiger synthetischer HTTP-Test und Nutzerinnenbestätigung | Aufnahmen bzw. Vorlesetexte verlassen den Rechner. Funktionstest ist keine allgemeine Erkennungs- oder Aussprachevalidierung. |
| Eingefrorene Evaluation statt weiterer Optimierung | Nach formativer Verbesserung soll ein klarer Abschlussstand gemessen und bewertet werden. | Commit 482f1f9, Quellarchiv/SHA-Inventar, neue Regression und einmalige vierstufige Erhebung | Bekannter Katalog ist kein unabhängiger Holdout; alle negativen Gates und Instrumentkonflikte bleiben sichtbar. |

Der letzte begrenzte Validator-10-Patch korrigiert Preis-/Alterskontext,
polnische Betriebs-/Erhaltphrasen und Tagesformen; echte Gegenbeispiele bleiben
gesperrt. Zwei gespeicherte terminale Texte werden im Offline-Replay zusätzlich
angenommen, die vier übrigen bleiben gesperrt. 28 neue Tests und vollständige
Regression/Runtimeprüfungen bestanden (Bericht 19). Die alte Vierstufenreihe
auf 482f1f9 bleibt Validator 9 zugeordnet; keine Umdeutung als neue Livequote.

Die fachlichen Entscheidungen vom 27.10. beruhen auf den Vorgaben der Nutzerin
und den dokumentierten Ablationsbefunden, nicht auf einer allgemeinen
medizinischen oder behördlichen Freigabe. Vorbereitete manuelle Erwartungen
werden vor der Erhebung an diese Entscheidungen gebunden; Rohurteile werden
nicht nachträglich passend gemacht. Die aktuelle Vierstufenmessung umfasst 83 Requests und 124 Provideraufrufe; nur
die Interpreterstufe besteht beide automatischen Gates. Regression, negative
Livebefunde und noch ausstehende manuelle Urteile werden getrennt berichtet
(siehe Implementierungsbericht 17 und THESIS_UPDATE_NOTES, Abschnitt M).
