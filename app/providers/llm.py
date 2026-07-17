"""Zweistufiger Blablador-Client mit strenger ID- und Faktenvalidierung."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Iterable

import httpx
from pydantic import ValidationError

from ..config import Settings
from ..models import Category, ChatTurn, LLMAnswer, LLMRoute, Language, OfferRecord
from ..offer_roles import sleep_roles


URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
NUMBERISH_RE = re.compile(r"(?<!\w)\+?\d[\d\s().:/-]{1,}\d(?!\w)")
TIME_ATOM_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
PLAIN_NUMBER_RE = re.compile(r"\d+")
UNSAFE_AVAILABILITY = (
    "open now",
    "currently open",
    "jetzt geoffnet",
    "aktuell geoffnet",
    "wolne miejsca",
    "locuri libere",
    "сейчас открыто",
    "свободные места",
)
LOGGER = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Kennzeichnet einen sicher auf Templates zurückfallenden Providerfehler."""
    pass


class ProviderTimeoutError(ProviderError):
    """Kennzeichnet eine abgelaufene Gesamtgrenze eines LLM-Schritts."""


@dataclass(frozen=True)
class ProviderAnswer:
    answer: str
    card_ids: list[str]


@dataclass(frozen=True)
class ProviderRoute:
    intent: Category | None
    offer_ids: list[str]
    needs_clarification: bool
    out_of_scope: bool
    acute_risk_detected: bool = False


def _record_payload(offer: OfferRecord) -> dict[str, Any]:
    return {
        "id": offer.id,
        "name": offer.name,
        "category": offer.source_category,
        "short_description": offer.short_description,
        "address": offer.address,
        "services": offer.services,
        "opening_hours": offer.opening_hours_raw,
        "stand_times": offer.standzeiten_raw,
        "phones": offer.phone_numbers,
        "emails": offer.emails,
        "website": offer.website,
        "notes": offer.notes,
        "other_source_fields": {
            label: values
            for label, values in offer.raw_fields.items()
            if label
            not in {
                "Name", "Kategorie", "Kurzbeschreibung", "Adresse", "Angebote", "Öffnungszeiten",
                "Telefon", "E-Mail", "Internetseite", "Sonstige Hinweise",
            }
        },
    }


def compact_offer_context(offers: Iterable[OfferRecord]) -> str:
    return json.dumps([_record_payload(offer) for offer in offers], ensure_ascii=False, separators=(",", ":"))


def _index_payload(offer: OfferRecord) -> dict[str, Any]:
    return {
        "id": offer.id,
        "name": offer.name,
        "category": offer.source_category,
        "short_description": offer.short_description,
        "address": offer.address,
        "services": offer.services,
        "notes": offer.notes,
    }


def compact_offer_index(offers: Iterable[OfferRecord]) -> str:
    return json.dumps([_index_payload(offer) for offer in offers], ensure_ascii=False, separators=(",", ":"))


def _conversation_payload(history: Iterable[ChatTurn] | None) -> list[dict[str, str]]:
    turns = list(history or [])[-6:]
    return [{"user": turn.question, "lena": turn.answer} for turn in turns]


