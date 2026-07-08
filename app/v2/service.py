from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx

from ..models import ConversationContext, KnowledgeAnswer, Language, RetrievedPage, TemporalContext
from ..retrieval import normalize_text, tokenize
from .kb import V2KnowledgeBase
from .models import V2Category, V2Intent, V2Offer
from .presentation import compact_names, display_name, primary_phone


SOURCE_PAGE_URL = "https://www.leipzig.de/leben-in-leipzig/gesundheit/suchthilfe/schadensminimierung"


@dataclass(frozen=True, slots=True)
class RankedOffer:
    offer: V2Offer
    score: float


@dataclass(frozen=True, slots=True)
class Availability:
    status: Literal["open_now", "available_today_later", "available_today_unknown_time", "not_available_today", "unknown"]
    time_text: str | None = None
    start_text: str | None = None


SleepTarget = Literal["unknown", "man", "woman", "diverse", "under_18", "substance_use"]


class V2AnswerService:
    name = "v2_clean"

    def __init__(self, settings) -> None:
        self.settings = settings
        self.uses_llm = settings.rewrite_provider in {"blablador", "openai_compatible"} and bool(settings.llm_base_url and settings.llm_api_key)
        self.model_name = settings.llm_model if self.uses_llm else None
        self.system_prompt_path = _v2_prompt_path(settings)
        self.system_prompt = _load_v2_prompt(self.system_prompt_path)
        self.prompt_loaded = bool(self.system_prompt)

    async def answer(
        self,
        transcript: str,
        language: Language,
        kb: V2KnowledgeBase,
        *,
        conversation_context: ConversationContext | None = None,
        temporal_context: TemporalContext | None = None,
    ) -> KnowledgeAnswer:
        guarded = _guarded_answer(transcript, language)
        if guarded:
            return guarded

        intent = _heuristic_intent(transcript, language, conversation_context)
        if self.uses_llm:
            intent = await self._llm_intent(intent, conversation_context, temporal_context) or intent

        target = _detect_sleep_target(transcript)
        if intent.primary_need != "sleep" and target != "unknown" and _context_was_sleep(conversation_context):
            intent = intent.model_copy(update={"primary_need": "sleep"})

        if intent.primary_need == "sleep":
            ranked = _retrieve_sleep(kb, intent, transcript, conversation_context, temporal_context, target)
            selected = [item.offer for item in ranked[:6]]
            answer_text = _sleep_answer(selected, intent, language, temporal_context, target)
            return KnowledgeAnswer(
                answer_text=_clean_text(answer_text),
                status="ok" if selected else "unknown",
                retrieved_page_ids=[item.offer.offer_id for item in ranked[:8]],
                sources=_sources(selected),
                last_checked=_last_checked(selected),
                answer_evidence=_evidence(selected),
                requirements=_requirements(selected),
                follow_up_options=_sleep_follow_up_options(language) if target == "unknown" else [],
            )

        ranked = _retrieve(kb, intent, transcript, conversation_context, temporal_context)
        if not ranked:
            return KnowledgeAnswer(answer_text=_t(UNKNOWN_TEXT, language), status="unknown")

        selected = [item.offer for item in ranked[:3]]
        deterministic = _deterministic_answer(selected, intent, language, temporal_context)
        answer_text = deterministic

        if self.uses_llm:
            candidate = await self._llm_answer(transcript, language, intent, selected, deterministic, conversation_context, temporal_context)
            if candidate and _is_simple_overview_answer(candidate) and not _unsupported_sensitive_fact(candidate, deterministic, selected):
                answer_text = candidate

        return KnowledgeAnswer(
            answer_text=_clean_text(answer_text),
            status="ok",
            retrieved_page_ids=[item.offer.offer_id for item in ranked[:5]],
            sources=_sources(selected),
            last_checked=_last_checked(selected),
            answer_evidence=_evidence(selected),
            requirements=_requirements(selected),
        )

    async def _llm_intent(
        self,
        fallback: V2Intent,
        conversation_context: ConversationContext | None,
        temporal_context: TemporalContext | None,
    ) -> V2Intent | None:
        prompt = "\n".join(
            [
                "Extract LENA v2 user intent. Return only JSON.",
                "selected_language is authoritative; do not detect language by default.",
                "Allowed primary_need values: food, sleep, medical, general_advice, addiction, hygiene, other_source_listed, unknown.",
                "Do not invent offers, facts, times, phones, addresses, medical advice, or legal advice.",
                f"Input JSON: {fallback.model_dump_json()}",
                f"Session context: {conversation_context.model_dump_json() if conversation_context else '{}'}",
                f"Temporal context: {temporal_context.model_dump_json() if temporal_context else '{}'}",
                "Schema:",
                json.dumps(V2Intent.model_json_schema(), ensure_ascii=False),
            ]
        )
        parsed = await self._openai_json(prompt, max_tokens=500)
        if not parsed:
            return None
        try:
            return V2Intent.model_validate(parsed)
        except Exception:
            return None

    async def _llm_answer(
        self,
        transcript: str,
        language: Language,
        intent: V2Intent,
        offers: list[V2Offer],
        deterministic: str,
        conversation_context: ConversationContext | None,
        temporal_context: TemporalContext | None,
    ) -> str | None:
        prompt = "\n".join(
            [
                "You are LENA v2. Answer a vulnerable user from the provided evidence only.",
                "Use simple, complete sentences.",
                "Use an informal tone for German with du, never Sie.",
                "Give only an overview answer. Do not list addresses, phone numbers, opening hours, or several offers in one paragraph.",
                "If the user needs details, tell them to tap a card or ask for more information.",
                "Maximum 4 short sentences.",
                "Do not invent phone numbers, times, addresses, costs, requirements, diagnoses, legal advice, or service availability.",
                "Keep official names, organization names, addresses, and source titles unchanged.",
                f"Selected language: {language.value}",
                f"User input: {transcript}",
                f"Intent: {intent.model_dump_json()}",
                f"Session context: {conversation_context.model_dump_json() if conversation_context else '{}'}",
                f"Temporal context: {temporal_context.model_dump_json() if temporal_context else '{}'}",
                "Evidence:",
                json.dumps([_offer_package(offer) for offer in offers], ensure_ascii=False),
                f"Safe deterministic draft: {deterministic}",
                "Return JSON: {\"answer_text\": \"...\"}",
            ]
        )
        parsed = await self._openai_json(prompt, max_tokens=700)
        if not isinstance(parsed, dict):
            return None
        text = parsed.get("answer_text")
        return _clean_text(text) if isinstance(text, str) and text.strip() else None

    async def _openai_json(self, prompt: str, *, max_tokens: int) -> dict | None:
        payload = {
            "model": self.settings.llm_model,
            "messages": _messages(self.system_prompt, prompt),
            "temperature": 0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=min(float(self.settings.llm_timeout_seconds), 12.0)) as client:
                response = await client.post(
                    f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                )
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            return None


