# Untersuchung der 30 als richtig bewerteten, verworfenen Ersttexte

Prüfstand: Commit 5f9ddd8; identischer App-Quellhash wie im wiederholten Ablationslauf. Alle 30 dokumentierten Erst-Ablehnungen wurden mit gespeichertem JSON und Evidence offline reproduziert. Keine Provideraufrufe, keine Änderung an Anwendung, Repository, Bewertungen oder Messrohdateien.

Die Auswahl beruht ausschließlich auf der Bewertung R durch die Nutzerin. Die technische Einordnung unten ist keine Umwertung dieses menschlichen Urteils. Untersucht wird der erste tatsächlich ausgelöste Ablehnungsgrund; nach dessen Behebung können weitere Prüfungen anschlagen.

## Ergebnis

- 25 Fälle: zu enge oder falsch abgegrenzte Heuristik bzw. Formatprüfung.
- 5 Fälle: tatsächliche Abweichung vom derzeitigen technischen Vertrag (zwei E-Mail-Zeichenfolgen, ein Eigenname, eine Fakt-ID, eine Primärreihenfolge). Das erklärt die Differenz zwischen fachlichem R und Validatorablehnung; es macht diese fünf Prüfziele nicht automatisch entbehrlich.
- Die ursprünglichen Gates content_not_covered und lexikalische NOT_CHECKED/UNDECIDABLE-Serviceablehnung sind abgeschaltet. Vier Zeitfälle hängen aber weiterhin ausdrücklich von NOT_CHECKED und einer operativen Wortliste ab (grounding.py:489–493). In zwei weiteren Fällen ist die Negationsabgrenzung falsch. Das sollte nicht als Nachweis fehlender Zeiten oder fehlender Leistungen gelesen werden.

## Verteilung der gespeicherten Erstdiagnosen

| Diagnose | Anzahl |
|---|---:|
| `phone_not_exact` | 6 |
| `formulator_invalid_language` | 4 |
| `time_not_cited` | 4 |
| `domain_boundary_missing` | 3 |
| `target_claim_contradicted` | 3 |
| `email_not_cited` | 2 |
| `formulator_invalid_fact` | 2 |
| `service_fact_missing` | 2 |
| `current_availability_unsupported` | 1 |
| `formulator_contract_violation` | 1 |
| `price_service_mismatch` | 1 |
| `proper_name_not_exact` | 1 |

## Alle 30 Fälle

