"""Gemeinsame Textnormalisierung für deterministische Phrasenvergleiche.

Aktiv im Anfragepfad (Systemfragen, ausdrückliche Trinkbrunnenwünsche). Vom
historischen lexikalischen Retrievalbaseline in ``retrieval.py`` getrennt,
damit dessen Aufbewahrung oder spätere Archivierung den Laufzeitpfad nicht
berührt (Audit C-01).
"""

from __future__ import annotations

import re
import unicodedata


def normalize_text(value: str) -> str:
    """Kleinschreibung, ß→ss, ohne Diakritika und Satzzeichen, einfache Leerzeichen."""
    value = value.casefold().replace("ß", "ss")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.replace("_", " ").split())
