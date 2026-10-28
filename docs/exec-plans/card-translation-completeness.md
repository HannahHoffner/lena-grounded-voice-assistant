# Exec-Plan: vollständige Kachelübersetzungen

## Status und Ziel

Verified, 28.10.2026. Eng begrenzter Folgeauftrag nach der manuellen
Evaluation: alle Kacheltexte in DE/EN/PL/RO/RU auf Vollständigkeit prüfen und
fehlende Übersetzungen ergänzen. Eigennamen und Adressen unverändert lassen.
Der vorherige Codefreeze ist nur für diese Darstellungskorrektur geöffnet.

## Abnahmevertrag und Scope

- [x] Bereitgestellte XLSX-Erfassung, P1-Tabelle, Screenshot-DOCX und ratings.py
  nur lesen; Originalhashes sichern. Keine Bewertungen umschreiben.
- [x] Alle aktiven sozialen Angebotskacheln einschließlich sämtlicher
  Markerziele, mobiler Standzeiten und Hilfebus sowie Infrastruktur prüfen.
- [x] Deutsche Kontaktzusätze und Standzeitprosa in vier Zielsprachen
  lokalisieren; Namen/Adressen/IDs/Nummern/Zeiten/Preise/Orte erhalten.
- [x] Kachel, Marker-Tafel und registrierter Vorlesetext konsistent halten.
- [x] Keine Auswahl-, Safety-, Grounding- oder Modellpromptänderung; keine
  Quelldaten-/Release-/Manifest-/Snapshotänderung, kein Commit/Tag/Push.
- [x] Gezielt testen, vollständige relevante Regression und Paket-/Runtime-
  Nachweise; neue historische Messungen nicht als korrigierten Stand ausgeben.
- [x] Bericht, Thesisnotizen und Versionen ehrlich fortschreiben; keine Thesis-
  oder ursprünglichen Evaluationsdateien ändern, keine Live-Evaluation.

## Review und Architektur

`i18n.localize_offer_card` übersetzt Beschreibung, Leistungen, Öffnungszeiten
und Hinweise. Telefonzeilen/Standzeiten bleiben vollständig deutsch, weil der
bisherige Schutzvertrag sie als unteilbare operative Fakten behandelt.
`service.query` lokalisiert Markerziele nochmals, lässt bei mobilen Ständen
aber Beschreibung/Öffnungszeiten/Standzeiten und teils Telefonzeilen deutsch.
Das Frontend rendert Markerziele vor API-Karten (`resultItems`), sodass eine
Prüfung nur von `response.cards` die tatsächlich sichtbaren Kacheln verfehlt.
Vorlesetexte entstehen serverseitig und müssen identische Werte verwenden.

Wiederverwenden: gespeicherte Angebotsübersetzungen für bestehende vier
Textfelder; versionierte Application Copy für geschlossene zusätzliche
Darstellungstexte; bestehende Literal-/Namensschutzprüfung und Infrastruktur-
Wörterbücher. Kein LLM-Aufruf zur Laufzeit, keine Frontend-Ersatzübersetzung.
Die zusätzlichen Darstellungsfelder sollen die Modell-Evidence nicht ändern.

Vorhandene Änderungen: acht Markdowndateien und der Exec-Plan der Messung auf
557a487 aus vorherigem Auftrag; erhalten. Ausgangscommit weiterhin 557a487.
Keine AGENTS.md/AGENTS.override.md im Workspace gefunden. Externe Belegwurzel
`%LOCALAPPDATA%/LENA/verification/2026-10-28-card-translation-review/`.
Dokument-/Tabellen-Skills für reine Lektüre; keine verbundenen Office-Sessions,
daher auf Datenträger gespeicherte Dateien als nachweisbare Eingaben sichern.

## Dead-End-Analyse und Entscheidungen

| Risiko / Alternative | Warum unzureichend | Behandlung |
|---|---|---|
| Nur Telefonnummer im Browser ersetzen | Vorlesetext/JSON/Marker bleiben deutsch | Gemeinsame serverseitige Projektion |
| Kontaktzeile vollständig übersetzen | Namen/Nummer könnten verändert werden | Nur bekannte Erläuterungen, operative Literale prüfen |
| Nur API-Karten prüfen | Markerziele erzeugen zusätzliche sichtbare Kacheln | Gesamtes Runtimeinventar plus Standziele und API-Pfad prüfen |
| Alle Angebotsübersetzungen neu generieren | Unnötige Provideraufrufe/inhaltliche Änderungen | Bestehende gültige Texte prüfen, nur belegte Lücken korrigieren |
| Originalbewertung nach Fix überschreiben | Historische Erhebung würde verfälscht | Neue technische Nachprüfung separat, kein menschliches Urteil erfinden |