def retrieve_for_symbols(kb: V2KnowledgeBase, category: V2Category, limit: int = 6) -> list[RankedOffer]:
    intent = V2Intent(selected_language=Language.DE, user_input=category, primary_need=category, confidence=0.9)
    ranked = _retrieve(kb, intent, category, None, None, limit=12)
    if category == "medical":
        allowed = {
            "medical",
            "addiction",
        }
        ranked = [
            item
            for item in ranked
            if item.offer.category in allowed
            or item.offer.offer_id in {"kontaktcafe-alternative-i", "alternative-i-notschlafstelle", "mobile-alternative"}
        ]
    elif category == "sleep":
        ranked = [item for item in ranked if item.offer.category == category or item.offer.offer_id == "hilfebus"]
    elif category == "general_advice":
        ranked = [item for item in ranked if item.offer.category == category]
    return ranked[:limit]


def _heuristic_intent(transcript: str, language: Language, context: ConversationContext | None = None) -> V2Intent:
    normalized = normalize_text(transcript)
    tokens = set(tokenize(transcript))
    primary = _detect_need(normalized, tokens)
    secondary: list[V2Category] = []
    for category in ("food", "sleep", "medical", "general_advice", "addiction", "hygiene"):
        if category != primary and _matches_need(category, normalized, tokens):
            secondary.append(category)  # type: ignore[arg-type]
    follow_up = None
    if context and context.follow_up_mode != "none":
        follow_up = context.follow_up_mode
        if primary == "unknown" and context.last_topic in {"food", "housing", "medical", "social", "addiction", "hygiene"}:
            primary = _need_from_context_topic(context.last_topic)
    return V2Intent(
        selected_language=language,
        user_input=transcript,
        primary_need=primary,
        secondary_needs=secondary,
        urgency=_detect_urgency(normalized),
        time_reference=_time_reference(normalized),
        follow_up_context=follow_up,
        clarification_needed=False,
        confidence=0.8 if primary != "unknown" else 0.35,
    )


def _detect_sleep_target(transcript: str) -> SleepTarget:
    normalized = normalize_text(transcript)
    tokens = set(tokenize(transcript))
    if any(term in normalized for term in ("unter 18", "unter achtzehn", "under 18", "under eighteen", "jugendlich", "minderjaehrig", "minderjährig")):
        return "under_18"
    if any(term in normalized for term in ("drogen", "droge", "konsum", "konsumiere", "substance use", "drug use", "drugs")):
        return "substance_use"
    if "divers" in tokens or "diverse" in tokens or "nonbinary" in normalized or "non-binary" in normalized:
        return "diverse"
    if tokens & {"frau", "frauen", "woman", "women", "female"}:
        return "woman"
    if tokens & {"mann", "maenner", "männer", "man", "men", "male"}:
        return "man"
    return "unknown"


def _context_was_sleep(context: ConversationContext | None) -> bool:
    if not context:
        return False
    topic = normalize_text(context.last_topic or "")
    place = normalize_text(context.last_place_page_id or "")
    summary = normalize_text(context.history_summary or "")
    haystack = f" {topic} {place} {summary} "
    return any(
        term in haystack
        for term in (
            "sleep",
            "uebernachtung",
            "ubernachtung",
            "notunterbringung",
            "notschlaf",
            "schlafplatz",
            "unterkunft",
        )
    )


def _retrieve(
    kb: V2KnowledgeBase,
    intent: V2Intent,
    transcript: str,
    context: ConversationContext | None,
    temporal_context: TemporalContext | None,
    *,
    limit: int = 5,
) -> list[RankedOffer]:
    preferred = set(context.preferred_page_ids if context and intent.primary_need == "unknown" else [])
    excluded = set(context.excluded_page_ids if context else [])
    categories = [intent.primary_need, *intent.secondary_needs]
    categories = [category for category in categories if category != "unknown"]
    query_tokens = set(tokenize(transcript))
    ranked: list[RankedOffer] = []
    for offer in kb.v2_dataset.offers:
        if not offer.is_user_offer or offer.offer_id in excluded:
            continue
        score = 0.0
        if offer.offer_id in preferred:
            score += 5.0
        if categories:
            for category in categories:
                if _category_matches(offer, category):
                    score += 4.0
                elif category == "food" and "food" in offer.services_provided:
                    score += 2.0
        haystack = normalize_text(
            " ".join(
                [
                    offer.offer_id,
                    offer.name,
                    offer.organization,
                    offer.category,
                    offer.subcategory or "",
                    offer.short_description,
                    offer.card_summary or "",
                    offer.location or "",
                    " ".join(offer.aliases),
                    " ".join(offer.retrieval_keywords),
                    " ".join(offer.services_provided),
                    " ".join(offer.target_group),
                    json.dumps(offer.facts, ensure_ascii=False),
                ]
            )
        )
        score += len(query_tokens & set(tokenize(haystack))) * 0.55
        if intent.urgency in {"now", "today", "tonight"}:
            availability = _availability_for_offer(offer, temporal_context, intent)
            if availability.status == "open_now":
                score += 2.4 if intent.urgency == "now" else 1.8
            elif availability.status == "available_today_later":
                score += 1.5
            elif availability.status == "available_today_unknown_time":
                score += 0.5
            elif availability.status == "not_available_today":
                score -= 0.8
        elif temporal_context and any(_weekday_hint(time, temporal_context) for time in offer.all_times):
            score += 0.35
        if intent.primary_need == "food":
            if "hilfebus" in offer.offer_id:
                score += 4.2
            elif offer.offer_id in {"safe-team-wohnen", "diakonie-streetwork"}:
                score += 2.8
            elif "timmi" in offer.offer_id:
                score += 2.4
            elif "bahnhofsmission" in offer.offer_id:
                score += 2.0
            elif offer.offer_id in {"tagestreff-insel", "leipziger-oase", "kontaktcafe-alternative-i"}:
                score += 1.0
            elif offer.category == "general_advice":
                score -= 0.7
        if offer.category == "food" and intent.primary_need == "food" and "registration_required" in offer.aliases:
            score -= 4.0
        if intent.primary_need == "general_advice":
            if offer.offer_id in {"safe-team-wohnen", "diakonie-streetwork", "bahnhofsmission", "soziale-wohnhilfen-wohnungsnotfallhilfe"}:
                score += 2.2
            if any(term in offer.offer_id for term in ("mobile-jugendarbeit", "streetwork-mitte", "streetwork-ost", "streetwork-nord")):
                score -= 1.2
        if intent.primary_need == "medical":
            if offer.offer_id == "uvo-medical-outreach":
                score += 4.0
            elif offer.offer_id == "cabl-clearingstelle":
                score += 3.2
            elif offer.offer_id == "kontaktcafe-alternative-i":
                score += 2.8
            elif offer.offer_id == "mobile-alternative":
                score += 2.4
            elif offer.offer_id in {"alternative-i-notschlafstelle", "alternative-iii-notschlafstelle"}:
                score += 1.8
        if score > 0:
            ranked.append(RankedOffer(offer=offer, score=round(score, 4)))
    ranked.sort(key=lambda item: (-item.score, _category_rank(item.offer, intent), item.offer.offer_id))
    return ranked[:limit]


