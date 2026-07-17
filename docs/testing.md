# Tests und Qualitätssicherung

## Ausführung

```powershell
cd code
python -m pip install -c requirements/constraints-py311.txt -e ".[dev]"
python -m pytest
```

Pytest liest `pyproject.toml`, sucht unter `tests/` und verwendet den Quiet-Modus.
Die Suite benötigt laut Testaufbau keinen Live-WFS. Netzwerkprovider werden
ersetzt beziehungsweise über lokale Testantworten geprüft.

## Abdeckung nach Testmodul

| Datei | Schwerpunkt |
|---|---|
| `tests/test_api.py` | Health, Query-API, LLM-Stufen und Fallbacks |
| `tests/test_kb_loader.py` | Markdown- und kanonisches JSON-Laden |
| `tests/test_retrieval.py` | Kategorien, Zielgruppen und Ranking |
| `tests/test_sessions.py` | Session-Lebenszyklus und Folgefragen |
| `tests/test_wfs_sync.py` | Validierung, Normalisierung, Diff und Promotion |
| `tests/test_frontend_security.py` | statische Absicherung der Leaflet-Popup-Sinks |
| `tests/test_safety.py` | Akutgefahr-Vertrag, kontrollierte Antwort und TTS |
| `tests/test_observability.py` | technische Events, finale JSONL-Paare, Redaktionsgrenzen und Schreibfehler |

## Continuous Integration

`.github/workflows/test.yml` verwendet GitHub Actions mit Python 3.11 und führt
dieselben nachgewiesenen Befehle wie lokal aus:

```powershell
python -m pytest
python -m compileall -q app
```

Der Workflow besitzt nur Leserechte auf Repository-Inhalte und benötigt keine
Secrets. Er baut außerdem ein Wheel, prüft die erforderlichen Dateien und
installiert es in eine frische virtuelle Umgebung. Der Smoke-Test lädt
Startseite, Wissensbasis und Health-Endpunkt aus einem fremden Arbeitsverzeichnis.
Der Workflow enthält bewusst kein Deployment, keinen Node-/Browser-Schritt und
keine noch unkonfigurierten Linter, Type-Checker oder Security-Scanner. Ein
Remote-CI-Lauf kann erst nach Push beziehungsweise Pull Request bestätigt
werden; die lokale Ausführung prüft nur Befehle und Workflowstruktur.

## Manuelle Smoke-Checks

1. Starte mit `REWRITE_PROVIDER=template` und `WFS_AUTO_SYNC=false`.
2. Prüfe `GET /api/health` und öffne `/`.
3. Stelle je eine Frage zu Essen, Schlafen, Medizin und Beratung.
4. Prüfe Karten, Kartendarstellung, Sprachwechsel und eine Folgefrage.
5. Prüfe Speech nur mit bewusst konfiguriertem externem Dienst.
6. Prüfe bei bewusst aktivierter Prototyp-Protokollierung eine erzeugte
   `runtime/logs/interactions.jsonl` und lösche lokale Testdaten anschließend.

Fokussierte Prüfung des Protokollpfads:

```powershell
python -m pytest tests/test_observability.py -q
```

## Fehlende automatisierte Prüfungen

Im Projekt sind derzeit keine Linter-, Type-Checker-, Coverage- oder
Dokumentations-Linkprüfungen konfiguriert. Es gibt außerdem keine Browser-End-to-
End-Suite. Die Python-3.11-Constraints fixieren Versionen, aber noch keine
Artefakthashes und sind kein universeller Lock für andere Python-Versionen oder
Plattformen. Ein Hash-Lock und zusätzliche Werkzeuge benötigen eine bewusste
Projektentscheidung in einem separaten Paket.
