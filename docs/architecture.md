# Architektur

## Systemgrenze

LENA besteht aktuell aus einer einzelnen FastAPI-Anwendung mit statischem
Frontend und dateibasierter Persistenz. Es gibt keine separate Datenbank und
keinen separaten Frontend-Build. Die Anwendung beantwortet Nutzerfragen niemals
durch einen Live-Aufruf des WFS.

```mermaid
flowchart LR
    U[Browser] -->|HTTP/JSON, Audio| A[FastAPI app/main.py]
    A --> S[QueryService]
    S --> R[Deterministische Kandidatenbegrenzung]
    S --> L[Blablador: Interpreter erforderlich, nachgelagerte Stufen mit Fallback]
    R --> Q[Freigegebene Runtime-Sicht]
    C[Active-Pointer prüfen] --> K[(data/wfs/releases/ID/offers.json)]
    K --> Q
    V[(schema-validierter Kurationskatalog)] --> Q
    E[(verifizierte paketierte Betreiberangebote)] --> Q
    S --> I[Übersetzungen]
    S --> X[Sessions]
    S --> G[Strukturierte Dialogpolitik]
    B[(Read-only Bootstrap im Wheel)] --> K
    D[(externe Datenwurzel)] --> C
    X --> T[(externe Runtimewurzel)]
    A --> O[(lokales Interaktions-JSONL)]
    A --> P[Speech-Dienste]
    A --> M[Kartendaten]
    W[Stadt Leipzig WFS] -->|genau ein Abruf je Check| Y[Validierung und Pending-Release]
    Y -->|Manifest- und Hashprüfung| C
    F[Wasserwerke-KML + Leipzig-Grenze] -->|nur Wartungspfad| Z[Trinkbrunnen-Validierung und Pending-Release]
    Z -->|explizite Aktivierung| FC[Trinkbrunnen-Pointer]
    FC --> Q
    TCSV[amtliche Toiletten-CSV] -->|nur Wartungspfad| J[Toiletten-Validierung und Pending-Release]
    J -->|explizite Aktivierung| TC[Toiletten-Pointer]
    TC --> Q
```

## Komponenten

`app/main.py` erzeugt die App, lädt die Wissensbasis, initialisiert Query- und
Speech-Dienste, startet optional die WFS-Hintergrundprüfung und registriert alle
Routen. Ein erfolgreicher automatischer Promote lädt die Wissensbasis neu.