def _retrieve_sleep(
    kb: V2KnowledgeBase,
    intent: V2Intent,
    transcript: str,
    context: ConversationContext | None,
    temporal_context: TemporalContext | None,
    target: SleepTarget,
    *,
    limit: int = 8,
) -> list[RankedOffer]:
    del context
    normalized_query = normalize_text(transcript)
    query_tokens = set(tokenize(transcript))
    ranked: list[RankedOffer] = []
    for offer in kb.v2_dataset.offers:
        if not offer.is_user_offer:
            continue
        haystack = normalize_text(
            " ".join(
                [
                    offer.offer_id,
                    offer.name,
                    offer.category,
                    offer.subcategory or "",
                    offer.card_summary or "",
                    " ".join(offer.services_provided),
                    " ".join(offer.target_group),
                    " ".join(offer.retrieval_keywords),
                    " ".join(offer.aliases),
                    offer.requirements or "",
                ]
            )
        )
        score = 0.0
        if offer.category == "sleep":
            score += 5.0
        if offer.offer_id == "hilfebus":
            score += 4.0
        if any(term in haystack for term in ("notunterbringung", "notschlaf", "uebernachtung", "schlafplatz", "unterkunft")):
            score += 2.0
        score += len(query_tokens & set(tokenize(haystack))) * 0.4
        if intent.urgency in {"now", "today", "tonight"}:
            availability = _availability_for_offer(offer, temporal_context, intent)
            if availability.status == "open_now":
                score += 1.4
            elif availability.status == "available_today_later":
                score += 1.0
            elif availability.status == "not_available_today":
                score -= 0.4
        score += _sleep_target_boost(offer, target, normalized_query)
        if score > 0:
            ranked.append(RankedOffer(offer=offer, score=round(score, 4)))
    ranked.sort(key=lambda item: (-item.score, _sleep_rank(item.offer, target), item.offer.offer_id))
    return ranked[:limit]


def _sleep_target_boost(offer: V2Offer, target: SleepTarget, normalized_query: str) -> float:
    offer_id = offer.offer_id
    if target == "woman":
        if "frauen" in offer_id:
            return 7.0
        if offer_id == "soziale-wohnhilfen-notunterbringung":
            return 4.0
        if offer_id == "hilfebus":
            return 3.5
    if target == "man":
        if offer_id == "uebernachtungshaus-maenner-leutzsch":
            return 7.0
        if offer_id == "soziale-wohnhilfen-notunterbringung":
            return 5.0
        if offer_id == "hilfebus":
            return 4.0
    if target == "substance_use":
        if offer_id == "alternative-i-notschlafstelle":
            return 8.0
        if offer_id == "alternative-iii-notschlafstelle":
            return 7.5
        if offer_id in {"hilfebus", "safe-team-konsum", "safe-team-wohnen"}:
            return 3.5
    if target == "under_18":
        if any(term in offer_id for term in ("streetwork", "jugend", "mobile-jugendarbeit", "suedpol", "machtlos")):
            return 7.0
        if offer_id in {"soziale-wohnhilfen-notunterbringung", "hilfebus"}:
            return 2.0
        if "adult" in normalized_query:
            return 0.0
    if target == "diverse":
        if offer_id == "soziale-wohnhilfen-notunterbringung":
            return 7.0
        if offer_id == "hilfebus":
            return 6.0
    if target == "unknown":
        if offer_id == "soziale-wohnhilfen-notunterbringung":
            return 8.0
        if offer_id == "uebernachtungshaus-maenner-leutzsch":
            return 6.5
        if offer_id == "hilfebus":
            return 6.0
        if "frauen" in offer_id:
            return 4.0
        if offer_id in {"alternative-i-notschlafstelle", "alternative-iii-notschlafstelle"}:
            return 2.5
    return 0.0


def _sleep_rank(offer: V2Offer, target: SleepTarget) -> int:
    orders = {
        "unknown": [
            "soziale-wohnhilfen-notunterbringung",
            "uebernachtungshaus-maenner-leutzsch",
            "hilfebus",
            "aww-frauen-uebernachtungshaus",
            "alternative-i-notschlafstelle",
            "alternative-iii-notschlafstelle",
        ],
        "woman": ["aww-frauen-uebernachtungshaus", "soziale-wohnhilfen-notunterbringung", "hilfebus"],
        "man": ["uebernachtungshaus-maenner-leutzsch", "soziale-wohnhilfen-notunterbringung", "hilfebus"],
        "diverse": ["soziale-wohnhilfen-notunterbringung", "hilfebus"],
        "substance_use": ["alternative-i-notschlafstelle", "alternative-iii-notschlafstelle", "safe-team-konsum", "hilfebus", "soziale-wohnhilfen-notunterbringung"],
        "under_18": ["streetwork-mitte", "streetwork-ost", "streetwork-nord", "mobile-jugendarbeit-westen", "hilfebus", "soziale-wohnhilfen-notunterbringung"],
    }
    try:
        return orders[target].index(offer.offer_id)
    except ValueError:
        return 50


