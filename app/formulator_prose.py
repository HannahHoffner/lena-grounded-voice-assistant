"""Current fact-referenced LLM prose contract, distinct from historical plans."""

import json
from typing import Literal

from .formulation import (
    FORMULATOR_CONTRACT_VERSION, FORMULATOR_SYSTEM_PROMPT,
    FormulatorEvidence, FormulatorResponse,
)


class GroundedFormulatorResponse(FormulatorResponse):
    """The model's actual visible text, checked atomically against evidence."""

    contract_version: Literal[FORMULATOR_CONTRACT_VERSION]


def formulator_response_prompt() -> str:
    """Keep JSON guidance synchronized with the actual strict parser schema."""
    return FORMULATOR_SYSTEM_PROMPT + "\nResponse JSON Schema:\n" + json.dumps(
        GroundedFormulatorResponse.model_json_schema(), ensure_ascii=False, separators=(",", ":"),
    )


def prose_evidence_payload(evidence: FormulatorEvidence) -> dict:
    """Expose the selected bounded evidence, not the full KB or prior answers.

    Capability codes stay available to the validator. Names/roles already have
    explicit fields; model citations are restricted to human-readable facts.
    Original fact values and IDs remain unchanged.
    """
    payload = evidence.model_dump(mode="json")
    hidden = {"capability", "offer_type", "place_type", "potable_water_status"}
    for offer in payload["selected_offers"]:
        offer["facts"] = [f for f in offer["facts"] if f["fact_type"] not in hidden]
    return payload
