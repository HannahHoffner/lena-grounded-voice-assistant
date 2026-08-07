"""Zentrale unveränderliche Systemfakten, die nicht in Übersetzungen dupliziert werden."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmergencyPolicyFact:
    """Fachlich gebundener Notruffakt ohne frei formulierbare Modelldaten."""

    policy_version: str
    emergency_number: str
    source_urls: tuple[str, ...]


EMERGENCY_POLICY = EmergencyPolicyFact(
    policy_version="1",
    emergency_number="112",
    source_urls=(
        "https://www.bbk.bund.de/DE/Warnung-Vorsorge/Vorsorge/Gesundheit-und-Hygiene/Erste-Hilfe-und-Notruf/erste-hilfe-und-notruf_node.html",
        "https://digital-strategy.ec.europa.eu/en/policies/112",
    ),
)
EMERGENCY_NUMBER = EMERGENCY_POLICY.emergency_number