## Dateiwirkung und Meilensteine

| Dateien | Wirkung |
|---|---|
| i18n/Copy und kleiner Darstellungshelfer, service/spoken_text/hilfebus | Geschlossene Anzeigeübersetzung und konsistente Ausgabe |
| Bootstrap-i18n-Ressourcen | Maschinenentwürfe, ehrlicher machine/review_pending-Status und neue Copy-Version |
| Übersetzungs-/API-/TTS-Tests | Neue Vollständigkeits- und unveränderte Literal-/Adressgegenproben |
| Bericht/Thesisnotizen/Test- und Vertragsdokumentation | Aktuellen Patch von erhobener Evaluation trennen |

- [x] Reale Render-/TTS-Pfade und Originalergebnisse lokalisiert, Hashes gesichert.
- [x] Vollständiges Inventar und Vergleich aller Sprachfelder prüfen.
- [x] Begrenzte Anzeigeprojektion implementieren und Versionen erhöhen.
- [x] Gezielte Tests, Regression, Packaging und lokale Runtime prüfen.
- [x] code-documentation anwenden, finalen Diff/Hash-/Secret-/Scopecheck durchführen.

## Validierung und Wiederherstellung

Zunächst reproduzierende Kachel-/Marker-/TTS-Tests; bestehende Übersetzungs-
Integritäts-/Curation-/Safetytests; vollständige Python-Suite und 19 JS-Tests.
Paket-/Docker-/Runtimeprüfung soweit durch Darstellungs-/Ressourcenänderung
betroffen. Alle Inventarprüfungen providerfrei und in isolierten Datenpfaden.
Nachprüfungen beziehen sich auf Originalnamen/Adressen und unveränderte
operative Zahlen; fehlende Sprachkompetenz wird nicht als menschliches Review
ausgegeben. Bei nötiger Rücknahme nur eigene neue Projektions-/Ressourcen-
änderungen entfernen; bisherige Notizen und erhobene Ergebnisse erhalten.

## Fortschritt

28.10.2026: Originaldateien gefunden und SHA gesichert. P1-Tabelle benennt
deutsche Hilfebus-Telefonzusätze in den fremdsprachigen Fällen. Runtimeinventar
hat 28 soziale Angebote, vier gültige Übersetzungen je Angebot, keine bisherigen
Integritätsfehler. Zusätzlich 18 verschiedene Standzeittexte und 46 verschiedene
Telefonzeilen inventarisiert. Screenshot-DOCX enthält 48 eingebettete Bilder.

Abschluss: Copy 11 mit 34 neuen Schlüsseln je Sprache, 131 korrigierte
Textfelder in 33 Sprachdatensätzen. Bootstrap/Checkoutkopie gleich, keine
Kuration geändert. Je 21 Toiletten/Brunnen ebenfalls in fünf Sprachen geprüft.
30 neue Tests; alte Grounding-Negativtests unverändert. Erster Volltest zeigte
zwei alte Copy-Versionserwartungen und zwölf an aufgezeichnetes RU-Zeitliteral
gebundene Fälle. Bereits vollständiges Literal wiederhergestellt statt
Negativtests zu ändern. Nach Korrektur volle Suiten/No-Cache-Build erneut:
je 1695 Python plus bekannter XFAIL/Warnung und je 19 JS, Runtime/Persistenz
bestanden. 169 App-/Test- und 112 installierte Runtime-Appdateien per SHA geprüft.

Bestehende Source-/Reviewed-only-Policy erhalten. UI-/Dialog-/Fallback-/Safety-
Textwerte außerhalb neuer Kacheltexte unverändert, KB-Fingerprint unverändert.
Inventaraudit/Originalhashes in externer Belegwurzel, finaler Export/Prüfungen in
`reviewed/`. code-documentation: Bericht 21, Thesisnotizen Q, README, Traceability,
Test-/Vertragsdokumentation, Entscheidungen und Checkliste fortgeschrieben.
Keine Source-/Test-/Übersetzungsänderung nach Abschluss; nur Markdown.
Keine neue Live- oder menschliche Qualitätsmessung. Normaler Server nicht
neu gestartet; Aktivierung und separate Nachsicht durch Nutzerin offen.
