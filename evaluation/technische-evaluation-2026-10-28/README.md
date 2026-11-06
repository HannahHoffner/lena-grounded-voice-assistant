# Technische Prüfung des Copy-11-Stands vom 28.10.2026

Die in reviewed/ gesicherten vollständigen Prüfungen liefen nach der Übersetzungs-
korrektur auf dem damals noch uncommittierten Patch zu 557a487. Dieser wurde als
5eebb72 committed. `zuordnung-finaler-code.json` vergleicht alle durch das damalige
Manifest gebundenen app/- und data/-Dateien byteweise mit dem aktuellen Checkout
5962d6c. Wartungsänderungen an Dokumentation/Paketierung sind davon getrennt.

JUnit: 1696 Fälle, 1695 bestanden, ein strikter XFAIL, 54 Module, keine Fehler.
Native Suite 435,88 s (JUnit 435,864 s), Container 318,67 s; je 19 JS-Tests.
Diese Zeiten gehören genau zu diesen Logs, nicht zu späteren Wiederholungen.
Container ohne Netz, saubere Builds mit --pull --no-cache, Runtime-Smoke und
Quellidentität dokumentiert. Eine Deprecation-Warnung des Starlette-TestClient.
Keine Coverage-Messung, vollständige Inhaltsprüfung oder erneute menschliche
Evaluation nach Copy 11. ui-check/ ist eine providerfreie Sichtprüfung mit
festen Eingaben/Fixtures in EN/PL/RO/RU; keine neuen Modellmessungen.

uebersetzung/ enthält vollständige Vorher-/Nachherprojektionen, Inventar und
131 geänderte Textfelder in 33 Sprachdatensätzen von neun sozialen Angeboten.
34 neue Anwendungstextschlüssel pro Sprache; Copy 10 → 11. Telefonnummern,
Adressen, Namen, Zeiten und Quellenbindung bleiben geschützt. Kein Nachweis
muttersprachlicher Freigabe. 30 neue Karten-Vollständigkeitstests bestanden.
Herkunft: gesichertes lokales Archiv 2026-10-28-card-translation-review.
SHA256.json bindet alle Dateien außer dem Index selbst.
