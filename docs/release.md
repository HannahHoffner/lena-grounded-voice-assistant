# Release und wissenschaftliche Archivierung

## Vorbereiteter Stand

Die Projektversion ist unverändert `0.2.0` (Paketmetadaten und vorhandene Tests).
Es wurde kein Release erzeugt und keine DOI vergeben. `CITATION.cff` ist die
einzige maschinenlesbare Zitiermetadatenquelle; eine parallele `.zenodo.json`
ist nicht erforderlich. Autorin: Hannah Hoffner, ohne Affiliation. Eigener Code:
GPL-3.0-only, siehe [Lizenz und Herkunft](../THIRD_PARTY_NOTICES.md).

Docker-Build, vollständige Containerprüfungen und Runtime-Neustart wurden am
21.10.2026 auf Linux/AMD64 erfolgreich geprüft (siehe Reproduzierbarkeitsanleitung).
**Freigabe noch offen:** Weitergaberechte für Daten ohne ausdrückliche Lizenz
müssen vor einer öffentlichen Archivierung geklärt werden. Ein vorbereiteter Softwarestand ist keine
Veröffentlichungsfreigabe und keine abgeschlossene Evaluation.

## Inhalt des Softwarearchivs

Die `.gitattributes` legt LF für reguläre Textdateien fest und deaktiviert
Zeilenendenkonvertierung für `data/` und `app/resources/bootstrap/`. Diese
Ressourcen enthalten auch bestehende gemischte Zeilenenden; maßgeblich sind
ihre validierten Originalbytes, nicht eine einheitliche LF-/CRLF-Normalisierung.
Bei erstmaliger Einführung der Regeln müssen die betroffenen Originaldateien
mit aufgenommen werden: Bereits normalisierte Git-Blobs können gemischte
Zeilenenden nicht rekonstruieren. Keine Prüfsummen an exportbedingt veränderte
Daten anpassen. Nach Änderungen an den Attributen ist ein neuer Commit nötig,
bevor ein gewöhnliches `git archive <commit>` die korrigierten Regeln nutzt.

Ein Release archiviert den überprüften, committeten Repositorystand: Quellcode,
Frontend einschließlich Drittanbieterhinweisen, freigegebene lokale Snapshots
und Manifeste, Tests, Dockerfile, Python-Hashlocks, Konfiguration ohne Geheimnisse,
reguläre Projektdokumentation und Zitiermetadaten. Das Wheel enthält ausschließlich
die für die Anwendung vorgesehenen Ressourcen und den unveränderlichen Bootstrap.
Die Source Distribution enthält zusätzlich Tests und Dokumentation; sie ist
kein Ersatz für das vollständige GitHub-Quellarchiv mit Checkout-Wartungsdaten.

Historische Arbeitspläne und interne Reviews sind über `.gitattributes` vom
`git archive`-Softwarepaket ausgeschlossen. Einige bleiben konservativ im
Repository, weil Quellen-/Qualitätsnachweise oder Codereferenzen enthalten sind.
Sie sind keine aktuellen Betriebsanweisungen und bleiben in der Git-Historie
nachvollziehbar. ZIP- und sdist-Inventar getrennt prüfen.

Nicht archivieren: `.env`, `.env.local`, Zugangsdaten, private Schlüssel, lokale
virtuelle Umgebungen, Caches, Buildreste, lokale Logs, Sessions, personenbezogene
Interaktionen, Modellgewichte, temporäre oder unbereinigte Evaluationsergebnisse.
Solche Dateien sind ignoriert, dürfen aber auch nicht manuell in Zenodo-Uploads
gelangen. `git archive` nimmt nur versionierten Inhalt auf; ignoriert bedeutet
nicht, dass eine früher versehentlich versionierte Datei automatisch entfernt ist.
Rohdaten-/Lizenzmanifeste im Bootstrap werden nicht als entbehrliche Hashdetails
entfernt. Forschungsnachweise bei Bedarf als getrenntes, geprüftes Datenpaket
mit eigener Provenienz, Zugriffsregelung und gegebenenfalls notwendigen Prüfsummen
archivieren; keine Rohinteraktionen in ein öffentliches Softwarepaket mischen.

## Checkliste vor einem Release

1. Autorenschaft, Rechte am eigenen Code und Weitergaberechte der Fremddaten
   prüfen. Fehlende Datensatzlizenz nicht durch die GPL ersetzen. Die
   KI-Offenlegung der Masterarbeit und vorhandene Quellenangaben erhalten.
