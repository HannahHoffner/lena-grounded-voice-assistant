# Arbeitspaket 1: Kurationsmodell und freigegebene Runtime-Sicht

## Ziel

Arbeitspaket 1 führt eine schema-validierte, nachvollziehbare Kurationsschicht ein. Sie trennt Organisation, Standort und konkretes Leistungsangebot, bindet den freigegebenen Prototypbestand an einen unveränderten WFS-Quellstand und erzeugt daraus genau eine Runtime-Sicht für alle Verbraucher. Die WFS-IDs 1 bis 4 bleiben in Rohdaten, normalisiertem Release, Diff und Provenienz erhalten, sind aber aus sämtlichen Runtime-Pfaden ausgeschlossen.

Nicht Bestandteil dieses Plans sind Arbeitspaket 2, eine allgemeine Neugestaltung der Anfragepipeline, neue räumliche Rankingregeln, externe Schreibprozesse oder Änderungen an Thesis- und Präsentationsdateien.

## Review-Befund

- `app/kb_loader.py` lädt derzeit den aktiven WFS-Release beziehungsweise den Bootstrap-Snapshot direkt als Runtime-Wissensbasis. Eine Kurationsschicht existiert nicht.
- `app/service.py` baut Routerindex, ID-Abbildung, Retrieval, Formulator-Kontext, Karten und Kartenmarker aus derselben Liste `KnowledgeBase.offers` auf. Deshalb muss die Freigabe vor dieser Liste erfolgen.
- `app/retrieval.py` und `app/providers/llm.py` kennen keine Organisations- oder Angebotsaliase und keine Trennung von Organisation, Standort und Leistung.
- `app/i18n.py` kann Namen aus dem Übersetzungsspeicher über einen kuratierten Anzeigenamen schreiben. Kuratierte Anzeigenamen müssen nach der maschinellen Übersetzung erneut Vorrang erhalten.
- Der aktive WFS-Release enthält 30 normalisierte Angebote einschließlich der auszuschließenden IDs 1 bis 4. Die Quelldaten dürfen nicht verändert werden.
- Die bestehende Testkonfiguration konstruiert `Settings` meist direkt. Die
  zunächst als optional modellierte Kurationsdatei erwies sich dadurch als
  Umgehungspfad; die Nachbesserung macht den paketierten Katalog auch bei
  `curation_path=None` verpflichtend und trennt reine Source-Tests über einen
  ausdrücklich benannten Loader.

## Verfolgte Sackgassen und Risiken

- Ausschluss nur im Retrieval: verworfen, weil Router, LLM-Kandidaten und UI die Datensätze weiterhin sehen könnten.
- Alias als exklusives Feld am Angebot: verworfen, weil A1/Schoppi und Mobile/Kübel mehrere getrennte Angebote derselben Organisation bezeichnen.
- Automatisches Überlagern jedes neuen aktiven WFS-Release: verworfen, weil ungeprüfte Quelländerungen sonst die freigegebene Runtime-Sicht verändern könnten.
- Zusammenführen der IDs 6 und 11: ausgeschlossen, weil es getrennte Leistungen am selben Standort sind.
- Periodischer Prüfturnus mit erfundenem Wert oder Datum: ausgeschlossen; Intervall und Stakeholder-Prüfdatum bleiben unbekannt beziehungsweise `null`.
- Allgemeine Teamwahl für Mobile/Kübel ohne Ortsbezug: ausgeschlossen; verbleibende Mehrdeutigkeit führt zu einer Rückfrage.

## Daten- und Laufzeitentwurf

1. Eine versionierte JSON-Kurationsdatei wird mit Pydantic-Schemas für `Organization`, `Location`, `ServiceOffer`, `OrganizationAlias`, `OfferAlias`, `SourceReference` und `CurationDecision` validiert.
2. Jeder `ServiceOffer` verweist auf genau eine Organisation und einen Standort sowie auf den normalisierten WFS-Datensatz über `source_id`.
3. Der Katalog nennt den geprüften WFS-Release und dessen Hash. Die Runtime-Projektion lädt diesen unveränderlichen Stand, validiert die vollständige ID-Abdeckung und wendet ausschließlich dokumentierte Overrides an.
4. Ausgeschlossene Angebote verbleiben im geprüften Quellstand, werden aber vor Erstellung von `KnowledgeBase.offers` entfernt.
5. Organisationsaliase bilden auf mehrere Angebots-IDs ab. Bei einer Aliasanfrage grenzt ein belegter Bedarf auf passende konkrete Angebote ein; verbleibende Mehrdeutigkeit wird ohne Modellaufruf als Rückfrage beantwortet.
6. Kuratierte Adress- und Anzeigenamenwerte haben in der Runtime-Sicht Vorrang. Ursprüngliche WFS-Felder bleiben als unveränderte `raw_*`- und Quellenwerte im normalisierten Snapshot erhalten.
7. Provenienz, Prüfstatus und noch nicht definierte Review-Policy werden im Katalog und in den Runtime-Metadaten sichtbar gespeichert.

