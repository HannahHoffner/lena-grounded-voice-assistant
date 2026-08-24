"""Vertrags-, Grounding- und Budgettests der Formulierungsstufe."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.candidate_contract import CandidateRole
from app.config import Settings
from app.formulation import (
    EVIDENCE_CONTRACT_VERSION,
    FORMULATOR_CONTRACT_VERSION,
    FORMULATOR_PROMPT_VERSION,
    FORMULATOR_SYSTEM_PROMPT,
    AnswerType,
    BindingPolicy,
    ClaimType,
    FactType,
    FormulatedSentence,
    FormulatorError,
    FormulatorResponse,
    GroundingDiagnosticCode,
    build_formulator_evidence,
)
from app.application_texts import application_text
from app.grounding import SUPPORTED_DOMAIN_STEMS, validate_formulation
from app.interpreter import Need, QueryInterpretation
from app.llm_budget import LLMBudgetExhausted, LLMRequestBudget
from app.llm_selection import CandidateSelectionResponse
from app.main import create_app
from app.models import Language, QueryInteraction, QueryRequest
from app.providers.llm import BlabladorProvider, ProviderAnswer


ROOT = Path(__file__).resolve().parents[1]


def _settings(provider: str = "template", **changes: object) -> Settings:
    base = Settings(
        app_root=ROOT,
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider=provider,
        blablador_base_url="https://example.invalid/v1" if provider == "blablador" else None,
        blablador_api_key="test-token" if provider == "blablador" else None,
        blablador_model="test-model" if provider == "blablador" else None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        interaction_logging_enabled=False,
    )
    return replace(base, **changes)


@pytest.fixture(scope="module")
def app():
    return create_app(_settings())


def _evidence(
    app,
    *,
    offer_ids: tuple[str, ...] = ("8",),
    offers: list | None = None,
    language: Language = Language.DE,
    answer_type: AnswerType = AnswerType.GROUNDED_RESULT,
    roles: dict[str, CandidateRole] | None = None,
    mandatory_ids: set[str] | None = None,
    query: str = "Ich brauche Hilfe.",
):
    offers = offers if offers is not None else [app.state.kb.by_id()[offer_id] for offer_id in offer_ids]
    role_map = roles or {offer.id: CandidateRole.DIRECT_SERVICE for offer in offers}
    return build_formulator_evidence(
        query=query,
        language=language,
        answer_type=answer_type,
        need=Need.SLEEP,
        offers=offers,
        roles=role_map,
        mandatory_ids=mandatory_ids or set(),
    )


def _fact(evidence, kind: FactType, *, offer_id: str | None = None, contains: str | None = None):
    for offer in evidence.selected_offers:
        if offer_id and offer.offer_id != offer_id:
            continue
        for fact in offer.facts:
            if fact.fact_type == kind and (contains is None or contains in fact.value):
                return fact
    raise AssertionError(f"missing {kind}")


def _response(
    evidence,
    *,
    text: str,
    claim_type: ClaimType = ClaimType.ACTION,
    offer_id: str | None = None,
    fact_ids: list[str] | None = None,
    policy_ids: list[BindingPolicy] | None = None,
    card_ids: list[str] | None = None,
    language: Language | None = None,
):
    bound_offer = offer_id if offer_id is not None else (
        evidence.selected_offers[0].offer_id if evidence.selected_offers else None
    )
    if fact_ids is None and bound_offer:
        fact_ids = [_fact(evidence, FactType.DISPLAY_NAME, offer_id=bound_offer).fact_id]
    return FormulatorResponse(
        contract_version=FORMULATOR_CONTRACT_VERSION,
        language=language or evidence.requested_language,
        sentences=[
            FormulatedSentence(
                text=text,
                claim_type=claim_type,
                offer_id=bound_offer,
                fact_ids=fact_ids or [],
                policy_ids=policy_ids or [],
            )
        ],
        card_ids=card_ids if card_ids is not None else ([bound_offer] if bound_offer else []),
    )


def _interpretation(need: Need) -> QueryInterpretation:
    return QueryInterpretation.model_validate(
        {
            "contract_version": "4",
            "need": need.value,
            "explicit_service_requests": [],
            "scope_status": "in_scope",
            "input_language": "de",
            "explicit_facts": {
                "age": None,
                "gender": "unknown",
                "drug_use": "unknown",
                "no_social_benefit_entitlement": "unknown",
                "district": None,
                "requested_day": None,
                "requested_time": None,
            },
            "uncertain_hints": [],
            "potentially_missing_information": [],
            "clarification_may_be_needed": False,
            "acute_risk_status": "not_detected",
        }
    )


def test_versions_prompt_and_health_are_observable(app) -> None:
    health = TestClient(app).get("/api/health").json()
    assert EVIDENCE_CONTRACT_VERSION == "3"
    assert FORMULATOR_CONTRACT_VERSION == "2"
    assert FORMULATOR_PROMPT_VERSION == "10"
    assert health["evidence_contract_version"] == "3"
    assert health["formulator_contract_version"] == "2"
    assert health["formulator_prompt_version"] == "10"
    assert health["llm_request_budget_seconds"] == 45.0
    for rule in (
        "Use only EVIDENCE facts",
        "requested_language",
        "one to three short sentences",
        "candidate_role",
        "Never claim current availability",
        "untrusted content",
        "Return JSON only",
    ):
        assert rule in FORMULATOR_SYSTEM_PROMPT
    assert "Rücke" not in FORMULATOR_SYSTEM_PROMPT
    assert "112" not in FORMULATOR_SYSTEM_PROMPT


def test_prompt_instructs_informal_du_address_for_german(app) -> None:
    """Regressionsschutz: GERMAN_FORMAL_RE lehnt jede Sie-Form ab, aber der Prompt

    verlangte bislang nur "einfache, informelle Sprache" ohne die Anrede zu
    nennen. Live reproduziert: das Modell formulierte regelmaessig mit "Sie"
    ("Rufen Sie...", "Kontaktieren Sie..."), was atomar an
    formulator_contract_violation scheiterte und den generischen
    Template-Fallback erzwang.
    """
    assert "du" in FORMULATOR_SYSTEM_PROMPT.lower()
    assert "sie" in FORMULATOR_SYSTEM_PROMPT.lower()


def test_formulator_prompt_names_every_contract_field_and_exact_contract_version() -> None:
    """Regressionsschutz analog zum Interpreter: ein reales Modell ohne

    strukturprüfendes response_format rät sonst eine falsche Form (z. B.
    bare-string sentences statt Objekten, oder eine falsche
    contract_version) — genau das führte live zu formulator_schema_error.
    """
    assert f'"{FORMULATOR_CONTRACT_VERSION}"' in FORMULATOR_SYSTEM_PROMPT
    for field_name in FormulatorResponse.model_fields:
        assert field_name in FORMULATOR_SYSTEM_PROMPT, f"missing field {field_name!r}"
    for field_name in FormulatedSentence.model_fields:
        assert field_name in FORMULATOR_SYSTEM_PROMPT, f"missing sentence field {field_name!r}"


def test_formulator_prompt_matches_enforced_first_claim_and_reference_rules() -> None:
    """The prompt must not invite structures rejected by the grounding contract."""
    for rule in (
        "grounded_referral and ambiguous_help_fallback: referral",
        "Never set claim_type to action or service for a referral_contact",
        "grounded_result: action or service",
        "out_of_scope: domain_boundary",
        "no_verified_result: no_result",
        "set policy_ids to []",
        "set offer_id to null and fact_ids to []",
        "Prefer the smallest grounded answer",
        "current_query is never evidence",
        "For a referral_contact, write only a short contact/ask/get-help instruction plus the exact display_name",
        "For a direct_service, write only a short go/contact instruction plus the exact display_name",
        "fact_ids must include a matching service, capability, or description fact",
        "fact_ids must include a matching target_group, eligible_gender, minimum_age, maximum_age, or access fact",
        "If you cannot identify the required matching fact_id with certainty, omit the detail",
        "immutable output token",
        "copy its value character-for-character",
        "Never translate, transliterate, abbreviate, inflect, decline, pluralize",
        "Grammar must adapt around the unchanged name",
        "do not name or paraphrase the user's need",
        "every visible need or service has a matching cited fact in the same sentence",
    ):
        assert rule in FORMULATOR_SYSTEM_PROMPT


def test_evidence_is_a_positive_list_for_only_final_runtime_offers(app) -> None:
    evidence = _evidence(app, offer_ids=("7", "8"), mandatory_ids={"7"})
    payload = evidence.model_dump(mode="json")
    assert set(payload) == {
        "evidence_version",
        "prompt_version",
        "requested_language",
        "answer_type",
        "current_query",
        "need",
        "selected_offers",
        "binding_policies",
    }
    assert all(
        set(item) == {"offer_id", "display_name", "candidate_role", "mandatory", "facts"}
        for item in payload["selected_offers"]
    )
    assert all(set(fact) == {"fact_id", "fact_type", "value"} for item in payload["selected_offers"] for fact in item["facts"])
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("raw_fields", "raw_properties", "source_index", "review_notes", '"offer_id": "1"'):
        assert forbidden not in serialized
    assert [item["offer_id"] for item in payload["selected_offers"]] == ["7", "8"]


def test_all_runtime_offers_have_opaque_unique_facts_and_exclude_social_office(app) -> None:
    offers = app.state.kb.offers
    fact_ids = []
    projected_ids = []
    for offer in offers:
        evidence = build_formulator_evidence(
            query="Hilfe",
            language=Language.DE,
            answer_type=AnswerType.GROUNDED_RESULT,
            need=Need.GENERAL_HELP,
            offers=[offer],
            roles={offer.id: CandidateRole.DIRECT_SERVICE},
        )
        projected_ids.append(evidence.selected_offers[0].offer_id)
        fact_ids.extend(fact.fact_id for fact in evidence.selected_offers[0].facts)
    assert all(fact_id.startswith("f_") and len(fact_id) == 18 for fact_id in fact_ids)
    assert len(fact_ids) == len(set(fact_ids))
    assert projected_ids == [offer.id for offer in offers]
    assert not {"1", "2", "3", "4"}.intersection(app.state.kb.by_id())


@pytest.mark.parametrize(
    ("language", "text"),
    [
        (Language.DE, "Geh zu Scharni."),
        (Language.EN, "Go to Scharni."),
        (Language.PL, "Idź do Scharni."),
        (Language.RO, "Mergi la Scharni."),
        (Language.RU, "Обратись в Scharni."),
    ],
)
def test_grounded_short_answer_in_all_languages(app, language: Language, text: str) -> None:
    evidence = _evidence(app, language=language)
    validated = validate_formulation(_response(evidence, text=text), evidence)
    assert validated.answer == text
    assert validated.card_ids == ["8"]
    assert validated.sentence_count == 1


def test_operational_facts_must_be_cited_and_exact(app) -> None:
    evidence = _evidence(app)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    address = _fact(evidence, FactType.ADDRESS)
    response = _response(
        evidence,
        text=f"Geh zu {name.value}, {address.value}.",
        fact_ids=[name.fact_id, address.fact_id],
    )
    assert "Georg-Schumann-Str. 268" in validate_formulation(response, evidence).answer


def test_curated_phone_name_and_price_format_must_remain_exact(app) -> None:
    scharni = _evidence(app)
    name = _fact(scharni, FactType.DISPLAY_NAME)
    phone = _fact(scharni, FactType.PHONE)
    changed_phone = _response(
        scharni,
        text="Ruf Scharni unter 0341 420920 0 an.",
        fact_ids=[name.fact_id, phone.fact_id],
    )
    with pytest.raises(FormulatorError, match="formulator_ungrounded_claim"):
        validate_formulation(changed_phone, scharni)

    changed_name = _response(scharni, text="Geh zu scharni.")
    with pytest.raises(FormulatorError, match="formulator_ungrounded_claim") as changed_name_error:
        validate_formulation(changed_name, scharni)
    assert changed_name_error.value.diagnostic_code == GroundingDiagnosticCode.PROPER_NAME_NOT_EXACT

    ruecke = _evidence(app, offer_ids=("7",))
    ruecke_name = _fact(ruecke, FactType.DISPLAY_NAME)
    valid_name = _response(ruecke, text="Kontaktiere Rücke.", fact_ids=[ruecke_name.fact_id])
    assert validate_formulation(valid_name, ruecke).answer == "Kontaktiere Rücke."
    changed_suffix = _response(ruecke, text="Kontaktiere Rücken.", fact_ids=[ruecke_name.fact_id])
    with pytest.raises(FormulatorError, match="formulator_ungrounded_claim") as suffix_error:
        validate_formulation(changed_suffix, ruecke)
    assert suffix_error.value.diagnostic_code == GroundingDiagnosticCode.PROPER_NAME_NOT_EXACT

    price = _fact(ruecke, FactType.SERVICE, contains="5,00")
    changed_price = _response(
        ruecke,
        text="R\u00fccke kostet 5.00 \u20ac.",
        claim_type=ClaimType.SERVICE,
        fact_ids=[_fact(ruecke, FactType.DISPLAY_NAME).fact_id, price.fact_id],
    )
    with pytest.raises(FormulatorError, match="formulator_ungrounded_claim") as price_error:
        validate_formulation(changed_price, ruecke)
    assert price_error.value.diagnostic_code in {
        GroundingDiagnosticCode.NUMBER_NOT_CITED,
        GroundingDiagnosticCode.PRICE_NOT_CITED,
    }


def test_sentence_with_e_v_abbreviation_is_not_treated_as_multiple_sentences(app) -> None:
    """Regressionsschutz: Die deutsche Vereinsform "e. V." im Angebotsnamen

    darf nicht fälschlich als Satzbruch (mehrere Sätze) gelten. Live
    reproduziert: 18 Angebote im Katalog enthalten "e. V." im Namen; jede
    Formulierung, die den Namen (auch nur teilweise) zitierte, schlug an
    dieser Prüfung fehl und erzwang den statischen Template-Fallback. Seit dem
    Fix für rohe Organisations-Rechtsnamen (Untersuchung zu unbemerkten
    Fallbacks, Folgefix) zeigt kein reales Angebot mehr "e. V." im
    Anzeigenamen; das Szenario wird daher mit einem synthetisch benannten
    Angebot nachgestellt statt mit echten Katalogdaten.
    """
    offer = app.state.kb.by_id()["24"].model_copy(update={"display_name": "CABL e. V."})
    evidence = _evidence(app, offers=[offer])
    name_fact = _fact(evidence, FactType.DISPLAY_NAME)
    assert "e. V." in name_fact.value
    response = _response(
        evidence,
        text="Geh zu CABL e. V. in Leipzig.",
        claim_type=ClaimType.ACTION,
        fact_ids=[name_fact.fact_id],
    )
    assert validate_formulation(response, evidence).answer == "Geh zu CABL e. V. in Leipzig."


def test_offer_name_containing_menschen_is_not_treated_as_target_assertion(app) -> None:
    """Regressionsschutz: TARGET_ASSERTION_RE darf nicht ueber das Praefix "men"

    in "Menschen" ausloesen. Live reproduziert: Jede Formulierung, die den
    amtlichen Namen von Angebot 25 ("... von Menschen ohne festen Wohnsitz")
    zitierte, wurde faelschlich als unbelegte Zielgruppenbehauptung abgelehnt
    und erzwang den generischen Template-Fallback ("Diese Angebote passen zu
    deiner Frage: ..."). Seit dem Fix für rohe Organisations-Rechtsnamen
    (Untersuchung zu unbemerkten Fallbacks, Folgefix) zeigt Angebot 25 den
    kuratierten Kurznamen "UVO"; das Szenario wird daher mit einem
    synthetisch benannten Angebot nachgestellt statt mit echten Katalogdaten.
    """
    offer = app.state.kb.by_id()["25"].model_copy(
        update={"display_name": "Umfeldnahe Versorgung von Menschen ohne festen Wohnsitz"}
    )
    evidence = _evidence(app, offers=[offer])
    name = _fact(evidence, FactType.DISPLAY_NAME)
    assert "Menschen" in name.value
    response = _response(
        evidence,
        text=f"Kontaktiere {name.value} telefonisch.",
        claim_type=ClaimType.ACTION,
        fact_ids=[name.fact_id],
    )
    assert validate_formulation(response, evidence).answer == f"Kontaktiere {name.value} telefonisch."


def test_target_assertion_still_rejects_real_gender_and_age_claims(app) -> None:
    """Die Praezisierung darf echte Zielgruppenbehauptungen nicht durchlassen."""
    evidence = _evidence(app)
    for text in ("Scharni ist für Männer.", "Scharni ist nur für Erwachsene."):
        with pytest.raises(FormulatorError, match="formulator_ungrounded_claim"):
            validate_formulation(_response(evidence, text=text), evidence)


def test_impersonal_pronoun_man_does_not_trigger_target_assertion(app) -> None:
    """Regressionsschutz: Das deutsche unpersoenliche Pronomen "man" ("man kann

    sich melden") ist keine Geschlechts-/Zielgruppenbehauptung und darf nicht
    ueber die englischen Zielgruppen-Stichworte "man"/"men" ausloesen.
    """
    evidence = _evidence(app)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    response = _response(
        evidence,
        text=f"Bei {name.value} kann man sich telefonisch melden.",
        claim_type=ClaimType.ACTION,
        fact_ids=[name.fact_id],
    )
    assert "man" in response.sentences[0].text
    assert validate_formulation(response, evidence).answer == response.sentences[0].text


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("Geh zu Scharni in der Scharnhorststr. 27.", "formulator_ungrounded_claim"),
        ("Ruf Scharni unter 0341 99999999 an.", "formulator_ungrounded_claim"),
        ("Scharni ist jetzt geöffnet.", "formulator_ungrounded_claim"),
        ("Scharni hat freie Plätze.", "formulator_ungrounded_claim"),
        ("Scharni bietet Wundversorgung an.", "formulator_ungrounded_claim"),
        ("Scharni ist für Männer.", "formulator_ungrounded_claim"),
        ("Geh zu Scharni unter https://erfunden.example.", "formulator_ungrounded_claim"),
        ("Geh zu Scharni um 23:59.", "formulator_ungrounded_claim"),
        ("Geh zu Scharni, Angebot ID 8.", "formulator_contract_violation"),
        ("Geh zu Scharni. Das ist ein zweiter Satz.", "formulator_contract_violation"),
        ("<script>Geh zu Scharni.</script>", "formulator_contract_violation"),
        ("**Geh zu Scharni.**", "formulator_contract_violation"),
    ],
)
def test_ungrounded_and_contract_attacks_are_rejected(app, text: str, code: str) -> None:
    evidence = _evidence(app)
    with pytest.raises(FormulatorError, match=code):
        validate_formulation(_response(evidence, text=text), evidence)


def test_unknown_or_cross_offer_fact_is_rejected_atomically(app) -> None:
    evidence = _evidence(app, offer_ids=("8", "10"))
    unknown = "f_0000000000000000"
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        validate_formulation(_response(evidence, text="Geh zu Scharni.", fact_ids=[unknown]), evidence)
    other_name = _fact(evidence, FactType.DISPLAY_NAME, offer_id="10")
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        validate_formulation(_response(evidence, text="Geh zu Scharni.", fact_ids=[other_name.fact_id]), evidence)


def test_referral_contact_cannot_be_claimed_as_direct_service(app) -> None:
    evidence = _evidence(
        app,
        offer_ids=("7",),
        answer_type=AnswerType.GROUNDED_REFERRAL,
        roles={"7": CandidateRole.REFERRAL_CONTACT},
        mandatory_ids={"7"},
    )
    service = _fact(evidence, FactType.SERVICE)
    with pytest.raises(FormulatorError, match="formulator_ungrounded_claim"):
        validate_formulation(
            _response(
                evidence,
                text="Rücke gibt dir sicher einen Schlafplatz.",
                claim_type=ClaimType.SERVICE,
                fact_ids=[service.fact_id],
            ),
            evidence,
        )
    name = _fact(evidence, FactType.DISPLAY_NAME)
    valid = _response(
        evidence,
        text="Melde dich bei Rücke.",
        claim_type=ClaimType.REFERRAL,
        fact_ids=[name.fact_id],
    )
    assert validate_formulation(valid, evidence).card_ids == ["7"]


def test_cards_are_limited_to_evidence_and_deterministic_order(app) -> None:
    evidence = _evidence(app, offer_ids=("8", "10"), mandatory_ids={"8"})
    response = _response(
        evidence,
        text="Geh zu Scharni.",
        offer_id="8",
        card_ids=["10", "8"],
    )
    assert validate_formulation(response, evidence).card_ids == ["8", "10"]
    invalid = response.model_copy(update={"card_ids": ["1"]})
    with pytest.raises(FormulatorError, match="formulator_invalid_card"):
        validate_formulation(invalid, evidence)


def test_out_of_scope_uses_only_policy_evidence(app) -> None:
    evidence = build_formulator_evidence(
        query="Wo ist ein Friseur?",
        language=Language.DE,
        answer_type=AnswerType.OUT_OF_SCOPE,
        need=Need.UNKNOWN,
        offers=[],
        roles={},
    )
    response = FormulatorResponse(
        contract_version="2",
        language=Language.DE,
        sentences=[
            FormulatedSentence(
                text="LENA beantwortet diese Frage nicht.",
                claim_type=ClaimType.DOMAIN_BOUNDARY,
                policy_ids=[BindingPolicy.OUT_OF_SCOPE_BOUNDARY],
            ),
            FormulatedSentence(
                text="Ich helfe bei Essen, Wasser, Schlafen, Medizin, Beratung und Toiletten in Leipzig.",
                claim_type=ClaimType.DOMAIN_BOUNDARY,
                policy_ids=[BindingPolicy.SUPPORTED_DOMAINS],
            ),
        ],
        card_ids=[],
    )
    assert validate_formulation(response, evidence).card_ids == []


def test_out_of_scope_policy_rejects_a_substantive_world_knowledge_answer(app) -> None:
    evidence = build_formulator_evidence(
        query="Wo ist ein Friseur?",
        language=Language.DE,
        answer_type=AnswerType.OUT_OF_SCOPE,
        need=Need.UNKNOWN,
        offers=[],
        roles={},
    )
    response = _response(
        evidence,
        text="Der beste Friseur ist am Leipziger Markt.",
        claim_type=ClaimType.DOMAIN_BOUNDARY,
        offer_id=None,
        policy_ids=[BindingPolicy.OUT_OF_SCOPE_BOUNDARY, BindingPolicy.SUPPORTED_DOMAINS],
        card_ids=[],
    )
    with pytest.raises(FormulatorError, match="formulator_ungrounded_claim"):
        validate_formulation(response, evidence)


@pytest.mark.parametrize(
    ("language", "text"),
    [
        (Language.DE, "Diese Frage kann ich nicht beantworten; ich helfe bei Essen, Wasser und Schlafen in Leipzig."),
        (Language.EN, "I cannot answer this; I help with food, water and sleep in Leipzig."),
        (Language.PL, "Nie mogę odpowiedzieć; pomagam w sprawach jedzenia, wody i noclegu w Lipsku."),
        (Language.RO, "Nu pot răspunde; te ajut cu mâncare, apă și dormit în Leipzig."),
        (Language.RU, "Не могу ответить; я помогаю с едой, водой и ночлегом в Лейпциге."),
    ],
)
def test_out_of_scope_policy_is_validated_in_all_languages(app, language: Language, text: str) -> None:
    evidence = build_formulator_evidence(
        query="out of scope",
        language=language,
        answer_type=AnswerType.OUT_OF_SCOPE,
        need=Need.UNKNOWN,
        offers=[],
        roles={},
    )
    response = _response(
        evidence,
        text=text,
        claim_type=ClaimType.DOMAIN_BOUNDARY,
        offer_id=None,
        policy_ids=[BindingPolicy.OUT_OF_SCOPE_BOUNDARY, BindingPolicy.SUPPORTED_DOMAINS],
        card_ids=[],
    )
    assert validate_formulation(response, evidence).answer == text


@pytest.mark.parametrize("language", list(Language))
def test_out_of_scope_fallback_text_names_all_six_supported_domains(language: Language) -> None:
    """AP10: der statische Fallback-Text muss alle sechs unterstützten Bereiche
    nennen, nicht nur eine Teilmenge (Wasser und Toiletten fehlten zuvor).

    SUPPORTED_DOMAIN_STEMS[Language.RU] enthält zwei alternative Stämme für
    die Schlaf-Domäne ("спа"/"ноч"); der Bezugstext nutzt konsistent mit dem
    Rest der Anwendung nur "ночлег", daher wird hier auf mindestens sechs
    Treffer statt auf jeden einzelnen Stamm geprüft.
    """
    text = application_text(language, "fallback.out_of_scope").casefold()
    matches = sum(stem in text for stem in SUPPORTED_DOMAIN_STEMS[language])
    assert matches >= 6, f"{language}: only {matches} domain stems found in {text!r}"


@pytest.mark.parametrize(
    ("language", "text"),
    [
        (Language.DE, "Ich habe kein passendes Angebot in den freigegebenen Daten gefunden."),
        (Language.EN, "I found no matching offer in the approved data."),
        (Language.PL, "Brak pasującej oferty w zatwierdzonych danych."),
        (Language.RO, "Nu am găsit o ofertă potrivită în datele aprobate."),
        (Language.RU, "Не нашлось подходящего предложения в проверенных данных."),
    ],
)
def test_no_result_policy_is_validated_in_all_languages(app, language: Language, text: str) -> None:
    evidence = build_formulator_evidence(
        query="nothing found",
        language=language,
        answer_type=AnswerType.NO_VERIFIED_RESULT,
        need=Need.MEDICAL,
        offers=[],
        roles={},
    )
    response = _response(
        evidence,
        text=text,
        claim_type=ClaimType.NO_RESULT,
        offer_id=None,
        policy_ids=[BindingPolicy.NO_VERIFIED_RESULT],
        card_ids=[],
    )
    assert validate_formulation(response, evidence).answer == text


def test_service_out_of_scope_formulator_gets_no_offer_data(app) -> None:
    service = app.state.service
    original = service.blablador
    captured = {}

    class Provider:
        async def interpret_query(self, **kwargs):
            result = _interpretation(Need.UNKNOWN)
            return result.model_copy(update={"scope_status": "out_of_scope"})

        def context_fits(self, evidence) -> bool:
            return True

        async def formulate_answer(self, **kwargs):
            evidence = kwargs["evidence"]
            captured["evidence"] = evidence
            return ProviderAnswer(
                "Diese Friseurfrage kann ich nicht beantworten; ich helfe bei Essen, Wasser und Schlafen in Leipzig.",
                [],
                sentence_count=1,
                answer_type=evidence.answer_type,
            )

    try:
        service.blablador = Provider()
        response = asyncio.run(service.query(QueryRequest(query="Wo ist ein Friseur?", language=Language.DE)))
    finally:
        service.blablador = original

    evidence = captured["evidence"]
    assert evidence.answer_type == AnswerType.OUT_OF_SCOPE
    assert evidence.selected_offers == []
    assert {item.policy_id for item in evidence.binding_policies} >= {
        BindingPolicy.OUT_OF_SCOPE_BOUNDARY,
        BindingPolicy.SUPPORTED_DOMAINS,
        BindingPolicy.NO_WORLD_KNOWLEDGE,
    }
    assert response.provider == "blablador"
    assert response.cards == []


def test_hilfebus_formulation_uses_only_curated_referral_evidence(app) -> None:
    service = app.state.service
    original = service.blablador
    captured = {}

    class Provider:
        def context_fits(self, evidence) -> bool:
            return True

        async def formulate_answer(self, **kwargs):
            evidence = kwargs["evidence"]
            captured["evidence"] = evidence
            return ProviderAnswer(
                "Melde dich beim Hilfebus.",
                [evidence.selected_offers[0].offer_id],
                answer_type=evidence.answer_type,
            )

    try:
        service.blablador = Provider()
        response = asyncio.run(
            service._hilfebus_response(
                Language.DE,
                query="Hilfe",
                interaction=QueryInteraction(),
                budget=LLMRequestBudget(45.0, lambda: 0.0),
                provider_failed=False,
            )
        )
    finally:
        service.blablador = original

    offer = captured["evidence"].selected_offers[0]
    assert offer.offer_id == "21"
    assert offer.candidate_role == CandidateRole.REFERRAL_CONTACT.value
    assert any(fact.fact_type == FactType.PHONE for fact in offer.facts)
    assert any(fact.fact_type in {FactType.STAND_TIME, FactType.OPENING_TIME} for fact in offer.facts)
    assert {fact.fact_type for fact in offer.facts}.issubset(
        {FactType.DISPLAY_NAME, FactType.PHONE, FactType.STAND_TIME, FactType.OPENING_TIME}
    )
    assert response.cards[0].id == "21"


def test_response_schema_rejects_extra_fields_and_more_than_three_sentences() -> None:
    valid_sentence = {
        "text": "Kurz.",
        "claim_type": "no_result",
        "offer_id": None,
        "fact_ids": [],
        "policy_ids": ["no_verified_result"],
    }
    with pytest.raises(ValidationError):
        FormulatorResponse.model_validate(
            {
                "contract_version": "2",
                "language": "de",
                "sentences": [valid_sentence],
                "card_ids": [],
                "answer": "freier Alttext",
            }
        )
    with pytest.raises(ValidationError):
        FormulatorResponse.model_validate(
            {
                "contract_version": "2",
                "language": "de",
                "sentences": [valid_sentence] * 4,
                "card_ids": [],
            }
        )


def test_wrong_language_and_mixed_script_are_rejected(app) -> None:
    ru = _evidence(app, language=Language.RU)
    with pytest.raises(FormulatorError, match="formulator_invalid_language"):
        validate_formulation(_response(ru, text="Go to Scharni."), ru)
    ro = _evidence(app, language=Language.RO)
    with pytest.raises(FormulatorError, match="formulator_invalid_language"):
        validate_formulation(_response(ro, text="Mergi la Scharni сейчас."), ro)


@pytest.mark.parametrize(
    ("language", "text"),
    [
        (Language.PL, "Idź do Scharni, für Hilfe."),
        (Language.RO, "Mergi la Scharni für Hilfe."),
        (Language.DE, "Geh zu Scharni, proszę."),
        (Language.DE, "Geh zu Scharni, mulțumesc."),
        (Language.EN, "Go to Scharni für Hilfe."),
        (Language.EN, "Go to Scharni, proszę."),
    ],
)
def test_latin_script_language_mismatch_is_rejected(app, language: Language, text: str) -> None:
    """Ein anderssprachiger diakritischer Fingerabdruck in Fließtext lehnt die Sprachpruefung ab."""
    evidence = _evidence(app, language=language)
    with pytest.raises(FormulatorError, match="formulator_invalid_language"):
        validate_formulation(_response(evidence, text=text), evidence)


def test_provider_requires_pure_json_and_exact_language(app, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = BlabladorProvider(_settings("blablador"))
    evidence = _evidence(app, language=Language.RO)

    async def markdown(_: dict) -> dict:
        return {"choices": [{"message": {"content": "```json\n{}\n```"}}]}

    monkeypatch.setattr(provider, "_post", markdown)
    with pytest.raises(FormulatorError, match="formulator_invalid_json"):
        asyncio.run(provider.formulate_answer(evidence=evidence))

    response = _response(evidence, text="Go to Scharni.", language=Language.EN)

    async def wrong_language(_: dict) -> dict:
        return {"choices": [{"message": {"content": response.model_dump_json()}}]}

    monkeypatch.setattr(provider, "_post", wrong_language)
    with pytest.raises(FormulatorError, match="formulator_invalid_language"):
        asyncio.run(provider.formulate_answer(evidence=evidence))


@pytest.mark.parametrize(
    ("content", "error_code"),
    [
        ("direct prose", "formulator_invalid_json"),
        (json.dumps({"answer": "legacy", "card_ids": []}), "formulator_schema_error"),
        ("x" * 3_001, "formulator_contract_violation"),
    ],
)
def test_provider_maps_parser_and_contract_failures_to_stable_codes(
    app,
    monkeypatch: pytest.MonkeyPatch,
    content: str,
    error_code: str,
) -> None:
    provider = BlabladorProvider(_settings("blablador"))
    evidence = _evidence(app)

    async def response(_: dict) -> dict:
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    with pytest.raises(FormulatorError, match=error_code):
        asyncio.run(provider.formulate_answer(evidence=evidence))


def test_provider_rejects_a_schema_valid_but_unknown_fact_reference(app, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = BlabladorProvider(_settings("blablador"))
    evidence = _evidence(app)
    response = _response(evidence, text="Geh zu Scharni.")
    response.sentences[0].fact_ids = ["f_0000000000000000"]

    async def model_response(_: dict) -> dict:
        return {"choices": [{"message": {"content": response.model_dump_json()}}]}

    monkeypatch.setattr(provider, "_post", model_response)
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        asyncio.run(provider.formulate_answer(evidence=evidence))


class _Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def test_llm_budget_uses_monotonic_provider_elapsed_time_and_truncates_stage() -> None:
    clock = _Clock()
    budget = LLMRequestBudget(20.0, clock)
    first = budget.begin(15.0)
    assert first.timeout_seconds == 15.0
    clock.advance(14.0)
    budget.finish(first)
    second = budget.begin(10.0)
    assert second.timeout_seconds == 6.0
    clock.advance(6.0)
    budget.finish(second)
    assert budget.exhausted
    with pytest.raises(LLMBudgetExhausted):
        budget.begin(30.0)


def test_exhausted_request_budget_skips_formulator_and_uses_template(app) -> None:
    clock = _Clock()
    service = app.state.service
    original_provider = service.blablador
    original_clock = service.monotonic_clock
    original_settings = service.settings
    original_wall_clock = service.clock
    # Eingefroren auf Montag 10:00, da die selektierbare Kandidatenmenge für
    # Need.FOOD ein geöffnetes Angebot voraussetzt; ohne feste Uhr hängt der
    # Testerfolg von der realen Tageszeit ab (WP9C).
    service.clock = lambda: datetime(2026, 8, 3, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    calls: list[str] = []

    class Provider:
        async def interpret_query(self, **kwargs):
            calls.append("interpreter")
            assert kwargs["timeout_seconds"] == 15.0
            clock.advance(14.0)
            return _interpretation(Need.FOOD)

        async def select_candidates(self, **kwargs):
            calls.append("selector")
            assert kwargs["timeout_seconds"] == 6.0
            clock.advance(6.0)
            return CandidateSelectionResponse(
                contract_version="1",
                selection_status="selected",
                selected_ids=[kwargs["decision"].selectable_candidates[0].offer_id],
            )

        def context_fits(self, evidence) -> bool:
            return True

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            calls.append("formulator")
            raise AssertionError("budget must stop the formulator")

    try:
        service.blablador = Provider()
        service.monotonic_clock = clock
        service.settings = replace(service.settings, llm_request_budget_seconds=20.0)
        response = asyncio.run(service.query(QueryRequest(query="Wo gibt es Essen?", language=Language.DE)))
    finally:
        service.blablador = original_provider
        service.monotonic_clock = original_clock
        service.settings = original_settings
        service.clock = original_wall_clock

    assert calls == ["interpreter", "selector"]
    assert response.provider == "template"
    assert response.interaction.formulator_error_code == "formulator_skipped_budget"
    assert response.interaction.llm_budget_status == "llm_budget_exhausted"


def test_tts_rejects_text_not_equal_to_last_validated_answer(app) -> None:
    client = TestClient(app)
    query = client.post("/api/query", json={"query": "Wo gibt es Essen?", "language": "de"}).json()
    rejected = client.post(
        "/api/speech/synthesize",
        json={"text": "Manipulierter Text", "language": "de", "session_id": query["session_id"]},
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"] == "tts_text_invalid"


def test_tts_rejects_an_older_answer_after_a_new_session_turn(app) -> None:
    class Provider:
        async def interpret_query(self, **kwargs):
            need = Need.SLEEP if "schlaf" in kwargs["query"].casefold() else Need.FOOD
            return _interpretation(need)

        def context_fits(self, _evidence):
            return False

    original_provider = app.state.service.blablador
    original_clock = app.state.service.clock
    app.state.service.blablador = Provider()
    # Eingefroren auf Montag 10:00, da der erste Turn Need.FOOD interpretiert
    # und ein geöffnetes Angebot voraussetzt; ohne feste Uhr hängt der
    # Testerfolg von der realen Tageszeit ab (WP9C). Der zweite Turn nutzt
    # bewusst Need.SLEEP statt Need.ADVICE: Beide Bedarfe führen in diesem
    # Katalog zur selben Mehrfachtreffer-Vorlage mit identischem Organisations-
    # text, wodurch die Antworten fälschlich gleich wären und die eigentliche
    # Testaussage (unterschiedliche Antworten je Turn) nicht mehr geprüft
    # würde.
    app.state.service.clock = lambda: datetime(2026, 8, 3, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    client = TestClient(app)
    try:
        first = client.post("/api/query", json={"query": "Ich habe Hunger.", "language": "de"}).json()
        second = client.post(
            "/api/query",
            json={
                "query": "Ich brauche einen Schlafplatz.",
                "language": "de",
                "session_id": first["session_id"],
            },
        ).json()
    finally:
        app.state.service.blablador = original_provider
        app.state.service.clock = original_clock
    assert second["session_id"] == first["session_id"]
    assert first["answer"] != second["answer"]
    rejected = client.post(
        "/api/speech/synthesize",
        json={"text": first["answer"], "language": "de", "session_id": first["session_id"]},
    )
    assert rejected.status_code == 409
