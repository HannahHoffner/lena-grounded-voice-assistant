"""Content support and declared citation quality are separate contracts."""

import asyncio

import pytest

from app.candidate_contract import CandidateRole
from app.formulation import AnswerType, ClaimType, FORMULATOR_CONTRACT_VERSION, FormulatorError, build_formulator_evidence
from app.grounding import validate_formulation
from app.grounding_references import resolve_offer_evidence
from app.interpreter import Need
from app.models import Language
from app.providers.llm import BlabladorProvider
from test_formulation import _settings
from test_grounding_claims import _answer, _evidence, _fact, app
from app.formulation import FactType
from app.grounding_constraints import price_services_match


def _recorded_response(app):
    evidence = build_formulator_evidence(
        query="Ich brauche einen Schlafplatz.", language=Language.DE,
        answer_type=AnswerType.GROUNDED_REFERRAL, need=Need.SLEEP,
        offers=[app.state.kb.by_id()["7"]], roles={"7": CandidateRole.REFERRAL_CONTACT},
        translation_catalog=app.state.service.translation_catalog,
        translation_policy=app.state.service.translation_policy,
    )
    name = _fact(evidence, FactType.DISPLAY_NAME)
    sleep = _fact(evidence, FactType.SERVICE, contains="5,00")
    place = _fact(evidence, FactType.PLACE_TYPE)
    address = _fact(evidence, FactType.ADDRESS)
    response = _answer(evidence,
        ("Melde dich bei “Rücke”.", ClaimType.REFERRAL, "7", [name.fact_id]),
        ("Sie bieten Übernachtung (5,00 € pro Nacht) und Wäschewaschen (2,50 €).",
         ClaimType.SERVICE, "7", [sleep.fact_id, place.fact_id]),
        ("Adresse: Rückmarsdorfer Straße 7, 04179 Leipzig.", ClaimType.FACT, "7", [address.fact_id]),
    )
    response.sentences[1].offer_id = "07"
    return evidence, response


def test_recorded_response_is_supported_without_rewriting_model_citations(app):
    evidence, response = _recorded_response(app)
    result = validate_formulation(response, evidence)
    assert result.card_ids == ["7"]
    assert result.answer == " ".join(" ".join(s.text.split()) for s in response.sentences)
    assert response.sentences[1].offer_id == "07"
    trace = result.reference_assessment
    assert trace["offer_id_normalizations"] == [{"provided": "07", "canonical": "7"}]
    laundry = _fact(evidence, FactType.SERVICE, contains="2,50")
    assert laundry.fact_id not in trace["declared_fact_ids"]["7"]
    assert laundry.fact_id in trace["available_fact_ids"]["7"]


def test_provider_exposes_internal_reference_assessment(app, monkeypatch):
    evidence, response = _recorded_response(app)
    from app.answer_plan import AnswerAct, FormulatorPlan
    response = FormulatorPlan(contract_version="6", language=evidence.requested_language,
        sentences=[AnswerAct(act="facts", offer_id="7",
            fact_ids=[_fact(evidence, FactType.SERVICE, contains="5,00").fact_id])], card_ids=["7"])
    provider = BlabladorProvider(_settings("blablador"))

    async def post(payload):
        return {"choices": [{"message": {"content": response.model_dump_json()}}]}

    monkeypatch.setattr(provider, "_post", post)
    result = asyncio.run(provider.formulate_answer(evidence=evidence))
    assert result.card_ids == ["7"]
    assert result.reference_assessment["scope"] == "selected_offer_evidence"
    assert result.reference_assessment["mode"] == "controlled_answer_plan"


@pytest.mark.parametrize("bad", ["999", "7.0", "vkkj_07"])
def test_unknown_and_non_integer_aliases_are_rejected(app, bad):
    evidence, response = _recorded_response(app)
    response.sentences[1].offer_id = bad
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        validate_formulation(response, evidence)


def test_colliding_numeric_alias_is_not_guessed(app):
    evidence, response = _recorded_response(app)
    other = evidence.selected_offers[0].model_copy(deep=True)
    other.offer_id = "07"
    other.facts = []
    evidence.selected_offers.append(other)
    response.sentences[1].offer_id = "007"
    with pytest.raises(FormulatorError):
        resolve_offer_evidence(response, evidence)


def test_card_aliases_use_canonical_ids_without_duplicate_cards(app):
    evidence, response = _recorded_response(app)
    response.card_ids = ["7", "007"]
    assert validate_formulation(response, evidence).card_ids == ["7"]


@pytest.mark.parametrize("text", [
    "Sie bieten Übernachtung (2,50 € pro Nacht).",
    "Sie bieten Wäschewaschen (5,00 €).",
    "Sie bieten Übernachtung (8,00 € pro Nacht).",
    "Sie bieten Übernachtung (2,50 €) und Wäschewaschen (5,00 €).",
])
def test_wrong_price_service_pair_is_rejected_even_if_amount_exists(app, text):
    evidence, response = _recorded_response(app)
    response.sentences[1].text = text
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


