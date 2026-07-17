"""Orchestriert Sessions, Schutzregeln, Retrieval, LLM und Template-Antworten."""

from __future__ import annotations

import logging

from .config import Settings
from .i18n import load_manual_overrides, load_translation_store, localize_offer_card
from .kb_loader import KnowledgeBase
from .maps import build_map_data
from .models import Category, ChatTurn, Language, OfferCard, OfferRecord, QueryInteraction, QueryRequest, QueryResponse
from .offer_roles import sleep_roles
from .providers.llm import BlabladorProvider, ProviderError
from .retrieval import detect_target, has_domain_signal, is_vague_query, normalize_text, retrieve, select_card_offers
from .sessions import SessionStore
from .temporal import apply_temporal_policy, build_temporal_context, prepend_temporal_notes


LOGGER = logging.getLogger(__name__)


SELF_DESCRIPTION = {
    Language.DE: "Ich bin LENA. Ich helfe dir, Hilfe in Leipzig zu finden: Essen, Schlafen, Medizin oder Beratung. Wähle ein Symbol, sprich deine Frage oder schreibe sie.",
    Language.EN: "I am LENA. I help you find help in Leipzig: food, sleep, medical help, or advice. Choose a symbol, speak your question, or type it.",
    Language.PL: "Jestem LENA. Pomagam znaleźć pomoc w Lipsku: jedzenie, nocleg, pomoc medyczną albo poradę. Wybierz symbol, powiedz pytanie albo napisz je.",
    Language.RO: "Sunt LENA. Te ajut să găsești ajutor în Leipzig: mâncare, dormit, ajutor medical sau consiliere. Alege un simbol, spune întrebarea sau scrie.",
    Language.RU: "Я LENA. Я помогаю найти помощь в Leipzig: еду, ночлег, медицинскую помощь или консультацию. Выберите символ, скажите вопрос или напишите его.",
}

OUT_OF_SCOPE = {
    Language.DE: "Dabei kann ich dir nicht helfen. Ich helfe bei Fragen zu Hilfsangeboten in Leipzig: Essen, Schlafen, Medizin und Beratung.",
    Language.EN: "I can’t help with that. I can help with support services in Leipzig: food, sleep, medical help, and advice.",
    Language.PL: "Nie mogę w tym pomóc. Pomagam w pytaniach o wsparcie w Lipsku: jedzenie, nocleg, pomoc medyczną i porady.",
    Language.RO: "Nu te pot ajuta cu asta. Te pot ajuta cu servicii de sprijin în Leipzig: mâncare, dormit, ajutor medical și consiliere.",
    Language.RU: "Я не могу с этим помочь. Я помогаю найти помощь в Лейпциге: еду, ночлег, медицинскую помощь и консультации.",
}

CLARIFY = {
    Language.DE: "Welche Hilfe brauchst du: Essen, einen Schlafplatz, medizinische Hilfe oder Beratung?",
    Language.EN: "What kind of help do you need: food, a place to sleep, medical help, or advice?",
    Language.PL: "Jakiej pomocy potrzebujesz: jedzenia, noclegu, pomocy medycznej czy porady?",
    Language.RO: "De ce ajutor ai nevoie: mâncare, un loc de dormit, ajutor medical sau consiliere?",
    Language.RU: "Какая помощь вам нужна: еда, ночлег, медицинская помощь или консультация?",
}

