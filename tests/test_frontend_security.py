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

    popup_arguments = re.findall(r"\.bindPopup\((.*?)\)\.addTo\(map\)", source, re.DOTALL)
    assert popup_arguments[0] == "buildMapPopup(origin.label, origin.address)"
    assert "buildMapPopup(" in popup_arguments[1]
    assert "destination.label" in popup_arguments[1]
    assert "destination.address" in popup_arguments[1]
    assert "destination.fee_raw" in popup_arguments[1]


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
    assert "destination.label" in render_map
    assert "destination.address" in render_map
    assert "destination.fee_raw" in render_map
    assert "document.createTextNode(detail)" in helper


def test_toilet_markers_are_not_distinguished_by_colour_alone() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    render_map = _function_body(source, "renderMap")

    assert 'radius: isToilet ? 11 : 9' in render_map
    assert 'dashArray: isToilet ? "4 2" : null' in render_map
    assert 'markerElement.setAttribute("role", "img")' in render_map
    assert '"aria-label"' in render_map
    assert "text().categories.toilet" in render_map
