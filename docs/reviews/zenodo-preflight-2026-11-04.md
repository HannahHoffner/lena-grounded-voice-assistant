# Zenodo-Vorprüfung des Code-Repositories, 04.11.2026

## Ergebnis und Prüfgegenstand

Ziel ist ausdrücklich `HannahHoffner/lena-grounded-voice-assistant`, nicht das
separate Repository `lena-final` und nicht das Thesis-Repository. Ausgangscommit:
`105c0b19fd91a8d1c71b9eda259f0380a947cf9c`. Zu Beginn war der Arbeitsbaum sauber.
Die Nutzerin beauftragte Prüfung, fehlende Veröffentlichungsvorbereitung und
Festlegung eines zur Thesis passenden Commits. Kein Push, Tag oder öffentliches
Release ist Bestandteil dieser Vorbereitung.

**Die Weitergaberechte der enthaltenen Trinkbrunnendaten sind ungeklärt.**
Dies verhindert eine uneingeschränkte öffentliche Freigabe des vollständigen
Archivs. Die bestehende GPL des eigenen Codes erteilt keine Fremddatenrechte.
Die Prüfung ersetzt weder eine Rechtefreigabe noch eine vollständige
Datenschutzprüfung. Die evaluierten Datenbytes wurden nicht verändert.

## Secrets, Laufzeitdaten und Historie

Gitleaks **8.30.1**, aus dem offiziellen Repository geladen und gegen die
veröffentlichten SHA-256-Prüfsummen geprüft, wurde lokal ausgeführt:

```text
gitleaks dir <git-archive-export> --redact=100 --report-format=json --report-path=<lokaler-bericht>
gitleaks git <repository> --log-opts=--all --redact=100 --report-format=json --report-path=<lokaler-bericht>
```

- Baseline-Quellarchiv aus `git archive HEAD`: **0 Secret-Funde**.
- Finaler Export des vorbereiteten Index-Trees: **218 Dateien**, beide
  Compose-Dateien enthalten, keine lokalen Secrets/Logs/Sessions oder internen
  Plan-/Reviewunterlagen. Erneuter Gitleaks-Scan: **0 Secret-Funde**.
- Alle **97** vor der Vorbereitung erreichbaren Commits, einschließlich
  lokaler Branches, Remote-Refs und Tags: **0 Secret-Funde**.
- Zusätzlicher exakter Vergleich des einen tatsächlich in den lokalen
  Konfigurationsdateien vorhandenen, ausreichend langen Secretwerts gegen
  **1481 eindeutige erreichbare Git-Blobs**: **0 Treffer**. Der Wert selbst
  wurde weder ausgegeben noch in Berichte übernommen.
- Sensible Dateinamen in versionierten Dateien und erreichbarer Historie:
  nur `.env.example`; dort stehen Variablennamen, leere Schlüssel und Beispiele.
  Keine versionierte echte `.env`, Sessiondatenbank, Interaktions-JSONL,
  Audiodatei, private Schlüsseldatei oder Laufzeit-Logdatei gefunden.
- Im lokalen Checkout existieren `.env`, `.env.local`, `runtime/` sowie
  `fixture-S-12.log`. Sie sind ignoriert und dürfen nicht mit einem manuellen
  Workspace-ZIP veröffentlicht werden. Die Prüfung hat sie nicht gelöscht.

Prüfgrenzen: Gitleaks erkennt bekannte Muster, nicht jede denkbare sensible
Information. Der exakte Vergleich ergänzt dies nur für bekannte lokale Werte.
Nicht erreichbare Git-Objekte, externe Backups, GitHub-Artefakte und fremde
Rechnersitzungen sind nicht Gegenstand dieses aktuellen Scans. Frühere
Protokollprüfungen sind im Bericht vom 30.10. gesondert dokumentiert.

## Personen- und Herkunftsdaten

- E-Mail-Kandidaten in **15 versionierten Dateien** wurden eingeordnet.
  Der Angebotsbestand enthält dienstliche Einrichtungskontakte und teilweise
  namentliche Ansprechpersonen; Kopien davon stehen in Snapshots, Bootstrap,
  Fixtures und einzelnen fachlichen Tests. Die maschinelle E-Mail-Suche
  belegt deshalb ausdrücklich keine Freiheit von personenbezogenen Daten.
