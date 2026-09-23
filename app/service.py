"""Orchestriert Sessions, Schutzregeln, Kandidaten, LLM und Template-Antworten."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from .application_texts import application_text
from .candidate_contract import CandidateDecision, CandidateRole, ReasonCode, SelectionStatus
from .candidates import CandidateSelector, build_selection_context
from .config import Settings
from .i18n import load_translation_catalog, localize_offer_card
from .spoken_text import offer_spoken_text
from .formulation import (
    AnswerType,
    FormulatorError,
    GroundingDiagnosticCode,
    build_drinking_water_evidence,
    build_formulator_evidence,
    build_public_toilet_evidence,
)
from .infrastructure_results import (
    DrinkingWaterResult,
    drinking_fountain_card,
    drinking_water_map_data,
    select_drinking_water_results,
    select_public_toilets,
    toilet_card,
    toilet_map_data,
)
from .dialogue import (
    DialogRequestError,
    DialogState,
    DialogStatus,
    DialogType,
    clarification_block,
    dialogue_text,
    load_dialogue_resource,
    new_dialog,
    visible_choice_text,
)
from .dialogue_flow import (
    choose_dialog,
    interpretation_from_choices,
    interpreter_dialog_context,
    is_clear_topic_change,
    known_facts,
    merge_dialog_facts,
)
from .interpreter import (
    AcuteRiskStatus,
    Need,
    QueryInterpretation,
    RequestedService,
    ScopeStatus,
    interpreter_alias_hints,
)
from .kb_loader import KnowledgeBase
from .llm_selection import (
    SelectionOutcome,
    SelectorBypassReason,
    SelectorError,
    bypass_outcome,
    fallback_outcome,
    selected_outcome,
)
from .llm_budget import LLMBudgetExhausted, LLMRequestBudget
from .maps import build_map_data
from .models import (
    ChatTurn,
    Language,
    MapData,
    OfferCard,
    OfferRecord,
    QueryInteraction,
    QueryRequest,
    QueryResponse,
)
from .providers.llm import BlabladorProvider, InterpreterError, ProviderAnswer, ProviderError
from .retrieval import normalize_text
from .result_ordering import order_social_results
from .safety import (
    SafetyPath,
    SafetyTextKind,
    preflight_detects_immediate_danger,
    safety_dialog_explicit_denial,
    safety_text,
)
from .sessions import SessionStore
from .spatial import LEIPZIG_HBF, distance_from_hbf
from .translation_contract import TranslationRuntimePolicy


LOGGER = logging.getLogger(__name__)

# A `FormulatorError` (contract violation, ungrounded claim, ...) is usually a
# single sampling weakness of the model, not a structural fault -- see
# docs/exec-plans/fix-formulator-fallback-sie-and-menschen-collision.md. One
# retry with a fresh sample clears a meaningful share of these without
# loosening the citation requirement itself. 2 = the original attempt plus one
# retry.
FORMULATOR_MAX_ATTEMPTS = 2

# Transport-level failures, not sampling weaknesses -- retrying buys nothing
# (a timeout is likely to time out again) and only spends the shared LLM
# request budget that another stage may still need.
_FORMULATOR_NON_RETRYABLE_ERRORS = frozenset({"formulator_timeout", "formulator_http_error"})


def _fallback_text(language: Language, key: str, **values: str) -> str:
    try:
        return application_text(language, f"fallback.{key}", **values)
    except RuntimeError:
        if language == Language.DE:
            raise
        return application_text(Language.DE, f"fallback.{key}", **values)


SELF_PATTERNS = {
    "wer bist du", "was ist lena", "was machst du", "who are you", "what is lena", "what do you do",
    "kim jestes", "co to jest lena", "cine esti", "ce este lena", "кто ты", "что такое lena",
}


def _matches_phrase(query: str, phrases: set[str]) -> bool:
    normalized = normalize_text(query)
    return any(normalize_text(phrase) in normalized for phrase in phrases)


def _explicit_drinking_fountain_request(query: str) -> bool:
    return _matches_phrase(query, {
        "trinkbrunnen",
        "trinkwasserbrunnen",
        "drinking fountain",
        "fontanna z wodą pitną",
        "fântână cu apă potabilă",
        "питьевой фонтан",
    })


def _card(
    offer: OfferRecord,
    language: Language,
    translation_catalog,
    translation_policy: TranslationRuntimePolicy,
) -> OfferCard:
    card = localize_offer_card(offer, language, translation_catalog, translation_policy)
    # Die Quelladresse des mobilen Hilfebus bleibt in Runtime/Provenienz, ist
    # aber kein Nutzerstandort. Sichtbar ist nur der separat belegte
    # Sonntagsstand, wenn der konkrete Leistungs- und Zeitpfad ihn zulässt.
    if offer.place_type == "help_bus":
        card.address = None
        card.spoken_text = offer_spoken_text(
            offer.model_copy(update={"address": None}), language,
            short_description=card.short_description, services=card.services,
            opening_hours_raw=card.opening_hours_raw, notes=card.notes,
        )
    return card


def _adopt_card_spoken_text(map_data: MapData | None, cards: list) -> None:
    """Lässt Kartenpunkte, die auch eine Karte haben, deren spoken_text übernehmen.

    Karte und Kartenpunkt-Tafel sollen beim Vorlesen nie auseinanderlaufen;
    die Karte ist die maßgebliche (ggf. lokalisierte) Quelle.
    """
    if not map_data:
        return
    spoken_by_id = {card.id: card.spoken_text for card in cards if card.spoken_text}
    for destination in map_data.destinations:
        if destination.id in spoken_by_id:
            destination.spoken_text = spoken_by_id[destination.id]


def _general_help_contact(offers: list[OfferRecord]) -> OfferRecord | None:
    return next((offer for offer in offers if "general_help_referral_first" in offer.priority_rules), None)


def _general_help_contact_times(offer: OfferRecord) -> str:
    """Liefert mobile Einsatz-/Anrufzeiten vor einer einzelnen Standzeit."""

    return "; ".join(offer.opening_hours_raw or offer.standzeiten_raw) or "—"


def _template_found(language: Language, offers: list[OfferRecord]) -> str:
    names = ", ".join(offer.name for offer in offers[:2])
    return _fallback_text(language, "found", names=names)


def _record_selector_outcome(
    interaction: QueryInteraction,
    decision: CandidateDecision,
    outcome: SelectionOutcome,
) -> None:
    """Überträgt ausschließlich redigierte Auswahlmetadaten in die Beobachtbarkeit."""
    interaction.selector_used = outcome.selector_used
    interaction.selection_source = outcome.selection_source.value
    interaction.selector_bypass_reason = outcome.bypass_reason.value if outcome.bypass_reason else None
    interaction.selector_eligible_count = len(decision.mandatory_candidates) + len(decision.selectable_candidates)
    interaction.selector_final_count = len(outcome.final_ids)
    interaction.selector_fallback_used = outcome.fallback_used
    interaction.selector_error_code = outcome.error_code
    interaction.fallback_used = interaction.fallback_used or outcome.fallback_used


def _record_selector_bypass(
    interaction: QueryInteraction,
    reason: SelectorBypassReason,
    *,
    eligible_count: int = 0,
) -> None:
    interaction.selector_used = False
    interaction.selector_bypass_reason = reason.value
    interaction.selector_eligible_count = eligible_count


def _template_for_offers(
    language: Language,
    decision: CandidateDecision,
    offers: list[OfferRecord],
) -> str:
    priority_id = next(
        (
            item.offer_id
            for item in decision.candidates
            if ReasonCode.GENERAL_SLEEP_CONTACT_PRIORITY in item.reason_codes
        ),
        None,
    )
    priority_offer = next((offer for offer in offers if offer.id == priority_id), None)
    if priority_offer and priority_offer.address:
        return _fallback_text(language, "sleep_priority", address=priority_offer.address)
    first_role = next((item.role for item in decision.candidates if item.offer_id == offers[0].id), None)
    if first_role == CandidateRole.REFERRAL_CONTACT:
        return _fallback_text(language, "referral_found", name=offers[0].display_name or offers[0].name)
    return _template_found(language, offers)


@dataclass(frozen=True)
class _CoreOutcome:
    response: QueryResponse
    next_dialog: DialogState | None = None
    visible_question: str = ""


class QueryService:
    """Zentraler Anwendungsdienst für eine vollständig geerdete Nutzeranfrage.

    Der Dienst verwendet Blablador nur, wenn alle Voraussetzungen erfüllt sind.
    Jeder Provider- oder Validierungsfehler fällt auf deterministische Logik
    zurück und verändert die zugrunde liegenden Angebotsdaten nicht.
    """
    def __init__(
        self,
        settings: Settings,
        kb: KnowledgeBase,
        *,
        clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        if (
            kb.source_kind != "curated_wfs"
            or not kb.runtime_kb_fingerprint
            or not kb.runtime_validated
        ):
            raise ValueError("QueryService requires a validated curated runtime knowledge base")
        if any(offer.id in {"1", "2", "3", "4"} for offer in kb.offers):
            raise ValueError("QueryService received excluded source records")
        self.settings = settings
        self.hbf_origin = LEIPZIG_HBF.model_copy(
            update={"latitude": settings.hbf_latitude, "longitude": settings.hbf_longitude}
        )
        self.kb = kb
        load_dialogue_resource()
        self.translation_policy = TranslationRuntimePolicy(settings.translation_runtime_policy)
        self.translation_catalog = load_translation_catalog(settings, kb)
        self.interpreter_aliases = interpreter_alias_hints(kb.offers, kb.organization_aliases)
        self.candidate_selector = CandidateSelector()
        self.clock = clock or (lambda: datetime.now(ZoneInfo("Europe/Berlin")))
        self.monotonic_clock = monotonic_clock or time.monotonic
        self.sessions = SessionStore(
            (settings.runtime_dir or settings.app_root / "runtime") / "sessions.json",
            timeout_seconds=settings.session_timeout_seconds,
            max_sessions=settings.session_max_entries,
        )
        self.blablador: BlabladorProvider | None = None
        if settings.blablador_configured:
            try:
                self.blablador = BlabladorProvider(settings)
            except ProviderError as exc:
                LOGGER.warning("query.provider.init_failed", extra={"error_type": type(exc).__name__})
                self.blablador = None

    @property
    def effective_provider(self) -> str:
        return "blablador" if self.blablador else "template"

    @property
    def interpreter_available(self) -> bool:
        return self.blablador is not None

    @property
    def formulator_context_available(self) -> bool:
        return self.blablador is not None

    @property
    def selector_available(self) -> bool:
        return callable(getattr(self.blablador, "select_candidates", None))

    def _safety_stop(
        self,
        language: Language,
        interaction: QueryInteraction,
        *,
        path: SafetyPath,
        kind: SafetyTextKind,
        risk_status: AcuteRiskStatus,
        dialogue_result: str | None = None,
        visible_question: str = "",
    ) -> _CoreOutcome:
        """Beendet eine Anfrage vor jedem fachlichen oder modellbasierten Folgepfad."""
        interaction.route = "acute_risk"
        interaction.answer_type = AnswerType.ACUTE_RISK.value
        interaction.acute_risk_detected = risk_status == AcuteRiskStatus.DETECTED
        interaction.acute_risk_status = risk_status.value
        interaction.safety_path = path.value
        interaction.safety_dialogue_used = dialogue_result is not None
        interaction.safety_dialogue_result = dialogue_result
        interaction.safety_response_language = language
        _record_selector_bypass(interaction, SelectorBypassReason.SAFETY_STOP)
        LOGGER.warning("safety.request.stopped", extra={"safety_path": path.value})
        return _CoreOutcome(
            QueryResponse(
                answer=safety_text(language, kind),
                language=language,
                provider="template",
                status="no_results",
                answer_type=AnswerType.ACUTE_RISK.value,
            ),
            visible_question=visible_question,
        )

    def _technical_safety_fallback(
        self,
        language: Language,
        interaction: QueryInteraction,
        *,
        visible_question: str = "",
    ) -> _CoreOutcome:
        """Interpreter nicht verfügbar oder fehlgeschlagen (kein Blablador, Timeout,
        HTTP-, JSON-, Schema- oder Vertragsfehler, Budgeterschöpfung).

        Gibt bewusst keinen reinen "versuche es erneut"-Text mehr aus, sondern den
        deterministischen Hilfebus-Kontakt (kein LLM nötig, siehe
        `_general_help_contact()`), sobald die Wissensbasis ihn liefert -- eine
        technische Störung soll nicht zur Sackgasse werden. Der bedingte
        112-Hinweis bleibt in jedem Fall Teil des Texts: `preflight_detects_immediate_danger()`
        läuft zwar bereits vor jedem Interpreteraufruf, ist aber bewusst eng
        gefasst (siehe `safety.py`) und fängt nicht jede echte Akutgefahr ab.
        Ist kein Hilfebus-Angebot in der Wissensbasis vorhanden, bleibt es beim
        bisherigen reinen 112-Text -- ebenso wie in `main.py`, wo mangels
        geladener Wissensbasis ohnehin kein Kontakt ermittelbar ist.
        """
        interaction.route = "interpreter_error"
        interaction.answer_type = AnswerType.TECHNICAL_FALLBACK.value
        interaction.safety_path = SafetyPath.INTERPRETER_FAILURE.value
        interaction.safety_fallback_used = True
        interaction.safety_response_language = language
        interaction.fallback_used = True
        _record_selector_bypass(interaction, SelectorBypassReason.INTERPRETER_UNAVAILABLE)
        offer = _general_help_contact(self.kb.offers)
        cards: list[OfferCard] = []
        if offer:
            phone = ", ".join(offer.phone_numbers) or "—"
            times = _general_help_contact_times(offer)
            answer = safety_text(language, SafetyTextKind.TECHNICAL_HILFEBUS, phone=phone, times=times)
            cards = [_card(offer, language, self.translation_catalog, self.translation_policy)]
        else:
            answer = safety_text(language, SafetyTextKind.TECHNICAL)
        return _CoreOutcome(
            QueryResponse(
                answer=answer,
                cards=cards,
                language=language,
                provider="template",
                status="error",
                answer_type=AnswerType.TECHNICAL_FALLBACK.value,
            ),
            visible_question=visible_question,
        )

    def _safety_dialog(
        self,
        language: Language,
        interpretation: QueryInterpretation,
        interaction: QueryInteraction,
        *,
        attempt_count: int = 1,
        visible_question: str = "",
        path: SafetyPath = SafetyPath.UNCERTAIN_DIALOG,
    ) -> _CoreOutcome:
        dialog = new_dialog(
            DialogType.ACUTE_RISK_CONFIRMATION,
            need=interpretation.need,
            services=interpretation.explicit_service_requests,
            fingerprint=self.kb.runtime_kb_fingerprint or "",
            session_timeout_seconds=self.settings.session_timeout_seconds,
            facts=known_facts(interpretation),
            attempt_count=attempt_count,
        )
        interaction.route = "acute_risk_clarification"
        interaction.answer_type = "acute_risk_clarification"
        interaction.acute_risk_status = AcuteRiskStatus.UNCERTAIN.value
        interaction.safety_path = path.value
        interaction.safety_dialogue_used = True
        interaction.safety_dialogue_result = "awaiting_answer"
        interaction.safety_response_language = language
        interaction.dialog_type = dialog.dialog_type.value
        interaction.dialog_attempt_count = dialog.attempt_count
        _record_selector_bypass(interaction, SelectorBypassReason.SAFETY_STOP)
        return _CoreOutcome(
            QueryResponse(
                answer=dialogue_text(language, "prompts", dialog.dialog_type.value),
                language=language,
                provider="template",
                status="no_results",
                answer_type="acute_risk_clarification",
            ),
            dialog,
            visible_question,
        )

    async def query(self, payload: QueryRequest) -> QueryResponse:
        """Beantwortet eine Anfrage und aktualisiert ihren lokalen Sessionzustand.

        Args:
            payload: Validierte Frage, Sprache, Kategorie und optionale Session-ID.

        Returns:
            Geerdete Antwort einschließlich Karten und neuem Sessionzustand.

        Side Effects:
            Liest und schreibt die dateibasierte Sessionablage.
        """
        session = self.sessions.resolve(
            payload.session_id,
            payload.language,
            self.kb.runtime_kb_fingerprint or "",
        )
        conversation_history = list(session.turns)
        interaction = QueryInteraction(data_release_id=self.kb.release_id)
        active_dialog: DialogState | None = None
        if payload.choice_values:
            session, active_dialog = self.sessions.claim_dialog(
                session,
                dialog_id=payload.dialog_id or "",
                choice_values=payload.choice_values,
            )
        elif (
            session.dialog
            and session.dialog.status == DialogStatus.AWAITING_ANSWER
            and (
                payload.query
                or session.dialog.dialog_type == DialogType.ACUTE_RISK_CONFIRMATION
            )
        ):
            if payload.dialog_id and payload.dialog_id != session.dialog.dialog_id:
                raise DialogRequestError()
            session, active_dialog = self.sessions.claim_dialog(
                session,
                dialog_id=session.dialog.dialog_id,
            )
        elif payload.dialog_id:
            raise DialogRequestError()
        outcome = await self._query_core(
            payload,
            conversation_history,
            interaction,
            active_dialog=active_dialog,
        )
        session = self.sessions.set_dialog(session, outcome.next_dialog)
        next_dialog = outcome.next_dialog
        response = outcome.response
        if next_dialog:
            response.clarification = clarification_block(next_dialog, payload.language)
        kb_by_id = self.kb.by_id()
        selected_offers = [kb_by_id[card.id] for card in response.cards if card.id in kb_by_id]
        map_data = response.map_data or build_map_data(selected_offers, language=payload.language, origin=self.hbf_origin)
        if map_data:
            # `build_map_data()`/`offer_stand_destinations()` (app/maps.py) build every
            # destination straight from the (German) `OfferRecord` -- that module has no
            # translation catalog, deliberately, to keep it pure geometry/offer-data. This
            # is the one place with both the full destination list (map_data is
            # intentionally uncapped, unlike the ~4 answer-citation `response.cards`) and
            # the translation catalog, so it re-localizes every destination that's backed
            # by a KB offer. Non-offer destinations (public toilets, drinking fountains)
            # aren't in `kb_by_id` and are already localized at their own source.
            for destination in map_data.destinations:
                base_id, _, stand_suffix = destination.id.partition(":")
                offer = kb_by_id.get(base_id)
                if offer is None:
                    continue
                card = _card(offer, payload.language, self.translation_catalog, self.translation_policy)
                if stand_suffix:
                    # A stand destination (e.g. "<id>:hbf-west") carries a hand-authored
                    # label/address/description/opening_hours for that one stand location
                    # (see offer_stand_destinations()) -- only the fields it otherwise
                    # inherits unchanged from the offer get localized here.
                    destination.services = card.services
                    destination.notes = card.notes
                    destination.spoken_text = offer_spoken_text(
                        offer.model_copy(update={
                            "display_name": destination.label,
                            "address": destination.address,
                        }), payload.language,
                        short_description=destination.description or "",
                        services=destination.services,
                        opening_hours_raw=destination.opening_hours,
                        notes=destination.notes,
                    )
                else:
                    destination.label = card.name
                    destination.description = card.short_description
                    destination.phone_numbers = card.phone_numbers
                    destination.opening_hours = card.opening_hours_raw[:4]
                    destination.services = card.services
                    destination.standzeiten_raw = card.standzeiten_raw
                    destination.notes = card.notes
                    destination.spoken_text = card.spoken_text
        persisted_question = outcome.visible_question or payload.query
        if interaction.safety_path != SafetyPath.NONE.value:
            persisted_question = application_text(payload.language, "safety.redacted_input")
        speakable_texts = [card.spoken_text for card in response.cards if card.spoken_text]
        if map_data:
            speakable_texts += [
                destination.spoken_text for destination in map_data.destinations if destination.spoken_text
            ]
        if response.clarification:
            speakable_texts.append(response.clarification.spoken_text)
        updated_session = self.sessions.add_turn(
            session,
            question=persisted_question,
            answer=response.answer,
            speakable_texts=speakable_texts,
        )
        response.session_id = updated_session.session_id
        response.question = outcome.visible_question or payload.query
        response.history = updated_session.turns
        response.map_data = map_data
        response.answer_type = interaction.answer_type or response.answer_type
        if not response.card_ids:
            response.card_ids = [card.id for card in response.cards]
        if not response.spoken_result_ids:
            response.spoken_result_ids = response.card_ids[:3]
        if not response.map_marker_ids and map_data:
            response.map_marker_ids = [destination.id for destination in map_data.destinations]
        interaction.source_ids = [
            card.id for card in response.cards if getattr(card, "record_type", "social_offer") == "social_offer"
        ]
        response.interaction = interaction
        return response

    async def _query_core(
        self,
        payload: QueryRequest,
        conversation_history: list[ChatTurn],
        interaction: QueryInteraction,
        *,
        active_dialog: DialogState | None,
    ) -> _CoreOutcome:
        language = payload.language
        query = payload.query
        llm_budget = LLMRequestBudget(
            self.settings.llm_request_budget_seconds,
            self.monotonic_clock,
        )

        if query and preflight_detects_immediate_danger(query):
            return self._safety_stop(
                language,
                interaction,
                path=SafetyPath.PREFLIGHT_DETECTED,
                kind=SafetyTextKind.DETECTED,
                risk_status=AcuteRiskStatus.DETECTED,
                visible_question=query,
            )

        safety_dialog_open = bool(
            active_dialog and active_dialog.dialog_type == DialogType.ACUTE_RISK_CONFIRMATION
        )
        # Nur reine Systemfragen dürfen den Interpreter umgehen. Zusätze können
        # Gefahr enthalten; ein offener Safety-Dialog braucht eine explizite Antwort.
        if not safety_dialog_open and normalize_text(query) in SELF_PATTERNS:
            interaction.route = "self_description"
            interaction.answer_type = AnswerType.SYSTEM_DESCRIPTION.value
            _record_selector_bypass(interaction, SelectorBypassReason.SYSTEM_RESPONSE)
            return _CoreOutcome(QueryResponse(answer=_fallback_text(language, "self_description"), language=language, provider="template", status="ok"))

        if not safety_dialog_open and not query and payload.category is None and not payload.choice_values:
            dialog = new_dialog(
                DialogType.GENERAL_NEED,
                need=Need.GENERAL_HELP,
                fingerprint=self.kb.runtime_kb_fingerprint or "",
                session_timeout_seconds=self.settings.session_timeout_seconds,
            )
            interaction.route = "dialog_general_need"
            interaction.answer_type = AnswerType.CLARIFICATION.value
            interaction.dialog_type = dialog.dialog_type.value
            _record_selector_bypass(interaction, SelectorBypassReason.DIALOGUE_REQUIRED)
            return _CoreOutcome(
                QueryResponse(
                    answer=dialogue_text(language, "prompts", dialog.dialog_type.value),
                    language=language,
                    provider="template",
                    status="no_results",
                ),
                dialog,
            )

        interpretation: QueryInterpretation | None = None
        interpreter_failed = False
        visible_question = ""
        if payload.choice_values and active_dialog:
            interpretation = interpretation_from_choices(active_dialog, payload.choice_values, language)
            visible_question = visible_choice_text(active_dialog, payload.choice_values, language)
        elif self.blablador:
            try:
                allocation = llm_budget.begin(self.settings.llm_interpreter_timeout_seconds)
                try:
                    interpretation = await self.blablador.interpret_query(
                        query=query or (payload.category.value if payload.category else "help"),
                        language=language,
                        category=payload.category,
                        aliases=self.interpreter_aliases,
                        conversation_history=[] if active_dialog else conversation_history,
                        dialog_context=(interpreter_dialog_context(active_dialog) if active_dialog else None),
                        timeout_seconds=allocation.timeout_seconds,
                    )
                finally:
                    llm_budget.finish(allocation)
                LOGGER.info(
                    "query.interpreter.completed",
                    extra={"contract_version": interpretation.contract_version},
                )
            except LLMBudgetExhausted:
                interpreter_failed = True
                interaction.fallback_used = True
                interaction.interpreter_error_code = "llm_budget_exhausted"
                interaction.llm_budget_status = "llm_budget_exhausted"
                LOGGER.warning("query.llm_budget.exhausted", extra={"stage": "interpreter"})
            except InterpreterError as exc:
                interpreter_failed = True
                interaction.fallback_used = True
                interaction.interpreter_error_code = exc.code
                if llm_budget.exhausted:
                    interaction.llm_budget_status = "llm_budget_exhausted"
                LOGGER.warning(
                    "query.interpreter.failed",
                    extra={"error_code": exc.code},
                )
                LOGGER.info("query.fallback.used", extra={"stage": "interpreter"})
        else:
            interpreter_failed = True

        if interpreter_failed:
            if active_dialog:
                interaction.dialog_type = active_dialog.dialog_type.value
                interaction.dialog_attempt_count = active_dialog.attempt_count
                interaction.dialog_result_status = "technical_error"
            return self._technical_safety_fallback(
                language,
                interaction,
                visible_question=visible_question or query,
            )

        if interpretation is None:
            return self._technical_safety_fallback(language, interaction, visible_question=visible_question)

        interaction.acute_risk_status = interpretation.acute_risk_status.value
        if interpretation.acute_risk_status == AcuteRiskStatus.DETECTED:
            return self._safety_stop(
                language,
                interaction,
                path=SafetyPath.INTERPRETER_DETECTED,
                kind=SafetyTextKind.DETECTED,
                risk_status=AcuteRiskStatus.DETECTED,
                dialogue_result=("confirmed" if active_dialog else None),
                visible_question=visible_question,
            )
        if interpretation.acute_risk_status == AcuteRiskStatus.UNCERTAIN:
            explicitly_unsure = bool(
                active_dialog
                and active_dialog.dialog_type == DialogType.ACUTE_RISK_CONFIRMATION
                and "immediate_danger_unsure" in payload.choice_values
            )
            if explicitly_unsure or (
                active_dialog
                and active_dialog.dialog_type == DialogType.ACUTE_RISK_CONFIRMATION
                and active_dialog.attempt_count >= active_dialog.max_attempts
            ):
                return self._safety_stop(
                    language,
                    interaction,
                    path=SafetyPath.UNCERTAIN_CONSERVATIVE,
                    kind=SafetyTextKind.UNCERTAIN,
                    risk_status=AcuteRiskStatus.UNCERTAIN,
                    dialogue_result="uncertain",
                    visible_question=visible_question,
                )
            return self._safety_dialog(
                language,
                interpretation,
                interaction,
                attempt_count=(active_dialog.attempt_count + 1 if active_dialog else 1),
                visible_question=visible_question,
            )

        if active_dialog and active_dialog.dialog_type == DialogType.ACUTE_RISK_CONFIRMATION:
            explicit_no = "immediate_danger_no" in payload.choice_values
            compatible_text_denial = (
                not payload.choice_values
                and safety_dialog_explicit_denial(query, language)
                and interpretation.scope_status == ScopeStatus.IN_SCOPE
                and (
                    # Ein Safety-Dialog mit generischem Ausgangsbedarf kennt noch
                    # keinen belastbaren Fachbedarf; eine ausdrückliche Verneinung
                    # darf deshalb die erste echte Bedarfsangabe übernehmen.
                    active_dialog.originating_need == Need.GENERAL_HELP
                    or interpretation.need in {
                        active_dialog.originating_need,
                        Need.UNKNOWN,
                        Need.GENERAL_HELP,
                    }
                )
            )
            if not (explicit_no or compatible_text_denial):
                if active_dialog.attempt_count >= active_dialog.max_attempts:
                    return self._safety_stop(
                        language,
                        interaction,
                        path=SafetyPath.UNCERTAIN_CONSERVATIVE,
                        kind=SafetyTextKind.UNCERTAIN,
                        risk_status=AcuteRiskStatus.UNCERTAIN,
                        dialogue_result="unresolved",
                        visible_question=visible_question,
                    )
                retry_interpretation = merge_dialog_facts(interpretation, active_dialog)
                retry_interpretation.acute_risk_status = AcuteRiskStatus.UNCERTAIN
                return self._safety_dialog(
                    language,
                    retry_interpretation,
                    interaction,
                    attempt_count=active_dialog.attempt_count + 1,
                    visible_question=visible_question,
                )
            interpretation = merge_dialog_facts(interpretation, active_dialog)
            interaction.safety_path = SafetyPath.DIALOGUE_CLEARED.value
            interaction.safety_dialogue_used = True
            interaction.safety_dialogue_result = "denied"
            interaction.safety_response_language = language
            interaction.dialog_type = active_dialog.dialog_type.value
            interaction.dialog_attempt_count = active_dialog.attempt_count
            interaction.dialog_result_status = "resolved"
            active_dialog = None

        if interpretation.scope_status == ScopeStatus.OUT_OF_SCOPE:
            interaction.route = "out_of_scope"
            _record_selector_bypass(interaction, SelectorBypassReason.OUT_OF_SCOPE)
            return _CoreOutcome(
                await self._formulate_or_fallback(
                    query=query,
                    language=language,
                    need=interpretation.need,
                    answer_type=AnswerType.OUT_OF_SCOPE,
                    offers=[],
                    roles={},
                    mandatory_ids=set(),
                    fallback_answer=_fallback_text(language, "out_of_scope"),
                    status="no_results",
                    interaction=interaction,
                    budget=llm_budget,
                ),
                visible_question=visible_question,
            )

        # Konkrete Waschleistungen sind kein Beleg für einen Toilettenbedarf.
        # Bei widersprüchlichen Modellfeldern hat die explizite Leistung Vorrang.
        if interpretation.need == Need.TOILET and set(interpretation.explicit_service_requests) & {
            RequestedService.SHOWER, RequestedService.HYGIENE, RequestedService.LAUNDRY,
        }:
            interpretation = interpretation.model_copy(update={"need": Need.GENERAL_HELP})

        if active_dialog and is_clear_topic_change(interpretation, active_dialog):
            interaction.dialog_type = active_dialog.dialog_type.value
            interaction.dialog_result_status = "topic_changed"
            active_dialog = None
        elif active_dialog:
            interpretation = merge_dialog_facts(interpretation, active_dialog)
        if interpretation.need == Need.TOILET:
            if active_dialog:
                interaction.dialog_type = active_dialog.dialog_type.value
                interaction.dialog_result_status = "topic_changed"
            return _CoreOutcome(
                await self._public_toilet_response(
                    query=query or Need.TOILET.value,
                    language=language,
                    interaction=interaction,
                    budget=llm_budget,
                    provider_failed=False,
                ),
                visible_question=visible_question,
            )
        context_query = query
        if active_dialog and active_dialog.alias:
            context_query = f"{active_dialog.alias} {query}".strip()
        selection_context = build_selection_context(
            query=context_query,
            interpretation=interpretation,
            offers=self.kb.offers,
            organization_aliases=self.kb.organization_aliases,
            ui_category=payload.category,
        )
        decision = self.candidate_selector.select(
            interpretation,
            self.kb.offers,
            context=selection_context,
            now=self.clock(),
        )
        interaction.candidate_selection_status = decision.selection_status.value
        interaction.candidate_result_count = len(decision.mandatory_candidates) + len(decision.selectable_candidates)
        LOGGER.info(
            "query.candidates.completed",
            extra={
                "result_count": interaction.candidate_result_count,
                "selection_status": decision.selection_status.value,
            },
        )
        if interpretation.need == Need.DRINKING_WATER:
            return _CoreOutcome(
                await self._drinking_water_response(
                    query=query or Need.DRINKING_WATER.value,
                    language=language,
                    decision=decision,
                    interaction=interaction,
                    budget=llm_budget,
                    provider_failed=False,
                ),
                visible_question=visible_question,
            )
        by_id = self.kb.by_id()
        selected_ids = [item.offer_id for item in decision.candidates]
        selected_offers = [by_id[offer_id] for offer_id in selected_ids if offer_id in by_id]

        if decision.selection_status == SelectionStatus.UNSUPPORTED_NEED:
            interaction.route = "unsupported_need"
            _record_selector_bypass(interaction, SelectorBypassReason.UNSUPPORTED_NEED)
            return _CoreOutcome(
                await self._formulate_or_fallback(
                    query=query,
                    language=language,
                    need=decision.need,
                    answer_type=AnswerType.NO_VERIFIED_RESULT,
                    offers=[],
                    roles={},
                    mandatory_ids=set(),
                    fallback_answer=_fallback_text(language, "no_results"),
                    status="no_results",
                    interaction=interaction,
                    budget=llm_budget,
                ),
                visible_question=visible_question,
            )

        # Ein unbekanntes Alter bleibt unbekannt. Der vorhandene bedingte
        # Hinweis reicht als Abschluss; eine weitere Pflichtfrage ist unnötig.
        facts = interpretation.explicit_facts
        if (
            interpretation.need == Need.SLEEP
            and not selection_context.alias
            and facts.gender.value == "female"
            and facts.age is None
            and facts.age_group.value == "unknown"
        ):
            ruecke = next((offer for offer in self.kb.offers if "general_sleep_contact_first" in offer.priority_rules), None)
            scharni = next((offer for offer in self.kb.offers if "female" in offer.eligible_genders and offer.minimum_age == 18), None)
            cards = [offer for offer in (ruecke, scharni) if offer]
            interaction.route = "sleep_conditional_contact"
            interaction.answer_type = AnswerType.GROUNDED_REFERRAL.value
            if active_dialog:
                interaction.dialog_type = active_dialog.dialog_type.value
                interaction.dialog_attempt_count = active_dialog.attempt_count
                interaction.dialog_result_status = "resolved_conditionally"
            _record_selector_bypass(interaction, SelectorBypassReason.NO_ELIGIBLE_CANDIDATE)
            return _CoreOutcome(
                QueryResponse(
                    answer=(
                        dialogue_text(language, "answers", "scharni_conditional") + " "
                        + dialogue_text(language, "answers", "sleep_intro")
                    ),
                    cards=[_card(offer, language, self.translation_catalog, self.translation_policy) for offer in cards],
                    language=language,
                    provider="template",
                    status="ok",
                ),
                visible_question=visible_question,
            )

        if active_dialog:
            interaction.dialog_type = active_dialog.dialog_type.value
            interaction.dialog_attempt_count = active_dialog.attempt_count
            # Bewusst ohne Formulator: der Kandidat ist nach dem Bezirksdialog bereits
            # eindeutig (genau ein conditional_candidate), unabhängig vom Bedarfstyp --
            # kein Auswahl- oder Formulierungsspielraum, siehe Untersuchung Zeile 11.
            district_team = None
            if (
                active_dialog.dialog_type == DialogType.ORGANIZATION_DISTRICT
                and selection_context.alias
                and selection_context.alias.district_narrowed
                and not selected_offers
                and len(decision.conditional_candidates) == 1
            ):
                district_team = by_id.get(decision.conditional_candidates[0].offer_id)
            if district_team:
                interaction.route = "dialog_district_contact"
                interaction.answer_type = AnswerType.GROUNDED_REFERRAL.value
                interaction.dialog_result_status = "resolved_conditionally"
                _record_selector_bypass(interaction, SelectorBypassReason.NO_ELIGIBLE_CANDIDATE)
                return _CoreOutcome(
                    QueryResponse(
                        answer=dialogue_text(language, "answers", "district_contact_conditional"),
                        cards=[_card(district_team, language, self.translation_catalog, self.translation_policy)],
                        language=language,
                        provider="template",
                        status="ok",
                    ),
                    visible_question=visible_question,
                )
            # Bewusst ohne Formulator: derselbe Grund wie bei district_team oben, nur
            # für den Organisationsdienst-Dialog statt den Bezirksdialog.
            organization_offer = None
            if (
                active_dialog.dialog_type == DialogType.ORGANIZATION_NEED
                and len(decision.conditional_candidates) == 1
            ):
                organization_offer = by_id.get(decision.conditional_candidates[0].offer_id)
            if organization_offer:
                interaction.route = "dialog_organization_service"
                interaction.answer_type = AnswerType.GROUNDED_RESULT.value
                interaction.dialog_result_status = "resolved_conditionally"
                _record_selector_bypass(interaction, SelectorBypassReason.NO_ELIGIBLE_CANDIDATE)
                return _CoreOutcome(
                    QueryResponse(
                        answer=dialogue_text(language, "answers", "organization_service_conditional"),
                        cards=[_card(organization_offer, language, self.translation_catalog, self.translation_policy)],
                        language=language,
                        provider="template",
                        status="ok",
                    ),
                    visible_question=visible_question,
                )
            unresolved_alias = bool(
                selection_context.alias
                and selection_context.alias.alias_kind == "organization"
                and len(selection_context.alias.offer_ids) > 1
                and not selected_offers
            )
            sleep_answer_missing = (
                active_dialog.dialog_type == DialogType.SLEEP_TARGET_GROUP
                and interpretation.explicit_facts.gender.value == "unknown"
                and interpretation.explicit_facts.age is None
                and interpretation.explicit_facts.age_group.value == "unknown"
            )
            still_unclear = (
                decision.need in {Need.UNKNOWN, Need.GENERAL_HELP}
                and not interpretation.explicit_service_requests
            ) or sleep_answer_missing
            if unresolved_alias or still_unclear or not selected_offers:
                interaction.route = "dialog_hilfebus"
                interaction.dialog_result_status = "unresolved"
                _record_selector_bypass(interaction, SelectorBypassReason.NO_ELIGIBLE_CANDIDATE)
                return _CoreOutcome(
                    await self._hilfebus_response(
                        language,
                        query=query,
                        interaction=interaction,
                        budget=llm_budget,
                        provider_failed=False,
                    ),
                    visible_question=visible_question,
                )
            interaction.dialog_result_status = "resolved"

        dialog = None if active_dialog else choose_dialog(
            interpretation,
            decision,
            selection_context,
            fingerprint=self.kb.runtime_kb_fingerprint or "",
            timeout_seconds=self.settings.session_timeout_seconds,
        )
        # Bewusst ohne Formulator: ein eindeutiger Organisations-Alias-Treffer ganz
        # ohne Dialog (derselbe Grund wie district_team/organization_offer oben) --
        # kein Auswahl- oder Formulierungsspielraum, siehe Untersuchung Zeile 11.
        direct_alias_offer = None
        if (
            not active_dialog
            and not dialog
            and selection_context.alias
            and selection_context.alias.alias_kind == "organization"
            and decision.need != Need.UNKNOWN
            and (decision.need != Need.GENERAL_HELP or bool(interpretation.explicit_service_requests))
            and len(decision.conditional_candidates) == 1
        ):
            direct_alias_offer = by_id.get(decision.conditional_candidates[0].offer_id)
        if direct_alias_offer:
            interaction.route = "organization_alias_service"
            interaction.answer_type = AnswerType.GROUNDED_RESULT.value
            _record_selector_bypass(interaction, SelectorBypassReason.NO_ELIGIBLE_CANDIDATE)
            return _CoreOutcome(
                QueryResponse(
                    answer=dialogue_text(language, "answers", "organization_service_conditional"),
                    cards=[_card(direct_alias_offer, language, self.translation_catalog, self.translation_policy)],
                    language=language,
                    provider="template",
                    status="ok",
                ),
                visible_question=visible_question,
            )
        if dialog:
            interaction.route = f"dialog_{dialog.dialog_type.value}"
            interaction.answer_type = AnswerType.CLARIFICATION.value
            interaction.dialog_type = dialog.dialog_type.value
            _record_selector_bypass(
                interaction,
                SelectorBypassReason.DIALOGUE_REQUIRED,
                eligible_count=len(decision.candidates),
            )
            cards: list[OfferRecord] = []
            answer = dialogue_text(language, "prompts", dialog.dialog_type.value)
            if dialog.dialog_type == DialogType.SLEEP_TARGET_GROUP:
                cards = [offer for offer in selected_offers if "general_sleep_contact_first" in offer.priority_rules]
                answer = f"{dialogue_text(language, 'answers', 'sleep_intro')} {answer}"
            return _CoreOutcome(
                QueryResponse(
                    answer=answer,
                    cards=[_card(offer, language, self.translation_catalog, self.translation_policy) for offer in cards],
                    language=language,
                    provider="template",
                    status="ok" if cards else "no_results",
                ),
                dialog,
                visible_question,
            )

        selector_method = getattr(self.blablador, "select_candidates", None) if self.blablador else None
        selection = bypass_outcome(
            decision,
            selector_available=callable(selector_method),
            interpreter_succeeded=True,
        )
        selector_provider_failed = False
        if selection is None:
            try:
                allocation = llm_budget.begin(self.settings.llm_selector_timeout_seconds)
                try:
                    selector_result = await selector_method(
                        query=query or decision.need.value,
                        language=language,
                        interpretation=interpretation,
                        decision=decision,
                        offers=self.kb.offers,
                        timeout_seconds=allocation.timeout_seconds,
                    )
                finally:
                    llm_budget.finish(allocation)
                selection = selected_outcome(decision, selector_result)
                LOGGER.info(
                    "query.selector.completed",
                    extra={"selected_count": len(selection.final_ids)},
                )
            except LLMBudgetExhausted:
                selector_provider_failed = True
                interaction.llm_budget_status = "llm_budget_exhausted"
                selection = fallback_outcome(decision, SelectorError("llm_budget_exhausted"))
                LOGGER.warning("query.llm_budget.exhausted", extra={"stage": "selector"})
            except SelectorError as exc:
                selector_provider_failed = True
                selection = fallback_outcome(decision, exc)
                if llm_budget.exhausted:
                    interaction.llm_budget_status = "llm_budget_exhausted"
                LOGGER.warning("query.selector.failed", extra={"error_code": exc.code})
        _record_selector_outcome(interaction, decision, selection)
        mandatory_order = [item.offer_id for item in decision.mandatory_candidates]
        priority_tiers = {item.offer_id: item.priority_tier for item in decision.candidates}
        final_offers = order_social_results(
            [by_id[offer_id] for offer_id in selection.final_ids if offer_id in by_id],
            mandatory_order=mandatory_order,
            service=decision.need.value,
            priority_tiers=priority_tiers,
            origin=self.hbf_origin,
        )[:3]
        if final_offers:
            candidate_by_id = {item.offer_id: item for item in decision.candidates}
            final_items = [candidate_by_id[offer.id] for offer in final_offers]
            roles = {item.offer_id: item.role for item in final_items}
            mandatory_ids = {
                item.offer_id
                for item in decision.mandatory_candidates
                if item.offer_id in roles
            }
            answer_type = (
                AnswerType.GROUNDED_REFERRAL
                if final_items and final_items[0].role == CandidateRole.REFERRAL_CONTACT
                else AnswerType.GROUNDED_RESULT
            )
            fallback_answer = _template_for_offers(language, decision, final_offers)
            response = await self._formulate_or_fallback(
                query=query or decision.need.value,
                language=language,
                need=decision.need,
                answer_type=answer_type,
                offers=final_offers,
                roles=roles,
                mandatory_ids=mandatory_ids,
                fallback_answer=fallback_answer,
                status="ok",
                interaction=interaction,
                budget=llm_budget,
                provider_failed=selector_provider_failed,
            )
            if interaction.route == "unknown":
                interaction.route = (
                    "llm_formulation"
                    if response.provider == "blablador"
                    else "template_fallback" if interaction.formulator_fallback_used else "template_candidates"
                )
            eligible_map_offers = order_social_results(
                [by_id[item.offer_id] for item in decision.candidates if item.offer_id in by_id],
                mandatory_order=mandatory_order,
                service=decision.need.value,
                priority_tiers=priority_tiers,
                origin=self.hbf_origin,
            )
            response.map_data = build_map_data(
                eligible_map_offers,
                language=language,
                limit=None,
                service=decision.need.value,
                origin=self.hbf_origin,
            )
            response.spoken_result_ids = [offer.id for offer in final_offers[:3]]
            response.card_ids = [card.id for card in response.cards]
            response.map_marker_ids = (
                [destination.id for destination in response.map_data.destinations]
                if response.map_data
                else []
            )
            return _CoreOutcome(response, visible_question=visible_question)

        interaction.route = "no_results"
        return _CoreOutcome(
            await self._formulate_or_fallback(
                query=query,
                language=language,
                need=decision.need,
                answer_type=AnswerType.NO_VERIFIED_RESULT,
                offers=[],
                roles={},
                mandatory_ids=set(),
                fallback_answer=_fallback_text(language, "no_results"),
                status="no_results",
                interaction=interaction,
                budget=llm_budget,
                provider_failed=selector_provider_failed,
            ),
            visible_question=visible_question,
        )

    async def _call_formulator(
        self,
        formulator_method,
        *,
        evidence,
        budget: LLMRequestBudget,
        interaction: QueryInteraction,
    ) -> ProviderAnswer:
        """Ruft den Formulator auf und wiederholt einmal bei einem Grounding-Fehlschlag.

        Jeder der drei Formulator-Aufrufer (`_formulate_or_fallback`,
        `_drinking_water_response`, `_public_toilet_response`) ruft diese eine
        Stelle statt eigener Retry-Logik auf, siehe `FORMULATOR_MAX_ATTEMPTS`.

        Grounding-/Parsing-Verstöße lösen höchstens einen zweiten Versuch aus.
        Wenn vorhanden, erhält dieser die geschlossene Groundingdiagnose als
        Korrekturhinweis, niemals den verworfenen Text. Ohne Diagnose bleibt
        die Wiederholung unverändert. `formulator_timeout`/`formulator_http_error` sind
        Transportfehler, kein Stichprobenproblem -- ein Retry würde dort nur
        das ohnehin knappe Zeitbudget für ein zweites, ebenso wahrscheinliches
        Scheitern verbrauchen (siehe
        `test_formulator_timeout_uses_existing_template_fallback`).
        `LLMBudgetExhausted` aus `budget.begin()` wird bewusst nicht
        abgefangen: ist die Zeit aufgebraucht, ist ein weiterer Versuch
        ohnehin sinnlos und soll den Aufrufer wie bisher direkt erreichen.
        """
        retry_feedback: dict[str, GroundingDiagnosticCode] = {}
        for attempt in range(FORMULATOR_MAX_ATTEMPTS):
            allocation = budget.begin(self.settings.llm_formulator_timeout_seconds)
            interaction.formulator_used = True
            try:
                result: ProviderAnswer = await formulator_method(
                    evidence=evidence,
                    timeout_seconds=allocation.timeout_seconds,
                    **retry_feedback,
                )
            except FormulatorError as exc:
                interaction.formulator_error_code = exc.code
                retryable = exc.code not in _FORMULATOR_NON_RETRYABLE_ERRORS
                if retryable and attempt + 1 < FORMULATOR_MAX_ATTEMPTS:
                    # No rejected text, free-form exception or extra provider call.
                    if exc.diagnostic_code is not None:
                        retry_feedback = {"retry_diagnostic": exc.diagnostic_code}
                    LOGGER.warning(
                        "query.formulation.retry",
                        extra={"error_code": exc.code, "attempt": attempt + 1},
                    )
                    continue
                raise
            finally:
                budget.finish(allocation)
            return result
        raise AssertionError("unreachable: the loop above always returns or raises")

    async def _formulate_or_fallback(
        self,
        *,
        query: str,
        language: Language,
        need: Need,
        answer_type: AnswerType,
        offers: list[OfferRecord],
        roles: dict[str, CandidateRole],
        mandatory_ids: set[str],
        fallback_answer: str,
        status: str,
        interaction: QueryInteraction,
        budget: LLMRequestBudget,
        provider_failed: bool = False,
    ) -> QueryResponse:
        """Verwendet genau ein Evidence-Paket oder fällt atomar auf Templates zurück."""
        interaction.answer_type = answer_type.value
        interaction.formulator_offer_count = len(offers)
        interaction.formulator_language = language
        try:
            evidence = build_formulator_evidence(
                query=query,
                language=language,
                answer_type=answer_type,
                need=need,
                offers=offers,
                roles=roles,
                mandatory_ids=mandatory_ids,
                translation_catalog=self.translation_catalog,
                translation_policy=self.translation_policy,
            )
        except (KeyError, ValueError):
            interaction.formulator_error_code = "formulator_contract_violation"
            interaction.formulator_fallback_used = True
            interaction.fallback_used = True
            LOGGER.warning(
                "query.formulation.failed",
                extra={"error_code": "formulator_contract_violation"},
            )
            return QueryResponse(
                answer=fallback_answer,
                cards=[_card(offer, language, self.translation_catalog, self.translation_policy) for offer in offers],
                language=language,
                provider="template",
                status=status,
            )
        formulator_method = getattr(self.blablador, "formulate_answer", None) if self.blablador else None
        if callable(formulator_method) and not provider_failed:
            try:
                if not self.blablador.context_fits(evidence):
                    raise FormulatorError("formulator_contract_violation")
                result: ProviderAnswer = await self._call_formulator(
                    formulator_method, evidence=evidence, budget=budget, interaction=interaction
                )
                interaction.formulator_sentence_count = result.sentence_count
                by_id = {offer.id: offer for offer in offers}
                return QueryResponse(
                    answer=result.answer,
                    cards=[
                        _card(by_id[offer_id], language, self.translation_catalog, self.translation_policy)
                        for offer_id in result.card_ids
                    ],
                    language=language,
                    provider="blablador",
                    status=status,
                )
            except LLMBudgetExhausted:
                interaction.llm_budget_status = "llm_budget_exhausted"
                interaction.formulator_error_code = "formulator_skipped_budget"
                LOGGER.warning("query.llm_budget.exhausted", extra={"stage": "formulator"})
            except FormulatorError as exc:
                interaction.formulator_error_code = exc.code
                if budget.exhausted:
                    interaction.llm_budget_status = "llm_budget_exhausted"
                LOGGER.warning("query.formulation.failed", extra={"error_code": exc.code})
        elif provider_failed:
            interaction.formulator_error_code = "formulator_skipped_provider"

        interaction.formulator_fallback_used = bool(self.blablador or provider_failed)
        interaction.fallback_used = interaction.fallback_used or interaction.formulator_fallback_used
        return QueryResponse(
            answer=fallback_answer,
            cards=[_card(offer, language, self.translation_catalog, self.translation_policy) for offer in offers],
            language=language,
            provider="template",
            status=status,
        )

    async def _drinking_water_response(
        self,
        *,
        query: str,
        language: Language,
        decision: CandidateDecision,
        interaction: QueryInteraction,
        budget: LLMRequestBudget,
        provider_failed: bool,
    ) -> QueryResponse:
        """Combines approved water offers and fixed fountains without district ranking."""

        results = select_drinking_water_results(
            decision,
            self.kb.offers,
            self.kb.drinking_fountains,
            now=self.clock(),
            fountain_only=_explicit_drinking_fountain_request(query),
            origin=self.hbf_origin,
        )
        interaction.route = "drinking_water"
        interaction.answer_type = AnswerType.GROUNDED_RESULT.value
        interaction.infrastructure_source = "approved_water_offers_and_fixed_fountains"
        interaction.infrastructure_result_count = len(results.eligible)
        interaction.infrastructure_spoken_count = len(results.spoken_results)
        interaction.infrastructure_card_count = len(results.card_results)
        interaction.infrastructure_marker_count = len(results.map_results)
        interaction.infrastructure_distance_ranking_used = bool(results.eligible)
        interaction.infrastructure_district_ranking_used = False
        interaction.candidate_result_count = len(results.eligible)
        interaction.selector_final_count = len(results.spoken_results)
        _record_selector_bypass(
            interaction,
            SelectorBypassReason.DETERMINISTIC_SPATIAL_RANKING,
            eligible_count=len(results.eligible),
        )
        interaction.selection_source = "deterministic_spatial_ranking"

        if not results.spoken_results:
            interaction.answer_type = AnswerType.NO_VERIFIED_RESULT.value
            interaction.infrastructure_error_code = "drinking_water_no_verified_result"
            return QueryResponse(
                answer=_fallback_text(language, "water_unavailable"),
                language=language,
                provider="template",
                status="no_results",
            )

        def result_card(result: DrinkingWaterResult):
            if result.social_offer is not None:
                return _card(
                    result.social_offer,
                    language,
                    self.translation_catalog,
                    self.translation_policy,
                )
            assert result.fountain is not None
            return drinking_fountain_card(result.fountain, language, origin=self.hbf_origin)

        cards = [result_card(result) for result in results.card_results]
        map_data = drinking_water_map_data(results.map_results, language, origin=self.hbf_origin)
        _adopt_card_spoken_text(map_data, cards)
        primary = results.spoken_results[0]
        primary_name = " ".join((
            primary.social_offer.display_name or primary.social_offer.name
            if primary.social_offer is not None
            else primary.fountain.name
            if primary.fountain is not None
            else ""
        ).split())
        fallback_sentences = [
            _fallback_text(language, "water_primary", primary=primary_name)
        ]
        if primary.fountain is not None:
            fallback_sentences.extend([
                _fallback_text(language, "water_free"),
                _fallback_text(language, "water_seasonal_unknown"),
            ])
        if len(results.map_results) > len(results.spoken_results):
            fallback_sentences.append(_fallback_text(language, "water_more_markers"))
        fallback = " ".join(fallback_sentences[:3])

        formulator_method = getattr(self.blablador, "formulate_answer", None) if self.blablador else None
        if callable(formulator_method) and not provider_failed:
            try:
                evidence = build_drinking_water_evidence(
                    query=query,
                    language=language,
                    results=list(results.spoken_results),
                )
                if not self.blablador.context_fits(evidence):
                    raise FormulatorError("formulator_contract_violation")
                result: ProviderAnswer = await self._call_formulator(
                    formulator_method, evidence=evidence, budget=budget, interaction=interaction
                )
                cards_by_id = {card.id: card for card in cards}
                interaction.formulator_sentence_count = result.sentence_count
                interaction.formulator_offer_count = len(result.card_ids)
                interaction.formulator_language = language
                return QueryResponse(
                    answer=result.answer,
                    cards=[cards_by_id[result_id] for result_id in result.card_ids],
                    language=language,
                    provider="blablador",
                    status="ok",
                    map_data=map_data,
                    spoken_result_ids=results.spoken_result_ids,
                    card_ids=result.card_ids,
                    map_marker_ids=[item.id for item in map_data.destinations] if map_data else [],
                )
            except LLMBudgetExhausted:
                interaction.llm_budget_status = "llm_budget_exhausted"
                interaction.formulator_error_code = "formulator_skipped_budget"
            except FormulatorError as exc:
                interaction.formulator_error_code = exc.code
        elif provider_failed:
            interaction.formulator_error_code = "formulator_skipped_provider"
        interaction.formulator_fallback_used = bool(self.blablador or provider_failed)
        interaction.fallback_used = interaction.formulator_fallback_used
        return QueryResponse(
            answer=fallback,
            cards=cards,
            language=language,
            provider="template",
            status="ok",
            map_data=map_data,
            spoken_result_ids=results.spoken_result_ids,
            card_ids=results.card_ids,
            map_marker_ids=[item.id for item in map_data.destinations] if map_data else [],
        )

    async def _public_toilet_response(
        self,
        *,
        query: str,
        language: Language,
        interaction: QueryInteraction,
        budget: LLMRequestBudget,
        provider_failed: bool,
    ) -> QueryResponse:
        """Umgeht Sozial-Candidates und LLM-Selector für deterministische Infrastruktur."""

        results = select_public_toilets(self.kb.public_toilets, origin=self.hbf_origin)
        interaction.route = "public_toilets"
        interaction.answer_type = AnswerType.GROUNDED_RESULT.value
        interaction.infrastructure_source = "deterministic_public_toilet_release"
        interaction.infrastructure_result_count = len(results.eligible)
        interaction.infrastructure_spoken_count = len(results.spoken_results)
        interaction.infrastructure_card_count = len(results.card_results)
        interaction.infrastructure_marker_count = len(results.map_results)
        interaction.infrastructure_distance_ranking_used = bool(results.eligible)
        nearest_toilet = results.eligible[0] if results.eligible else None
        nearest_distance = (
            distance_from_hbf(nearest_toilet.latitude, nearest_toilet.longitude, origin=self.hbf_origin)
            if nearest_toilet is not None
            else None
        )
        interaction.infrastructure_distance_class = (
            "under_1km"
            if nearest_distance is not None and nearest_distance < 1_000
            else "1_to_3km"
            if nearest_distance is not None and nearest_distance < 3_000
            else "over_3km"
            if nearest_distance is not None
            else None
        )
        interaction.candidate_result_count = len(results.spoken_results)
        interaction.selection_source = "deterministic_infrastructure"
        interaction.selector_final_count = len(results.spoken_results)
        _record_selector_bypass(
            interaction,
            SelectorBypassReason.DETERMINISTIC_INFRASTRUCTURE,
            eligible_count=len(results.eligible),
        )
        if not results.spoken_results:
            interaction.answer_type = AnswerType.NO_VERIFIED_RESULT.value
            interaction.infrastructure_error_code = "toilet_no_rankable_location"
            return QueryResponse(
                answer=_fallback_text(language, "toilet_unavailable"),
                language=language,
                provider="template",
                status="no_results",
            )
        primary = results.spoken_results[0]
        cards = [toilet_card(record, language, origin=self.hbf_origin) for record in results.card_results]
        primary_card = cards[0]
        names = ", ".join(record.display_name for record in results.spoken_results)
        fallback_sentences = [
            _fallback_text(
                language,
                "toilet_primary",
                names=names,
                primary=primary.display_name,
                district=primary.district,
            )
        ]
        if primary.fee_status.value == "paid":
            fallback_sentences.append(_fallback_text(language, "toilet_fee_paid", fee=primary_card.fee_raw))
        elif primary.fee_status.value == "free":
            fallback_sentences.append(_fallback_text(language, "toilet_fee_free"))
        if len(results.map_results) > len(results.spoken_results):
            fallback_sentences.append(_fallback_text(language, "toilet_more_markers"))
        fallback = " ".join(fallback_sentences[:3])
        map_data = toilet_map_data(results.map_results, language, origin=self.hbf_origin)
        _adopt_card_spoken_text(map_data, cards)
        formulator_method = getattr(self.blablador, "formulate_answer", None) if self.blablador else None
        if callable(formulator_method) and not provider_failed:
            try:
                distances = {record.id: card.distance_meters for record, card in zip(results.card_results, cards, strict=True)}
                evidence = build_public_toilet_evidence(
                    query=query,
                    language=language,
                    toilets=list(results.spoken_results),
                    distances=distances,
                )
                if not self.blablador.context_fits(evidence):
                    raise FormulatorError("formulator_contract_violation")
                result: ProviderAnswer = await self._call_formulator(
                    formulator_method, evidence=evidence, budget=budget, interaction=interaction
                )
                by_id = {card.id: card for card in cards}
                interaction.formulator_sentence_count = result.sentence_count
                interaction.formulator_offer_count = len(result.card_ids)
                interaction.formulator_language = language
                return QueryResponse(
                    answer=result.answer,
                    cards=[by_id[record_id] for record_id in result.card_ids],
                    language=language,
                    provider="blablador",
                    status="ok",
                    map_data=map_data,
                    spoken_result_ids=results.spoken_result_ids,
                    card_ids=result.card_ids,
                    map_marker_ids=results.map_marker_ids,
                )
            except LLMBudgetExhausted:
                interaction.llm_budget_status = "llm_budget_exhausted"
                interaction.formulator_error_code = "formulator_skipped_budget"
            except FormulatorError as exc:
                interaction.formulator_error_code = exc.code
        elif provider_failed:
            interaction.formulator_error_code = "formulator_skipped_provider"
        interaction.formulator_fallback_used = bool(self.blablador or provider_failed)
        interaction.fallback_used = interaction.formulator_fallback_used
        return QueryResponse(
            answer=fallback,
            cards=cards,
            language=language,
            provider="template",
            status="ok",
            map_data=map_data,
            spoken_result_ids=results.spoken_result_ids,
            card_ids=results.card_ids,
            map_marker_ids=results.map_marker_ids,
        )

    async def _hilfebus_response(
        self,
        language: Language,
        *,
        query: str,
        interaction: QueryInteraction,
        budget: LLMRequestBudget,
        provider_failed: bool,
    ) -> QueryResponse:
        offer = _general_help_contact(self.kb.offers)
        if not offer:
            return QueryResponse(answer=_fallback_text(language, "no_results"), language=language, provider="template", status="no_results")
        phone = ", ".join(offer.phone_numbers) or "—"
        times = _general_help_contact_times(offer)
        answer = dialogue_text(language, "answers", "hilfebus", phone=phone, times=times)
        return await self._formulate_or_fallback(
            query=query,
            language=language,
            need=Need.GENERAL_HELP,
            answer_type=AnswerType.AMBIGUOUS_HELP_FALLBACK,
            offers=[offer],
            roles={offer.id: CandidateRole.REFERRAL_CONTACT},
            mandatory_ids={offer.id},
            fallback_answer=answer,
            status="ok",
            interaction=interaction,
            budget=budget,
            provider_failed=provider_failed,
        )
