from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..models import Manifest, PageMetadata, PublishedDataset
from ..retrieval import normalize_text
from .models import V2Dataset, V2Offer


class V2KnowledgeBase:
    """Reviewed one-source v2 KB with the small protocol V1 sessions need."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.reload()

    def reload(self) -> None:
        self.v2_dataset = V2Dataset.model_validate_json(self.path.read_text(encoding="utf-8"))
        self.offers_by_id = {offer.offer_id: offer for offer in self.v2_dataset.offers}
        self._pages_by_id = {offer.offer_id: self._page_for_offer(offer) for offer in self.v2_dataset.offers}
        self.dataset = PublishedDataset(
            manifest=Manifest(
                kb_version=self.v2_dataset.version,
                generated_at=self.v2_dataset.generated_at,
                source_count=1,
                page_count=len([offer for offer in self.v2_dataset.offers if offer.is_user_offer]),
                document_count=len(self.v2_dataset.offers),
                entity_count=len(self.v2_dataset.offers),
            ),
            pages=[page for page in self._pages_by_id.values()],
            aliases=self._alias_index(),
            field_indexes={},
        )

    @property
    def source_last_checked(self) -> str | None:
        values = [offer.last_checked for offer in self.v2_dataset.offers if offer.last_checked]
        return max(values) if values else None

    def get_offer(self, offer_id: str) -> V2Offer:
        return self.offers_by_id[offer_id]

    def get_page(self, page_id: str) -> PageMetadata:
        return self._pages_by_id[page_id]

    def get_page_markdown(self, page_id: str) -> str:
        offer = self.get_offer(page_id)
        return "\n".join(
            [
                f"# {offer.name}",
                offer.card_summary or offer.short_description,
                f"Category: {offer.category}",
                f"Keywords: {', '.join(offer.retrieval_keywords)}",
                f"Services: {', '.join(offer.services_provided)}",
                f"Location: {offer.location or ''}",
                f"Address: {offer.address or ''}",
                f"Times: {' | '.join(offer.all_times)}",
                f"Phone: {offer.phone or ''}",
                f"Email: {offer.email or ''}",
                f"Website: {offer.website or ''}",
                f"Facts: {json.dumps(offer.facts, ensure_ascii=False)}",
                f"Requirements: {offer.requirements or ''}",
                f"Cost: {offer.cost or ''}",
                f"Source: {offer.source_url}",
            ]
        )

    def get_index_hits(self, index_name: str, term: str) -> list[str]:
        del index_name, term
        return []

    def _page_for_offer(self, offer: V2Offer) -> PageMetadata:
        category = {
            "sleep": "housing",
            "general_advice": "social",
            "addiction": "addiction",
            "hygiene": "hygiene",
            "emergency_system": "emergency",
        }.get(offer.category, offer.category)
        return PageMetadata(
            entity_id=offer.offer_id,
            page_id=offer.offer_id,
            entity_kind="service_location" if offer.address else "service_program",
            organization=offer.organization,
            title=offer.name,
            canonical_title=offer.name,
            category=category,
            service_type=offer.subcategory or offer.category,
            language="de",
            source_url=offer.source_url,
            source_urls=[offer.source_url, *offer.detail_source_urls],
            last_updated=offer.last_checked,
            last_verified=offer.last_checked,
            publisher=offer.organization,
            address=offer.address,
            latitude=offer.coordinates.latitude if offer.coordinates else None,
            longitude=offer.coordinates.longitude if offer.coordinates else None,
            geo_status="ready" if offer.coordinates and offer.address else None,
            geo_source="manual" if offer.coordinates else None,
            geo_confidence=1.0 if offer.coordinates else None,
            geo_precision="exact" if offer.coordinates else None,
            district=offer.location,
            opening_hours=offer.all_times,
            description=offer.card_summary or offer.short_description,
            target_groups=offer.target_group,
            eligibility=offer.requirements,
            walk_in="registration" not in normalize_text(offer.requirements or ""),
            requires_registration="registration" in normalize_text(offer.requirements or "") or "anmeldung" in normalize_text(offer.requirements or ""),
            appointment_required=None,
            languages=offer.languages,
            phone=offer.phone,
            email=offer.email,
            tags=[offer.category, offer.subcategory or "", *offer.services_provided, *offer.retrieval_keywords, *offer.aliases],
            aliases=[offer.name, offer.organization, *offer.aliases],
            source_trust_tier=1,
            review_status="published" if offer.review_status in {"reviewed", "published"} else "needs_review",
            validation_issues=[] if offer.review_status in {"reviewed", "published"} else ["not_reviewed"],
            source_snapshot_path=offer.snapshot_path,
            source_content_hash=offer.source_hash,
            source_last_seen=offer.last_checked,
            source_updated_at=offer.last_checked,
            summary=offer.card_summary or offer.short_description,
            file_path=f"{offer.offer_id}.md",
        )

    def _alias_index(self) -> dict[str, list[str]]:
        aliases: dict[str, list[str]] = {}
        for offer in self.v2_dataset.offers:
            terms = [
                offer.offer_id,
                offer.name,
                offer.organization,
                offer.category,
                offer.subcategory or "",
                offer.card_summary or "",
                *offer.aliases,
                *offer.services_provided,
                *offer.retrieval_keywords,
            ]
            for term in terms:
                normalized = normalize_text(term).strip()
                if not normalized:
                    continue
                aliases.setdefault(normalized, []).append(offer.offer_id)
        return aliases


def load_v2_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
