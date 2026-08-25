# VKKJ-Angebote auf der Karte

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-25
- Scope: Ausschließlich verifizierte Geometrien und Kartenmarker der beiden bereits freigegebenen VKKJ-Angebote

## Review-first-Befund

- Die Runtime enthält `vkkj_notschlafstelle` und `vkkj_jugendnotdienst` bereits als getrennte, kuratierte Angebote mit den Anschriften Breite Straße 10 und Ringstraße 4.
- Die paketierte offizielle Quelle setzt bei beiden Datensätzen `geometry` ausdrücklich auf `null`. `app.maps.build_map_data()` erzeugt deshalb keine Marker; Angebotskarten bleiben davon unabhängig sichtbar.
- Die beiden bereits hinterlegten offiziellen VKKJ-Seiten veröffentlichen neben der Anschrift jeweils strukturierte `GeoCoordinates` im HTML. Damit ist weder eine Schätzung noch ein externer Geocoder erforderlich.
- Der offizielle Quelldatensatz ist über `approved_official_source_hash` an den Kurationskatalog gebunden. Jede Änderung muss diese Bindung und damit den Runtime-KB-Fingerabdruck aktualisieren.
- Der Übersetzungsspeicher bindet alle Einträge zusätzlich an den vollständigen Kurationskataloghash. Nach der Hashaktualisierung dürfen bestehende Übersetzungen nur dann technisch neu gebunden werden, wenn ihre übersetzbaren Felder und sichtbaren operativen Fakten nachweislich unverändert sind; es findet keine neue Übersetzung und keine menschliche Freigabe statt.

## Umsetzung

- [x] Offizielle VKKJ-Quelle auf einen neuen, datierten Quellenstand setzen und die auf den Betreiberseiten publizierten WGS84-Punkte mit explizitem CRS speichern.
- [x] Kartenkonvertierung auf explizit deklarierte WGS84-Geometrien erweitern; unbekannte CRS und Punkte außerhalb des Leipziger Prüfrahmens bleiben ohne Marker.
- [x] Kurationskatalog an den neuen Hash der offiziellen Quelle binden und beide Koordinatenstände als extern verifiziert ausweisen.
- [x] Vorhandene Übersetzungsidentitäten ausschließlich mechanisch auf den neuen Kataloghash binden, nachdem für alle Angebote unveränderte übersetzbare und operative Fakten geprüft wurden.
- [x] Tests für Quellenprovenienz, exakte Koordinaten, Runtime-Projektion, API-Kartenmarker, Karteninhalt und unveränderte Ausschlüsse ergänzen.
- [x] Betroffene Architektur-, Datenfluss- und Testdokumentation knapp aktualisieren.

## Nicht im Umfang

- keine Änderung der Minderjährigen-, Schlaf- oder Dialoglogik
- keine neue Übersetzung und kein Provideraufruf
- kein allgemeines Geocoding oder geografisches Ranking
- keine Änderung an Thesis- oder Präsentationsdateien
- keine Änderung der bestehenden Scharni-Geometriesperre

## Verifikation

- [x] fokussierte Quellen-, Kurations-, Karten- und API-Tests: 147 bestanden
- [x] Runtime-/Fallback-Regression: 46 bestanden
- [x] Übersetzungsintegrität: 112 aktive Sprachdatensätze geprüft; ausschließlich Identitätsfelder technisch neu gebunden
- [x] vollständige Testsuite: 748 bestanden
- [x] `python -m compileall -q app tests`
- [x] `git diff --check`

## Ergebnis

Die Kontakt- und Notschlafstelle für Jugendliche wird bei Ausgabe unter
`51.3372778, 12.4080206`, der Jugendnotdienst unter
`51.314376, 12.294794` markiert. Beide Werte stammen aus den strukturierten
`GeoCoordinates` der jeweils bereits freigegebenen Betreiberseite. Ein
laufender Server muss neu gestartet werden, weil die Runtime-Wissensbasis beim
Prozessstart geladen und fingerprintgebunden wird.