def _sleep_answer(offers: list[V2Offer], intent: V2Intent, language: Language, temporal_context: TemporalContext | None, target: SleepTarget) -> str:
    day = _sleep_day_phrase(intent, language, temporal_context)
    day_part = f" {day}" if day else ""
    hilfebus_phone = "0152 33661087"
    if target == "woman":
        return _t(
            {
                "de": f"Du suchst einen Schlafplatz{day_part}. Für Frauen passt zuerst das Übernachtungshaus in der Scharnhorststraße. Die Notunterbringung kann auch weiterhelfen. Der Hilfebus hilft abends: {hilfebus_phone}.",
                "en": f"You are looking for a place to sleep{day_part}. For women, start with the women’s overnight shelter in Scharnhorststraße. The emergency accommodation office can also help. The Hilfebus can help in the evening: {hilfebus_phone}.",
                "pl": f"Szukasz miejsca do spania{day_part}. Dla kobiet najpierw pokażę noclegownię dla kobiet. Pomóc może też urząd ds. noclegu awaryjnego. Hilfebus pomaga wieczorem: {hilfebus_phone}.",
                "ro": f"Cauți un loc de dormit{day_part}. Pentru femei, începe cu adăpostul pentru femei. Te poate ajuta și biroul pentru cazare de urgență. Hilfebus ajută seara: {hilfebus_phone}.",
                "ru": f"Ty ishchesh mesto dlya sna{day_part}. Dlya zhenshchin snachala podhodit nochleg dlya zhenshchin. Otdel Notunterbringung tozhe mozhet pomoch. Hilfebus pomogaet vecherom: {hilfebus_phone}.",
            },
            language,
        )
    if target == "man":
        return _t(
            {
                "de": f"Du suchst einen Schlafplatz{day_part}. Wende dich zuerst an das Übernachtungshaus Rücke in der Rückmarsdorfer Straße. Telefon: 0341 1234504. Der Hilfebus hilft abends: {hilfebus_phone}.",
                "en": f"You are looking for a place to sleep{day_part}. First contact Übernachtungshaus Rücke in Rückmarsdorfer Straße. Phone: 0341 1234504. The Hilfebus can help in the evening: {hilfebus_phone}.",
                "pl": f"Szukasz miejsca do spania{day_part}. Najpierw skontaktuj się z Übernachtungshaus Rücke przy Rückmarsdorfer Straße. Telefon: 0341 1234504. Hilfebus pomaga wieczorem: {hilfebus_phone}.",
                "ro": f"Cauți un loc de dormit{day_part}. Contactează mai întâi Übernachtungshaus Rücke pe Rückmarsdorfer Straße. Telefon: 0341 1234504. Hilfebus ajută seara: {hilfebus_phone}.",
                "ru": f"Ty ishchesh mesto dlya sna{day_part}. Snachala obratis v Übernachtungshaus Rücke na Rückmarsdorfer Straße. Telefon: 0341 1234504. Hilfebus pomogaet vecherom: {hilfebus_phone}.",
            },
            language,
        )
    if target == "substance_use":
        return _t(
            {
                "de": f"Du suchst einen Schlafplatz{day_part}. Bei Drogengebrauch passen zuerst Alternative I und Alternative III. Der Hilfebus kann abends auch helfen: {hilfebus_phone}.",
                "en": f"You are looking for a place to sleep{day_part}. For substance use, start with Alternative I and Alternative III. The Hilfebus can also help in the evening: {hilfebus_phone}.",
                "pl": f"Szukasz miejsca do spania{day_part}. Przy używaniu substancji najpierw pasują Alternative I i Alternative III. Hilfebus może też pomóc wieczorem: {hilfebus_phone}.",
                "ro": f"Cauți un loc de dormit{day_part}. Pentru consum de substanțe, începe cu Alternative I și Alternative III. Hilfebus poate ajuta seara: {hilfebus_phone}.",
                "ru": f"Ty ishchesh mesto dlya sna{day_part}. Pri upotreblenii veshchestv snachala podhodyat Alternative I i Alternative III. Hilfebus tozhe mozhet pomoch vecherom: {hilfebus_phone}.",
            },
            language,
        )
    if target == "under_18":
        return _t(
            {
                "de": "Wenn du unter 18 bist, leite ich dich nicht zuerst zu Erwachsenen-Unterkünften. Wende dich an Streetwork oder Jugendhilfe. Bei akuter Gefahr ruf 112. Wenn du heute Nacht nicht sicher bist, ruf 110 oder 112.",
                "en": "If you are under 18, I will not send you first to adult shelters. Contact youth streetwork or youth help. If you are in immediate danger, call 112. If you are not safe tonight, call 110 or 112.",
                "pl": "Jeśli masz mniej niż 18 lat, nie kieruję cię najpierw do noclegowni dla dorosłych. Skontaktuj się ze streetworkiem dla młodzieży albo pomocą dla młodzieży. W nagłym zagrożeniu dzwoń 112.",
                "ro": "Dacă ai sub 18 ani, nu te trimit mai întâi la adăposturi pentru adulți. Contactează streetwork pentru tineri sau ajutor pentru tineri. În pericol imediat sună la 112.",
                "ru": "Esli tebe menshe 18 let, ya ne napravlyayu snachala vo vzroslye nochlegi. Obratis v molodezhnyy streetwork ili pomoshch molodezhi. Pri srochnoy opasnosti zvoni 112.",
            },
            language,
        )
    question = _t(SLEEP_TARGET_QUESTION, language)
    return _t(
        {
            "de": f"Du suchst einen Schlafplatz{day_part}. Wende dich zuerst an die Notunterbringung Rückmarsdorfer Straße. Dort wird dir weitergeholfen. Telefon: 0341 1234504. Der Hilfebus kann abends auch helfen: {hilfebus_phone}. {question}",
            "en": f"You are looking for a place to sleep{day_part}. First contact the emergency accommodation office at Rückmarsdorfer Straße. They can help you. Phone: 0341 1234504. The Hilfebus can also help in the evening: {hilfebus_phone}. {question}",
            "pl": f"Szukasz miejsca do spania{day_part}. Najpierw skontaktuj się z pomocą przy Rückmarsdorfer Straße. Tam powiedzą ci, co dalej. Telefon: 0341 1234504. Hilfebus może też pomóc wieczorem: {hilfebus_phone}. {question}",
            "ro": f"Cauți un loc de dormit{day_part}. Contactează mai întâi ajutorul de la Rückmarsdorfer Straße. Acolo primești sprijin. Telefon: 0341 1234504. Hilfebus poate ajuta seara: {hilfebus_phone}. {question}",
            "ru": f"Ty ishchesh mesto dlya sna{day_part}. Snachala obratis v pomoshch na Rückmarsdorfer Straße. Tam tebe pomogut. Telefon: 0341 1234504. Hilfebus tozhe mozhet pomoch vecherom: {hilfebus_phone}. {question}",
        },
        language,
    )


def _sleep_day_phrase(intent: V2Intent, language: Language, temporal_context: TemporalContext | None) -> str:
    normalized = normalize_text(intent.user_input)
    weekdays = [
        ("montag", "Monday"),
        ("dienstag", "Tuesday"),
        ("mittwoch", "Wednesday"),
        ("donnerstag", "Thursday"),
        ("freitag", "Friday"),
        ("samstag", "Saturday"),
        ("sonntag", "Sunday"),
    ]
    for de_name, en_name in weekdays:
        if de_name in normalized or en_name.casefold() in normalized:
            return _t(
                {
                    "de": f"für {de_name.capitalize()}",
                    "en": f"on {en_name}",
                    "pl": f"w dzień: {de_name.capitalize()}",
                    "ro": f"pentru {de_name.capitalize()}",
                    "ru": f"na {de_name.capitalize()}",
                },
                language,
            )
    if intent.urgency == "tonight":
        return _t({"de": "für heute Nacht", "en": "tonight", "pl": "na dzisiejszą noc", "ro": "pentru seara aceasta", "ru": "na segodnya noch"}, language)
    if intent.urgency in {"today", "now"}:
        return _t({"de": "für heute", "en": "today", "pl": "na dziś", "ro": "pentru azi", "ru": "na segodnya"}, language)
    if temporal_context:
        return _t({"de": "", "en": "", "pl": "", "ro": "", "ru": ""}, language)
    return ""


def _deterministic_answer(offers: list[V2Offer], intent: V2Intent, language: Language, temporal_context: TemporalContext | None) -> str:
    del temporal_context
    names = compact_names(offers)
    templates = CATEGORY_RESULT_TEXT.get(intent.primary_need, CATEGORY_RESULT_TEXT["general_advice"])
    text = _t(templates, language)
    if not names:
        return text
    return f"{text} {_t(CARD_HINT_TEXT, language)}"


