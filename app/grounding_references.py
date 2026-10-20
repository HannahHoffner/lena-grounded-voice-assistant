"""Selected-offer reference resolution; never consult the full knowledge base."""

import re

from .formulation import EvidenceFact, FormulatorError, FormulatorEvidence, FormulatorResponse


def resolve_offer_evidence(
    response: FormulatorResponse, evidence: FormulatorEvidence,
) -> tuple[FormulatorResponse, dict[str, list[EvidenceFact]], dict[str, object]]:
    """Preserve model citations separately from the evidence used for checking."""
    offers = {offer.offer_id: offer for offer in evidence.selected_offers}
    facts = {fact.fact_id: offer.offer_id for offer in evidence.selected_offers for fact in offer.facts}
    normalized = response.model_copy(deep=True)
    changes = []

    def resolve(value: str, code: str) -> str:
        if value in offers:
            return value
        matches = []
        if re.fullmatch(r"[0-9]+", value):
            key = value.lstrip("0") or "0"
            matches = [item for item in offers if re.fullmatch(r"[0-9]+", item)
                       and (item.lstrip("0") or "0") == key]
        if len(matches) != 1:
            raise FormulatorError(code)
        changes.append({"provided": value, "canonical": matches[0]})
        return matches[0]

    declared: dict[str, list[str]] = {}
    for sentence in normalized.sentences:
        if sentence.offer_id is None:
            continue
        sentence.offer_id = resolve(sentence.offer_id, "formulator_invalid_fact")
        for fact_id in sentence.fact_ids:
            if facts.get(fact_id) != sentence.offer_id:
                raise FormulatorError("formulator_invalid_fact")
        declared.setdefault(sentence.offer_id, []).extend(sentence.fact_ids)
    normalized.card_ids = list(dict.fromkeys(resolve(item, "formulator_invalid_card") for item in normalized.card_ids))
    pools = {offer_id: list(offers[offer_id].facts) for offer_id in declared}
    assessment = {
        "scope": "selected_offer_evidence",
        "offer_id_normalizations": changes,
        "declared_fact_ids": {key: list(dict.fromkeys(value)) for key, value in declared.items()},
        "available_fact_ids": {key: [fact.fact_id for fact in value] for key, value in pools.items()},
    }
    return normalized, pools, assessment