Öffentliche Toiletten und feste Trinkwasserbrunnen bilden daneben je einen
eigenen Release- und Datentyp. Sie werden nicht zu sozialen Angeboten
konvertiert und durchlaufen keine sozialen Zielgruppenregeln. Brunnen außerhalb
Leipzigs und mobile Brunnen ohne verifizierten Zeitraum bleiben ausschließlich
in Quellrelease und Provenienz. `app/spatial.py` ist die einzige Definition von
Haversine-Luftlinie und EPSG:25833-Transformation; `LEIPZIG_HBF` bleibt darin
Standard- und Testwert des Referenzpunkts. `QueryService` löst den tatsächlich
verwendeten Ursprung einmal pro Prozess aus `Settings.hbf_latitude`/
`hbf_longitude` (`HBF_LATITUDE`/`HBF_LONGITUDE`, siehe
[Konfiguration](configuration.md#räumliche-auswahl)) auf und reicht ihn an
Kandidatenordnung, Toiletten und Trinkbrunnen weiter. Der
gemeinsame Runtime-Fingerprint bindet sozialen Release/Kuration sowie Toiletten-
und Trinkbrunnen-Release, Hash und Normalisierung; bei einer Änderung verwirft
die zentrale Sessionlogik den fachlichen Altverlauf.

`app/service.py` ist die fachliche Orchestrierung. Der Dienst löst Sessions auf,
führt zuerst den engen Preflight und danach den LLM-Interpreter aus und wertet
den validierten Risikostatus vor Scope, Fachdialog,
Kandidaten und Infrastruktur aus. `app/safety.py` begrenzt diese Entscheidung
deterministisch; Nummer und sichtbare Texte stammen aus versionierten lokalen
Policy- und I18n-Ressourcen. Reine bekannte Selbstbeschreibungsfragen dürfen
nach dem Preflight ohne Interpreter beantwortet werden, solange kein
Safety-Dialog offen ist. Zusätzlicher Text verhindert diesen Shortcut.

Bei `drinking_water` verbindet `app/infrastructure_results.py` die positive
soziale `CandidateDecision` mit der freigegebenen Brunnenprojektion. Fachliche
Pflichtresultate bleiben vorn; danach folgen ausschließlich HBF-Luftlinie und
stabile ID. Eine ausdrückliche Trinkbrunnenanfrage verwendet im belegten
Saisonfenster nur feste Brunnen. Der LLM-Selector wird mit dem redigierten Grund
`deterministic_spatial_ranking` umgangen. Höchstens drei Resultate erreichen
Evidence und Karten, alle zulässigen Geometrien erreichen die Karte. Ein
erkanntes Stadtteilfeld bleibt für dieses Ranking wirkungslos.

Zeitgebundene soziale Wasserleistungen müssen vor dieser räumlichen Projektion
positiv zum angefragten Zeitbezug oder, ohne Zeitangabe, zur aktuellen
Europe/Berlin-Zeit passen. So kann der mobile Hilfebus nur während seiner
belegten Sonntagsstandzeit als Wasserort am Hauptbahnhof erscheinen. In
allgemeinen Hilfefällen bleibt er dagegen ein telefonischer `referral_contact`
mit den belegten mobilen Einsatzzeiten; seine Organisationsadresse wird nicht
als Nutzerstandort oder Marker projiziert.

Dasselbe Prinzip gilt für mobile Touren ohne verifizierte Einzelkoordinaten:
TiMMi ToHelp bleibt ein ServiceOffer mit einer kuratierten Donnerstagsroute.
Standzeiten und Erkennungshinweis gelangen aus der gemeinsamen Runtime-KB in
Evidence, Karte und TTS; die alte WFS-Punktgeometrie wird weder als aktueller
Tourstopp noch für eine Entfernungswertung verwendet.

`app/curation.py` validiert Organisationen, Standorte, getrennte
Leistungsangebote, Organisations- und Angebotsaliase, Quellenreferenzen und
Kurationsentscheidungen. Der Katalog ist an Release-ID und Hash eines
unveränderlichen normalisierten WFS-Stands gebunden. Erst seine Projektion wird
von Aliasauflösung, Kandidatenbegrenzung, Formulator, Karten und Map-Markern gemeinsam verwendet.
Ein angebotseigener Anzeigename hat dabei Vorrang vor dem Anzeigenamen der
Organisation. So heißt der Tagestreff mit ID 10 „Leipziger Oase“, während die
gemeinsame Organisation und ihr Streetwork-Angebot ID 14 weiterhin „Diakonie
Leipzig“ heißen. Der vollständige WFS-Quellenname wird dadurch nicht verändert.
Ein abweichender aktiver WFS-Stand wird in Health als ausstehende Quelländerung
gemeldet und nicht ungeprüft in die Runtime-Sicht übernommen.

Zwei Jugendnotangebote des VKKJ stammen nicht aus dem WFS. Sie liegen deshalb
als eigene, schema-validierte Betreiberquelle in
`app/resources/bootstrap/official/verified_offers.json`. Der Loader prüft
Quellenreferenzen, Positivschema und Dateihash, verbindet die Records erst
danach mit dem exakt gebundenen WFS-Stand und erzeugt weiterhin genau eine
kuratierte Runtime-Projektion. Der Kurationskatalog bindet auch diesen Hash;
der gemeinsame Session-Fingerprint ändert sich bei einer Änderung der
Betreiberquelle. Ein fehlender, ungültiger oder abweichender Betreiberstand
führt zu einem kontrollierten Fehler, niemals zu einer Teilprojektion.
Die im Betreiber-HTML strukturiert veröffentlichten WGS84-Punkte werden mit
explizitem CRS in derselben Quelle gespeichert. `app/maps.py` akzeptiert dafür
nur das bekannte CRS und Punkte im Leipziger Prüfrahmen; dadurch erhalten beide
VKKJ-Angebote Informationskarten und Marker, ohne einen Geocoder aufzurufen.

`app/candidate_contract.py` definiert den strikten, versionierten Vertrag der
Kandidatenstufe. `app/candidates.py` wendet ausschließlich positiv kuratierte
Leistungen, Ortstypen, Zielgruppen-, Zugangs-, Verweis-, Zeit- und
Prioritätsmerkmale an. Das Ergebnis trennt `direct_service`, `referral_contact`
und `conditional_candidate`, enthält maschinenlesbare Ein- und Ausschlussgründe
und dokumentiert Konflikte mit dem schwächeren UI-Hinweis. Bedingte Kandidaten
werden weder an Formulator noch Karten weitergegeben. `app/retrieval.py` enthält
noch lexikalische Hilfsfunktionen und isolierte Legacy-Tests, ist aber nicht mehr
der primäre Kandidatenpfad. Die früheren namens- beziehungsweise
`source_index`-gebundenen Auswahlmodule `app/offer_roles.py` und
`app/temporal.py` sind entfernt.

`app/interpreter.py` definiert den versionierten ersten Modellvertrag. Der
Interpreter sieht keinen Angebotsindex und keine Angebots- oder Quellen-IDs. Er
liefert ausschließlich Bedarf, Scope, Eingabesprache, ausdrücklich genannte
Fakten, getrennte unsichere Hinweise, potenziell relevante Informationslücken
und das dreiwertige Signal `acute_risk_status`. Modellantworten müssen reines
JSON sein und werden mit verbotenen Zusatzfeldern, strikten Typen, begrenzten
Texten und semantischen Querverträgen validiert. Alias-Hinweise bestehen nur aus
Aliastext, Aliasart und Mehrdeutigkeit.

`app/dialogue.py` ersetzt den früheren booleschen Klärungsmarker durch genau
einen schema-validierten Dialogzustand pro Session. Er enthält nur Dialogart,
angefragte Felder, begrenzte ausdrückliche Fakten, stabile Choice-Werte,
Versuchszahl, Ablaufzeit und Runtime-Fingerprint. `app/dialogue_flow.py` bildet
Buttons deterministisch auf Bedarf oder ausdrückliche Fakten ab; Freitext und
STT-Transkripte laufen mit einem minimalen offenen Dialogkontext erneut durch
den Interpreter. Beide Wege verwenden danach denselben `CandidateSelector`.
Die explizite Altersgruppe trennt `under_18` von den Erwachsenenbereichen
18–26 und ab 27, ohne ein numerisches Alter zu erfinden.

Die aktive Politik kennt Schlafzielgruppe,
A1/Schoppi-Leistungsart, Mobile/Kübel-Ort, allgemeinen Bedarf und den
Safety-Dialog `acute_risk_confirmation` für unklare Risikoklassifikationen. Ein
enger eindeutiger Preflight-Treffer stoppt dagegen unmittelbar ohne Dialog.
Fachliche Dialoge schließen nach einer verwertbaren Antwort ab. Bei „Frau“ ohne
Alter folgt keine weitere Pflichtfrage: Scharni wird ausdrücklich als Angebot
für volljährige Frauen bedingt genannt, Rücke bleibt der Erstkontakt. Der alte
`sleep_age`-Zustand bleibt für bestehende Sessions lesbar, wird aber nicht neu
geöffnet. Der allgemeine Bedarfsdialog öffnet sich bei fehlender konkreter
Leistungsangabe sowohl bei `need=general_help` als auch bei `need=unknown` (AP10: unklare, aber
möglicherweise relevante Anfrage) — beide werden auf denselben
Originating-Need normalisiert. Bleibt die Lage unklar, stammen Telefon und
Zeiten des Hilfebus ausschließlich aus dem kuratierten Runtime-Datensatz.
Akutrisiko oder Out-of-Scope schließen den Dialog vorher ohne Hilfebus oder
Angebote.

Für Schlafbedarf gilt keine U27-Priorität mehr. Bei 14 bis 17 Jahren ist die
Kontakt- und Notschlafstelle für Jugendliche der direkte erste Dienst und der
Jugendnotdienst ein ergänzender Schutz- und Vermittlungskontakt. Bei 12 bis 13
Jahren wird nur der Jugendnotdienst als belegter erster Kontakt verwendet; bei
`under_18` ohne Zahl bleibt die Notschlafstelle bis zur Altersklärung bedingt.
Ein ausdrücklicher Schutz- oder Krisenbedarf priorisiert den Jugendnotdienst.
Ab 18 führt der Schlafpfad nach den kuratierten Erwachsenenregeln zu Rücke
beziehungsweise bei ausdrücklich bekannter weiblicher Zielperson zu Scharni.
Jugendtreffs und Jugendstreetwork bis einschließlich 26 werden unabhängig
davon nur durch ausdrücklichen Jugendbedarf oder einen exakten Alias aktiviert;
ein Alter allein genügt nicht.

Ein Schlafsack allein aktiviert diesen Schlafplatzpfad nicht. Er wird als
Sachleistung (`general_help` plus `clothing`) interpretiert und führt zum
kuratierten Hilfebus-Verweis, dessen Leistungsbeschreibung Schlafsäcke belegt.
Nur eine zusätzlich ausdrücklich verlangte Übernachtung hält die Anfrage im
Schlafpfad. Scharni erhält seinen Kartenpunkt aus der kuratierten,
quellenreferenzierten Geometrie der aktuellen Anschrift; die alte WFS-Geometrie
der früheren Anschrift wird nicht wiederverwendet.

Bei einem engen eindeutigen Preflight-Treffer oder
`acute_risk_status=detected` beendet `QueryService` den normalen Pfad
unmittelbar und gibt den zentralen sprachabhängigen 112-Text ohne Karten aus.
Bei `uncertain` öffnet es den fingerprintgebundenen Safety-Dialog. Ja und
Unsicher führen deterministisch zu 112; nur ein validierter Modellstatus plus
eine kontrolliert ausdrückliche Verneinung öffnet den strukturierten
ursprünglichen Bedarf wieder. Das LLM erzeugt weder Nummer, Text noch
Eskalationsziel und kann den Abbruch nicht allein aufheben.

Nach der Interpretation erzeugt genau eine deterministische Kandidatenkomponente
die zulässige Menge. Ihr Vertrag Version 2 trennt verbindliche,
auswählbare, bedingte und ausgeschlossene Kandidaten. Fachliche Eignung,
Zugang, dokumentierte Zeitbedingungen und kuratierte Prioritäten werden vor
jedem weiteren Modellaufruf geprüft. Mandatory-Kandidaten wie kuratierte erste
Verweise verlassen diese Stufe bereits in bindender Reihenfolge.

`app/llm_selection.py` baut ausschließlich aus `selectable_candidates` einen
kompakten Positivlistenindex. Er enthält weder Kontakte, Adressen, Rohdaten,
Reviewnotizen noch bedingte oder ausgeschlossene Angebote. Ab zwei tatsächlich
auswählbaren Kandidaten darf `BlabladorProvider.select_candidates()` eine
Teilmenge nennen. Die gesamte JSON-Antwort wird gegen exakt diesen aktuellen
Index validiert; fremde, doppelte oder zu viele IDs verwerfen die vollständige
Modellantwort. Mandatory-Kandidaten werden anschließend deterministisch
vorangestellt und die Modellmenge in der stabilen Candidate-Reihenfolge
ausgegeben. Bei einem oder ausschließlich mandatory Kandidaten entfällt der
zusätzliche Aufruf mit maschinenlesbarem Bypassgrund.

Selectorprompt 3 fordert innerhalb der bereits zulässigen Menge mehrere
komplementäre oder gleich passende Optionen, wenn sie einen konkreten Nutzen
haben und die Ergebnisgrenze dies erlaubt. Bei ausdrücklichem Zeitbezug haben
Kandidaten mit strukturiert passendem Zeitstatus Vorrang; dadurch wird keine
neue Zeit- oder Eignungsentscheidung an das Modell delegiert.

Der alte Adapter `Interpreterbedarf → Category → Retrieval`, der frühere
ID-selektierende LLM-Router, der ungenutzte Kandidatenindex und die direkte
erste-vier-Übergabe sind nicht mehr aktiv. `app/formulation.py` projiziert die
höchstens drei sichtbaren finalen Runtime-Angebote in den Evidence-Vertrag 4.
Er enthält
nur freigegebene Positivlistenfelder, Kandidatenrollen, opake Faktenreferenzen
und bindende Policies. Conditional-, Excluded- und Sozialamt-Angebote sowie
WFS-Rohfelder, Reviewnotizen und technische Provenienz gelangen nicht hinein.

Die aktuelle Nutzerfrage wird separat als nicht vertrauenswürdiger Kontext in
`current_query` übergeben, auch im Trinkwasserpfad. Sie steuert die Relevanz der
Antwort, liefert aber keine Angebotsfakten und ändert nicht die Auswahl.

Der Formulatorvertrag 3 erlaubt ein bis drei kurze Sätze. Promptversion 20
priorisiert die konkrete Nutzerfrage: etwa belegte Kosten bei einer Kostenfrage
oder belegte Zeiten bei einer Zeitfrage. Bei kurzen Folgeantworten dient der
aufgelöste Bedarf als Kontext. Fehlende Details dürfen nicht ergänzt werden;
anwendbare Unsicherheitspolicies und belegte nächste Schritte bleiben möglich.
Der Prompt verlangt für normale angebotsbezogene Antworten zwei oder drei natürliche,
rollenrichtige Sätze ohne festes `Nutze ...`-Muster. Das erste Angebot und der
wichtigste nächste Schritt stehen zuerst. Sind mehrere finale Angebote
komplementär hilfreich, kann die Antwort bis zu drei davon in der bereits
deterministisch hergestellten Evidence-Reihenfolge nennen; jeder Satz bleibt an
genau ein Angebot gebunden; belegen darf ihn jeder Fakt im übergebenen
Evidence-Paket dieses ausgewählten Angebots. Nur der eng begrenzte
Prompt-Injection-Pfad verwendet weiterhin einen festen sicheren Handlungssatz.
Der sichtbare Antworttext verweist nicht auf technische UI-Container wie
Ergebniskarten oder die Kartenansicht. Wo eine kurze Orientierung nötig ist,
verwendet die lokalisierte Fassung sinngemäß „Mehr Infos stehen unten“.
Tatsächliche Kartenfunktionen und belegte Angaben wie Kartenzahlung bleiben
davon unberührt.
Jeder Satz nennt Claimtyp, Angebots- und Faktenreferenzen oder einen erlaubten
Policybaustein; freier Text außerhalb des JSON-Vertrags existiert nicht.
`app/grounding.py` validiert die Antwort atomar gegen genau das Evidence-Paket:
Fakt-Angebot-Zuordnung, operative Zahlen, Adressen, Kontakte, URLs, Zeiten,
Zielskript, Längen, interne IDs und Kartenbindung. Mandatory-Karten und die
deterministische Reihenfolge werden serverseitig wiederhergestellt.
Kapazitäts-, Echtzeit- und garantierte Aufnahmebehauptungen werden verworfen.

### Antwortweiter, angebotsgebundener Groundingvertrag

`app/grounding_references.py` löst Referenzen zuerst innerhalb des ausgewählten
Evidence-Pakets auf. Exakte IDs haben Vorrang; sonst sind ausschließlich
ASCII-Ganzzahlvarianten mit führenden Nullen bei genau einem passenden Angebot
zulässig. `07` kann damit `7` bedeuten, nicht aber bei einer Kollision mit
mehreren ausgewählten IDs. Dezimal- und Namensraum-IDs werden nicht numerisch
umgedeutet. Unbekannte/fremde Fakt-IDs bleiben Fehler. Die Modellantwort wird
nicht verändert; eine interne Kopie trägt kanonische Angebots- und Karten-IDs.

Der Prüfumfang umfasst alle angebotenen Fakten desselben ausgewählten Angebots,
nicht die vollständige Wissensbasis und nicht andere ausgewählte Angebote.
Geprüft wird gegen die **Werte** dieser
Fakten, nicht gegen ihre Typen: `app/grounding_claims.py` erkennt mit einem
geschlossenen mehrsprachigen Stammwortschatz, welche Leistungs- und
Zielgruppenkonzepte der sichtbare Satz nennt, und sucht sie in den bereitgestellten
Werten. Eine bereitgestellte lokalisierte Beschreibung kann damit eine
Zielgruppenaussage belegen; eine zusätzliche typisierte Referenz ist dann nicht
zwingend. Umgekehrt belegt das bloße Vorhandensein eines Fakts zulässigen Typs
nichts mehr.

Die Kandidatenrolle beschreibt, warum ein Angebot ausgewählt wurde, nicht seinen
Leistungsumfang. Ein `referral_contact` kann eigene Leistungen haben — die
allgemeine Schlafplatzvermittlung ist genau so eingestuft. Ein Satz mit
`claim_type=service` ist deshalb nicht mehr allein wegen des Enumwerts falsch;
entscheidend sind die belegte Aussage und ihre Einschränkungen. Unverändert
unzulässig bleiben in jeder Rolle unbelegte Aufnahme-, Eignungs- und
Verfügbarkeitszusagen: aus einer belegten Leistungsbeschreibung folgt weder,
dass die fragende Person aufgenommen wird, noch dass das Angebot für sie
geeignet ist, noch dass die Leistung gerade jetzt verfügbar ist. Nennt ein Satz
eine Leistung mit dokumentiertem Zeitfenster, darf er keine Zeit einer anderen
Leistung dafür ausgeben.

Die Konzeptprüfung unterscheidet vier Ergebnisse.
*Belegt* wird freigegeben, auch wenn die passende Faktreferenz ausgelassen wurde.
*Widersprüchlich* — eine Aussage, die eine kuratierte Beschränkung des Angebots
ausschließt — wird verworfen. *Nicht entscheidbar* wird ebenfalls verworfen,
aber getrennt diagnostiziert: die Antwort wird damit nicht als nachweislich
unwahr bezeichnet, sondern nur nicht ungeprüft freigegeben. Beide Fälle führen
in denselben unveränderten begrenzten Retry beziehungsweise Templatefallback.
*Nicht geprüft* (`NOT_CHECKED`) bedeutet dagegen, dass kein bekanntes Konzept
erkannt wurde; es ist kein positiver Beleg. Ein `service`-Satz ohne erkanntes
Leistungs- oder belegtes Zielgruppenkonzept braucht einen wörtlichen bereitgestellten
Leistungswert, sonst folgt `service_fact_missing`. Kontaktanweisungen und
operative Fakten bleiben mit ihren eigenen Prüfungen möglich.

Referenzqualität und inhaltliche Prüfung bleiben getrennt: intern werden
deklarierte Fakt-IDs, verfügbare Fakt-IDs und eindeutige ID-Normalisierungen
erfasst. Verfügbare IDs sind der Prüfumfang, keine nachträglich erfundenen
Modellzitate und kein Nachweis, dass jeder Fakt semantisch benötigt wurde.
Die öffentliche QueryResponse und das Interaktionsprotokoll erhalten keine
neuen Freitextfelder. Lokale synthetische Evaluationsberichte enthalten die
Referenzbewertung zusätzlich zum unveränderten technischen Gate.

Eurobeträge werden außerdem begrenzt an erkannte Leistungsbegriffe gebunden:
ein Wäschepreis darf keinen Übernachtungspreis belegen. Die Prüfung verwendet
den bestehenden mehrsprachigen Leistungswortschatz und ergänzende Wasch-/
Wäschebegriffe. Unbekannte Satzformen, andere Währungen oder nicht erkannte
Relationen sind damit nicht allgemein semantisch verifiziert.

`app/grounding_constraints.py` prüft erkannte Altersrelationen gegen die
typisierten Angebotsgrenzen (auch ohne deren Zitat). Bei leistungsgebundenen
Zeitangaben werden Tagesumfang und Reihenfolge der Uhrzeiten zusammen geprüft;
Fenster werden nicht durch Zusammenwerfen ihrer Zahlen kombiniert. Persönliche
Erhaltzusagen brauchen die bereitgestellte Bedingung vollständig sichtbar mit Tag und
Zeit; sie darf in einem anderen Satz über dasselbe Angebot stehen.
Allgemeine Leistungsbeschreibungen dürfen weiterhin ohne Zeitangabe
stehen. Eine persönliche Schlafplatzzusage braucht kein Wort wie „garantiert“,
um unbelegt zu sein.

Vor der Satzgrenzen- und Sprachprüfung werden vollständig übereinstimmende
belegte Zeitliterale intern maskiert. Bei `opening_time` und `stand_time`
darf dabei der führende Darstellungsmarker `> ` des Evidence-Werts fehlen;
der verbleibende Zeit-/Ortstext muss weiterhin vollständig übereinstimmen.
So zählt beispielsweise das belegte `18:30 ч. Hauptbahnhof` nicht wegen
des russischen Stundenkürzels als zusätzlicher Satz. Die sichtbare Antwort
und die anschließenden Fakt-, Referenz- und Groundingprüfungen bleiben
unverändert. Es gibt keine globale Ausnahme für Stundenkürzel: Zusätzliche
Sätze außerhalb des passenden Literals bleiben sichtbar. Andere Marker,
unbelegte Kürzel oder nur teilweise passende Zeitangaben werden durch diese
Regel nicht normalisiert. Regression: `tests/test_grounding_schedule_literals.py`.

Für die Leistungsprüfung wird eine vollständig belegte Zielgruppenphrase wie
„Menschen ohne Krankenversicherung“ intern ausgeblendet: Sie verneint weder
die Beratung noch belegt sie eine angebotene Krankenversicherung. Dieselbe
Normalisierung gilt für Aussage und zitierte Evidenz in DE/EN/PL/RO/RU.
Nur vollständig übereinstimmende Phrasen der begrenzten Sprachmuster werden
ausgeblendet. Folgt innerhalb desselben Satzteils eine zweite Leistung, wird
die Zielgruppe nur dann vor einer sprachpassenden Konjunktion abgegrenzt,
wenn der gesamte nachfolgende Text einem separat bereitgestellten, nicht negierten
Leistungswert entspricht. Beim Vergleich dieses Werts werden führende
`>`-Listenmarker und abschließende Satzzeichen entfernt. Die Leistungsphrase
bleibt sichtbar und durchläuft die normalen Grounding-Prüfungen.
Eine Konjunktion allein oder ein nicht belegter beziehungsweise nur teilweise
passender Leistungstext bildet keine Grenze. Vollständig belegte Zielgruppen
mit mehreren fehlenden Dingen werden weiterhin als Ganzes ausgeblendet;
Verneinungen außerhalb bleiben sichtbar. Diese Regel gilt für DE/EN/PL/RO/RU,
ist keine allgemeine semantische Analyse und erweitert nicht die vorhandene
Negationswortliste. Die Regressionen in `tests/test_grounding_audience.py`
prüfen sowohl die Abgrenzung als auch den echten Validator einschließlich
einer gespeicherten dreisätzigen CABL-Ausgabe.

Erkannte Verneinungen belegen keine positive Leistung und umgekehrt. Freie
negative Paraphrasen werden konservativ nicht freigegeben; ein vollständig
zitierter negativer Fakt darf wörtlich wiedergegeben werden. Ein unbekannter
aktueller Status ist nur bei vollständiger Wiedergabe eines zitierten
Notizwertes eine Ausnahme vom Gegenwartswächter. Unabhängige unbekannte Details
erlauben keine aktuelle Leistungszusage.

### Zwei lexikalische Regeln und ihre Grenzen

Zwei ältere Regeln entschieden lexikalisch über etwas, das lexikalisch nicht
immer entscheidbar ist; beide sind auf ihren eindeutigen Bereich zurückgeführt.

Die deutsche **Anredeprüfung** wertet eine großgeschriebene Höflichkeitsform
mitten im Satz weiterhin als Verstoß: dort schreibt das Deutsche weder „sie"
noch „ihr" groß. Am Satzanfang wird jedes Wort großgeschrieben, dort ist „Sie
bieten Übernachtungen an" nicht von der Aussage über den Träger zu
unterscheiden. Ein satzinitiales „Sie"/„Ihr" gilt deshalb nur dann als
Höflichkeitsform, wenn ihm kein Satz vorausgeht, auf den es sich beziehen
könnte. Grenze: eine echte Höflichkeitsform am Anfang eines Folgesatzes wird
nicht erkannt.

Die **Namensbindung** blendet E-Mail-Adressen und URLs aus, bevor sie nach
Eigennamen sucht. In `uvo@cab-leipzig.de` steckt der Name `UVO`, aber die
Adresse ist keine Namensnennung; `@` ist kein Wortzeichen, weshalb die
Wortgrenze allein nicht genügte. E-Mails und URLs haben eigene exakte
Prüfungen, es geht also keine Zusicherung verloren. Die Forderung, einen
zitierten Namensfakt unverändert auszuschreiben, gilt außerdem antwortweit je
Angebot statt je Satz: ein Satz darf den Namen mitzitieren, um Telefon oder
E-Mail zuzuordnen, ohne ihn zu wiederholen. Gebeugte oder sonst veränderte
Schreibweisen bleiben unzulässig. Grenze: steht der Name in einem Satz exakt und
in einem anderen gebeugt, erkennt die satzweise Prüfung die Beugung nur, solange
sie als Namensnennung erkennbar bleibt.

**Grenze.** Diese Prüfung ist und bleibt keine vollständige semantische oder
linguistische Qualitätsbewertung. Der Validator arbeitet ohne zusätzliche
Modellstufe und kann freie mehrsprachige Paraphrasen nicht vollständig auf
Bedeutung prüfen. Abgesichert sind konkret prüfbare Aussagen: benannte
Leistungs- und Zielgruppenkonzepte gegen zitierte Werte, Widersprüche gegen
typisierte kuratierte Beschränkungen, Zusagemuster und leistungsgebundene
Zeitfenster. Eine Formulierung außerhalb dieses geschlossenen Wortschatzes wird
nicht erkannt (`NOT_CHECKED`), nicht automatisch als wahr oder falsch bewertet.
Die strengere Behandlung unbeurteilter `service`-Sätze ist keine allgemeine
semantische Garantie: zusätzliche unbekannte Aussagen neben einem erkannten
Konzept, falsch deklarierte Claimtypen, freie Negationsbezüge und nicht erkannte
Alters-/Zeitparaphrasen können weiterhin außerhalb der Prüfabdeckung liegen.
Umgekehrt kann ein
lexikalisch passender Treffer inhaltlich danebenliegen (dokumentiert am
Beispiel „minor injuries"). Eine manuelle Evaluation bleibt deshalb erforderlich.

Scheitert der Selector technisch, verwendet die Anfrage nur die stabile
deterministische CandidateDecision und den Templatepfad; der gleiche Provider
wird nicht unmittelbar nochmals als Formulator aufgerufen. Jeder
Formulatorfehler verwirft die vollständige Modellantwort. Bei Parsing- oder
Groundingfehlern ist innerhalb des Restbudgets ein neuer Versuch erlaubt; bei
Transportfehlern nicht. Liegt eine geschlossene Groundingdiagnose vor, erhält
dieser zweite Versuch einen festen Korrekturhinweis, niemals den verworfenen
Text. Evidence und Validator bleiben unverändert. Der Hinweis korrigiert keine
Antwort automatisch und ist kein Beleg für semantische Vollständigkeit;
[bekannte Grenzen und Diagnoseverfahren](live-provider-evaluation.md#prompt-17-und-begrenztes-korrekturfeedback)
bleiben ausdrücklich dokumentiert. Bleibt die Antwort ungültig, verwendet die Anwendung
die bereits finalen Angebote im lokalisierten Templatefallback.

Interpreter, Selector und Formulator verwenden denselben asynchronen
HTTPX-Transport, aber getrennte Stufengrenzen von standardmäßig 15, 10 und 30
Sekunden. Eine requestlokale monotone Budgetinstanz begrenzt ihre kumulierte
tatsächliche Providerwartezeit zusätzlich auf standardmäßig 45 Sekunden. Jede
Stufe erhält `min(Stufengrenze, Restbudget)`; bei erschöpftem Budget startet
keine weitere Modellstufe. Deterministische Verarbeitung wird nicht als externe
LLM-Wartezeit gezählt. HTTPX begrenzt zusätzlich seine Transportphasen.
Transportfehler werden nicht automatisch wiederholt. Scheitert bereits der
Interpreter durch Timeout, HTTP-/JSON-/Schema-/Vertragsfehler, Budget oder
Nichtverfügbarkeit, endet die Anfrage fail-closed mit einem technischen Text
und bedingtem 112-Hinweis sowie gegebenenfalls der lokalen Hilfebus-Kontaktkarte
ohne Marker. Kandidaten, Infrastruktur, Selector und Formulator
laufen nicht; eine lexikalische Fachklassifikation wird nicht verwendet.

Schemaverwerfungen des Interpreters tragen intern `schema_issues`: höchstens
acht Einträge mit `field_path` und einem geschlossenen `error_type`.
`app/providers/diagnostics.py` projiziert ausschließlich erlaubte Vertragsfelder;
Listenpositionen erscheinen als `*`, unbekannte Feldnamen als `<extra>` und
modellweite Konsistenzfehler unter `$`. Bekannte semantische Fehler erhalten
Codes wie `out_of_scope_need_mismatch` oder `clarification_mismatch`.
Eingabewerte, Rohantworten, freie Fehlermeldungen, Pydantic-Kontext und URLs
werden nicht in diese Diagnose übernommen. Sie steht im Logereignis
`query.interpreter.schema_invalid` und in lokalen Evaluationsberichten, nicht
im öffentlichen Antwortvertrag oder als neues Interaktionsprotokollfeld.
Promptversion `11` beschreibt die bestehende Kopplung
`scope_status=out_of_scope` → `need=unknown` ausdrücklich; Vertragversion `4`
und Validatorsemantik bleiben unverändert. Diese Vorgabe ist keine tolerante
Reparatur ungültiger Antworten und löst keinen Interpreter-Retry aus.

`app/resources.py` löst statische Paketressourcen und den rein lesbaren
Bootstrap unabhängig vom aktuellen Arbeitsverzeichnis auf. Im Source-Checkout
bleiben `data/` und `runtime/` kompatible Standards. Eine Wheel-Installation
verwendet externe, konfigurierbare Daten- und Runtimewurzeln und schreibt nie in
`site-packages`. Der Bootstrap ist der einzige paketierte Startstand; ein
externer valider Active-Pointer hat Vorrang, Pending-Releases niemals.

`app/version.py` liest die kanonische Version aus den Paketmetadaten. Wheel,
FastAPI, CLI und Interaktionsprotokoll verwenden diesen Wert; nur ein nicht
installierter Source-Baum ohne Metadaten erhält die eindeutige Kennzeichnung
`0+unknown`. Interaktions- und WFS-Schema-Versionen bleiben getrennte Verträge.

`app/wfs_sync.py` validiert eine vollständige GeoJSON-FeatureCollection,
normalisiert Features und berechnet stabile Hashes. `app/wfs_releases.py`
schreibt daraus einen unveränderlichen Ordner mit `offers.json`,
`snapshot.geojson`, `diff.json` und typisiertem `manifest.json`. Promotion lädt
nicht erneut vom WFS, sondern prüft alle gespeicherten Bytes und ersetzt zuletzt
genau den kleinen Pointer `data/wfs/active_release.json` atomar. Rollback nutzt
denselben validierten Pointerwechsel. `app/kb_loader.py` prüft Pointer und Releasebindung beim
Laden; solange noch kein
Pointer existiert, diagnostiziert `app/kb_loader.py` diesen Zustand getrennt
vom Runtime-Bestand. Die Nutzeranwendung lädt ausschließlich die kuratierte
Projektion: zuerst den exakt kataloggebundenen und vollständig verifizierten
lokalen Release, danach den manifest- und hashverifizierten Paket-Bootstrap.
Ungefilterte normalisierte Daten sind nur über die ausdrückliche
Wartungsfunktion `load_normalized_source_release()` erreichbar.

`app/i18n.py` führt deutsche Quelldaten und integritätsgeprüfte
gespeicherte Übersetzungen zu Karten zusammen. Es liest einen vorhandenen externen Store oder
sonst den paketierten Bootstrap. `app/translate_offers.py` schreibt ausschließlich
in die externe Datenwurzel und aktualisiert den Store explizit als
Wartungsschritt, nicht während einer Nutzeranfrage.

`app/sessions.py` speichert eine begrenzte Anzahl kurzer Frage-/Antwortpaare in
`runtime/sessions.json`. Ein nach absolutem Pfad geteilter `RLock` umfasst im
Einzelprozess den gesamten Lese-Bereinigungs-Änderungs-Schreib-Zyklus. Writes
werden als eindeutige temporäre Datei im Zielordner geschrieben, mit `fsync`
gesichert und per `os.replace()` atomar aktiviert. TTL- und Kapazitätsbereinigung
laufen opportunistisch bei Sessionzugriffen. Beschädigtes JSON wird unter
`runtime/` als `sessions.corrupt.<Zeit>.<UUID>.json` quarantänisiert; ein
Persistenzfehler verhindert die fachliche Antwort nicht. Vor Verwendung eines
Verlaufs vergleicht der Store dessen Runtime-Fingerabdruck aus Quellenrelease,
Quellenhash und Kurationsstand. Legacy- und abweichende Sessions werden fachlich
zurückgesetzt und erhalten eine neue Session-ID. Ein reiner Sprachwechsel
aktualisiert dagegen die Antwortsprache und erhält einen gültigen Dialog.
Dialogantworten werden unter demselben Lock einmalig beansprucht; parallele,
abgelaufene, fremde oder manipulierte Antworten werden redigiert abgewiesen.
Diese Mechanismen
koordinieren keine mehreren Prozesse oder Uvicorn-Worker. `app/maps.py`
transformiert WFS-Koordinaten aus
EPSG:25833 nach WGS84 und erstellt Ziele relativ zum Leipziger Hauptbahnhof.
`app/speech.py` kapselt externe Speech-Endpunkte und `edge-tts`.
Vor der Synthese ersetzt der Adapter das eigenständige Token `112`
sprachabhängig durch einzeln gesprochene Ziffern. Die visuelle API-Antwort bleibt
unverändert. Der TTS-Endpunkt verlangt zusätzlich die aktive Session-ID und
akzeptiert nur die letzte Antwort sowie serverseitig freigegebene Angebots-,
Marker- und Rückfragetexte dieses Turns in derselben Sprache. Faktenreferenzen, Policy-IDs, Fehlercodes oder clientseitig veränderte
Texte können dadurch nicht als reguläre Antwort synthetisiert werden.

STT und TTS besitzen jeweils eine konfigurierbare Gesamtgrenze von standardmäßig
45 Sekunden. OpenAI-kompatible Aufrufe erhalten zusätzlich denselben HTTPX-
Transporttimeout. Bei Edge-TTS bricht Cancellation den lokalen asynchronen
Stream ab; LENA kann nicht garantieren, dass dadurch bereits begonnene Arbeit
des externen Dienstes beendet wird. Die Adapter erzeugen keine temporären
Audiodateien, sondern halten Request und Ergebnis im Speicher.

`app/interactions.py` trennt das lokale Forschungsprotokoll vom technischen
Logging. Der HTTP-Adapter schreibt nach dem finalen `QueryService`-Ergebnis
genau eine validierte UTF-8-JSONL-Zeile nach
`runtime/logs/interactions.jsonl`. Sie enthält die tatsächlich verarbeitete
Anfrage, die tatsächlich sichtbare Antwort, kurzlebige Session-ID, Sprache,
Eingabemodus, Antwortpfad, Quellen-IDs, Kandidatenzahl und redigierten
Kandidatenstatus sowie Safety- und
Fallbackstatus und – bei pointerbasierten WFS-Daten – die tatsächlich für die
Antwort geladene `data_release_id`. Das Interaktionsschema besitzt deshalb
Version 11. Safety-Eingaben werden vor Session- und JSONL-Persistenz redigiert;
gespeichert werden nur Status, Pfad, Dialogergebnis, Fallback und Sprache. Ein-
und Ausschlusslisten, Gefahrenfreitext, Diagnose, Score, Fakten, Reason Codes und freie
Modellüberlegungen werden nicht zusätzlich persistiert. Eine kleine Sperre schützt parallele Threads desselben
Prozesses; Schreibfehler werden redigiert geloggt und verändern die Antwort
nicht. Mehrprozesssynchronisierung, Rotation und ein Forschungsdaten-Backend
sind nicht implementiert.

Das technische Logging verwendet stabile Ereignisnamen für HTTP-Laufzeiten,
Interpreter, Kandidatenbegrenzung, Formulator, Fallback, Akutgefahr, Speech, Sessions, WFS und
Interaktions-Schreibfehler. Diese Logs enthalten absichtlich keine vollständigen
Anfragen oder Antworten. Das vollständige Interaktionsprotokoll ist davon
konfigurations- und dateiseitig getrennt.

Das Frontend baut Leaflet-Popups in `app/static/app.js` als DOM-Knoten auf.
Dynamische Labels und Adressen gelangen ausschließlich über `textContent` und
`createTextNode()` in diese Knoten. Die vendorte Leaflet-Version übernimmt
Nicht-String-Inhalte direkt per `appendChild`; WFS-, Wissensbasis- und
Übersetzungswerte werden daher im Popup nicht als HTML interpretiert. Für
spätere Popup-Erweiterungen gilt dieselbe Grenze: Text über DOM-Text-APIs,
Links nur nach expliziter Protokollprüfung.

## Tatsächliche Betriebsprofile

- Ohne Interpreterzugang: Start und Health funktionieren, freie Anfragen fallen
  jedoch auf den technischen 112-Hinweis mit gegebenenfalls einer telefonischen
  Hilfebus-Kontaktkarte zurück. Fachsuche und Kartenmarker entfallen.
  Server-Transkription fehlt ohne eigene Speech-Konfiguration;
  Sprachsynthese kann über `edge-tts` verfügbar sein.
- Mit `REWRITE_PROVIDER=blablador`: strukturierte Interpretation und geerdete
  Formulierung mit vorgeschaltetem Akutgefahr-Signal und deterministischem
  Fallback bei jeder Provider- oder Validierungsstörung. Der enge deterministische
  Preflight bleibt als Defense-in-Depth verfügbar; eine allgemeine sprachliche
  Risikoklassifikation ohne Interpreter wird nicht behauptet.
- Mit `WFS_AUTO_SYNC=true`: Prüfung beim Start und anschließend periodisch.
  `WFS_AUTO_PROMOTE=false` hält Änderungen zur manuellen Prüfung zurück.
  Dieses technische WFS-Prüfintervall ist kein fachlich vereinbarter Turnus für
  Kurationsreviews; ein solcher Turnus ist derzeit nicht formal definiert.

## Konfigurationsabhängig

- Blablador benötigt Base-URL, API-Key und Modell.
- Server-STT benötigt einen OpenAI-kompatiblen Audio-Endpunkt.
- OpenAI-kompatibles TTS benötigt Endpunkt, Key und Modell; alternativ nutzt die
  Anwendung `edge-tts`.
- Kartenkacheln und `edge-tts` benötigen im Browser beziehungsweise Backend
  Netzwerkzugriff.
- Der WFS-Client verwendet standardmäßig 10 Sekunden für den Verbindungsaufbau
  und 30 Sekunden für das Lesen. Ein Timeout findet vor Validierung und Writes
  statt und lässt den aktiven Datenstand unverändert.

## Unvollständig oder bewusst nicht implementiert

- keine Kapazitäts-, Aufnahme- oder Echtzeitverfügbarkeitsdaten
- keine grafische Review-/Administrationsoberfläche für WFS, Kuration und Übersetzungen
- keine prozessübergreifende Sperre für parallele WFS-Checks oder Promotionen;
  alte und verwaiste vollständige Releases werden nicht automatisch rotiert
- kein produktionsreifes Einwilligungs-, Zugriffs-, Aufbewahrungs-, Lösch-,
  Pseudonymisierungs- oder Anonymisierungskonzept für Interaktionsprotokolle
- keine prozessübergreifende Provider-Nebenläufigkeitsbegrenzung; mangels lokaler
  Modelle und belegter externer Kontingentgrenzen ist derzeit keine Semaphore
  implementiert
- keine Mehrbenutzer-, Mehrprozess- oder Datenbank-Persistenz für Sessions;
  Recovery-Dateien werden nicht automatisch rotiert oder gelöscht
- keine dokumentierte produktive Deployment-Orchestrierung, Authentifizierung,
  Rate-Limits oder TLS-Terminierung
- kein konfiguriertes Linter-, Type-Checker- oder Dokumentations-Buildsystem
- keine bitidentische Buildgarantie und kein plattformübergreifender Hash-Lock;
  Wheel/sdist-Inventar und Clean-Installation sind reproduzierbar geprüft
- keine Garantie, dass das LLM jede akute Gefahr erkennt oder Falschpositive
  vollständig vermeidet; die Übersetzungsentwürfe für Englisch, Polnisch,
  Rumänisch und Russisch benötigen noch menschliche Prüfung

Diese Punkte sind Einschränkungen des vorhandenen Codes, keine Zusage für eine
spätere Implementierung.