CLARIFY_HILFEBUS = {
    Language.DE: (
        "Welche Hilfe brauchst du: Essen, einen Schlafplatz, medizinische Hilfe oder Beratung? "
        "Wenn du sehr unsicher bist, kannst du auch den Hilfebus zu den Einsatzzeiten anrufen."
    ),
    Language.EN: (
        "What kind of help do you need: food, a place to sleep, medical help, or advice? "
        "If you are very unsure, you can also call Hilfebus during its service times."
    ),
    Language.PL: (
        "Jakiej pomocy potrzebujesz: jedzenia, noclegu, pomocy medycznej czy porady? "
        "Jeśli nie wiesz, czego potrzebujesz, możesz też zadzwonić do Hilfebus w czasie dyżuru."
    ),
    Language.RO: (
        "De ce ajutor ai nevoie: mâncare, un loc de dormit, ajutor medical sau consiliere? "
        "Dacă nu ești sigur, poți suna și la Hilfebus în timpul programului."
    ),
    Language.RU: (
        "Какая помощь вам нужна: еда, ночлег, медицинская помощь или консультация? "
        "Если вы не уверены, можно также позвонить в Hilfebus во время работы."
    ),
}

NO_RESULTS = {
    Language.DE: "Ich habe dazu kein passendes Angebot gefunden. Versuche eine kurze Frage zu Essen, Schlafen, Medizin oder Beratung.",
    Language.EN: "I could not find a matching service. Try a short question about food, sleep, medical help, or advice.",
    Language.PL: "Nie znalazłam pasującej oferty. Spróbuj krótkiego pytania o jedzenie, nocleg, pomoc medyczną lub poradę.",
    Language.RO: "Nu am găsit un serviciu potrivit. Încearcă o întrebare scurtă despre mâncare, dormit, ajutor medical sau consiliere.",
    Language.RU: "Я не нашла подходящего предложения. Задайте короткий вопрос о еде, ночлеге, медицинской помощи или консультации.",
}

ACUTE_RISK_RESPONSE = {
    Language.DE: "Das klingt nach einer akuten Gefahr. Bitte rufe jetzt die 112 an oder bitte eine Person in deiner Nähe, den Notruf für dich anzurufen.",
    Language.EN: "This sounds like an immediate danger. Please call 112 now, or ask someone near you to call the emergency services for you.",
    Language.PL: "To brzmi jak bezpośrednie zagrożenie. Zadzwoń teraz pod numer 112 albo poproś osobę w pobliżu, aby zadzwoniła po pomoc za ciebie.",
    Language.RO: "Pare să fie un pericol imediat. Sună acum la 112 sau roagă o persoană din apropiere să apeleze serviciul de urgență pentru tine.",
    Language.RU: "Похоже, это непосредственная опасность. Позвони сейчас по номеру 112 или попроси человека рядом вызвать экстренную помощь за тебя.",
}

FOUND = {
    Language.DE: "Diese Angebote passen zu deiner Frage: {names}. Die genauen Angaben stehen in den Karten.",
    Language.EN: "These services match your question: {names}. The exact details are in the cards.",
    Language.PL: "Te oferty pasują do pytania: {names}. Dokładne informacje są na kartach.",
    Language.RO: "Aceste servicii corespund întrebării tale: {names}. Detaliile exacte sunt în carduri.",
    Language.RU: "Эти предложения подходят к вашему вопросу: {names}. Точные данные указаны в карточках.",
}

SELF_PATTERNS = {
    "wer bist du", "was ist lena", "was machst du", "who are you", "what is lena", "what do you do",
    "kim jestes", "co to jest lena", "cine esti", "ce este lena", "кто ты", "что такое lena",
}


def _matches_phrase(query: str, phrases: set[str]) -> bool:
    normalized = normalize_text(query)
    return any(normalize_text(phrase) in normalized for phrase in phrases)


def _acute_risk_response(language: Language) -> str:
    """Liefert kontrollierten Safety-Text mit deutschem Sicherheitsfallback."""
    return ACUTE_RISK_RESPONSE.get(language, ACUTE_RISK_RESPONSE[Language.DE])


def _card(
    offer: OfferRecord,
    language: Language,
    translation_store: dict,
    manual_overrides: dict,
) -> OfferCard:
    return localize_offer_card(offer, language, translation_store, manual_overrides)


def _hilfebus_offer(offers: list[OfferRecord]) -> OfferRecord | None:
    return next((offer for offer in offers if "hilfebus" in normalize_text(offer.name)), None)