## Umsetzungsschritte

- [x] Pydantic-Kurationsschemas, Katalogvalidierung, Quellbindung und Runtime-Projektion in einem eigenständigen Modul implementieren.
- [x] `Settings` und Wissensbasis-Lader um den expliziten Kurationspfad und freigabebezogene Metadaten ergänzen.
- [x] Kurationskatalog als paketierte Bootstrap-Ressource anlegen, einschließlich A1/Schoppi, Mobile/Kübel, Scharni, Prototype-Review-Metadaten und Ausschlüssen 1 bis 4.
- [x] Runtime-Angebotsmodell um kuratierte Organisation-, Standort-, Alias-, Such- und Bedarfsfelder ergänzen.
- [x] Routerindex, deterministisches Retrieval und vollständigen Formulator-Kontext um die freigegebenen Alias- und Kurationsfelder ergänzen.
- [x] Organisationsalias-Auflösung mit bedarfsbasierter Eingrenzung und deterministischer Rückfrage bei Mehrdeutigkeit in den bestehenden Anfragepfad integrieren.
- [x] Kuratierte Anzeigenamen nach Übersetzung priorisieren und Health-/Release-Metadaten auf die kuratierte Sicht ausrichten.
- [x] Paketressourcen und knappe betriebliche Dokumentation zur Kurationsdatei aktualisieren.
- [x] Gezielte Tests für Schema, Provenienz, Rohdatenerhalt, Aliasauflösung, Mehrdeutigkeit, Scharni-Override und alle Runtime-Ausschlusspfade ergänzen.
- [x] Pakettests, vollständige Testsuite, Syntax-/Startprüfung und abschließenden Git-Diff ausführen und prüfen.

## Verifikation

- Gezielte Tests: neues Kurations-Testmodul sowie betroffene API-, Retrieval-, Provider-, WFS- und Packaging-Tests.
- Vollständig: `python -m pytest`.
- Syntax: `python -m compileall app tests`.
- Start/Smoke lokal und ohne externe Provider: Anwendung mit Template-Provider über `TestClient`, Health- und Beispielanfragen.
- Paket: bestehende Build-, Wheel- und Clean-Install-Tests ohne Installation neuer Abhängigkeiten.
- Abschluss: `git status --short`, `git diff --check`, `git diff --stat` und inhaltliche Prüfung des vollständigen Diffs.

## Dokumentation

Die Dokumentationsänderung beschränkt sich auf die bestehende technische Repository-Dokumentation und beschreibt nur die tatsächlich implementierte Kurationsdatei, die Quellbindung, den Freigabestatus und die sichtbare Behandlung ausstehender Reviews. Thesis- und Präsentationsdateien bleiben unverändert.

## Stoppbedingung

Nach erfolgreicher beziehungsweise transparent dokumentierter Verifikation und Diff-Prüfung endet die Arbeit. Arbeitspaket 2 beginnt ausschließlich nach ausdrücklicher Freigabe.

## Begrenzte Nachbesserung nach Review-First-Pruefung

Die abschliessende Diff-Pruefung hat vier innerhalb von Arbeitspaket 1 liegende
Umgehungs- beziehungsweise Integritaetsrisiken bestaetigt:

1. Ein direkt konstruiertes `Settings`-Objekt mit `curation_path=None` konnte
   die Kuration umgehen und die normalisierte WFS-Quelle als Runtime-Bestand
   verwenden.
2. Der Formulator-Payload wurde aus dem Runtime-Datensatz mit einer
   Ausschlussliste aufgebaut; dadurch konnten unbekannte Rohfelder und
   ueberschriebene Scharni-Fakten in den Prompt gelangen.
3. Die Anwendung lud zuerst den aktiven Pointer und konnte bei einem
   beschaedigten Pointer oder Release den exakt gebundenen, freigegebenen Stand
   nicht als Kaltstart-Fallback verwenden.
4. Sessions waren nicht an den tatsaechlich verwendeten kuratierten
   Wissensbestand gebunden und konnten dadurch veraltete Antworttexte in neue
   Modellkontexte uebernehmen.

Die Nutzerin hat ausschliesslich die kleinste Behebung dieser vier Befunde und
der direkt verbundenen Statusluecken freigegeben. Der strukturierte LLM-Router
aus Arbeitspaket 2 bleibt ausdruecklich ausserhalb dieses Plans.

### Nachbesserungs-Meilensteine

