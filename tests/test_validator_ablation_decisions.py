"""Fachentscheidungen 27.10.2026: observable output, not correctness ratings."""

import asyncio
import json

import pytest

from app.candidate_contract import CandidateRole
from app.formulation import AnswerType, BindingPolicy, ClaimType, FactType, FormulatorError, build_formulator_evidence
from app.formulator_prose import prose_evidence_payload, formulator_response_prompt
from app.grounding import validate_formulation
from app.hilfebus import contact_hint, operational_phone, prose_limit
from app.interpreter import AcuteRiskStatus, Need, RequestedService, ScopeStatus
from app.models import Language, QueryRequest
from app.policy_facts import EMERGENCY_NUMBER
from app.safety import SafetyTextKind, safety_text
from test_dialogue import client_with, interpretation
from test_formulation import _evidence, _response, app
from test_candidates import decide, interpretation as candidate_interpretation


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("route", ["out_of_scope", "no_verified_result", "general_help", "technical_fallback"])
def test_deterministic_hint_and_contact_tile_before_session_persistence(tmp_path, language, route):
    need = Need.UNKNOWN if route in {"general_help", "out_of_scope"} else Need.ADVICE
    scopes = ScopeStatus.OUT_OF_SCOPE if route == "out_of_scope" else ScopeStatus.IN_SCOPE
    client, _ = client_with(tmp_path, [interpretation(need, scope=scopes)])
    service = client.app.state.service
    if route == "technical_fallback":
        service.blablador = None
    if route == "no_verified_result":
        service.kb.offers[:] = [offer for offer in service.kb.offers if offer.id == "21"]
        # A deliberately unsupported explicit service, not a broken KB.
        service.blablador.responses = [interpretation(Need.MEDICAL, services=[RequestedService.WOUND_CARE])]
    result = client.post('/api/query', json={'query':'Hilfe bitte', 'language':language.value}).json()
    bus = service.kb.by_id()['21']
    assert result['answer'].endswith(contact_hint(bus, language))
    assert len(result['answer']) <= 600
    assert result['history'][-1]['answer'] == result['answer']
    assert [card['id'] for card in result['cards']].count('21') == 1
    card = next(card for card in result['cards'] if card['id'] == '21')
    assert card['address'] is None
    assert 'Demmering' not in json.dumps(card)
    assert 'Hauptbahnhof' not in json.dumps(card)
    assert '0175 6758041' not in result['answer']
    assert '0175 6758041' in ' '.join(card['phone_numbers'])
    assert '0175 6758041' not in card['spoken_text']
    assert not result['map_data'] or all(not item['id'].startswith('21:') for item in result['map_data']['destinations'])


@pytest.mark.parametrize("language", list(Language))
def test_acute_risk_stays_byte_equal_without_contact_tile(tmp_path, language):
    client, _ = client_with(tmp_path, [interpretation(Need.MEDICAL, risk=AcuteRiskStatus.DETECTED)])
    result = client.post('/api/query', json={'query':'Hilfe bitte', 'language':language.value}).json()
    assert result['answer'] == safety_text(language, SafetyTextKind.DETECTED)
    assert result['cards'] == []


@pytest.mark.parametrize("language", list(Language))
def test_medical_emergency_number_is_a_binding_policy_and_literal_allowance(app, language):
    evidence = _evidence(app, offer_ids=('25',), need=Need.MEDICAL, language=language)
    assert any(policy.policy_id == BindingPolicy.MEDICAL_EMERGENCY and EMERGENCY_NUMBER in policy.instruction
               for policy in evidence.binding_policies)
    texts={Language.DE:'Bei Gefahr ruf 112.',Language.EN:'In danger call 112.',Language.PL:'W razie zagrożenia zadzwoń pod 112.',
           Language.RO:'În pericol sună la 112.',Language.RU:'При опасности звони 112.'}
    # A policy-only block can cite the central policy without a made-up offer fact.
    from app.formulation import FormulatedSentence
    from app.formulator_prose import GroundedFormulatorResponse
    response=GroundedFormulatorResponse(contract_version='7',language=language,card_ids=[],sentences=[
        FormulatedSentence(text=texts[language],claim_type=ClaimType.UNCERTAINTY,offer_id=None,
                           fact_ids=[],policy_ids=[BindingPolicy.MEDICAL_EMERGENCY])])
    assert validate_formulation(response,evidence).answer == texts[language]
    response.sentences[0].text=texts[language].replace('112','999999')
    with pytest.raises(FormulatorError): validate_formulation(response,evidence)
    evidence.binding_policies=[p for p in evidence.binding_policies if p.policy_id != BindingPolicy.MEDICAL_EMERGENCY]
    response.sentences[0].text=texts[language]
    with pytest.raises(FormulatorError): validate_formulation(response,evidence)