def _template_found(language: Language, offers: list[OfferRecord]) -> str:
    names = ", ".join(offer.name for offer in offers[:2])
    return FOUND[language].format(names=names)


SLEEP_PRIORITY = {
    Language.DE: (
        "Wende dich bei einer allgemeinen Übernachtungsanfrage zuerst an das Übernachtungshaus in der {address}. "
        "Je nach Zielgruppe gibt es außerdem unterschiedliche Angebote für Männer, Frauen und drogengebrauchende Menschen."
    ),
    Language.EN: (
        "For a general overnight request, first contact the accommodation at {address}. "
        "Different services are available for men, women, and people who use drugs."
    ),
    Language.PL: (
        "W przypadku ogólnego pytania o nocleg najpierw skontaktuj się z placówką przy {address}. "
        "Dostępne są różne oferty dla mężczyzn, kobiet i osób używających narkotyków."
    ),
    Language.RO: (
        "Pentru o cerere generală de cazare, contactează mai întâi adăpostul de la {address}. "
        "Există servicii diferite pentru bărbați, femei și persoane care consumă droguri."
    ),
    Language.RU: (
        "При общем запросе на ночлег сначала обратитесь в учреждение по адресу {address}. "
        "Для мужчин, женщин и людей, употребляющих наркотики, предусмотрены разные предложения."
    ),
}


def _sleep_policy_offers(
    routed: list[OfferRecord],
    all_offers: list[OfferRecord],
    query: str,
    *,
    limit: int = 4,
) -> list[OfferRecord]:
    roles = sleep_roles(all_offers)
    target = detect_target(query)
    if target == "women":
        preferred = roles["women"]
        excluded_ids = {offer.id for offer in roles["men"]}
    elif target == "drug":
        preferred = roles["drug"]
        excluded_ids = {offer.id for offer in [*roles["men"], *roles["women"]]}
    elif target == "men":
        preferred = [*roles["ruecke"], *[offer for offer in roles["men"] if offer not in roles["ruecke"]]]
        excluded_ids = {offer.id for offer in roles["women"]}
    else:
        preferred = [
            *roles["ruecke"][:1],
            *roles["women"][:1],
            *roles["drug"][:1],
        ]
        excluded_ids: set[str] = set()

    selected: list[OfferRecord] = []
    for offer in preferred:
        if offer not in selected:
            selected.append(offer)
    for offer in routed:
        if len(selected) >= limit:
            break
        if offer.id not in excluded_ids and offer not in selected:
            selected.append(offer)
    return selected[:limit]


def _sleep_routing_context(query: str) -> dict[str, str]:
    target = detect_target(query) or "unspecified"
    return {
        "intent": "sleep",
        "target_group": target,
        "policy": (
            "For an unspecified target group, begin with the Rückmarsdorfer Straße offer, then distinguish "
            "men, women, and people who use drugs. For an explicit target group, use only compatible offers. "
            "Do not claim new admissions because that is not stated in the supplied records."
        ),
    }


def _template_for_offers(
    language: Language,
    category: Category | None,
    query: str,
    offers: list[OfferRecord],
) -> str:
    if category == Category.SLEEP and not detect_target(query):
        role_map = sleep_roles(offers)
        ruecke = role_map["ruecke"][0] if role_map["ruecke"] else None
        if ruecke and ruecke.address:
            return SLEEP_PRIORITY[language].format(address=ruecke.address)
    return _template_found(language, offers)


def _add_temporal_context(routing_context: dict, temporal_notes: list[str]) -> dict:
    if not temporal_notes:
        return routing_context
    return {
        **routing_context,
        "temporal_policy": (
            "These notes are binding. If a service has stand times, name the exact day, time, "
            "and place. Do not present office hours or the office address as the place where a "
            "mobile service or food distribution happens."
        ),
        "temporal_policy_notes": temporal_notes,
    }