def test_missing_fact_is_rejected_when_not_in_selected_offer_packet(app):
    evidence, response = _recorded_response(app)
    evidence.selected_offers[0].facts = [f for f in evidence.selected_offers[0].facts if "2,50" not in f.value]
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


def test_explicit_wrong_or_cross_offer_fact_ids_are_still_invalid(app):
    evidence, response = _recorded_response(app)
    response.sentences[1].fact_ids.append("f_0000000000000000")
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        validate_formulation(response, evidence)


def test_missing_citation_uses_same_offer_evidence_not_other_offer(app):
    evidence = _evidence(app, offer_ids=("8", "10"))
    name = _fact(evidence, FactType.DISPLAY_NAME, offer_id="8")
    response = _answer(evidence, ("Nutze Scharni für Frauen.", ClaimType.ACTION, "8", [name.fact_id]))
    assert validate_formulation(response, evidence).card_ids == ["8"]
    evidence.selected_offers[0].facts = [name]
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


@pytest.mark.parametrize(("language", "sleep", "laundry", "joiner"), [
    (Language.DE, "Übernachtung", "Wäschewaschen", "und"),
    (Language.EN, "Overnight accommodation", "laundry", "and"),
    (Language.PL, "Nocleg", "pranie", "oraz"),
    (Language.RO, "Cazare", "spălat", "și"),
    (Language.RU, "Ночлег", "стирка", "и"),
])
def test_price_service_binding_in_supported_languages(language, sleep, laundry, joiner):
    facts = [("service", f"{sleep} (5,00 €)"), ("service", f"{laundry} (2,50 €)")]
    assert price_services_match(f"{sleep} (5,00 €) {joiner} {laundry} (2,50 €).", facts, language)
    assert not price_services_match(f"{sleep} (2,50 €) {joiner} {laundry} (5,00 €).", facts, language)


def test_price_before_named_service_is_also_bound():
    facts = [("service", "Übernachtung (5,00 €)"), ("service", "Wäschewaschen (2,50 €)")]
    assert price_services_match("5,00 € für Übernachtung.", facts, Language.DE)
    assert not price_services_match("2,50 € für Übernachtung.", facts, Language.DE)


def test_reference_assessment_reaches_stage_two_reports(tmp_path):
    import json
    from app.providers.llm import ProviderAnswer
    from app.live_evaluation import EvaluationStage, load_live_scenario_catalog
    from app.live_evaluation_runner import run_selector_formulator_live_gate
    from test_live_evaluation import FakeSelectorFormulatorProvider, _settings as live_settings

    class ReportingProvider(FakeSelectorFormulatorProvider):
        async def formulate_answer(self, *, evidence, **kwargs):
            return ProviderAnswer(answer="Synthetische Antwort.", card_ids=[o.offer_id for o in evidence.selected_offers],
                                  reference_assessment={"scope": "selected_offer_evidence"})

    settings = live_settings(tmp_path)
    limits = load_live_scenario_catalog().plan(EvaluationStage.SELECTOR_FORMULATOR).live_limits
    result = asyncio.run(run_selector_formulator_live_gate(settings, limits, provider_factory=ReportingProvider))
    rows = [json.loads(line) for line in (settings.runtime_dir / result["report_directory"] / "stage-results.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(row["reference_assessment"]["scope"] == "selected_offer_evidence"
               for row in rows if row["component"] == "formulator")


def test_reference_assessment_is_turn_bound_in_e2e_reports(tmp_path):
    import json
    from app.providers.llm import ProviderAnswer
    from app.live_evaluation import EvaluationStage, load_live_scenario_catalog
    from app.live_evaluation_runner import run_end_to_end_live_gate
    from test_live_evaluation import FakeFullPipelineProvider, _settings as live_settings

    class ReportingProvider(FakeFullPipelineProvider):
        async def formulate_answer(self, *, evidence, **kwargs):
            return ProviderAnswer(answer="Synthetische Antwort.", card_ids=[o.offer_id for o in evidence.selected_offers],
                                  reference_assessment={"scope": "selected_offer_evidence"})

    settings = live_settings(tmp_path)
    limits = load_live_scenario_catalog().plan(EvaluationStage.END_TO_END).live_limits
    result = asyncio.run(run_end_to_end_live_gate(settings, limits, provider_factory=ReportingProvider))
    rows = [json.loads(line) for line in (settings.runtime_dir / result["report_directory"] / "stage-results.jsonl").read_text(encoding="utf-8").splitlines()]
    assessments = [item for row in rows for item in row["reference_assessments"]]
    assert assessments
    assert all(item["scope"] == "selected_offer_evidence" and item["turn"] >= 1 for item in assessments)