def _response_content(response: dict[str, Any]) -> str:
    raw_content = response["choices"][0]["message"]["content"]
    if isinstance(raw_content, str):
        content = raw_content.strip()
    elif isinstance(raw_content, list):
        content = "".join(
            item.get("text", "")
            for item in raw_content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ).strip()
    else:
        raise TypeError("Blablador response contains no answer text")
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE)
    return content


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _canonical_number(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def _validate_grounding(answer: str, records: list[dict[str, Any]]) -> None:
    source_strings = list(_iter_strings(records))
    source_urls = {url.rstrip(".,;)") for text in source_strings for url in URL_RE.findall(text)}
    source_emails = {email.casefold() for text in source_strings for email in EMAIL_RE.findall(text)}
    source_times = {_canonical_number(value) for text in source_strings for value in TIME_ATOM_RE.findall(text)}
    source_plain_numbers = {value for text in source_strings for value in PLAIN_NUMBER_RE.findall(text)}
    source_long_numbers = {
        _canonical_number(value)
        for text in source_strings
        for value in NUMBERISH_RE.findall(text)
        if ":" not in value and len(_canonical_number(value)) >= 6
    }

    for url in URL_RE.findall(answer):
        if url.rstrip(".,;)") not in source_urls:
            raise ProviderError("LLM returned an unsupported URL")
    for email in EMAIL_RE.findall(answer):
        if email.casefold() not in source_emails:
            raise ProviderError("LLM returned an unsupported e-mail address")
    for value in TIME_ATOM_RE.findall(answer):
        if _canonical_number(value) not in source_times:
            raise ProviderError("LLM returned an unsupported time")
    for value in NUMBERISH_RE.findall(answer):
        canonical = _canonical_number(value)
        if ":" not in value and len(canonical) >= 6 and canonical not in source_long_numbers:
            raise ProviderError("LLM returned an unsupported long number")
    for value in PLAIN_NUMBER_RE.findall(answer):
        if len(value) >= 3 and value not in source_plain_numbers:
            raise ProviderError("LLM returned an unsupported number")

    normalized_answer = answer.casefold().replace("ö", "o")
    if any(claim in normalized_answer for claim in UNSAFE_AVAILABILITY):
        raise ProviderError("LLM made an unsupported current-availability claim")


class BlabladorProvider:
    """Routet über einen kompakten Index und formuliert aus ausgewählten Records."""
    name = "blablador"

    def __init__(self, settings: Settings) -> None:
        if not settings.blablador_configured:
            raise ProviderError("Blablador is not configured")
        self.base_url = settings.blablador_base_url or ""
        self.api_key = settings.blablador_api_key or ""
        self.model = settings.blablador_model or ""
        self.timeout = settings.blablador_timeout_seconds
        self.router_timeout = settings.llm_router_timeout_seconds
        self.formulator_timeout = settings.llm_formulator_timeout_seconds
        self.max_context_chars = settings.blablador_max_context_chars
        self.max_tokens = settings.blablador_max_tokens

    def context_fits(self, offers: Iterable[OfferRecord]) -> bool:
        return len(compact_offer_context(offers)) <= self.max_context_chars

    def index_context_fits(self, offers: Iterable[OfferRecord]) -> bool:
        return len(compact_offer_index(offers)) <= self.max_context_chars

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def _request_with_timeout(
        self,
        payload: dict[str, Any],
        *,
        timeout_seconds: float,
        stage: str,
    ) -> dict[str, Any]:
        """Begrenzt einen asynchronen Provideraufruf auf eine Gesamtdauer."""
        try:
            async with asyncio.timeout(timeout_seconds):
                return await self._post(payload)
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise ProviderTimeoutError(f"Blablador {stage} timed out") from exc

    async def route(
        self,
        *,
        query: str,
        language: Language,
        category: Category | None,
        offers: list[OfferRecord],
        conversation_history: list[ChatTurn] | None = None,
    ) -> ProviderRoute:
        """Ermittelt Intent und ausschließlich bekannte Angebots-IDs."""
        records = [_index_payload(offer) for offer in offers]
        context = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
        if len(context) > self.max_context_chars:
            raise ProviderError("Offer index is too large")

        roles = sleep_roles(offers)
        ruecke_id = roles["ruecke"][0].id if roles["ruecke"] else None
        sleep_policy = {
            "general_sleep_first": ruecke_id,
            "men": [offer.id for offer in roles["men"]],
            "women": [offer.id for offer in roles["women"]],
            "drug_use": [offer.id for offer in roles["drug"]],
            "source_note": (
                "Alternative I states that referral mainly occurs through the emergency shelter in "
                "Rückmarsdorfer Straße. The source does not state that new people are always admitted."
            ),
        }
        system = (
            "You are LENA's retrieval router. Map the question to the supplied OFFER_INDEX. "
            "Return JSON only with intent, offer_ids, needs_clarification, out_of_scope, and "
            "acute_risk_detected. acute_risk_detected is only a safety signal for the application. "
            "Set it to true when the latest question indicates acute self-harm or suicide intent, "
            "acute danger to another person, a concrete threat of violence, an acute medical danger, "
            "or a comparable immediate danger. Do not diagnose. Do not choose or mention a phone number, "
            "emergency service, or safety response. Set it to false for normal, metaphorical, historical, "
            "or clearly past non-acute statements unless the current context still indicates immediate danger. "
            "intent must be food, sleep, medical, advice, or unknown. Select at most six existing IDs. "
            "Do not answer the question and do not add facts. A selected category is a strong user hint. "
            "Use CONVERSATION_CONTEXT to resolve follow-up answers, corrections, and constraints such as "
            "age, gender, drug use, language, time, or a previously asked help type. The latest question "
            "has priority when it corrects earlier context. "
            "For a general sleep request, select the Rückmarsdorfer Straße priority first and then useful "
            "target-group alternatives. For explicit men, women, or drug-use wording, select only compatible "
            "sleep offers and apply the supplied SLEEP_ROUTING_POLICY. If context says the user is under 18, "
            "prefer youth-compatible records; if none are present, select relevant sleep records only as "
            "context so the answer can explain that they are not suitable, not to recommend them. "
            "Never treat a male-only offer as a "
            "women's offer. Set out_of_scope only when the question is clearly unrelated to Leipzig support."
        )
        user = json.dumps(
            {
                "requested_language": language.value,
                "question": query,
                "selected_category": category.value if category else None,
                "CONVERSATION_CONTEXT": _conversation_payload(conversation_history),
                "SLEEP_ROUTING_POLICY": sleep_policy,
                "OFFER_INDEX": records,
            },
            ensure_ascii=False,
        )
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": min(self.max_tokens, 600),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            response = await self._request_with_timeout(
                payload,
                timeout_seconds=self.router_timeout,
                stage="router",
            )
            parsed = LLMRoute.model_validate_json(_response_content(response))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            LOGGER.warning(
                "llm_route_response_invalid",
                extra={"event": "llm_route_response_invalid", "error_type": type(exc).__name__},
            )
            raise ProviderError("Blablador returned an unusable routing response") from exc

        if parsed.acute_risk_detected:
            return ProviderRoute(
                intent=None,
                offer_ids=[],
                needs_clarification=False,
                out_of_scope=False,
                acute_risk_detected=True,
            )

        allowed_ids = {offer.id for offer in offers}
        if len(parsed.offer_ids) != len(set(parsed.offer_ids)) or any(
            offer_id not in allowed_ids for offer_id in parsed.offer_ids
        ):
            raise ProviderError("Blablador router returned an unknown or duplicate offer ID")
        if parsed.out_of_scope and parsed.offer_ids:
            raise ProviderError("Out-of-scope routing must not return offers")
        if category and parsed.intent not in {category.value, "unknown"}:
            raise ProviderError("Blablador router contradicted the selected category")
        intent = Category(parsed.intent) if parsed.intent != "unknown" else None
        if intent and not parsed.needs_clarification and not parsed.offer_ids:
            raise ProviderError("Blablador router returned no offers for a mapped request")
        return ProviderRoute(
            intent=intent,
            offer_ids=parsed.offer_ids,
            needs_clarification=parsed.needs_clarification,
            out_of_scope=parsed.out_of_scope,
            acute_risk_detected=False,
        )

    async def answer(
        self,
        *,
        query: str,
        language: Language,
        category: Category | None,
        offers: list[OfferRecord],
        routing_context: dict[str, Any] | None = None,
        conversation_history: list[ChatTurn] | None = None,
    ) -> ProviderAnswer:
        """Formuliert eine Antwort und validiert sie gegen übergebene Records.

        Raises:
            ProviderError: Bei HTTP-, Format-, ID- oder Groundingfehlern.
        """
        records = [_record_payload(offer) for offer in offers]
        context = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
        if len(context) > self.max_context_chars:
            raise ProviderError("Grounded context is too large")

        system = (
            "You formulate short answers for LENA. Use only facts in OFFER_RECORDS. "
            "Never invent, infer, enrich, search, or claim current availability or free capacity. "
            "Keep facts attached to their offer. Return JSON only with keys answer and card_ids. "
            "The answer must use the requested language and simple, easy-to-understand wording. "
            "Use CONVERSATION_CONTEXT to understand follow-up messages, corrections, and personal constraints. "
            "The latest user message has priority when it changes earlier context. If the conversation shows "
            "that a selected offer no longer fits the user, say that clearly instead of recommending it. "
            "Always address the user informally and directly: German du/dir/dich, Polish ty/Ci/ciebie, "
            "Romanian tu/te/iti, Russian ты/тебе/тебя. Never use formal German Sie/Ihnen. "
            "Never mention internal record IDs, source IDs, offer IDs, card IDs, or labels like 'ID 7'. "
            "Translate explanatory prose into the requested language, but keep proper names, service names, "
            "street names, place names, addresses, phone numbers, e-mail addresses, URLs, and exact times unchanged. "
            "Use at most two short sentences. card_ids may contain zero to four IDs from OFFER_RECORDS. "
            "Return no card_ids when no supplied record is safe or suitable for the user's stated constraints. "
            "If the user says they are under 18 and asks for a place to sleep, do not list adult shelters "
            "as suitable. Explain in the requested language that LENA has no suitable verified overnight "
            "place for minors in these records. "
            "Operational details remain in cards. "
            "If routing_context contains temporal_policy_notes, treat them as binding and include the relevant "
            "day, time, and place in the answer. For stand times or mobile offers, do not say that help is "
            "available at the office address unless OFFER_RECORDS explicitly says so. Do not mix office hours "
            "with food distribution, mobile medical service, or Hilfebus stand times. "
            "For general sleep routing, begin with the supplied Rückmarsdorfer Straße priority, then explain "
            "briefly that different places apply to men, women, and drug-using people. For an explicit target "
            "group, never recommend an incompatible offer. Do not claim that new people are admitted unless "
            "that statement appears in OFFER_RECORDS."
        )
        user = json.dumps(
            {
                "requested_language": language.value,
                "question": query,
                "selected_category": category.value if category else None,
                "routing_context": routing_context,
                "CONVERSATION_CONTEXT": _conversation_payload(conversation_history),
                "OFFER_RECORDS": records,
            },
            ensure_ascii=False,
        )
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            response = await self._request_with_timeout(
                payload,
                timeout_seconds=self.formulator_timeout,
                stage="formulator",
            )
            parsed = LLMAnswer.model_validate_json(_response_content(response))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise ProviderError("Blablador returned an unusable response") from exc

        answer = " ".join(parsed.answer.split())
        if not answer or len(answer) > 600:
            raise ProviderError("Blablador answer length is invalid")
        allowed_ids = {offer.id for offer in offers}
        if len(parsed.card_ids) != len(set(parsed.card_ids)) or any(card_id not in allowed_ids for card_id in parsed.card_ids):
            raise ProviderError("Blablador returned an unknown or duplicate offer ID")
        _validate_grounding(answer, records)
        return ProviderAnswer(answer=answer, card_ids=parsed.card_ids)
