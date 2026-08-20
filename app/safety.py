"""Deterministische Grenze nach der sprachlichen Akutrisiko-Interpretation."""

from __future__ import annotations

import json
import re
import unicodedata
from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .application_texts import application_text
from .models import Language
from .policy_facts import EMERGENCY_NUMBER, EMERGENCY_POLICY
from .resources import packaged_bootstrap_data_root


SAFETY_POLICY_VERSION = "1"
SAFETY_PREFLIGHT_VERSION = "1"
SAFETY_SCENARIO_CONTRACT_VERSION = "1"
SUPPORTED_SAFETY_LANGUAGES = tuple(language.value for language in Language)


class SafetyPath(str, Enum):
    NONE = "none"
    PREFLIGHT_DETECTED = "preflight_detected"
    INTERPRETER_DETECTED = "interpreter_detected"
    UNCERTAIN_DIALOG = "uncertain_dialog"
    UNCERTAIN_CONSERVATIVE = "uncertain_conservative"
    DIALOGUE_CLEARED = "dialogue_cleared"
    INTERPRETER_FAILURE = "interpreter_failure"


class SafetyTextKind(str, Enum):
    DETECTED = "detected"
    UNCERTAIN = "uncertain"
    TECHNICAL = "technical"
    # Nur für den Fall "Interpreter nicht verfügbar/fehlgeschlagen", wenn eine
    # Wissensbasis geladen ist und der deterministische Hilfebus-Kontakt
    # (siehe `_general_help_contact()` in service.py) ermittelt werden konnte.
    # Ersetzt in diesem Fall den reinen 112-Text durch einen konkreten,
    # sofort nutzbaren Kontakt, ohne den bedingten 112-Hinweis zu streichen.
    TECHNICAL_HILFEBUS = "technical_hilfebus"


_IMMEDIATE_SENTENCE_PATTERNS = tuple(
    re.compile(rf"(?:^|[.!?]\s*){phrase}(?:[.!?]|$)", re.IGNORECASE)
    for phrase in (
        r"ich (?:will|werde) mich jetzt (?:umbringen|töten|verletzen)",
        r"ich bringe mich jetzt um",
        r"ich werde jetzt jemanden (?:töten|umbringen|verletzen)",
        r"ich greife jetzt jemanden an",
        r"ich (?:kann gerade nicht atmen|bekomme gerade keine luft)",
        r"i (?:am going to|will) (?:kill|hurt) myself (?:right )?now",
        r"i (?:am going to|will) (?:kill|hurt|attack) someone (?:right )?now",
        r"i (?:cannot|can't) breathe (?:right )?now",
        r"chcę się teraz (?:zabić|zranić)",
        r"zaraz kogoś (?:zaatakuję|zabiję|zranię)",
        r"nie mogę teraz oddychać",
        r"vreau să mă (?:rănesc|sinucid) acum",
        r"voi (?:ataca|răni|ucide) pe cineva acum",
        r"nu pot să respir acum",
        r"я сейчас (?:причиню себе вред|убью себя)",
        r"я сейчас (?:причиню кому-то вред|нападу на кого-то|убью кого-то)",
        r"я сейчас не могу дышать",
    )
)


def _normalize_for_preflight(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def preflight_detects_immediate_danger(query: str) -> bool:
    """Erkennt nur vollständige, explizite und unmittelbar formulierte Sätze.

    Die Funktion ist keine allgemeine Risikoklassifikation und erkennt keinen
    Zitat-, Berichts- oder Verneinungskontext. Historische, verneinte,
    metaphorische oder zitierte Aussagen lösen die Prüfung nur dann nicht aus,
    wenn ihr Wortlaut von den engen Mustern abweicht (z. B. fehlendes "jetzt"
    oder ein eingeschobenes "nicht"); eine zitierte Aussage mit exakt
    passendem Wortlaut kann fälschlich auslösen. Dieses Risiko ist bewusst zur
    sicheren Seite (unnötiger Stopp statt übersehener Gefahr) in Kauf
    genommen; die abschließende, kontextsensitive Einordnung bleibt beim
    LLM-Interpreter, sofern die Prüfung hier nicht bereits auslöst.
    """

    normalized = _normalize_for_preflight(query)
    return any(pattern.search(normalized) for pattern in _IMMEDIATE_SENTENCE_PATTERNS)


_EXPLICIT_DIALOG_DENIALS: dict[Language, tuple[str, ...]] = {
    Language.DE: ("nein", "nein, gerade nicht", "es besteht gerade keine unmittelbare gefahr"),
    Language.EN: ("no", "no, not right now", "there is no immediate danger right now"),
    Language.PL: ("nie", "nie, nie teraz", "nie ma teraz bezpośredniego zagrożenia"),
    Language.RO: ("nu", "nu, nu acum", "nu există acum un pericol imediat"),
    Language.RU: ("нет", "нет, не сейчас", "сейчас непосредственной опасности нет"),
}


def safety_dialog_explicit_denial(query: str, language: Language) -> bool:
    """Bestätigt nur wenige eindeutige Antworten auf die geschlossene Safety-Frage.

    Damit kann ein Modellstatus allein den Safety-Abbruch nicht aufheben. Freie
    fachliche Zusätze oder Themenwechsel gelten nicht als Bestätigung.
    """

    normalized = _normalize_for_preflight(query).strip(" .!?")
    return normalized in _EXPLICIT_DIALOG_DENIALS[language]


def safety_text(language: Language, kind: SafetyTextKind, **values: str) -> str:
    """Liefert einen zentralen Text und fällt zuletzt sichtbar auf 112 zurück."""

    resource_id = f"safety.{kind.value}"
    for candidate in (language, Language.DE):
        try:
            text = application_text(candidate, resource_id, **values)
        except RuntimeError:
            continue
        if text.count(EMERGENCY_NUMBER) == 1:
            return text
    return EMERGENCY_NUMBER


class SafetyScenarioModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SafetyScenario(SafetyScenarioModel):
    scenario_id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,79}$")
    scenario_group: Literal["detected", "uncertain", "not_detected"]
    expected_risk_status: Literal["detected", "uncertain", "not_detected"]
    expected_policy_path: Literal["acute_risk", "acute_risk_clarification", "regular"]
    synthetic_inputs: dict[Language, str]

    @model_validator(mode="after")
    def validate_languages(self) -> "SafetyScenario":
        if set(self.synthetic_inputs) != set(Language):
            raise ValueError("safety scenario must contain every supported language")
        if any(not value.strip() or len(value) > 500 for value in self.synthetic_inputs.values()):
            raise ValueError("safety scenario input is empty or too long")
        return self


class SafetyScenarioCatalog(SafetyScenarioModel):
    contract_version: Literal[SAFETY_SCENARIO_CONTRACT_VERSION]
    policy_version: Literal[SAFETY_POLICY_VERSION]
    emergency_policy_version: Literal[EMERGENCY_POLICY.policy_version]
    synthetic_data_only: Literal[True]
    scenarios: list[SafetyScenario] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "SafetyScenarioCatalog":
        ids = [scenario.scenario_id for scenario in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("safety scenario IDs must be unique")
        return self


@lru_cache(maxsize=1)
def load_safety_scenarios() -> SafetyScenarioCatalog:
    path = packaged_bootstrap_data_root() / "safety" / "scenarios.json"
    try:
        return SafetyScenarioCatalog.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except OSError as exc:
        raise RuntimeError("safety_scenario_resource_missing") from exc
    except (ValueError, TypeError) as exc:
        raise RuntimeError("safety_scenario_resource_invalid") from exc