- Diese Kontakte sind als Angebots-/Quellangaben dokumentiert. Keine privaten
  Klientinnen- oder Klientenakten und keine realen Nutzerinteraktionen im
  versionierten Softwarebestand identifiziert. Eine eigenständige aktuelle
  Freigabe jedes einzelnen beruflichen Kontakts wurde nicht eingeholt.
- Git-Autorinnenmetadaten enthalten neben einer GitHub-noreply-Adresse eine
  persönliche Hochschuladresse. Ein normales `git archive` enthält keine
  Commit-Historie; eine öffentliche GitHub-Freigabe würde diese Metadaten
  dagegen offenlegen. Die Historie wurde nicht umgeschrieben.
- Historische technische Dokumentation enthält lokale Pfade mit dem generischen
  Windows-Benutzernamen `User`. Diese Pfade erschließen keine externen Belege
  für Dritte; sie sind keine Zugangsdaten. Die Originalnachweise bleiben
  historisch zugeordnet.
- WFS-/Toilettenquellen sind im Repository mit Datenlizenz Deutschland –
  Namensnennung – Version 2.0 und Herkunft dokumentiert. Für Brunnen heißt der
  gespeicherte Lizenzstatus ausdrücklich `not_explicitly_specified`, insbesondere
  in `app/resources/bootstrap/drinking_fountains/releases/20260802T122318Z-58d55e2ab090/source_evidence.json`.
  Die fachliche Freigabe `reviewed_for_prototype` ist keine Weitergabelizenz.

## Lizenz, README und Zitiermetadaten

- Vollständige `LICENSE` bereits vorhanden: **GPL-3.0-only**. Erhalten, keine
  neue Lizenzwahl oder Umwidmung fremder Inhalte vorgenommen.
- `THIRD_PARTY_NOTICES.md` enthält Rechteabgrenzung, Leaflet-Hinweise und offene
  Datenrechte. Erhalten.
- README enthält bereits Voraussetzungen, Docker, LLM-/Sprachkonfiguration,
  Offline-Grenzen, Datenschutz-/Betriebsgrenzen, Tests und Evaluationseinordnung.
  Ergänzt: explizite Lizenz/Zitation und tatsächlich nutzbarer Compose-Start.
  Der nur zum lokalen Workspace passende Befehl `cd code` wurde korrigiert.
- `compose.yaml` bildet den vorhandenen Runtime-Start mit Loopback-Port,
  schreibgeschütztem Dateisystem und flüchtigem `/tmp` ab. Standard ohne
  persönliche Konfiguration. `compose.provider.yaml` verlangt ausdrücklich
  `LENA_ENV_FILE` mit einer externen Datei; keine implizite `.env.local`-Übernahme.
- `MANIFEST.in` und `.dockerignore` nehmen beide Compose-Dateien in den
  Source-/Build-Kontext auf. Bei der Inventarprüfung wurde der anfangs fehlende
  Docker-Allowlist-Eintrag erkannt und korrigiert.
- `CITATION.cff` war bereits vorhanden: Titel, Hannah Hoffner, Version **0.2.0**,
  GPL-3.0-only und kanonische Repository-URL. Mit **cffconvert 2.0.0** gegen
  Schema **1.2.0** validiert. Keine `.zenodo.json` vorhanden, also keine zweite
  überschreibende Metadatenquelle.
- `date-released` bleibt bis zur Festlegung des tatsächlichen Releasedatums
  offen. Keine heutige Vorbereitung als Veröffentlichung ausgegeben. Auch
  keine DOI erfunden. Das Ergänzen eines tatsächlichen Datums ist im
  Releaseablauf beschrieben und erfordert einen neu protokollierten Commit.

## Commitentscheidung und Thesis-Bezug

Die Thesis bezeichnet
`5962d6c172d6f6eeddf6bc65c8644b833838b671` als finalen Wartungs-/Prüfstand.
Git-Objektvergleich gegen den Ausgangscommit dieser Vorbereitung:

| Inhalt | Ergebnis |
|---|---|
| `app/` einschließlich Frontend und Bootstrap | identische Tree-ID |
| `data/` | identische Tree-ID |
| `tests/` | identische Tree-ID |
| `requirements/` | identische Tree-ID |
| `Dockerfile` | identische Blob-ID |
| `pyproject.toml` | identische Blob-ID |
| `.env.example` | identische Blob-ID |

Entscheidung: Der lokale Commit
`Prepare thesis-aligned Zenodo archive and Compose setup` ist der geprüfte
Archivkandidat. Die vollständige SHA wird nach seiner Erstellung im getrennten
Prüfmanifest zusammen mit Archiv-SHA-256 und Inventar gespeichert. Damit ist
der Codegegenstand der Thesis erhalten; die Vorbereitung erweitert nur
Bereitstellung und Dokumentation. Die historische Evaluation wird nicht
rückwirkend auf einen neuen Commit umetikettiert.

## Verifikation

- `docker compose --env-file .env.example config --quiet`: gültig.
- Provider-Erweiterung ohne `LENA_ENV_FILE`: verweigert wie vorgesehen den Start.
- Provider-Erweiterung mit rein synthetischer externer Datei: korrekt eingebunden;
  Loopback-Port, Runtime-Ziel und `read_only` erhalten.
- Standard-Compose: keine Umgebungswerte oder env_file an den Container übergeben.
- Runtime-Compose aus isoliertem Projekt mit dynamischem lokalen Port:
  gebaut, Healthcheck erfolgreich, `/` HTTP 200 und `kb_loaded=true`.
  Testcontainer und Projektnetz anschließend entfernt.
- Netzloser Docker-Testlauf von `test_packaging.py`,
  `test_configuration_profiles.py` und `test_architecture_boundaries.py`:
  **24 bestanden**, eine bestehende Starlette-Deprecation-Warnung.
- Netzlose JavaScript-Suite im Testimage: **19 bestanden**.
- Ein erster nativer Windows-Lauf: **23 bestanden, 1 fehlgeschlagen** beim
  frisch installierten Wheel. Direkte Wiederholung des unveränderten isolierten
  Prüfskripts in derselben temporären Installation bestand; damit ist der
  Erstfehler noch nicht ursächlich erklärt. Auch die erneute Ausführung des
  einzelnen ursprünglichen pytest-Falls bestand.
- Nach Ergänzung der Docker-Allowlist: Testimage erneut gebaut, alle
  **7 Packagingtests bestanden**; Source-Inventar bestätigt beide Compose-Dateien,
  CFF und Lizenz sowie den Ausschluss lokaler Konfiguration und Laufzeitdaten.
- Vollständige Python-Suite und echte externe Provider nicht erneut ausgeführt:
  Anwendung, Tests und Daten wurden nicht geändert. Die historischen
  Vollprüfungen und die manuelle Finalprüfung bleiben getrennte Nachweise.

## Offene Veröffentlichungsschritte

1. Weitergaberechte der Brunnenressourcen klären oder eine separat geplante,
   erneut geprüfte Archivvariante ohne diese Daten erstellen. Diese Variante
   wäre nicht byteidentisch zum vollständig evaluierten Paket.
2. Tatsächliches Releasedatum festlegen, CFF ergänzen und endgültigen
   Release-Commit samt Archiv erneut protokollieren.
3. GitHub-Sichtbarkeit bewusst entscheiden oder manuell bei Zenodo hochladen.
   Das Repository war bei der API-Prüfung am 04.11.2026 **privat**.
4. Tatsächliche Versions-DOI nach Vergabe/Reservierung in Thesis und
   Veröffentlichungsmetadaten übernehmen. Keine DOI-Veröffentlichung erfolgte
   im Rahmen dieser lokalen Vorbereitung.

Quellen: [Zenodo CFF](https://help.zenodo.org/docs/github/describe-software/citation-file/),
[GitHub/Zenodo](https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content),
[Gitleaks](https://github.com/gitleaks/gitleaks).