def _offer_sentence(offer: V2Offer, language: Language, temporal_context: TemporalContext | None, intent: V2Intent) -> str:
    time = _best_time(offer, temporal_context)
    details: list[str] = [display_name(offer)]
    if offer.address:
        details.append(_t({"de": f"Adresse: {offer.address}.", "en": f"Address: {offer.address}.", "pl": f"Adres: {offer.address}.", "ro": f"Adresa: {offer.address}.", "ru": f"Adres: {offer.address}."}, language))
    elif offer.location:
        details.append(_t({"de": f"Ort: {offer.location}.", "en": f"Location: {offer.location}.", "pl": f"Miejsce: {offer.location}.", "ro": f"Loc: {offer.location}.", "ru": f"Mesto: {offer.location}."}, language))
    if time:
        details.append(_t({"de": f"Zeit: {time}.", "en": f"Time: {time}.", "pl": f"Czas: {time}.", "ro": f"Program: {time}.", "ru": f"Vremya: {time}."}, language))
    if intent.urgency in {"now", "today", "tonight"}:
        timing = _availability_sentence(_availability_for_offer(offer, temporal_context, intent), language)
        if timing:
            details.append(timing)
    phone = primary_phone(offer)
    if phone:
        phone_text = f"{phone}"
        details.append(_t({"de": f"Telefon: {phone_text}.", "en": f"Phone: {phone_text}.", "pl": f"Telefon: {phone_text}.", "ro": f"Telefon: {phone_text}.", "ru": f"Telefon: {phone_text}."}, language))
    if offer.requirements:
        details.append(_t({"de": f"Wichtig: {offer.requirements}.", "en": f"Important: {offer.requirements}.", "pl": f"Wazne: {offer.requirements}.", "ro": f"Important: {offer.requirements}.", "ru": f"Vazhno: {offer.requirements}."}, language))
    return " ".join(details)


def _best_time(offer: V2Offer, temporal_context: TemporalContext | None) -> str | None:
    times = offer.all_times
    if not times:
        return None
    if temporal_context:
        for value in times:
            if _weekday_hint(value, temporal_context):
                return value
    return times[0]


def _availability_for_offer(offer: V2Offer, temporal_context: TemporalContext | None, intent: V2Intent) -> Availability:
    if not temporal_context or not offer.all_times:
        return Availability("unknown")
    now_minutes = _minutes_from_temporal_context(temporal_context)
    if now_minutes is None:
        return Availability("unknown")
    has_day_specific_time = False
    has_unknown_today = False
    later: tuple[int, str, str] | None = None
    for time_text in offer.all_times:
        normalized = normalize_text(time_text)
        days = _days_for_time_text(normalized)
        if days is not None:
            has_day_specific_time = True
            if temporal_context.weekday_index not in days:
                continue
        if "ganztag" in normalized or "ganztägig" in normalized:
            return Availability("open_now", time_text)
        ranges = _time_ranges(time_text)
        if not ranges:
            if days is None or temporal_context.weekday_index in days:
                has_unknown_today = True
            continue
        for start, end, start_text in ranges:
            if _range_open_now(start, end, now_minutes):
                return Availability("open_now", time_text, start_text)
            if _range_later_today(start, end, now_minutes):
                candidate = (start, time_text, start_text)
                if later is None or candidate[0] < later[0]:
                    later = candidate
    if later:
        return Availability("available_today_later", later[1], later[2])
    if has_unknown_today:
        return Availability("available_today_unknown_time")
    if has_day_specific_time:
        return Availability("not_available_today")
    return Availability("unknown")


def _availability_sentence(availability: Availability, language: Language) -> str | None:
    if availability.status == "open_now":
        return _t({"de": "Jetzt möglich.", "en": "Available now.", "pl": "Dostępne teraz.", "ro": "Disponibil acum.", "ru": "Dostupno seychas."}, language)
    if availability.status == "available_today_later" and availability.start_text:
        return _t(
            {
                "de": f"Heute möglich, aber erst ab {availability.start_text} Uhr.",
                "en": f"Available today, but only from {availability.start_text}.",
                "pl": f"Dostępne dzisiaj, ale dopiero od {availability.start_text}.",
                "ro": f"Disponibil azi, dar doar de la {availability.start_text}.",
                "ru": f"Dostupno segodnya, no tolko s {availability.start_text}.",
            },
            language,
        )
    if availability.status == "available_today_unknown_time":
        return _t({"de": "Zeiten bitte prüfen.", "en": "Please check times.", "pl": "Sprawdź godziny.", "ro": "Verifică programul.", "ru": "Prover vremya."}, language)
    if availability.status == "not_available_today":
        return _t({"de": "Heute wahrscheinlich nicht.", "en": "Probably not available today.", "pl": "Prawdopodobnie nie dzisiaj.", "ro": "Probabil nu azi.", "ru": "Skoree vsego ne segodnya."}, language)
    return None


def _minutes_from_temporal_context(temporal_context: TemporalContext) -> int | None:
    try:
        value = temporal_context.now_iso.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.hour * 60 + parsed.minute


def _days_for_time_text(normalized: str) -> set[int] | None:
    if any(term in normalized for term in ("taeglich", "täglich", "jeden tag", "montag - sonntag", "montag bis sonntag")):
        return set(range(7))
    if any(term in normalized for term in ("montag - freitag", "montag bis freitag", "montag-freitag")):
        return set(range(5))
    if "wochenende" in normalized:
        return {5, 6}
    result = {index for index, names in enumerate(WEEKDAY_NAMES) if any(name in normalized for name in names)}
    return result or None


def _time_ranges(text: str) -> list[tuple[int, int, str]]:
    ranges: list[tuple[int, int, str]] = []
    for match in re.finditer(r"\b(\d{1,2})[:.](\d{2})\s*(?:-|–|bis)\s*(\d{1,2})[:.](\d{2})\b", text):
        start_hour, start_minute, end_hour, end_minute = (int(group) for group in match.groups())
        if start_hour > 23 or end_hour > 23 or start_minute > 59 or end_minute > 59:
            continue
        ranges.append((start_hour * 60 + start_minute, end_hour * 60 + end_minute, f"{start_hour:02d}:{start_minute:02d}"))
    return ranges


def _range_open_now(start: int, end: int, now: int) -> bool:
    if end <= start:
        return now >= start or now <= end
    return start <= now <= end


def _range_later_today(start: int, end: int, now: int) -> bool:
    if end <= start:
        return now < start
    return now < start


def _weekday_hint(text: str, temporal_context: TemporalContext) -> bool:
    normalized = normalize_text(text)
    names = [
        ("montag", "mo", "monday"),
        ("dienstag", "di", "tuesday"),
        ("mittwoch", "mi", "wednesday"),
        ("donnerstag", "do", "thursday"),
        ("freitag", "fr", "friday"),
        ("samstag", "sa", "saturday"),
        ("sonntag", "so", "sunday"),
    ][temporal_context.weekday_index]
    if any(name in normalized for name in names):
        return True
    return temporal_context.weekday_index <= 4 and "montag bis freitag" in normalized


def _detect_need(normalized: str, tokens: set[str]) -> V2Category | Literal["unknown"]:
    for category in ("food", "sleep", "medical", "addiction", "hygiene", "general_advice"):
        if _matches_need(category, normalized, tokens):
            return category  # type: ignore[return-value]
    return "unknown"


