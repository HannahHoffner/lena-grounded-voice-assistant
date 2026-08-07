"""Löst unveränderliche Paketressourcen ohne Abhängigkeit vom Arbeitsordner auf."""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path


def package_root() -> Path:
    """Liefert den entpackten Installationspfad des Pythonpakets.

    pip installiert Wheels entpackt. Ein nicht dateisystembasiertes Importformat
    wird bewusst abgewiesen, weil FastAPI statische Dateien dauerhaft mountet.
    """
    root = files("app")
    try:
        return Path(os.fspath(root)).resolve()
    except TypeError as exc:  # pragma: no cover - pip wheels are unpacked
        raise RuntimeError("LENA requires unpacked package resources") from exc


def checkout_root() -> Path | None:
    """Erkennt einen Source-Checkout anhand seiner versionierten Fachdaten."""
    candidate = package_root().parent
    if (candidate / "data" / "canonical" / "offers.json").is_file():
        return candidate
    return None


def bootstrap_data_root() -> Path:
    """Wählt Checkoutdaten oder den unveränderlichen Wheel-Bootstrap."""
    checkout = checkout_root()
    return checkout / "data" if checkout else package_root() / "resources" / "bootstrap"


def packaged_bootstrap_data_root() -> Path:
    """Liefert stets den unveraenderlichen, mit dem Paket ausgelieferten Bootstrap."""

    return package_root() / "resources" / "bootstrap"


def static_root() -> Path:
    """Liefert das vollständig paketierte Browser-Frontend."""
    return package_root() / "static"
