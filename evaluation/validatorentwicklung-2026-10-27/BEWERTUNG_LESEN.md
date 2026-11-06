# Blindes Bewertungspaket, 27.10.2026

Dieses Paket enthält 134 Modelltexte und ihre vorgelegten Fakten. Die
Reihenfolge ist zufällig; Validatorurteil und Erst-/Retryrolle sind verborgen.
Die Bewertungsfelder sind leer. Codex hat keine Antworten als richtig bewertet.

1. Öffne `bewertung.csv` (UTF-8, Trennzeichen Semikolon). Bewerte jeden Text mit
   R = richtig, FK = falsch/kritisch, FU = falsch/unkritisch oder U = unklar.
   Trage Fehlerstelle und Kommentar ein. `evidenz.md` enthält die zugehörigen
   Fakten in gleicher Reihenfolge.
2. Für Polnisch, Rumänisch und Russisch gibt es 82 deutsche Hilfsübersetzungen
   von Codex. Sie sind maschinell, nicht menschlich freigegeben und nicht
   maßgeblich. Zahlen, Bedingungen, Zusagen und Auffälligkeiten sollen anhand
   des Originaltexts beurteilt werden. Die Übersetzungen korrigieren die
   Aussagen der Antworten nicht.
3. `anzeigepruefung.csv` enthält zusätzlich die tatsächlich angezeigten 120
   Antworten samt Kacheln und Kartenorten, ebenfalls ohne Provider-/
   Validatorurteil. Hier kannst du den Kontaktzusatz, Namen, Ort und Kontakte
   der Hilfebuskachel prüfen. Diese Anzeigeprüfung ist vom ursprünglichen
   Modelltext-Rating getrennt.

Die Schlüsseldatei gehört nicht zu diesem Paket und sollte erst nach Abschluss
der Bewertung geöffnet werden. Frühere Bewertungsdateien wurden nicht
überschrieben. Das zugrunde liegende `run.py` und der 120er-Katalog sind
unverändert; der neue Anwendungsstand ist durch Quellhashes identifiziert und
wurde nicht committet.