@pytest.mark.parametrize("language", list(Language))
def test_hilfebus_evidence_has_only_operating_phone_and_no_office(app, language):
    evidence = _evidence(app, offer_ids=('21',), need=Need.FOOD, language=language)
    values=[fact.value for fact in evidence.selected_offers[0].facts if fact.fact_type == FactType.PHONE]
    assert values == [operational_phone(app.state.kb.by_id()['21'])]
    assert '0152 33661087' in values[0] and 'Einsatzzeiten' in values[0]
    assert 'Demmering' not in evidence.model_dump_json()
    assert not any(f.fact_type == FactType.ADDRESS for f in evidence.selected_offers[0].facts)
    for oid in ('12','13'):
        assert 'Demmering' in app.state.kb.by_id()[oid].address


@pytest.mark.parametrize("language", list(Language))
def test_matching_offer_boundary_and_reserved_model_length(app, language):
    from app.application_texts import application_text
    bus=app.state.kb.by_id()['21']
    limit=prose_limit(bus,language,AnswerType.NO_VERIFIED_RESULT.value)
    evidence=build_formulator_evidence(query='?',language=language,answer_type=AnswerType.NO_VERIFIED_RESULT,
        need=Need.ADVICE,offers=[],roles={},max_answer_chars=limit)
    text=application_text(language,'fallback.no_results')
    response=_response(evidence,text=text,claim_type=ClaimType.NO_RESULT,policy_ids=[BindingPolicy.NO_VERIFIED_RESULT])
    assert validate_formulation(response,evidence).answer == text
    response.sentences[0].text=text+' '+('a'*(limit-len(text)))
    with pytest.raises(FormulatorError):validate_formulation(response,evidence)
    assert limit+len(contact_hint(bus,language))+1 == 600


def test_sunday_food_keeps_bus_mandatory_and_prompt_explains_stand():
    decision=decide(candidate_interpretation(Need.FOOD,day='sunday'))
    assert '21' in {item.offer_id for item in decision.mandatory_candidates}
    prompt=formulator_response_prompt()
    assert 'Sunday stand, soup distribution and service-specific time' in prompt
    assert 'very severe symptoms or danger' in prompt
    assert 'Otherwise do not mention it' in prompt


@pytest.mark.parametrize('language',list(Language))
def test_sunday_food_fallback_has_stand_time_and_marker(tmp_path,language):
    client,_=client_with(tmp_path,[interpretation(Need.FOOD,facts={'requested_day':'sunday'})])
    result=client.post('/api/query',json={'query':'Essen Sonntag','language':language.value}).json()
    assert 'Hilfebus' in result['answer'] and '20:00' in result['answer'] and '21:00' in result['answer']
    card=next(c for c in result['cards'] if c['id']=='21')
    assert 'Westseite' in card['address']
    assert '21:hbf-west' in result['map_marker_ids']
    assert 'Demmering' not in json.dumps(result)


@pytest.mark.parametrize('language',list(Language))
def test_wound_query_reaches_medical_results_and_regular_contact_tile(tmp_path,language):
    client,_=client_with(tmp_path,[interpretation(Need.MEDICAL,services=[RequestedService.WOUND_CARE])])
    result=client.post('/api/query',json={'query':'Ich habe eine Wunde am Bein und brauche Versorgung',
                                        'language':language.value}).json()
    assert result['answer_type'] in {'grounded_result','grounded_referral'}
    assert {'10','24','25'} & {c['id'] for c in result['cards']}
    assert '21' in result['card_ids']
    assert not result['answer'].endswith(contact_hint(client.app.state.kb.by_id()['21'],language))


@pytest.mark.parametrize('query,oid',[('Scharni','8'),('Scharnhorst','8'),('Insel','9'),('Leipziger Oase','10'),('Oase','10'),
                                      ('Team Konsum','12'),('Team Wohnen','13')])
def test_old_names_remain_resolvable_aliases(app,query,oid):
    from app.candidates import build_selection_context
    context=build_selection_context(query=query,interpretation=candidate_interpretation(Need.GENERAL_HELP),
        offers=app.state.kb.offers,organization_aliases=app.state.kb.organization_aliases,ui_category=None)
    assert context.alias and oid in context.alias.offer_ids


def test_toilet_phone_and_fountain_review_status_are_not_prose_facts(app):
    from app.formulation import build_public_toilet_evidence, build_drinking_water_evidence
    from app.infrastructure_results import select_public_toilets, select_drinking_water_results
    toilets=select_public_toilets(app.state.kb.public_toilets).spoken_results
    packet=build_public_toilet_evidence(query='WC',language=Language.DE,toilets=list(toilets),distances={t.id:1 for t in toilets})
    assert all(f.fact_type != FactType.PHONE for offer in packet.selected_offers for f in offer.facts)
    # Internal metadata remains available to the validator, hidden from the model.
    from app.formulation import EvidenceFact
    packet.selected_offers[0].facts.append(EvidenceFact(fact_id='f_1111111111111111',fact_type=FactType.POTABLE_WATER_STATUS,value='verified'))
    assert all(f['fact_type'] != 'potable_water_status' for offer in prose_evidence_payload(packet)['selected_offers'] for f in offer['facts'])
