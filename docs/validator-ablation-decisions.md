# Fachentscheidungen nach dem Validator-Ablationstest, 27.10.2026

Nachfolgendes technisches Korrekturpaket auf `5f9ddd8`: Prompt 27 / Validator 9
präzisieren Format-, Sprach-, Alters-, Negations-, Zeit- und Policyprüfungen;
Textvertrag/Evidence/Copy und Fachentscheidungen bleiben erhalten. Das
NOT_CHECKED-Zeitgate wird durch beleggebundene Fensterprüfung ersetzt.
[Bericht 15](../IMPLEMENTATION_REPORT.md#15-validator-korrekturpaket-auf-5f9ddd8)
trennt die neue Offline-Wiederprüfung von der ursprünglichen Live-Messung.
Die folgenden Versionen und Zahlen beschreiben die vorausgehende Ablationsentscheidung.

Die manuelle Bewertung von 127 Formulatortexten auf `02a3612` ergab für
Erstversuche ohne unklare Bewertungen eine Fehlerquote von 4,9 % (5/103),
keine beobachtete Formulator-Erfindung und 86 unnötige Ablehnungen unter 98
richtigen Antworten. Alle fünf beobachteten Fehler entsprachen der vorgelegten
Daten-/Angebotsauswahl. Das ist keine allgemeine Fehlerfreiheitsgarantie.
Verfahren, Grenzen und Vierfeldertafel: [ursprünglicher Plan](exec-plans/validator-ablation.md).

Validator 8 verwendet deshalb weder `content_not_covered` noch lexikalisches
NOT_CHECKED/UNDECIDABLE als Ablehnungsgrund. `service_fact_missing` bleibt bei
expliziten Leistungsnegationen möglich. Literalprüfungen, Eigennamen,
Angebots-/Fakt-/Kartenbindung, Vertrag/Sprache/interne IDs, Zielgruppen-/Alter,
Zusage-/Echtzeitgrenzen, leistungsgebundene Zeiten, Preise/Entgelt und
Grenzanker bleiben bestehen. R-20/R-21 sind begrenzt abgesichert; eine mit der
Evidence übereinstimmende Falschaussage kann nicht erkannt werden.

`wound_care` umfasst medizinische Versorgung und medizinischen Zugang. Die
Kandidatenprüfung erhält sämtliche persönlichen Zugangsvoraussetzungen. Bei
Rücke/Helene bleibt eine ungeklärte Zielgruppe bedingt, A1/Schoppi erfordern
weiter belegten Drogenkonsum. Die Sonntagsessensfrage hält den zulässigen
Hilfebus verbindlich in der Auswahl; Prompt und Templatefallback nennen den
dokumentierten Stand. Andere Zusatzkacheln ändern die Auswahl nicht.

Anzeigenamen werden ausschließlich im Kurationskatalog gepflegt: Tagestreff
Insel (9), Tagestreff Oase (10), Übernachtungshaus für wohnungslose Frauen (8),
Safe-Straßensozialarbeit für Erwachsene - Team Konsum (12) und Team Wohnen
(13). Die Teamnamen stammen aus dem unveränderten WFS-Bestand. Frühere Namen
und neue Namen bleiben suchbar; SZL Suchtzentrum/Suchtzentrum sind wegen der
mehreren Teams Organisationsaliase, keine willkürliche Einzelauswahl.

Der Hilfebus hat als mobiler Kontakt keine Büroanschrift/Geometrie in der
Runtimeprojektion. Das Formularpaket erhält ausschließlich die als „nur zu
Einsatzzeiten“ gekennzeichnete Nummer. Die volle Kachel behält beide
Telefonkontakte; die zusätzliche Kontaktprosa wird deterministisch lokalisiert
und bezieht Nummer/Zeiten aus der Kuration. Das Modellbudget berücksichtigt
den Zusatz innerhalb von insgesamt 600 Zeichen. Der endgültige Antwort- und
Kacheltext wird vor der Session-/TTS-Freigabe zusammengesetzt. Akutgefahr und
deren Klärungsdialog bleiben ohne Zusatz und ohne Kachel.

Versionen: Prompt 26, Evidence 5 (neue Policy und Zeichenbudget, geänderte
Projektion), Validator 8, Application Copy 10; Textvertrag 7 bleibt erhalten.
Katalog `prototype-2026-10-27-validator-ablation`. Bestehende Übersetzungsfelder
werden nach Prüfung ihrer geschützten Tokens an den neuen Kurationshash
gebunden; ihre Sprachreviewstatus bleiben unverändert. Keine neue
Konfigurationsoption und keine Änderung an `.env.example` erforderlich.

Technische Ergebnisse und vollständige Liste der umformulierten
Charakterisierungstests: [Implementation Report](../IMPLEMENTATION_REPORT.md).
Thesisänderungen werden ausschließlich in
[THESIS_UPDATE_NOTES](../THESIS_UPDATE_NOTES.md) vorbereitet.