def _matches_need(category: str, normalized: str, tokens: set[str]) -> bool:
    terms = NEED_TERMS[category]
    return bool(tokens & terms or any(term in normalized for term in terms))


def _need_from_context_topic(topic: str | None) -> V2Category | Literal["unknown"]:
    return {
        "housing": "sleep",
        "social": "general_advice",
        "medical": "medical",
        "food": "food",
        "addiction": "addiction",
        "hygiene": "hygiene",
    }.get(topic or "", "unknown")  # type: ignore[return-value]


def _category_matches(offer: V2Offer, category: str) -> bool:
    haystack = normalize_text(
        " ".join(
            [
                offer.category,
                offer.subcategory or "",
                offer.card_summary or "",
                " ".join(offer.services_provided),
                " ".join(offer.retrieval_keywords),
                json.dumps(offer.facts, ensure_ascii=False),
            ]
        )
    )
    if offer.category == category:
        return True
    if category == "food":
        return any(term in haystack for term in ("essen", "lebensmittel", "mittagessen", "fruehstueck", "broetchen", "getraenk", "kaffee"))
    if category == "hygiene":
        return any(term in haystack for term in ("dusche", "duschen", "waesche", "waschmaschine", "hygiene"))
    if category == "general_advice":
        return offer.category in {"general_advice", "addiction"} or any(term in haystack for term in ("beratung", "unterstuetzung", "vermittlung"))
    if category == "medical":
        return any(
            term in haystack
            for term in (
                "medizin",
                "arzt",
                "aerzt",
                "gesundheit",
                "behandlung",
                "sprechstunde",
                "safer use",
                "konsummittel",
                "spritzen",
                "notversorgung",
                "medibus",
            )
        )
    return False


def _category_rank(offer: V2Offer, intent: V2Intent) -> int:
    if intent.primary_need == "food":
        if "hilfebus" in offer.offer_id:
            return 0
        if offer.offer_id in {"safe-team-wohnen", "diakonie-streetwork"}:
            return 1
        if "bahnhofsmission" in offer.offer_id:
            return 2
    if intent.primary_need == "sleep":
        if "notunterbringung" in offer.offer_id:
            return 0
        if "alternative" in offer.offer_id:
            return 1
    if intent.primary_need == "medical":
        order = {
            "uvo-medical-outreach": 0,
            "cabl-clearingstelle": 1,
            "kontaktcafe-alternative-i": 2,
            "mobile-alternative": 3,
            "alternative-i-notschlafstelle": 4,
            "alternative-iii-notschlafstelle": 5,
        }
        if offer.offer_id in order:
            return order[offer.offer_id]
        if offer.category == "medical":
            return 2
    if intent.primary_need == "addiction" and offer.category == "addiction":
        return 0
    if intent.primary_need == "general_advice":
        if offer.offer_id in {"safe-team-wohnen", "diakonie-streetwork", "bahnhofsmission", "soziale-wohnhilfen-wohnungsnotfallhilfe"}:
            return 0
    return 5


def _detect_urgency(normalized: str) -> str:
    if any(term in normalized for term in ("sofort", "jetzt", "now", "teraz", "acum", "seychas")):
        return "now"
    if any(term in normalized for term in ("heute nacht", "tonight")):
        return "tonight"
    if any(term in normalized for term in ("heute", "today", "dzis", "azi")):
        return "today"
    return "unknown"


def _time_reference(normalized: str) -> str | None:
    urgency = _detect_urgency(normalized)
    return None if urgency == "unknown" else urgency


def _guarded_answer(transcript: str, language: Language) -> KnowledgeAnswer | None:
    normalized = normalize_text(transcript)
    if any(term in normalized for term in CRISIS_TERMS):
        return KnowledgeAnswer(answer_text=_t(CRISIS_TEXT, language), status="crisis", crisis_mode=True)
    if _is_self_description(normalized):
        return KnowledgeAnswer(answer_text=_t(SELF_DESCRIPTION_TEXT, language), status="self_description", self_description=True)
    if any(term in normalized for term in OUT_OF_SCOPE_TERMS):
        return KnowledgeAnswer(answer_text=_t(OUT_OF_SCOPE_TEXT, language), status="out_of_scope", out_of_scope=True)
    return None


def _sleep_follow_up_options(language: Language) -> list[dict[str, str]]:
    return [{"label": label, "value": value} for label, value in SLEEP_FOLLOW_UP_OPTIONS.get(language.value, SLEEP_FOLLOW_UP_OPTIONS["de"])]


def _is_self_description(normalized: str) -> bool:
    return any(term in normalized for term in SELF_DESCRIPTION_TERMS)


def _sources(offers: list[V2Offer]) -> list[str]:
    result: list[str] = []
    for offer in offers:
        for source in [offer.source_url, *offer.detail_source_urls]:
            if source and source not in result:
                result.append(source)
    return result


def _last_checked(offers: list[V2Offer]) -> str | None:
    values = [offer.last_checked for offer in offers]
    return max(values) if values else None