def _query_with_session_context(query: str, history: list[ChatTurn]) -> str:
    if not history or has_domain_signal(query):
        return query
    context_parts: list[str] = []
    for turn in history[-2:]:
        context_parts.append(turn.question)
        context_parts.append(turn.answer)
    context_parts.append(query)
    return " ".join(part for part in context_parts if part)


class QueryService:
    """Zentraler Anwendungsdienst für eine vollständig geerdete Nutzeranfrage.

    Der Dienst verwendet Blablador nur, wenn alle Voraussetzungen erfüllt sind.
    Jeder Provider- oder Validierungsfehler fällt auf deterministische Logik
    zurück und verändert die zugrunde liegenden Angebotsdaten nicht.
    """
    def __init__(self, settings: Settings, kb: KnowledgeBase) -> None:
        self.settings = settings
        self.kb = kb
        self.translation_store = load_translation_store(settings)
        self.manual_overrides = load_manual_overrides(settings)
        self.sessions = SessionStore(
            settings.app_root / "runtime" / "sessions.json",
            timeout_seconds=settings.session_timeout_seconds,
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
    def full_context_available(self) -> bool:
        return bool(self.blablador and self.blablador.index_context_fits(self.kb.offers))

    async def query(self, payload: QueryRequest) -> QueryResponse:
        """Beantwortet eine Anfrage und aktualisiert ihren lokalen Sessionzustand.

        Args:
            payload: Validierte Frage, Sprache, Kategorie und optionale Session-ID.

        Returns:
            Geerdete Antwort einschließlich Karten und neuem Sessionzustand.

        Side Effects:
            Liest und schreibt die dateibasierte Sessionablage.
        """
        session = self.sessions.resolve(payload.session_id, payload.language)
        conversation_history = list(session.turns)
        interaction = QueryInteraction()
        response = await self._query_core(payload, conversation_history, interaction)
        selected_offers = [self.kb.by_id()[card.id] for card in response.cards if card.id in self.kb.by_id()]
        map_data = build_map_data(selected_offers)
        if map_data:
            localized_cards = {card.id: card for card in response.cards}
            for destination in map_data.destinations:
                card = localized_cards.get(destination.id)
                if card:
                    destination.label = card.name
                    destination.description = card.short_description
                    destination.phone_numbers = card.phone_numbers
                    destination.opening_hours = card.opening_hours_raw[:4]
        updated_session = self.sessions.add_turn(
            session,
            question=payload.query,
            answer=response.answer,
            pending_clarification=response.status == "no_results",
        )
        response.session_id = updated_session.session_id
        response.question = payload.query
        response.history = updated_session.turns
        response.map_data = map_data
        interaction.source_ids = [card.id for card in response.cards]
        response.interaction = interaction
        return response

    async def _query_core(
        self,
        payload: QueryRequest,
        conversation_history: list[ChatTurn],
        interaction: QueryInteraction,
    ) -> QueryResponse:
        language = payload.language
        query = payload.query
        effective_query = _query_with_session_context(query, conversation_history)
        temporal_context = build_temporal_context(effective_query)

        if _matches_phrase(query, SELF_PATTERNS):
            interaction.route = "self_description"
            return QueryResponse(answer=SELF_DESCRIPTION[language], language=language, provider="template", status="ok")
        if not query and payload.category is None:
            interaction.route = "clarification"
            return QueryResponse(answer=CLARIFY[language], language=language, provider="template", status="no_results")
        if payload.category is None and is_vague_query(query) and not conversation_history:
            interaction.route = "clarification"
            hilfebus = _hilfebus_offer(self.kb.offers)
            return QueryResponse(
                answer=CLARIFY_HILFEBUS[language],
                cards=(
                    [_card(hilfebus, language, self.translation_store, self.manual_overrides)]
                    if hilfebus
                    else []
                ),
                language=language,
                provider="template",
                status="no_results",
            )

        routed_offers: list[OfferRecord] = []
        routed_category: Category | None = None
        if self.blablador and self.blablador.index_context_fits(self.kb.offers):
            try:
                route = await self.blablador.route(
                    query=effective_query or (payload.category.value if payload.category else "help"),
                    language=language,
                    category=payload.category,
                    offers=self.kb.offers,
                    conversation_history=conversation_history,
                )
                LOGGER.info("query.router.completed")
                if route.acute_risk_detected:
                    interaction.route = "acute_risk"
                    interaction.acute_risk_detected = True
                    LOGGER.warning("safety.acute_risk_detected")
                    return QueryResponse(
                        answer=_acute_risk_response(language),
                        language=language,
                        provider="template",
                        status="no_results",
                    )
                if route.out_of_scope:
                    interaction.route = "out_of_scope"
                    return QueryResponse(
                        answer=OUT_OF_SCOPE[language], language=language, provider="template", status="no_results"
                    )
                if route.needs_clarification:
                    interaction.route = "clarification"
                    return QueryResponse(
                        answer=CLARIFY[language], language=language, provider="template", status="no_results"
                    )
                if route.intent and route.offer_ids:
                    routed_category = route.intent
                    by_id = self.kb.by_id()
                    routed_offers = [by_id[offer_id] for offer_id in route.offer_ids]
                    if routed_category == Category.SLEEP:
                        routed_offers = _sleep_policy_offers(routed_offers, self.kb.offers, effective_query)
                    else:
                        routed_offers = routed_offers[:4]
                    routed_offers, temporal_notes = apply_temporal_policy(
                        routed_offers,
                        routed_category,
                        effective_query,
                        temporal_context,
                    )
                    if not routed_offers:
                        raise ProviderError("Temporal policy removed routed offers")

                    routing_context = (
                        _sleep_routing_context(effective_query)
                        if routed_category == Category.SLEEP
                        else {"intent": routed_category.value, "source": "llm_router"}
                    )
                    routing_context = _add_temporal_context(routing_context, temporal_notes)
                    result = await self.blablador.answer(
                        query=query or routed_category.value,
                        language=language,
                        category=routed_category,
                        offers=routed_offers,
                        routing_context=routing_context,
                        conversation_history=conversation_history,
                    )
                    LOGGER.info("query.formulation.completed")
                    selected = [by_id[card_id] for card_id in result.card_ids]
                    if routed_category == Category.SLEEP and selected:
                        selected = _sleep_policy_offers(selected, routed_offers, effective_query)
                        target = detect_target(effective_query)
                        if selected and target in {None, "men"} and "ruckmarsdorfer" not in normalize_text(result.answer):
                            raise ProviderError("Sleep answer omitted the Rückmarsdorfer priority")
                    interaction.route = "llm_formulation"
                    return QueryResponse(
                        answer=prepend_temporal_notes(result.answer, temporal_notes, language),
                        cards=[_card(offer, language, self.translation_store, self.manual_overrides) for offer in selected],
                        language=language,
                        provider="blablador",
                        status="ok",
                    )
            except ProviderError as exc:
                event = "query.formulation.failed" if routed_offers else "query.router.failed"
                LOGGER.warning(event, extra={"error_type": type(exc).__name__})
                interaction.fallback_used = True
                LOGGER.info("query.fallback.used", extra={"stage": event})
                if routed_offers:
                    routed_offers, temporal_notes = apply_temporal_policy(
                        routed_offers,
                        routed_category,
                        effective_query,
                        temporal_context,
                    )
                    if routed_offers:
                        interaction.route = "template_fallback"
                        return QueryResponse(
                            answer=prepend_temporal_notes(
                                _template_for_offers(language, routed_category, effective_query, routed_offers),
                                temporal_notes,
                                language,
                            ),
                            cards=[_card(offer, language, self.translation_store, self.manual_overrides) for offer in routed_offers],
                            language=language,
                            provider="template",
                            status="ok",
                        )

        outcome = retrieve(self.kb.offers, effective_query, payload.category)
        interaction.retrieval_result_count = len(outcome.results)
        LOGGER.info(
            "query.retrieval.completed",
            extra={"result_count": interaction.retrieval_result_count},
        )
        if not outcome.in_scope:
            interaction.route = "out_of_scope"
            return QueryResponse(answer=OUT_OF_SCOPE[language], language=language, provider="template", status="no_results")

        template_offers = select_card_offers(outcome, effective_query)
        llm_offers = [item.offer for item in outcome.results[:3]]
        template_temporal_notes: list[str] = []
        llm_temporal_notes: list[str] = []
        if outcome.selected_category == Category.SLEEP:
            llm_offers = _sleep_policy_offers(llm_offers, self.kb.offers, effective_query, limit=3)
            template_offers = _sleep_policy_offers(template_offers, self.kb.offers, effective_query)
            template_offers, template_temporal_notes = apply_temporal_policy(
                template_offers,
                outcome.selected_category,
                effective_query,
                temporal_context,
            )
            llm_offers, llm_temporal_notes = apply_temporal_policy(
                llm_offers,
                outcome.selected_category,
                effective_query,
                temporal_context,
            )
        elif outcome.selected_category in {Category.FOOD, Category.MEDICAL}:
            temporally_ranked, _ = apply_temporal_policy(
                [item.offer for item in outcome.results],
                outcome.selected_category,
                effective_query,
                temporal_context,
            )
            template_offers = temporally_ranked[:4]
            llm_offers = temporally_ranked[:4]
            _, template_temporal_notes = apply_temporal_policy(
                template_offers,
                outcome.selected_category,
                effective_query,
                temporal_context,
            )
            llm_temporal_notes = template_temporal_notes

        if self.blablador and llm_offers and self.blablador.context_fits(llm_offers):
            try:
                routing_context = (
                    _sleep_routing_context(effective_query)
                    if outcome.selected_category == Category.SLEEP
                    else {"source": "deterministic_router_fallback"}
                )
                routing_context = _add_temporal_context(routing_context, llm_temporal_notes)
                result = await self.blablador.answer(
                    query=query or (outcome.selected_category.value if outcome.selected_category else "help"),
                    language=language,
                    category=outcome.selected_category,
                    offers=llm_offers,
                    routing_context=routing_context,
                    conversation_history=conversation_history,
                )
                LOGGER.info("query.formulation.completed")
                by_id = self.kb.by_id()
                selected = [by_id[card_id] for card_id in result.card_ids]
                if outcome.selected_category == Category.SLEEP:
                    direct_available = any("hilfebus" not in normalize_text(offer.name) for offer in llm_offers)
                    only_hilfebus = all("hilfebus" in normalize_text(offer.name) for offer in selected)
                    if selected and direct_available and only_hilfebus:
                        raise ProviderError("Hilfebus cannot replace direct sleep offers")
                interaction.route = "llm_formulation"
                return QueryResponse(
                    answer=prepend_temporal_notes(result.answer, llm_temporal_notes, language),
                    cards=[_card(offer, language, self.translation_store, self.manual_overrides) for offer in selected],
                    language=language,
                    provider="blablador",
                    status="ok",
                )
            except ProviderError as exc:
                LOGGER.warning("query.formulation.failed", extra={"error_type": type(exc).__name__})
                interaction.fallback_used = True
                LOGGER.info("query.fallback.used", extra={"stage": "query.formulation.failed"})

        if template_offers:
            interaction.route = "template_fallback" if interaction.fallback_used else "template_retrieval"
            return QueryResponse(
                answer=prepend_temporal_notes(
                    _template_for_offers(language, outcome.selected_category, effective_query, template_offers),
                    template_temporal_notes,
                    language,
                ),
                cards=[_card(offer, language, self.translation_store, self.manual_overrides) for offer in template_offers],
                language=language,
                provider="template",
                status="ok",
            )
        interaction.route = "no_results"
        return QueryResponse(answer=NO_RESULTS[language], language=language, provider="template", status="no_results")
