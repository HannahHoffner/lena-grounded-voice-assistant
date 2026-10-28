# Exec-Plan: letzte eng begrenzte Validator-Fehlalarme

## Status und Auftrag

Verified, 27.10.2026. Basis `482f1f9` mit vorhandenen eigenen
Dokumentationsfortschreibungen aus Abschlussmessung/Diagnose. Die Nutzerin
fragt anschließend nach einer schnellen, unkomplizierten Verbesserung.
Dieser begrenzte Korrekturauftrag öffnet die zuvor eingefrorene Implementierung
nur für die unten genannten Fehler; keine allgemeine Optimierungsrunde.

## Abnahmevertrag und Scope

- [x] Der deutsche Preissatz und der normale polnische Hilfebusfall aus der
  gespeicherten Reihe passieren nach gezielter Korrektur den Validator.
- [x] Reale Alterswidersprüche neben Preisen, geänderte Preise/Nummern,
  persönliche Zusagen und falsche Leistungszeiten bleiben gesperrt.
- [x] Exakte Eigennamen, zulässige Policy-IDs und explizite Telefonbetriebs-
  bedingungen bleiben erforderlich; kein automatisches Reparieren von Modelltext.
- [x] Validatorversion 10; Prompt 27, Evidence 5, Copy 10 unverändert.
- [x] Gezielte Tests, kompletter nativer/Container-Regressionslauf und
  Runtime-Prüfung; nur Offline-Replay alter Antworten, keine neue Livemessung.
- [x] Alte Vierstufenmessung bleibt Validator 9 zugeordnet; neue Anwendung
  nicht durch Umbenennung alter Messergebnisse als live gemessen ausgeben.
- [x] Keine Thesis-/Quelldaten-/Kurations-/Safetyänderung, kein Commit/Tag/Push.

## Repositoryreview und Wiederverwendung

Preis-/Altersfehler in `grounding_constraints.contradicts_age_bound`: `ab 5`
aus `ab 5,00 €` wird als Altersgrenze gelesen. Bereits vorhandenes `EURO_RE`
maskiert genau die Eurobeträge für die Altersprüfung; die unabhängige Preis-
und Zahlenprüfung bleibt bestehen. Kein allgemeines Löschen numerischer Angaben.

Polnische Betriebsbedingung in `grounding_surface.operating_restriction_present`:
das vorhandene geschlossene Muster kennt `w godzinach pracy`, aber nicht
`w godzinach ich działań`. Nur diese nahe Form aufnehmen; direkt negierte
Formen weiterhin ablehnen, zusätzliche Negative dafür prüfen.

`grounding_claims._contains_phrase` sucht überall Teilstrings. Das muss nicht
global geändert werden, weil andere Stemprüfungen darauf beruhen. Für die
polnischen persönlichen Erhaltzusagen einen kohäsiven lokalen Helfer mit
Wortgrenzen verwenden und sowohl `claims_admission` als auch
`claims_personal_receipt` daran binden. So wird `dają ci` nicht mehr in
`rozdają ciepłe` gefunden; echte zweite Person bleibt erkennbar.

`grounding_constraints.stated_weekdays` bekommt die polnischen Akkusativformen
`środę`, `sobotę` und `niedzielę` neben den kanonischen Bezeichnungen. Eine
zusätzliche echte Negativprobe des gespeicherten polnischen Textes zeigte:
Mit korrigierter Erhaltphrasenerkennung wurde die auf `sobotę` verfälschte
Sonntagsausgabe sonst nicht zurückgewiesen. Daher sind die drei abweichenden
Tagesformen notwendig; alle sechs falschen Wochentage werden im produktiven
Validator geprüft. Keine Umstellung auf umfassendes Sprachmodell/NLU und
keine Lockerung der Leistungs-/Fensterbindung.

Die betroffenen bestehenden Module überschreiten teils 400 Zeilen. Es sind
kleine Änderungen innerhalb ihrer bestehenden Verantwortung; eine umfassende
Extraktion wäre für diesen eng begrenzten Auftrag unnötig und riskanter.
Vorhandene `packet`-/`response`-Testhilfen wiederverwenden. Vorhandene
Dokumentationsänderungen bewahren.

## Sackgassen und verworfene Alternativen