def _evidence(offers: list[V2Offer]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for offer in offers:
        for item in offer.source_evidence[:3]:
            rows.append(
                {
                    "offer_id": offer.offer_id,
                    "field_name": item.field_name,
                    "source_url": item.source_url,
                    "checked_at": item.checked_at,
                }
            )
    return rows


def _requirements(offers: list[V2Offer]) -> list[str]:
    result: list[str] = []
    for offer in offers:
        if offer.requirements and offer.requirements not in result:
            result.append(offer.requirements)
    return result


def _offer_package(offer: V2Offer) -> dict:
    return {
        "offer_id": offer.offer_id,
        "name": offer.name,
        "organization": offer.organization,
        "category": offer.category,
        "description": offer.short_description,
        "card_summary": offer.card_summary,
        "retrieval_keywords": offer.retrieval_keywords,
        "address": offer.address,
        "location": offer.location,
        "times": offer.all_times,
        "phone": offer.phone,
        "email": offer.email,
        "website": offer.website,
        "phone_reachable_when": offer.phone_reachable_when,
        "requirements": offer.requirements,
        "cost": offer.cost,
        "services": offer.services_provided,
        "facts": offer.facts,
        "source_url": offer.source_url,
        "detail_source_urls": offer.detail_source_urls,
        "last_checked": offer.last_checked,
    }


def _unsupported_sensitive_fact(answer: str, deterministic: str, offers: list[V2Offer]) -> bool:
    allowed = normalize_text(deterministic + " " + json.dumps([_offer_package(offer) for offer in offers], ensure_ascii=False))
    candidate = normalize_text(answer)
    for pattern in (r"\b\d{1,2}[:.]\d{2}\b", r"\+?\d[\d /\-]{6,}\d", r"\b\d+\s*(?:eur|euro|cent)\b"):
        for match in re.findall(pattern, candidate):
            if normalize_text(match) not in allowed:
                return True
    return False


def _is_simple_overview_answer(answer: str) -> bool:
    text = answer.strip()
    if len(text) > 360:
        return False
    if re.search(r"\b(?:telefon|phone|adresse|address|zeit|time|öffnungszeit|opening)\s*:", text, flags=re.IGNORECASE):
        return False
    if re.search(r"\b(?:\+49\s*)?(?:0\d{2,5}[\s/-]?\d{3,}|\d{3,}[\s/-]\d{3,})\b", text):
        return False
    sentence_count = len([part for part in re.split(r"[.!?]+", text) if part.strip()])
    return sentence_count <= 4


def _clean_text(text: str | None) -> str:
    return " ".join((text or "").split()).strip()


def _v2_prompt_path(settings) -> Path:
    return settings.prompt_root / "system_prompt_v2.md"


def _load_v2_prompt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    if system_prompt:
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    return [{"role": "user", "content": user_prompt}]


def _t(values: dict[str, str], language: Language) -> str:
    return values.get(language.value) or values["de"]


UNKNOWN_TEXT = {
    "de": "Dazu habe ich keine sichere Information. Du kannst nach Essen, Schlafen, Medizin oder Beratung fragen.",
    "en": "I do not have safe information for that. Ask about food, sleep, medical help, clothes, showers, or advice.",
    "pl": "Nie mam do tego pewnej informacji. Zapytaj o jedzenie, nocleg, pomoc medyczna, ubrania, prysznic albo poradę.",
    "ro": "Nu am informații sigure pentru asta. Întreabă despre mâncare, somn, ajutor medical, haine, dușuri sau consiliere.",
    "ru": "U menya net nadezhnoy informatsii ob etom. Sprosi pro edu, nochleg, meditsinskuyu pomoshch, odezhdu, dush ili konsultatsiyu.",
}
FOOD_PREFIX = {
    "de": "Hier kannst du nach Essen oder Getränken fragen:",
    "en": "You can ask here for food or drinks:",
    "pl": "Tu mozesz zapytac o jedzenie albo napoje:",
    "ro": "Aici poti intreba despre mancare sau bauturi:",
    "ru": "Zdes mozhno sprosit pro edu ili napitki:",
}
SLEEP_PREFIX = {
    "de": "Ich kann keinen freien Platz versprechen. Diese Stellen können dir helfen:",
    "en": "I cannot promise that a bed is free. These places can help:",
    "pl": "Nie moge obiecac wolnego lozka. Te miejsca moga pomoc:",
    "ro": "Nu pot promite un loc liber. Aceste locuri pot ajuta:",
    "ru": "Ya ne mogu obeshchat svobodnoe mesto. Eti mesta mogut pomoch:",
}
MEDICAL_PREFIX = {
    "de": "Das ist keine Diagnose. Bei akuter Gefahr ruf 112. Für medizinische Hilfe:",
    "en": "This is not a diagnosis. In immediate danger call 112. For medical help:",
    "pl": "To nie jest diagnoza. W naglym zagrozeniu dzwon 112. Pomoc medyczna:",
    "ro": "Aceasta nu este un diagnostic. In pericol imediat suna la 112. Pentru ajutor medical:",
    "ru": "Eto ne diagnoz. Pri srochnoy opasnosti zvoni 112. Meditsinskaya pomoshch:",
}
ADVICE_PREFIX = {
    "de": "Hier kannst du nach Beratung fragen:",
    "en": "You can ask here for advice:",
    "pl": "Tu mozesz zapytac o porade:",
    "ro": "Aici poti cere consiliere:",
    "ru": "Zdes mozhno sprosit konsultatsiyu:",
}
ADDICTION_PREFIX = {
    "de": "Bei Fragen zu Drogen, Konsum oder Sucht können diese Stellen helfen:",
    "en": "For drugs, use, or addiction questions, you can start here:",
    "pl": "W sprawach narkotykow, uzywania albo uzaleznienia mozesz zaczac tutaj:",
    "ro": "Pentru droguri, consum sau dependenta poti incepe aici:",
    "ru": "Po voprosam narkotikov, potrebleniya ili zavisimosti mozhno nachat zdes:",
}
HYGIENE_PREFIX = {
    "de": "Für Duschen, Waschen oder Hygiene können diese Stellen helfen:",
    "en": "For showering, washing, or hygiene, these places can help:",
    "pl": "W sprawie prysznica, prania albo higieny te miejsca moga pomoc:",
    "ro": "Pentru dus, spalat sau igiena, aceste locuri pot ajuta:",
    "ru": "Dlya dusha, stirki ili gigieny eti mesta mogut pomoch:",
}
CATEGORY_RESULT_TEXT = {
    "food": {
        "de": "Ich habe Orte für Essen oder Getränke gefunden.",
        "en": "I found places for food or drinks.",
        "pl": "Znalazłam miejsca z jedzeniem albo napojami.",
        "ro": "Am găsit locuri pentru mâncare sau băuturi.",
        "ru": "Ya nashla mesta s edoy ili napitkami.",
    },
    "sleep": {
        "de": "Ich habe Orte für Schlafen oder Notunterkunft gefunden.",
        "en": "I found places for sleep or emergency accommodation.",
        "pl": "Znalazłam miejsca do spania albo noclegu awaryjnego.",
        "ro": "Am găsit locuri pentru dormit sau cazare de urgență.",
        "ru": "Ya nashla mesta dlya nochlega ili srochnogo razmeshcheniya.",
    },
    "medical": {
        "de": "Ich habe medizinische Hilfe gefunden.",
        "en": "I found medical help.",
        "pl": "Znalazłam pomoc medyczną.",
        "ro": "Am găsit ajutor medical.",
        "ru": "Ya nashla meditsinskuyu pomoshch.",
    },
    "general_advice": {
        "de": "Ich habe Beratungsstellen gefunden.",
        "en": "I found advice services.",
        "pl": "Znalazłam miejsca z poradą.",
        "ro": "Am găsit servicii de consiliere.",
        "ru": "Ya nashla mesta dlya konsultatsii.",
    },
    "addiction": {
        "de": "Ich habe Hilfe zu Drogen, Konsum oder Sucht gefunden.",
        "en": "I found help for drugs, substance use, or addiction.",
        "pl": "Znalazłam pomoc przy narkotykach, używaniu albo uzależnieniu.",
        "ro": "Am găsit ajutor pentru droguri, consum sau dependență.",
        "ru": "Ya nashla pomoshch po narkotikam, upotrebleniyu ili zavisimosti.",
    },
    "hygiene": {
        "de": "Ich habe Orte für Duschen, Waschen oder Hygiene gefunden.",
        "en": "I found places for showers, washing, or hygiene.",
        "pl": "Znalazłam miejsca z prysznicem, praniem albo higieną.",
        "ro": "Am găsit locuri pentru duș, spălat sau igienă.",
        "ru": "Ya nashla mesta dlya dusha, stirki ili gigieny.",
    },
}
CARD_HINT_TEXT = {
    "de": "Brauchst du mehr Informationen? Tippe auf eine Karte. Dort siehst du Ort, Zeit und Telefon.",
    "en": "Do you need more information? Tap a card. It shows place, time, and phone.",
    "pl": "Czy potrzebujesz więcej informacji? Naciśnij kartę. Tam jest miejsce, czas i telefon.",
    "ro": "Ai nevoie de mai multe informații? Apasă pe un card. Acolo vezi locul, ora și telefonul.",
    "ru": "Nuzhno bolshe informatsii? Nazhmi na kartochku. Tam est mesto, vremya i telefon.",
}
SLEEP_TARGET_QUESTION = {
    "de": "Für wen suchst du einen Schlafplatz?",
    "en": "Who needs a place to sleep?",
    "pl": "Dla kogo szukasz miejsca do spania?",
    "ro": "Pentru cine cauți un loc de dormit?",
    "ru": "Dlya kogo nuzhno mesto dlya sna?",
}
SLEEP_FOLLOW_UP_OPTIONS = {
    "de": [
        ("Mann", "Mann"),
        ("Frau", "Frau"),
        ("Divers", "Divers"),
        ("Unter 18", "Unter 18"),
        ("Drogengebrauch / Konsum", "Ich konsumiere Drogen"),
    ],
    "en": [
        ("Man", "man"),
        ("Woman", "woman"),
        ("Diverse", "diverse"),
        ("Under 18", "under 18"),
        ("Drug use / substance use", "drug use"),
    ],
    "pl": [
        ("Mężczyzna", "Mann"),
        ("Kobieta", "Frau"),
        ("Osoba różnorodna", "Divers"),
        ("Poniżej 18", "Unter 18"),
        ("Używanie substancji", "Ich konsumiere Drogen"),
    ],
    "ro": [
        ("Bărbat", "Mann"),
        ("Femeie", "Frau"),
        ("Divers", "Divers"),
        ("Sub 18", "Unter 18"),
        ("Consum de substanțe", "Ich konsumiere Drogen"),
    ],
    "ru": [
        ("Muzhchina", "Mann"),
        ("Zhenshchina", "Frau"),
        ("Divers", "Divers"),
        ("Mladshe 18", "Unter 18"),
        ("Upotreblenie veshchestv", "Ich konsumiere Drogen"),
    ],
}
CRISIS_TEXT = {
    "de": "Akute Gefahr: Ruf sofort 112. Bei Gewalt oder Gefahr durch andere Menschen ruf 110. Bleib nicht allein.",
    "en": "Immediate danger: call 112 now. For violence or danger from another person, call 110. Do not stay alone.",
    "pl": "Bezposrednie zagrozenie: dzwon 112. Przy przemocy lub zagrozeniu od innej osoby dzwon 110. Nie zostawaj sam.",
    "ro": "Pericol imediat: suna la 112. Pentru violenta sau pericol de la alta persoana suna la 110. Nu ramane singur.",
    "ru": "Srochnaya opasnost: zvoni 112. Pri nasilii ili opasnosti ot drugogo cheloveka zvoni 110. Ne ostavaysya odin.",
}
OUT_OF_SCOPE_TEXT = {
    "de": "Dabei kann ich dir nicht helfen. Ich helfe bei Fragen zu Hilfsangeboten in Leipzig, zum Beispiel Essen, Schlafen, Medizin, Kleidung, Duschen oder Beratung.",
    "en": "I can’t help with that. I can help with support services in Leipzig, for example food, sleep, medical help, clothes, showers, or advice.",
    "pl": "Nie moge w tym pomoc. Odpowiadam tylko na pytania o pomoc w Lipsku.",
    "ro": "Nu pot ajuta cu asta. Raspund doar la intrebari despre ajutor in Leipzig.",
    "ru": "Ya ne mogu s etim pomoch. Ya otvechayu tolko na voprosy o pomoshchi v Leyptsige.",
}
SELF_DESCRIPTION_TEXT = {
    "de": "Ich bin LENA. Ich helfe dir, passende Hilfe in Leipzig zu finden. Zum Beispiel Essen, Schlafplätze, medizinische Hilfe, Kleidung, Duschen oder Beratung. Du kannst ein Symbol auswählen oder mir deine Frage schreiben.",
    "en": "I am LENA. I help you find support in Leipzig. For example food, a place to sleep, medical help, clothes, showers, or advice. You can choose a symbol or write your question.",
    "pl": "Jestem LENA. Pomagam znaleźć pomoc w Lipsku. Na przykład jedzenie, nocleg, pomoc medyczną, ubrania, prysznic albo poradę. Możesz wybrać symbol albo napisać pytanie.",
    "ro": "Sunt LENA. Te ajut să găsești sprijin în Leipzig. De exemplu mâncare, un loc de dormit, ajutor medical, haine, dușuri sau consiliere. Poți alege un simbol sau poți scrie întrebarea.",
    "ru": "Ya LENA. Ya pomogayu nayti pomoshch v Leyptsige. Naprimer edu, mesto dlya sna, meditsinskuyu pomoshch, odezhdu, dush ili konsultatsiyu. Mozhno vybrat simvol ili napisat vopros.",
}
NEED_TERMS = {
    "food": {"essen", "food", "mahlzeit", "suppe", "hungrig", "hunger", "jedzenie", "jedzenia", "mancare", "foame", "eda", "edu"},
    "sleep": {"schlafen", "schlafplatz", "uebernachten", "ubernachten", "notunterkunft", "notunterbringung", "obdachlos", "wohnungslos", "unterkunft", "sleep", "shelter", "homeless", "place to sleep", "nocleg", "spac", "somn", "dormi", "adapost", "nochleg"},
    "medical": {"medizin", "medizinisch", "arzt", "medical", "doctor", "wunde", "krank", "lekarz", "medyczna", "medic", "cabl", "uvo"},
    "addiction": {"sucht", "drogen", "droge", "konsum", "addiction", "drugs", "narkotyk", "narkotyki", "droguri", "dependenta"},
    "hygiene": {"duschen", "dusche", "waesche", "waschen", "shower", "wash", "prysznic", "dus", "igiena", "hygiene"},
    "general_advice": {"beratung", "advice", "hilfe", "help", "support", "porada", "pomoc", "consiliere", "ajutor", "bahnhofsmission"},
}
WEEKDAY_NAMES = [
    ("montag", "mo", "monday"),
    ("dienstag", "di", "tuesday"),
    ("mittwoch", "mi", "wednesday"),
    ("donnerstag", "do", "thursday"),
    ("freitag", "fr", "friday"),
    ("samstag", "sa", "saturday"),
    ("sonntag", "so", "sunday"),
]
CRISIS_TERMS = {
    "ich will sterben",
    "ich bringe mich um",
    "ueberdosis",
    "uberdosis",
    "bewusstlos",
    "kann nicht atmen",
    "kill myself",
    "overdose",
    "unconscious",
    "cant breathe",
    "can't breathe",
    "violence",
    "gewalt",
}
SELF_DESCRIPTION_TERMS = {"wer bist du", "was machst du", "was ist lena", "who are you", "what do you do", "what is lena"}
OUT_OF_SCOPE_TERMS = {
    "hauptstadt",
    "capital of",
    "witz",
    "joke",
    "hausaufgabe",
    "homework",
    "telescope",
    "teleskop",
    "mathe",
    "math",
    "wetter",
    "weather",
    "code",
    "programming",
}