2. Vollständige lokale und Containerprüfungen aus
   [testing.md](testing.md) und [reproducibility.md](reproducibility.md) ausführen.
   Docker-Version, Plattform, reale Build-/Testbefehle und Ergebnisse protokollieren.
   Container zweimal mit leerem Zustand prüfen. Fehlgeschlagene Tests offenlegen.
3. Version in `pyproject.toml`, `CITATION.cff` und versionierenden Tests abgleichen.
   Die aktuelle `0.2.0` nicht als neue Nummer ausgeben. Falls diese Version bereits
   veröffentlicht ist, vor einem neuen Release eine tatsächlich beschlossene
   Folgeversion vergeben und alle Stellen konsistent aktualisieren.
4. Diff, Secrets, Paket- und Archivinventar prüfen. `git diff --check` ausführen.
   Vorbestehende Änderungen anderer Aufgaben getrennt halten. Erst nach eigener
   ausdrücklicher Freigabe committen; der Bereinigungsauftrag selbst erlaubt
   weder Commit noch Push.
5. Tagkonvention: `v<Projektversion>`, beispielsweise `v0.2.0` **nur**, falls diese
   Version tatsächlich für dieses Release festgelegt, geprüft und noch frei ist.
   Historische Tags nicht verschieben. Tag und Release müssen auf denselben
   geprüften Commit zeigen; dessen kurze ID ergänzend protokollieren.
6. Aus dem festgelegten Tag mit `git archive --format=zip --output=<archiv.zip>
   <tag>` ein Quellarchiv erzeugen und vor Veröffentlichung vollständig prüfen.
   Lizenzierte Quellen, erforderliche Daten, Bootstrap und Hashlocks einschließen.
   Test-/Buildprotokolle gehören ins geprüfte Reproduzierbarkeitspaket, nicht
   ungeprüft in den Quellbaum. Optional das gebaute Runtime-Image separat exportieren.

## Manuelle Schritte für GitHub und Zenodo

Es gibt zwei mögliche Veröffentlichungswege; nicht beide unabhängig für denselben
Stand benutzen:

- **GitHub-Integration:** In Zenodo anmelden und das berechtigte GitHub-Konto
  verbinden, Repository aktivieren, Metadatenvorschau prüfen. Erst danach das
  freigegebene GitHub-Release zum geprüften Tag veröffentlichen. Zenodo importiert
  das Release; den tatsächlich angelegten Record und dessen Dateien kontrollieren.
  Falls die Integration das Repository wegen Sichtbarkeit oder Berechtigungen
  nicht anbietet, den manuellen Weg verwenden.
- **Manueller Zenodo-Entwurf:** Das geprüfte Archiv hochladen, Softwaremetadaten
  aus `CITATION.cff` übernehmen, Lizenzen differenziert angeben und eine DOI im
  Entwurf reservieren. Erst wenn diese Reservierung tatsächlich existiert,
  die echte DOI in den vorgesehenen Releaseunterlagen und der Masterarbeit
  verwenden. Vor Veröffentlichung nochmals Dateiinhalt und Metadaten prüfen.

`date-released` ist das tatsächliche Releasedatum, nicht das Datum dieser
Vorbereitung. Einen reservierten DOI nicht als veröffentlichten Nachweis
darstellen. Bei der GitHub-Integration steht die neue DOI gegebenenfalls erst
nach dem Release fest; eine spätere Metadatenkorrektur ist kein stillschweigender
Austausch des bereits archivierten Quellarchivs. Den Zusammenhang in den
Releasehinweisen dokumentieren.

Nach erfolgreicher Veröffentlichung:

1. Die **Versions-DOI** genau dieses unveränderlichen Records in die finale
   Softwarezitation und die markierte Stelle der Masterarbeit übernehmen.
   `CITATION.cff` für den veröffentlichten Stand entsprechend nachführen.
2. Die **Concept DOI** bezeichnet die gesamte Versionsreihe. Sie ist für
   versionsübergreifende Verweise geeignet, ersetzt bei einer Evaluation aber
   nicht die Versions-DOI. Sie wird hier nicht „dynamic DOI“ genannt.
3. Tatsächliche DOI-Auflösung, Version, Titel, Autorin, Lizenzangaben, Datum und
   Dateien kontrollieren. Bei späteren Releases neue Versionen veröffentlichen;
   die frühere Evaluationszuordnung nicht rückwirkend ändern.

Offizielle Anleitungen: [Zenodo/GitHub](https://help.zenodo.org/docs/github/),
[CITATION.cff](https://help.zenodo.org/docs/github/describe-software/citation-file/),
[DOI-Versionierung](https://zenodo.org/help/versioning),
[Lizenzen](https://help.zenodo.org/docs/deposit/describe-records/licenses/).
