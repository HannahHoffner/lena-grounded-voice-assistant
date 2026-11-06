# Neue Live-Messung: 557a487 / Validator 10

27.10.2026. Alle vier offiziellen Stufen einmal vollständig durchgeführt:
**83 Requests, 126 Provideraufrufe**, separat ein Modellinventar-GET.
Keine ausgewählten Wiederholungen, keine Code- oder Thesisänderung.

| Stufe | Requests / Calls | Technische Fehlerfälle vorher → jetzt | Anwendbare Inhaltsbeanstandungen jetzt | Rohgates Vertrag / Inhalt |
|---|---:|---:|---:|---|
| Interpreter | 15 / 15 | 0 → 0 | 0 | bestanden / bestanden |
| Selector/Formulator | 16 / 20 | 6 → 4 | 0 | nicht bestanden / nicht bestanden |
| End-to-End | 34 / 53 | 1 → 3 | 0 | nicht bestanden / nicht bestanden |
| Stabilität | 18 / 38 | 3 → 2 | 0 | nicht bestanden / nicht bestanden |

Vergleich: 482f1f9 / Validator 9, gleicher Katalog, gleiche KB, Limits und
Konfiguration. Die Rohberichte enthalten weiterhin E2E 3/Stabilität 6
markerbedingte Beanstandungen. Der bereits abgelöste Markermaßstab wird in der
aktuellen separaten Auswertung nicht angelegt; Originalgates bleiben erhalten.
Auch das Kartenverbot bei normalen out_of_scope-Antworten entfällt; Verbote bei
Akutgefahr bleiben aktiv.

Alle **6/6 Antworttypfolgen** über je drei Wiederholungen stabil (vorher 5/6).
E2E/Stabilität **53/51 anwendbare Metrikvorkommen ungeprüft**. Null automatisch
katalogseitig kritische Safetyabweichungen ist keine Garantie null falscher
Aussagen. Neue Antworten wurden nicht durch Codex als richtig bewertet.

Die vier terminalen Formulatorablehnungen: zweimal „Rücken“ statt „Rücke“,
zweimal nicht bereitgestellte Policy out_of_scope_boundary. Beide polnischen
Fälle passieren. E2E: zwei erholte Fehler und ein Templatefallback; Stabilität:
zwei erholte Fehler. Diagnosen stehen in audit.json. Der Gesamtpfad hatte
diesmal mehr technische Fehlerfälle; keine Verbesserung aller Maße behaupten.
Stochastisch andere Texte und bekannter Katalog erlauben keinen kausalen oder
unabhängigen Generalisierungsnachweis.

## Belege

- live/measurement-summary.json: vollständige Zähler, Versionen, Run-IDs.
- live/runtime/live-evaluations/: unveränderte Originalberichte und Antworten.
- current-assessment.json, analysis/current_assessment.py: aktuelle Ableitung,
  entfallene Kriterien und Originalhashes.
- audit.json, analysis/audit.py: Vergleich, Fehlerfälle, Identitäts-/Secretcheck.
- live/measurement-profile.json, live/source-manifest.json, live/source-557a487.zip:
  vorab gesicherte Baseline und Messprofil ohne Zugangsdaten.
- regression-link.json: 167 App-/Testdateien bytegleich zum vollständig
  geprüften Validator-10-Export. Je 1665 Python plus bekannter XFAIL, je 19 JS,
  No-Cache-Build und Runtime/Persistenz bereits bestanden; für die reine
  Messung nicht nochmals ausgeführt. Keine Tests verändert.
- manuelle-evaluation-557a487-vorbereitet.zip: vorbereitetes 16-Einheiten-
  Paket, finaler Commit und neuer Referenzlauf gebunden; keine manuellen
  Ausgaben oder Bewertungen. Tatsächliche Instanz vor Erhebung abgleichen.

Die manuelle Eigenbewertung bleibt bei Beibehaltung der angekündigten Methode
noch durchzuführen. Der normale Server 8002 wurde durch diese isolierte
CLI-Messung nicht neu gestartet. Repositorydokumentation: Bericht 20,
Thesisnotizen P. Historische 120er-Ablation und menschliche Quoten bleiben ihren
ursprünglichen Ständen zugeordnet.