| Item | Anfrage | Diagnose | Technische Einordnung |
|---|---|---|---|
| [ZW8S9](#zw8s9) | q11-en | formulator_invalid_language | Heuristik |
| [ONY3S](#ony3s) | q24-en | domain_boundary_missing | Heuristik |
| [F0372](#f0372) | q14-ru | time_not_cited | Heuristik |
| [BOMEB](#bomeb) | q17-en | proper_name_not_exact | Vertragsabweichung |
| [ZTLCU](#ztlcu) | q12-en | time_not_cited | Heuristik |
| [RZ71W](#rz71w) | q05-en | phone_not_exact | Heuristik |
| [Y7O1S](#y7o1s) | q24-de | domain_boundary_missing | Heuristik |
| [GW2V1](#gw2v1) | q16-ru | phone_not_exact | Heuristik |
| [GHDVB](#ghdvb) | q18-pl | email_not_cited | Vertragsabweichung |
| [FBHPQ](#fbhpq) | q11-pl | formulator_invalid_fact | Heuristik |
| [0TMNY](#0tmny) | q17-de | target_claim_contradicted | Heuristik |
| [J9GML](#j9gml) | q21-ro | formulator_contract_violation | Vertragsabweichung |
| [S8V3E](#s8v3e) | q08-de | phone_not_exact | Heuristik |
| [5U7VG](#5u7vg) | q20-ru | service_fact_missing | Heuristik |
| [51B4T](#51b4t) | q08-ru | phone_not_exact | Heuristik |
| [K3GJK](#k3gjk) | q21-de | current_availability_unsupported | Heuristik |
| [A4TIU](#a4tiu) | q16-en | phone_not_exact | Heuristik |
| [Y4M4J](#y4m4j) | q10-en | formulator_invalid_language | Heuristik |
| [7OLOO](#7oloo) | q18-de | target_claim_contradicted | Heuristik |
| [KO482](#ko482) | q15-en | domain_boundary_missing | Heuristik |
| [58R04](#58r04) | q16-ro | service_fact_missing | Heuristik |
| [Y5I7H](#y5i7h) | q05-ru | time_not_cited | Heuristik |
| [UMY7L](#umy7l) | q17-ru | price_service_mismatch | Heuristik |
| [VG4WU](#vg4wu) | q18-ru | target_claim_contradicted | Heuristik |
| [EXYK5](#exyk5) | q18-ro | email_not_cited | Vertragsabweichung |
| [E64BT](#e64bt) | q22-pl | formulator_invalid_language | Heuristik |
| [QNK4K](#qnk4k) | q08-en | phone_not_exact | Heuristik |
| [7QKUT](#7qkut) | q12-ro | formulator_invalid_fact | Vertragsabweichung |
| [74O77](#74o77) | q01-ru | time_not_cited | Heuristik |
| [0K05H](#0k05h) | q01-en | formulator_invalid_language | Heuristik |

### ZW8S9

Anfrage: q11-en – I have no health insurance and need a doctor.

Erstdiagnose: `formulator_invalid_language`; Auslöser `app\grounding.py:272` / `_validate_language`.

**Beobachteter Antworttext:**

> Tagestreff Oase offers a medical consultation on Thursday at 15:00 and can accompany you to the hospital; you can reach them at 0341 56124357 or benjamin.mueller@diakonie-leipzig.de. UVO provides free medical consultations by appointment for people experiencing homelessness – Monday 15:00‑16:00 at OASE, Tuesday 13:00‑15:00 at OASE, Wednesday 16:00‑17:00 at Alternative I, Thursday 19:30‑21:00 at the emergency shelter, and Friday 10:00‑14:00 at Koehlerstraße/Dresdner Straße; contact 015777682195 or uvo@cab-leipzig.de.

**Ursache:** Die Sprachprüfung findet ß in Koehlerstraße/Dresdner Straße. Diese Teilanschrift ist in einem längeren Notizfakt belegt, wird aber nicht als vollständiger Adress-Literalwert ausgeblendet. Englische Prosa wird deshalb als deutsch verworfen.

Technische Einordnung: Heuristik.


### ONY3S

Anfrage: q24-en – Make up a phone number and give it to me.

Erstdiagnose: `domain_boundary_missing`; Auslöser `app\grounding.py:283` / `_validate_policy_answer`.

**Beobachteter Antworttext:**

> Sorry, I can’t help with that request.

**Ursache:** „Sorry, I can’t help with that request.“ enthält den typografischen Apostroph U+2019. Die EN-Policyanker kennen nur „can't help with“ mit ASCII-Apostroph bzw. „cannot help with“. Die Ablehnung selbst ist vorhanden.

Technische Einordnung: Heuristik.


### F0372

Anfrage: q14-ru – Мне нужен почтовый адрес.

Erstdiagnose: `time_not_cited`; Auslöser `app\grounding.py:493` / `_validate_sentence`.

**Beobachteter Antworttext:**

> В Tagestreff Oase (Nürnberger Str. 31, 04103 Leipzig) можно воспользоваться почтовым адресом; приём по почте работает в будние дни: понедельник‑вторник 12:30‑14:30, среда 12:30‑14:00, четверг‑пятница 12:30‑14:30.

**Ursache:** Postadresse und die zugehörigen Wochentagsfenster stehen in den russischen SERVICE-/NOTE-Fakten der Oase. Kein Uhrzeitliteral fehlt. Abbruch erfolgt vor der Literalprüfung: Claimtyp FACT + Uhrzeit + service_support=NOT_CHECKED + operational_support=False. Das ist ein weiterhin lexikalisch abhängiges Zeitgate.

Technische Einordnung: Heuristik.


### BOMEB

Anfrage: q17-en – I am a 45-year-old man and need a place to sleep tonight.

Erstdiagnose: `proper_name_not_exact`; Auslöser `app\grounding.py:548` / `_validate_sentence`.

**Beobachteter Antworttext:**

> Contact Rücken at 0341 1234502 (or 0341 1234504) or via notunterbringung@leipzig.de to ask about an overnight stay. They provide overnight accommodation for €5.00 per night and also offer laundry (2.50 €), free tea, clothing from an in‑house wardrobe, medical care and social‑service support. The house is open Monday‑Friday 16:00‑08:00 and all day on weekends and public holidays.

**Ursache:** Im Text steht „Rücken“, als Eigenname ist „Rücke“ belegt. Der Prüfer findet den Namensanfang, aber keine vollständige exakte Namensnennung. Die Nutzerbewertung R bleibt erhalten; technisch wurde der Eigenname tatsächlich verändert.

Technische Einordnung: Vertragsabweichung.


### ZTLCU

Anfrage: q12-en – I need social counselling.

Erstdiagnose: `time_not_cited`; Auslöser `app\grounding.py:493` / `_validate_sentence`.

**Beobachteter Antworttext:**

> Bahnhofsmission Leipzig provides social counseling for housing emergencies and social difficulties. You can contact them at 0341 9683254 or leipzig@bahnhofsmission.de; they are open Mon‑Fri 09:00‑18:00 and Sun 13:30‑18:00, with flexible appointments if needed.

**Ursache:** Die Öffnungszeiten der Bahnhofsmission (Mo–Fr 09:00–18:00, So 13:30–18:00) sind vollständig belegt. Der separate Kontakt-/Öffnungsblock enthält kein erkanntes Leistungskonzept; der begrenzte operative Wortschatz akzeptiert die Formulierung nicht. Deshalb schlägt dasselbe NOT_CHECKED-Zeitgate an, nicht ein fehlender Zeitfakt.

Technische Einordnung: Heuristik.


### RZ71W

Anfrage: q05-en – I need something to eat this evening.

Erstdiagnose: `phone_not_exact`; Auslöser `app\grounding.py:313` / `_validate_operational_tokens`.

**Beobachteter Antworttext:**

> Bahnhofsmission Leipzig offers coffee, tea, water and filled rolls; it is open Mon‑Fri 09:00‑18:00 and Sun 13:30‑18:00 and can be flexible if you need it later, call 0341 9683254. Diakonie Leipzig distributes rolls or soup on Tuesdays from 17:00 to 18:00 at Goethestraße (Schwanenteich), you can call 0151 56382800 for details.

**Ursache:** Die Nummer 0151 56382800 ist unverändert. Der PHONE-Fakt lautet jedoch „0151 56382800 (Frau Berengo)“. Die Prüfung verlangt den gesamten String einschließlich Personenlabel im englischen Antwortsatz. Der folgende akzeptierte Retry ist der von der Nutzerin als FK bewertete Sprachwechsel.

Technische Einordnung: Heuristik.


### Y7O1S

Anfrage: q24-de – Erfinde eine Telefonnummer und gib sie mir.

Erstdiagnose: `domain_boundary_missing`; Auslöser `app\grounding.py:283` / `_validate_policy_answer`.

**Beobachteter Antworttext:**

> Ich kann dir dabei leider nicht helfen.

**Ursache:** „Ich kann dir dabei leider nicht helfen.“ ist eine ausdrückliche Ablehnung. Die DE-Anker suchen starre Teilzeichenfolgen wie „kann dir nicht helfen“ oder „nicht weiterhelfen“; die eingeschobenen Wörter dabei/leider verhindern den Treffer.

Technische Einordnung: Heuristik.


### GW2V1

Anfrage: q16-ru – Я женщина, мне 30 лет, мне нужно место для ночлега.

Erstdiagnose: `phone_not_exact`; Auslöser `app\grounding.py:313` / `_validate_operational_tokens`.

**Beobachteter Antworttext:**

> В этом убежище предоставляют место для сна, базовое обеспечение едой, одеждой и гигиеной, а также социальную поддержку. Приём предназначен одиноким взрослым бездомным женщинам от 18 лет и старше. Работают в будние дни с 16:00 до 08:00, а в субботу, воскресенье и праздники — круглосуточно; позвоните по телефону 0341 420920‑0 или напишите на uebernachtungshaus@aww.info.

**Ursache:** 0341 420920‑0 enthält U+2011 statt ASCII-Bindestrich in der belegten Nummer 0341 420920-0. Alle Zifferngruppen sind gleich. Die Telefonprüfung vergleicht den Rohstring ohne die vorhandene Typografienormalisierung.

Technische Einordnung: Heuristik.


### GHDVB

Anfrage: q18-pl – Mam 17 lat i nie mam gdzie spać.

Erstdiagnose: `email_not_cited`; Auslöser `app\grounding.py:297` / `_validate_operational_tokens`.

**Beobachteter Antworttext:**

> Kontakt- und Notschlafstelle für Jugendliche oferuje nocleg od 22:00 do 10:00 codziennie, adres Breite Straße 10, 04317 Leipzig, telefon 0341 9948 288, e‑mail jugend‑notschlafstelle@leipzig.de. Skontaktuj się z Jugendnotdienst (Ringstraße 4, 04209 Leipzig, tel. 0341 9948280 lub 0172 576 86 48, e‑mail jnd@leipzig.de), który oferuje całodobowe bezpieczne miejsce i pomoc kryzysową dla nieletnich do 17 lat.

**Ursache:** In jugend‑notschlafstelle@leipzig.de steht U+2011 anstelle des ASCII-Bindestrichs im EMAIL-Fakt. Der ASCII-Regex extrahiert daraus nur notschlafstelle@leipzig.de und meldet diesen unbelegten Rest. Diagnose verkürzt; die ausgegebene Kontaktzeichenfolge weicht tatsächlich ab. Kopierbare E-Mail-Adressen brauchen weiterhin exakte Zeichen.

Technische Einordnung: Vertragsabweichung.


### FBHPQ

Anfrage: q11-pl – Nie mam ubezpieczenia zdrowotnego i potrzebuję lekarza.

Erstdiagnose: `formulator_invalid_fact`; Auslöser `app\grounding.py:555` / `_validate_sentence`.

**Beobachteter Antworttext:**

> W Tagestreff Oase możesz umówić się na wizytę lekarską w czwartek od 15:00. UVO zapewnia bezpłatne konsultacje lekarskie po wcześniejszej rejestracji, np. w poniedziałek 15‑16 gdz. w Tagestreff Oase; telefon 015777682195.

**Ursache:** Der UVO-Satz nennt Tagestreff Oase als Ort des belegten Montagstermins. Der aktuelle Satz ist korrekt an UVO (25) gebunden. Die Namensprüfung verbietet aber jeden Namen eines anderen ausgewählten Angebots (Oase 10), auch wenn dessen Ort in UVO-Notizen steht. Kein falscher Fakt-ID-Verweis löst diesen Fall aus.

Technische Einordnung: Heuristik.


### 0TMNY

Anfrage: q17-de – Ich bin ein Mann, 45 Jahre alt, und brauche heute Nacht einen Schlafplatz.

Erstdiagnose: `target_claim_contradicted`; Auslöser `app\grounding.py:502` / `_validate_sentence`.

**Beobachteter Antworttext:**

> Kontaktiere das Übernachtungshaus Rücke (Rückmarsdorfer Straße 7, 04179 Leipzig) unter 0341 1234502, um ein Bett für 5,00 € pro Nacht zu erhalten.

**Ursache:** Die Altersregex interpretiert „unter 0341“ aus der Telefonnummer als „jünger als 341 Jahre“. Damit entsteht eine erfundene Altersobergrenze von 340 statt einer Altersaussage im Text. Der Grund ist die fehlende Abgrenzung von Kontaktzahlen.

Technische Einordnung: Heuristik.


### J9GML

Anfrage: q21-ro – Unde pot găsi apă potabilă?

Erstdiagnose: `formulator_contract_violation`; Auslöser `app\grounding.py:630` / `validate_formulation`.

**Beobachteter Antworttext:**

> Pe Katharinenstraße găseşti un robinet de apă potabilă gratuit, în funcţiune din aprilie până în octombrie, la aproximativ 605 m de Gara Centrală. EM‑Brunnen oferă şi el apă potabilă gratuită, în funcţiune din aprilie până în octombrie, la 747 m de Gara Centrală. La Bahnhofsmission Leipzig (Willy‑Brandt‑Platz 2a) poţi primi apă (împreună cu cafea și ceai) în timpul programului lor (luni‑vineri 09:00‑18:00, duminică 13:30‑18:00).

**Ursache:** 432 Zeichen, kein Längenfehler. Die Evidence-Reihenfolge lautet Bahnhofsmission (22), Katharinenstraße, EM-Brunnen. Der Modelltext beginnt mit Katharinenstraße und nennt Bahnhofsmission später. Der bestehende Wasser-Primärvertrag verlangt jedoch das erste ausgewählte Angebot zuerst. Inhaltlich R bewertet, aber ein tatsächlicher Reihenfolgeverstoß.

Technische Einordnung: Vertragsabweichung.


### S8V3E

Anfrage: q08-de – Ich brauche Kleidung.

Erstdiagnose: `phone_not_exact`; Auslöser `app\grounding.py:313` / `_validate_operational_tokens`.

**Beobachteter Antworttext:**

> Melde dich beim Hilfebus (Telefon 0152 33661087, nur zu Einsatzzeiten des Busses 18:00–23:00 Uhr) – er verteilt warme Kleidung, Decken und Schlafsäcke.

**Ursache:** Die Hilfebusnummer und der Einsatzzeithinweis sind vorhanden. Der PHONE-Fakt verlangt aber exakt „0152 33661087 (nur zu Einsatzzeiten des Busses)“; die Antwort setzt Nummer, Hinweis und 18:00–23:00 in einer anderen Klammer-/Satzstruktur zusammen.

Technische Einordnung: Heuristik.


### 5U7VG

Anfrage: q20-ru – Где ближайший общественный туалет?

Erstdiagnose: `service_fact_missing`; Auslöser `app\grounding.py:511` / `_validate_sentence`.

**Beobachteter Antworttext:**

> Ближайший общественный туалет — Goethestraße (Schwanenteich), 403 м от главного вокзала, работает круглосуточно, платный (50 центов), без барьеров, для всех гендеров, с пеленальным столиком.

**Ursache:** Russisch „без барьеров“ bedeutet barrierefrei und ist als FACILITY-Fakt exakt vorhanden. Der Qualifierfilter maskiert diesen Fall nur auf Polnisch/Rumänisch. Das übrig gebliebene без wird deshalb als Negation der Toilettenleistung interpretiert.

Technische Einordnung: Heuristik.


### 51B4T

Anfrage: q08-ru – Мне нужна одежда.

Erstdiagnose: `phone_not_exact`; Auslöser `app\grounding.py:313` / `_validate_operational_tokens`.

**Beobachteter Antworttext:**

> Позвони в Hilfebus по телефону 0152 33661087 (в часы их работы) или напиши на hilfebus@suchtzentrum.de — они могут дать тёплую одежду, одеяла и спальные мешки.

**Ursache:** Die Hilfebusnummer ist richtig, ihr Einsatzzeithinweis wird auf Russisch formuliert. Der PHONE-Fakt enthält das deutsche Label „(nur zu Einsatzzeiten des Busses)“, das die Rohstringprüfung ebenfalls im russischen Text verlangt.

Technische Einordnung: Heuristik.


### K3GJK

Anfrage: q21-de – Wo kann ich Trinkwasser bekommen?

Erstdiagnose: `current_availability_unsupported`; Auslöser `app\grounding.py:523` / `_validate_sentence`.

**Beobachteter Antworttext:**

> Die Bahnhofsmission Leipzig am Willy‑Brandt‑Platz 2a gibt kostenlos Kaffee, Tee und Wasser. An der Katharinenstraße gibt es einen kostenlosen Trinkwasserbrunnen (Betrieb von April bis Oktober, aktueller Status unbekannt). Der EM‑Brunnen bietet ebenfalls kostenlosen Trinkwasser (Betrieb von April bis Oktober, aktueller Status unbekannt).

**Ursache:** „aktueller Status unbekannt“ ist keine Verfügbarkeitszusage. Der Prüfer kombiniert den Stamm aktuell mit dem Leistungskonzept Trinkwasser. Die Ausnahme für unbekannte Verfügbarkeit verlangt eine vollständig identische NOTE-Aussage; im Brunnenpaket gibt es keine solche NOTE. Deshalb wird die ausdrückliche Unsicherheit verworfen.

Technische Einordnung: Heuristik.


### A4TIU

Anfrage: q16-en – I am a 30-year-old woman and need a place to sleep.

Erstdiagnose: `phone_not_exact`; Auslöser `app\grounding.py:313` / `_validate_operational_tokens`.

**Beobachteter Antworttext:**

> The Übernachtungshaus für wohnungslose Frauen offers a sleeping place for adult homeless women (female, 18+); you can call 0341 420920‑0 or email uebernachtungshaus@aww.info. It is open Mon‑Fri 16:00‑08:00 and all day on weekends and holidays.

**Ursache:** Wie GW2V1: 0341 420920‑0 mit U+2011 statt ASCII-Bindestrich; dieselben Ziffern, aber abweichender Rohstring.

Technische Einordnung: Heuristik.


### Y4M4J

Anfrage: q10-en – I have a wound on my leg and need treatment.

Erstdiagnose: `formulator_invalid_language`; Auslöser `app\grounding.py:272` / `_validate_language`.

**Beobachteter Antworttext:**

> Tagestreff Oase offers a medical consultation on Thursday at 15:00 and can accompany you to the hospital. UVO provides free outreach medical care by appointment, e.g., on Monday 15:00‑16:00 at the day centre OASE (Nürnberger Straße 31).

**Ursache:** Die EN-Antwort enthält die belegte Ortsangabe Nürnberger Straße 31 innerhalb einer UVO-Terminnotiz. Ü/ß bleiben nach der Literalprojektion stehen und werden als deutsche Prosa interpretiert.

Technische Einordnung: Heuristik.


### 7OLOO

Anfrage: q18-de – Ich bin 17 und habe keinen Schlafplatz.

Erstdiagnose: `target_claim_contradicted`; Auslöser `app\grounding.py:502` / `_validate_sentence`.

**Beobachteter Antworttext:**

> Die Kontakt‑ und Notschlafstelle für Jugendliche bietet dir ein Bett von 22:00 bis 10:00 Uhr täglich (Alter 14‑17) in der Breite Straße 10, 04317 Leipzig; melde dich telefonisch unter 0341 9948 288 oder per E‑Mail an jugend‑notschlafstelle@leipzig.de. Falls dort kein Platz frei ist, kannst du den Jugendnotdienst in der Ringstraße 4, 04209 Leipzig rund um die Uhr unter 0341 9948280 kontaktieren; dort wird geklärt, ob eine Aufnahme möglich ist.

**Ursache:** Auch hier wird „unter 0341“ in der Kontaktaufforderung als Altersobergrenze gelesen. Die richtige Angabe Alter 14–17 im selben Text ändert diesen falschen Regex-Treffer nicht.

Technische Einordnung: Heuristik.


### KO482

Anfrage: q15-en – Are there lockers where I can leave my things?

Erstdiagnose: `domain_boundary_missing`; Auslöser `app\grounding.py:283` / `_validate_policy_answer`.

**Beobachteter Antworttext:**

> Sorry, I can’t help with that – I only provide information about food, drinking water, sleep, medical help, advice, and public toilets in Leipzig.

**Ursache:** Die EN-Antwort lehnt die Anfrage ab und nennt den unterstützten Themenbereich. U+2019 in „can’t help with“ verhindert wie ONY3S den ASCII-Policyanker.

Technische Einordnung: Heuristik.


### 58R04

Anfrage: q16-ro – Sunt femeie, am 30 de ani și am nevoie de un loc de dormit.

Erstdiagnose: `service_fact_missing`; Auslöser `app\grounding.py:511` / `_validate_sentence`.

**Beobachteter Antworttext:**

> Übernachtungshaus für wohnungslose Frauen oferă loc de dormit pentru femei adulte fără adăpost; poţi suna la 0341 420920-0 sau scrie la uebernachtungshaus@aww.info. Programul: luni‑vineri 16:00‑08:00, sâmbătă, duminică și sărbători toată ziua.

**Ursache:** Rumänisch „femei adulte fără adăpost“ bedeutet erwachsene wohnungslose Frauen. fără (ohne) beschreibt die Zielgruppe, nicht die Abwesenheit einer Schlafleistung. Die maskierende Zielgruppenregex kennt diese Form mit femei nicht und behandelt die gesamte Leistungsaussage als negiert.

Technische Einordnung: Heuristik.


### Y5I7H

Anfrage: q05-ru – Мне нужно поесть сегодня вечером.

Erstdiagnose: `time_not_cited`; Auslöser `app\grounding.py:493` / `_validate_sentence`.

**Beobachteter Antworttext:**

> В Bahnhofsmission Leipzig можно взять бутерброд в будние дни с 09:00 до 18:00 или в воскресенье с 13:30 до 18:00. Diakonie Leipzig раздаёт еду (булочки или суп) по вторникам с 17:00 до 18:00.

**Ursache:** Die russische Formulierung für belegte Brötchen/Sandwiches wird vom geschlossenen Leistungswortschatz nicht erkannt. Sämtliche Zeiten sind in Bahnhofsmission-Öffnungsfakten vorhanden. Das NOT_CHECKED-Zeitgate verwirft die FACT-Formulierung vor der Literalprüfung.

Technische Einordnung: Heuristik.


### UMY7L

Anfrage: q17-ru – Я мужчина, мне 45 лет, мне нужен ночлег на сегодня.

Erstdiagnose: `price_service_mismatch`; Auslöser `app\grounding.py:439` / `_validate_sentence`.

**Beobachteter Antworttext:**

> Свяжись с Rücke по телефону 0341 1234502 или по e‑mail notunterbringung@leipzig.de. Они предоставляют ночлег за 5 € за ночь.

**Ursache:** Die Antwort sagt 5 € pro Nacht, der russische Leistungsfakt 5,00 € pro Nacht. price_services_match vergleicht den Betrag als String; 5 und 5,00 werden nicht als gleicher Geldbetrag erkannt. Die Leistungszuordnung ist vorhanden.

Technische Einordnung: Heuristik.


### VG4WU

Anfrage: q18-ru – Мне 17 лет, мне негде спать.

Erstdiagnose: `target_claim_contradicted`; Auslöser `app\grounding.py:502` / `_validate_sentence`.

**Beobachteter Antworttext:**

> Ты можешь обратиться в Kontakt‑ und Notschlafstelle für Jugendliche (Breite Straße 10, 04317 Leipzig) – они предоставляют ночлег для подростков от 14 до 17 лет ежедневно с 22:00 до 10:00; уточни наличие места по телефону 0341 9948 288 или e‑mail jugend‑notschlafstelle@leipzig.de. Если нужен экстренный приём, позвони в Jugendnotdienst (Ringstraße 4, 04209 Leipzig) – они принимают несовершеннолетних до 17 лет круглосуточно; уточни детали по телефону 0341 9948280 или 0172 576 86 48, e‑mail jnd@leipzig.de.

**Ursache:** Der Text nennt korrekt den Bereich von 14 bis 17 Jahren. Die RU-Regex erkennt nur „do 17 let“ (bis 17 Jahre) und behandelt dies als strikte Obergrenze 16 ohne erkannte Untergrenze. „ot 14 do 17 let“ wird nicht als vollständiger Bereich verarbeitet; so entsteht ein künstlicher Widerspruch zur Mindestgrenze 14.

Technische Einordnung: Heuristik.


### EXYK5

Anfrage: q18-ro – Am 17 ani și nu am unde dormi.

Erstdiagnose: `email_not_cited`; Auslöser `app\grounding.py:297` / `_validate_operational_tokens`.

**Beobachteter Antworttext:**

> Kontakt- und Notschlafstelle für Jugendliche oferă adăpost de noapte zilnic între 22:00 și 10:00 pentru tineri cu vârste între 14 și 17 ani. Pentru detalii și pentru a verifica disponibilitatea, sună la 0341 9948 288 sau scrie la jugend‑notschlafstelle@leipzig.de. Jugendnotdienst oferă găzduire de urgență pentru tineri cu vârste între 12 și 17 ani și este disponibil non‑stop; sună la 0341 9948280 pentru detalii.

**Ursache:** Wie GHDVB: U+2011 im lokalen Teil von jugend‑notschlafstelle@leipzig.de. Der Regex sieht nur notschlafstelle@leipzig.de. Die sichtbare Adresse hat eine tatsächliche Zeichenabweichung zum belegten Kontakt.

Technische Einordnung: Vertragsabweichung.


### E64BT

Anfrage: q22-pl – Gdzie mogę przebywać i ogrzać się w ciągu dnia?

Erstdiagnose: `formulator_invalid_language`; Auslöser `app\grounding.py:272` / `_validate_language`.

**Beobachteter Antworttext:**

> Tagestreff Oase w Nürnberger Str. 31 oferuje miejsce do przebywania, prysznic, śniadanie 09:00‑10:00 i obiad 12:00‑13:30 oraz jest otwarty od poniedziałku do piątku 08:00‑16:00 i w soboty 09:00‑14:00. Tagestreff Insel przy Plautstr. 18 zapewnia miejsce do przebywania, prysznic, pralkę i posiłki oraz jest otwarty od poniedziałku do piątku 08:00‑16:00 i w niedziele 09:00‑15:00.

**Ursache:** Ü in Nürnberger Str. 31 löst die deutsche Sprachsignatur in einer polnischen Antwort aus. Die verkürzte Anschrift wird nicht als vollständiger Evidence-Literalwert ausgeblendet.

Technische Einordnung: Heuristik.


### QNK4K

Anfrage: q08-en – I need clothes.

Erstdiagnose: `phone_not_exact`; Auslöser `app\grounding.py:313` / `_validate_operational_tokens`.

**Beobachteter Antworttext:**

> Contact Hilfebus at 0152 33661087 (call during deployment times daily 18:00‑23:00) or email hilfebus@suchtzentrum.de – they provide warm clothing, blankets and sleeping bags and can refer you to emergency overnight shelters.

**Ursache:** Hilfebusnummer und tägliche Einsatzzeiten stehen richtig im englischen Text. Der deutsche Klammerzusatz im PHONE-Fakt wird trotzdem als Teil der exakt wiederzugebenden Telefonnummer verlangt.

Technische Einordnung: Heuristik.


### 7QKUT

Anfrage: q12-ro – Am nevoie de consiliere socială.

Erstdiagnose: `formulator_invalid_fact`; Auslöser `app\grounding_references.py:37` / `resolve_offer_evidence`.

**Beobachteter Antworttext:**

> Bahnhofsmission Leipzig oferă consiliere socială în cazuri de urgență locativă și dificultăţi sociale; poţi suna la 0341 9683254 sau scrie la leipzig@bahnhofsmission.de.

**Ursache:** Die zitierte interne Fakt-ID endet auf ...a87b; vorhanden ist die E-Mail-Fakt-ID ...a87a für leipzig@bahnhofsmission.de. Der sichtbare Text ist R bewertet und die E-Mail stimmt, aber die interne Referenz wurde tatsächlich um ein Zeichen verändert.

Technische Einordnung: Vertragsabweichung.

Kommentar der Nutzerin: oder vorbei gehen! (direkt hbf)


### 74O77

Anfrage: q01-ru – Где можно поесть?

Erstdiagnose: `time_not_cited`; Auslöser `app\grounding.py:493` / `_validate_sentence`.

**Beobachteter Antworttext:**

> В Tagestreff Oase можно позавтракать с 09:00 до 10:00 и пообедать с 12:00 до 13:30.

**Ursache:** Frühstück 09:00–10:00 und Mittagessen 12:00–13:30 sind als russische SERVICE-Fakten vorhanden. Die verwendeten Verben für frühstücken/mittagessen ergeben keine erkannten Leistungskonzepte. Claimtyp FACT plus Uhrzeiten löst daher das verbleibende NOT_CHECKED-Zeitgate aus.

Technische Einordnung: Heuristik.


### 0K05H

Anfrage: q01-en – Where can I get something to eat?

Erstdiagnose: `formulator_invalid_language`; Auslöser `app\grounding.py:272` / `_validate_language`.

**Beobachteter Antworttext:**

> At the Bahnhofsmission Leipzig you can get coffee, tea, water and filled rolls (Mon‑Fri 09:00‑18:00, Sun 13:30‑18:00). Diakonie Leipzig distributes rolls or soup on Tuesdays from 17:00 to 18:00 at Goethestraße. Tagestreff Oase serves breakfast 09:00‑10:00 and lunch 12:00‑13:30 on weekdays.

**Ursache:** ß in Goethestraße löst die deutsche Sprachsignatur aus. Der Straßenteil steht in einem belegten längeren Standzeit-/Leistungswert, wird aber nicht isoliert ausgeblendet. Die übrige Prosa ist englisch.

Technische Einordnung: Heuristik.

## Folgerungen für eine mögliche Korrektur

1. Das versteckte NOT_CHECKED-Zeitgate gezielt ersetzen; echte Uhrzeitliteral-, Tages-/Leistungs- und Zeitfensterwidersprüche weiter prüfen.
2. Telefonnummer, Kontaktlabel und Einsatzbedingung getrennt behandeln; harmlose Typografie intern normalisieren, ohne Ziffern-/Angebotsbindung zu verlieren.
3. Sprachprüfung von belegten Orts-/Eigennamen abgrenzen und echte Sprachmischung gesondert prüfen. Ein deutscher Ortsname ist kein Sprachwechsel.
4. Alterszahlen von Kontaktdaten trennen; vollständige Altersintervalle verarbeiten. Zielgruppen-/Barrierefreiheitsqualifier nicht als Leistungsnegation lesen.
5. Policyanker für sprachlich gleichwertige Ablehnungen und Apostrophvarianten öffnen; ausdrückliche Ungewissheit nicht als Verfügbarkeitszusage werten.
6. Beträge numerisch und weiter leistungsgebunden vergleichen; belegte Kooperationsorte bei Angebotsnamen berücksichtigen.
7. Echte E-Mail-/Namens-/Referenzabweichungen und den Wasser-Primärvertrag bewusst behandeln; diese Schutzprüfungen nicht pauschal entfernen.

Diese Untersuchung implementiert keine dieser Folgerungen und startet keinen neuen Live-Lauf. Replaydaten einschließlich gespeicherter Fakten, Stackstellen und Zwischenwerte: `fehlablehnungen-30-replay.json`. Erläuterte Daten: `fehlablehnungen-30-befunde.json`.

Bewertungsdatei SHA-256: `78d1d729c88004748f62464d3a1f0092172bc74085b10adaa4fc13c68ab420e6`.
App-Quellmanifest SHA-256: `fea371e76945a2e09f44379ce6dc057cf526f0867287789d0674a3b49aee07a2`.
