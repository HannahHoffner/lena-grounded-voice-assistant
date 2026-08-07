from __future__ import annotations

import re
from pathlib import Path


APP_JS = Path(__file__).resolve().parents[1] / "app" / "static" / "app.js"


def _function_body(source: str, name: str) -> str:
    match = re.search(
        rf"function {re.escape(name)}\([^)]*\) \{{(?P<body>.*?)\n\}}\n\nfunction ",
        source,
        flags=re.DOTALL,
    )
    assert match, f"Produktiver JavaScript-Helper {name} wurde nicht gefunden"
    return match.group("body")


def test_leaflet_popups_bind_dom_nodes_for_all_dynamic_values() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    helper = _function_body(source, "buildMapPopup")

    assert 'document.createElement("div")' in helper
    assert 'document.createElement("strong")' in helper
    assert "title.textContent = label" in helper
    assert "document.createTextNode(addressText)" in helper
    assert "if (addressText)" in helper

    for forbidden_sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert forbidden_sink not in helper

    popup_arguments = re.findall(r"\.bindPopup\((.*?)\)\.addTo\(map\)", source)
    assert popup_arguments == [
        "buildMapPopup(origin.label, origin.address)",
        "buildMapPopup(destination.label, destination.address)",
    ]


def test_popup_path_never_interpolates_xss_payloads_as_markup() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    helper = _function_body(source, "buildMapPopup")
    render_map = _function_body(source, "renderMap")

    payloads = (
        "<img src=x onerror=alert(1)>",
        "<script>alert(1)</script>",
        '\"><svg onload=alert(1)>',
    )
    assert all(payload not in source for payload in payloads)

    # Beide dynamischen Werte werden ausschließlich an Text-Sinks übergeben.
    assert re.search(r"title\.textContent\s*=\s*label\s*\?\?\s*\"\"", helper)
    assert re.search(r"createTextNode\(addressText\)", helper)
    assert "label ?? \"\"" in helper
    assert "address ?? \"\"" in helper

    assert "bindPopup(`" not in render_map
    assert "bindPopup(\"" not in render_map
    assert "bindPopup('" not in render_map
    assert "buildMapPopup(origin.label, origin.address)" in render_map
    assert "buildMapPopup(destination.label, destination.address)" in render_map