| Ansatz | Warum verworfen / Gegenprobe |
|---|---|
| Alters-/Betriebszeitprüfung abschalten | Würde echte Widersprüche freigeben; nur Zahlenkontext bzw. Wortformen korrigieren. |
| Globale Phraseerkennung ändern | Könnte andere Sprachen und bewusst stemmbasierte Regeln verschieben; nur polnische Erhaltphrasen mit Grenzen versehen. |
| Telefonnummer durch allgemeine Leistungszeiten rechtfertigen | Aussagebindung wäre schwächer; manipulativer PL-Fall ohne explizite Telefonbedingung bleibt abgelehnt. |
| Rücken/Policy-ID automatisch korrigieren | Würde echte Namens-/Referenzabweichungen verstecken; keine Änderung. |
| Alle sechs Ablehnungen als Falschtexte behandeln | Diagnose zeigt konkrete Fehlalarme; keine menschlichen Urteile ersetzen. |
| Neue Modellantworten erzeugen statt Regression | Kleine Validatoränderung zuerst gegen unveränderte gespeicherte Texte und echte Gegenbeispiele prüfen. |

## Dateiauswirkung

`app/grounding_constraints.py`, `app/grounding_claims.py`,
`app/grounding_surface.py`: begrenzte Musterkorrekturen.
`app/grounding.py`: nur Versionsnummer.
`tests/test_grounding_final_false_positives.py`: sinnvolle positive/negative
Regressionsfälle; `tests/test_live_evaluation.py`: neue Metadatenversion.
Bestehende Negativtests inhaltlich unverändert. Bericht/Thesisnotizen/README/
Traceability/Testdokumentation mit Skill code-documentation fortschreiben.
Keine Änderung des Evaluationsrunners oder der ursprünglichen Reports.

## Validierung und Wiederherstellung

1. Neue Tests vor dem Fix ausführen und beobachtete Fehler festhalten.
2. Korrekturen, gezielte Grounding-/Negativtests, Replay der sechs Ablehnungen
   und der 134 bereits menschlich bewerteten Texte (keine Umkodierung).
3. Vollständige Python-/JS-Suiten, sauberer Docker-Neubau/netzloser Test,
   Runtime/Health/ohne Schlüssel/Persistenz. Neue externe Proofwurzel verwenden.
4. Diff-/Secret-/Datenprüfung; Dokumentation und Versionsbindung reviewen.

Rücknahme: ausschließlich die eigenen vier Muster-/Versionskorrekturen und
ihre neuen Tests/Notizen zurücknehmen; vorhandene Dokumentationsänderungen,
Runtime und historische Belege unangetastet lassen. Keine automatische
Rücknahme fremder Dateien. Ausstehend nach Codeänderung: neuer sauberer Commit
durch Nutzerin und bewusst festgelegter abschließender Live-/Manualbezug.

## Abschlussnachweise

28 neue Gegenproben bestanden; beide gespeicherten Fehlalarme nun angenommen,
vier übrige gesperrt; frühere 134 Entscheidungen gegenüber Validator 9 identisch.
Zehn verfälschte Kopien echter gespeicherter Texte sämtlich gesperrt.
Nach zusätzlicher Tagesgegenprobe beide vollständigen Suiten und No-Cache-
Build erneut: je 1665 Python bestanden plus bekannter XFAIL und Warnung, je
19 JS. Runtime mit installiertem Validator 10 healthy und persistent über
Neustart/Containerersatz. Abschlussbelege in externem `reviewed/`; erster
1657er-Lauf im Elternordner bewusst nur Zwischenbeleg.

code-documentation angewandt: Bericht 19, Thesisnotizen O, README, Traceability,
Prüfdokumentation, Entscheidungstabelle und Review-Checkliste fortgeschrieben;
historische Messungen standgebunden erhalten. Keine Source-/Safety-/Daten-/
Abhängigkeitsänderungen außerhalb des beschriebenen engen Pakets.

Aktivierung der normalen nativen Instanz bleibt offen: automatische
Freigabeprüfung lehnte deren Stoppen/Neustarten mit `blocked by policy` ohne
nähere Begründung ab. Kein Prozess wurde dadurch beendet. Nutzerin muss
Instanz 8002 neu starten; kein automatisches Umgehen der Ablehnung.
