"""Kanonische Laufzeitauflösung der in den Paketmetadaten definierten Version."""

from importlib.metadata import PackageNotFoundError, version


PACKAGE_NAME = "lena-code3"
DEVELOPMENT_VERSION = "0+unknown"


def software_version() -> str:
    """Liest die Wheel-Version oder kennzeichnet einen uninstallierten Source-Baum."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return DEVELOPMENT_VERSION
