# U18-Hilfebus als Ergebnisinformation anzeigen

Status: completed

## Ziel

Bei einer Schlafanfrage einer Person unter 18 Jahren muss der bereits fachlich
ausgewählte Hilfebus neben den VKKJ-Angeboten sichtbar bleiben. Seine
freigegebene Telefonnummer und seine Einsatzzeiten sollen in einer
aufklappbaren Ergebnisinformation erreichbar sein. Es wird kein fester
Hilfebus-Standort und kein Marker erfunden.

## Review-Befund

- CandidateSelector, LLM-Selector, Grounding und API liefern den Hilfebus in
  diesem Pfad bereits als ID `21` aus.
- Die API-Karte enthält die kuratierten Telefon- und Zeitangaben, aber bewusst
  keine stationäre Büroadresse.
- `renderResultList()` verwendet bei vorhandenen Markerdaten ausschließlich
  `map_data.destinations` und verwirft dadurch ausgewählte Angebotskarten ohne
  Geometrie. Das betrifft im beobachteten Fall den mobilen Hilfebus.

## Umsetzung

1. Markerdaten und ausgewählte Angebotskarten im Frontend zusammenführen.
2. Angebotskarten nur ergänzen, wenn sie nicht bereits als Ziel oder als
   angebotsgebundener Stand (`<offer-id>:<stand-id>`) dargestellt werden.
3. Den Browser-Cache-Buster für `app.js` aktualisieren.
4. Den U18-API-Test um die freigegebenen Hilfebus-Kontaktdaten erweitern und
   die Frontend-Zusammenführung statisch absichern.
5. Den Datenfluss der Ergebnisdarstellung dokumentieren.

## Akzeptanzkriterien

- U18-Schlafantworten zeigen VKKJ-Ergebnisse und eine Hilfebus-Information.
- Die Hilfebus-Information verwendet ausschließlich Runtime-Kurationsdaten.
- Ohne verifizierten aktuellen Stand entsteht kein Hilfebus-Marker und keine
  vermeintlich stationäre Adresse.
- Ein bereits als Sonntagstand dargestellter Hilfebus wird nicht doppelt
  angezeigt.
- Vorhandene Marker und ihre reicheren Entfernungsdaten bleiben unverändert.

## Nicht im Umfang

- Änderungen an Auswahl-, Zeit-, Safety- oder U18-Fachregeln.
- Neue Koordinaten oder Standorte für den mobilen Hilfebus.
- Hartcodierte Telefonnummern oder Zeiten in JavaScript, Prompts oder Texten.
- Änderungen an Thesis- oder Präsentationsdateien.

## Verworfene Ansätze

- Einen fiktiven Hilfebus-Marker erzeugen: würde Mobilität und Einsatzort
  falsch darstellen.
- Kontaktdaten in den Antworttext duplizieren: umgeht die freigegebene
  Runtime-Wissensbasis und erschwert Aktualisierungen.
- Den Hilfebus erneut im Backend erzwingen: unnötig, weil Auswahl und API
  bereits korrekt sind.

## Verifikation

- Fokussierte API- und Frontendtests.
- Relevante Dialog- und Kurationsregressionen.
- Vollständige Testsuite.
- Python-Syntaxprüfung und `git diff --check`.
- JavaScript-Syntaxprüfung, sofern eine JavaScript-Laufzeit vorhanden ist.

## Ergebnis

- Fokussierte API-/Frontendtests: 44 bestanden.
- Dialog-, Auswahl-, Trinkwasser- und Kurationsregressionen: 124 bestanden.
- Vollständige Testsuite: 754 bestanden.
- `python -m compileall -q app tests`: bestanden.
- `git diff --check`: bestanden; lediglich vorhandene
  Zeilenenden-Warnhinweise wurden ausgegeben.
- Eine direkte `node --check`-Prüfung war nicht möglich, weil in der lokalen
  Umgebung keine Node-Laufzeit vorhanden ist. Die statische Frontendregression
  wurde ausgeführt und bestanden.
