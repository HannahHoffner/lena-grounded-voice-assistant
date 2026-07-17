# Tests und Qualitätssicherung

## Ausführung

```powershell
cd Code3
python -m pip install -e ".[dev]"
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

## Manuelle Smoke-Checks

1. Starte mit `REWRITE_PROVIDER=template` und `WFS_AUTO_SYNC=false`.
2. Prüfe `GET /api/health` und öffne `/`.
3. Stelle je eine Frage zu Essen, Schlafen, Medizin und Beratung.
4. Prüfe Karten, Kartendarstellung, Sprachwechsel und eine Folgefrage.
5. Prüfe Speech nur mit bewusst konfiguriertem externem Dienst.

## Fehlende automatisierte Prüfungen

Im Projekt sind derzeit keine Linter-, Type-Checker-, Coverage- oder
Dokumentations-Linkprüfungen konfiguriert. Es gibt außerdem keine Browser-End-to-
End-Suite. Solche Werkzeuge dürfen erst nach bewusster Projektentscheidung als
neue Entwicklungsabhängigkeiten ergänzt werden.