- [x] Runtime- und Source-Loader explizit trennen; `None` auf den paketierten
      Standardkatalog abbilden und jede ungefilterte Runtime-Konfiguration
      ausschliessen.
- [x] Exakt gebundenen lokalen Release und verifizierten paketierten
      Bootstrapstand als einzige sichere Runtime-Quellen implementieren.
- [x] Schema-validierte Positivlisten fuer Router-, Kandidaten- und
      Formulator-Transportmodelle einfuehren und das Inventar aller
      Runtime-Angebote pruefen.
- [x] Sessions zentral an einen Fingerabdruck aus Quellenrelease,
      Quellenhash und Kurationsstand binden.
- [x] Health-Ausgabe um Runtime-/Quellenstatus, redigierte Fehlercodes,
      Uebersetzungsstatus und formalen Freigabestatus ergaenzen.
- [x] Scharni-Geometriestatus strukturiert ausweisen und weiterhin aus Marker-
      und Distanzpfaden ausschliessen.
- [x] Fokussierte Loader-, Release-, Payload-, Session-, Health- und
      Sicherheitsregressionstests ergaenzen beziehungsweise anpassen.
- [x] Vollstaendige Suite, Syntaxpruefung, Wheel/sdist, Clean-Install,
      Template-Smoke und `git diff --check` ausfuehren.
- [x] Gesamtdiff erneut gegen `9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`
      pruefen und Arbeitspaket 2 nicht beginnen.

## Ergebnis der Verifikation

- Fokussiert: `tests/test_curation.py` und `tests/test_packaging.py` vollständig bestanden, einschließlich Wheel-Bau und Clean-Install außerhalb des Checkouts.
- Vollständig: `python -m pytest` mit 178 bestandenen Tests; einzige Meldung ist die bereits bestehende Starlette-Abkündigungswarnung für den TestClient.
- Syntax: `python -m compileall -q app tests` erfolgreich.
- Start/Smoke: Template-Start ohne WFS-Autosync oder externe Provider; Health meldet 26 Runtime-Angebote, `Schoppi schlafen` liefert ausschließlich ID 6 und `Kübel` keine willkürliche Karte.
- Diff: `git diff --check` erfolgreich. Änderungen liegen ausschließlich in Anwendung, paketierter Kuration, Tests, bestehender technischer Dokumentation, `.env.example` und diesem Plan. WFS-Rohdaten, normalisierte Releases, Pointer, Thesis und Präsentation sind unverändert.

## Ergebnis der begrenzten Nachbesserung

- Runtime-Loader: `curation_path=None` lädt den paketierten Standardkatalog;
  explizit fehlende oder ungültige Kataloge ergeben einen kontrollierten Fehler
  ohne Angebote. Ungefilterte Daten sind nur über
  `load_normalized_source_release()` erreichbar.
- Fallback: aktiver exakt gebundener Release, exakt gebundener lokaler Fallback,
  manifest- und hashverifizierter Paket-Bootstrap, danach Fehler. Pending-,
  ungeprüfte oder beliebige ältere Releases werden nie verwendet.
- LLM-Daten: Router-, Kandidaten- und Formulator-Sicht besitzen getrennte
  Pydantic-Positivlisten. Das Inventar aller 26 Runtime-Angebote enthält keine
  Rohfelder, alten Scharni-Kontakte/-Adresse oder ausgeschlossenen IDs 1 bis 4.
- Sessions: Neue Sessions speichern den 64-stelligen Runtime-Fingerabdruck aus
  Quellenrelease-ID, Quellenhash, Katalogversion und Kataloghash. Legacy- oder
  abweichende Verläufe werden vor jedem LLM-Kontext verworfen.
- Health: Runtime-/Quellen-/Fallbackstatus, redigierte Fehlercodes,
  Übersetzungszustände, formaler Freigabestatus und Scharni-Koordinatenstatus
  werden getrennt ausgegeben.
- Fokussiert: 126 Kurations-, Runtime-, Session-, API-, Safety- und
  Observabilitytests bestanden; 47 engere Loader-/Kurations-/Sessiontests
  bestanden.
- Packaging: 7 Packagingtests bestanden, einschließlich Wheel, sdist,
  Ressourceninventar und Clean-Install außerhalb des Repositorys.
- Vollständig: `python -m pytest -q` mit 203 bestandenen Tests; nur die bereits
  bekannte Starlette-Abkündigungswarnung.
- Syntax/Smoke/Diff: `python -m compileall -q app tests`, isolierter
  Template-Smoke und `git diff --check` erfolgreich. Gesamtdiff gegen
  `9673668fbd2619dbec3ff57c5cdb0f69c400d6b0` liegt weiterhin ausschließlich
  im Umfang von Arbeitspaket 1 und seiner freigegebenen Nachbesserung.
