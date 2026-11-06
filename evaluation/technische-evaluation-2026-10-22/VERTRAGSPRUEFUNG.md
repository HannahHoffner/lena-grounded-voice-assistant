# Vertragsprüfung: belegte Aussagen vor Formvorgaben

Stand: `597e1f0216c72eedd01b7b9e6d49be67ca8150f9`, Formulatorvertrag 5,
Prompt 22, Groundingvalidator 3. Der Formulator bleibt die reguläre
Antwortstufe. Angebotsauswahl, Quelldaten und bestehende strukturierte
Rückfragen werden dadurch nicht ersetzt.

| Regel | Ergebnis der Prüfung und Umsetzung |
|---|---|
| Genau ein Satz pro Textfeld, höchstens 32 Wörter | Kein Wahrheitskriterium. Mehrere Sätze zum selben Angebot sind erlaubt; Satzgrenzen werden als Stilbeobachtung protokolliert. |
| Höchstens 220 Zeichen pro Feld | Zu eng für einen Textblock. Eine diagnostizierte Schemaablehnung betraf 226 Zeichen. Jetzt bis zu 600 pro Block und unverändert höchstens 600 für alle Blöcke zusammen. |
| Zwei oder drei Sätze auch bei einfacher Frage | Kann unnötige Details erzwingen. Ein kurzer, relevanter Block genügt. |
| Fester erster Claimtyp | Ein belegter Fakt darf direkt die Frage beantworten. Die primäre Reihenfolge bei Wasser/Toiletten bleibt als Auswahlentscheidung erhalten. |
| Ein als Leistung etikettierter Betriebszeitensatz | Das Etikett allein ist kein Inhaltsbeleg. Rein operative Angaben können trotz falschem Etikett akzeptiert werden, wenn Werte, Wortumfang und Tages-/Zeitbindung geprüft sind. Ein zusätzlich erfundenes Zimmer-/Essensangebot bleibt unzulässig. |
| Gebühren müssen immer im Antworttext stehen | Ergänzende Details dürfen in der Kachel stehen. Wird eine Gebühr oder Zahlungsart erwähnt, muss sie stimmen. Falsches „kostenlos“, erfundene Kartenzahlung oder widersprüchliches „nur bar“ werden gezielt geprüft. |
| Mindestens drei Hilfebereiche in jeder Abgrenzung | Für eine kurze richtige Abgrenzung unnötig; die Liste ist optional. Die Aussage muss weiterhin abgrenzen, nicht die fremde Sachfrage aus Weltwissen beantworten. |
| Nur feste Ich-Formen bei Abgrenzung/Ergebnislosigkeit | Sprachliche Varianten erweitert, unter anderem „LENA kann nicht antworten“ und belegte polnische Ergebnisformulierungen. Positive Behauptungen werden dadurch nicht zu negativen Ergebnisberichten. |
| Exakte Unicode-Zeichen von Namen | Gleichwertige Bindestriche und Leerraum dürfen abweichen. Buchstaben, Wortgrenzen, Namenszuordnung und Referenzen bleiben gebunden; kein freies Umbenennen, Übersetzen oder Flektieren. |
| Deutsche Höflichkeitsform oder wiederholter Block | Stilbeobachtung, keine Tatsachenwiderlegung; löst allein keinen Fallback aus. Der Prompt bevorzugt weiterhin kurze Antworten mit „du“. |
| Rumänisch „masă de înfășat“ | Wickeltisch ist kein Essensangebot. Nur die vollständige Wendung wird entsprechend behandelt; ein zusätzlich erwähntes Essen bleibt sichtbar. |
| „fără bariere“ / „bez barier“ | Eine belegte barrierefreie Ausstattung verneint nicht die Toilettenleistung. Die Ausnahme gilt nur für den belegten Ausstattungswert und verdeckt keine weitere Verneinung. |

Erhalten bleiben JSON-/Referenzintegrität, der begrenzte Kreis ausgewählter
Angebote, Belegbindung von Zahlen, Adressen und Kontakten, Leistungs- und
Zielgruppenprüfungen, Altersgrenzen sowie Verbote unbelegter Aufnahme-,
Eignungs- und aktueller Verfügbarkeitszusagen. Kontaktdaten und Zahlen werden
weiter konservativ geprüft. Fehlende Details dürfen weggelassen, aber nicht
aus der Nutzerfrage oder aus Weltwissen ergänzt werden.

Für ungeklärte persönliche Voraussetzungen bleibt die vorhandene Dialogsteuerung
mit ihren Rückfragen zuständig. Der Formulator kann zusätzlich vorschlagen,
beim ausgewählten Kontakt nicht verifizierte Details zu erfragen. Ein zweiter,
unstrukturierter Rückfragedialog wurde nicht eingebaut.

Die Gegenproben in `tests/test_formulator_factual_freedom.py` verbinden jeweils
zulässige Formulierungen mit falschen/unbelegten Varianten: Gratiszugang in fünf
Sprachen, Preise/Zahlungsarten, Altersober- und -untergrenzen, Tagesbereiche,
vertauschte Zeitintervalle, erfundene Adressen, Namensänderungen und eine
zusätzliche unbelegte medizinische Leistung im längeren Antwortblock. Bestehende
Fakt-/Safetytests bleiben Teil der vollständigen Regression.

Die providerfreie Rekonstruktion aus früheren Berichten ist eine Diagnose,
keine neue Modellevaluation: 17 von 20 rekonstruierbaren verworfenen Versuchen
wurden ohne Textänderung akzeptiert. Zwei Wasserpakete wurden nicht
rekonstruiert. Ursprüngliche Reports und ihre Gates bleiben unverändert.

Die Regeln sind keine vollständige semantische Beweisführung. Unbekannter
Wortschatz, nicht abgedeckte Beziehungen und sprachliche Angemessenheit bleiben
Gegenstand der manuellen Sichtprüfung. Eine niedrigere Ablehnungsquote allein
beweist keine höhere Faktenqualität. Die konkreten Live-Ergebnisse stehen in
[TESTERGEBNIS.md](TESTERGEBNIS.md), die final ausgelieferten Antworten und
verworfenen Versuche in [BEISPIELANTWORTEN.md](BEISPIELANTWORTEN.md).

Zusätzliche Schlusskorrektur: Validator 3 erkennt flektierte Wochentage wie „montags“ und „Mondays“ wieder. Eine Montagsbehauptung darf nicht zu einem Sonntagsfenster passen; ein Bereich „montags bis freitags“ braucht auch die dazwischenliegenden Tage. Direkte Gegenproben und der vollständige Validator prüfen diese Fälle.

Ergänzende fachliche Bestätigung des Nutzers: Die Leipziger Oase bietet warmes
Essen. Diese Formulierung wird deshalb als korrekt akzeptiert; es wurde keine
zusätzliche Temperatur-Sperrregel eingebaut. Die Bestätigung ist separat in
`USER_CONFIRMATIONS.json` dokumentiert. Der eingefrorene Laufdatenbestand und
die automatischen Messergebnisse wurden dadurch nicht nachträglich verändert.
