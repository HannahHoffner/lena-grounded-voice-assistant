from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import httpx


class BuildQualityReviewer(ABC):
    name = "disabled"

    @abstractmethod
    async def review(self, changed_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError


class DisabledBuildQualityReviewer(BuildQualityReviewer):
    async def review(self, changed_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        del changed_records
        return []


class OpenAICompatibleBuildQualityReviewer(BuildQualityReviewer):
    name = "openai-compatible"

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def review(self, changed_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not changed_records:
            return []
        prompt = {
            "task": (
                "Review the changed knowledge-base entities for contradictions, likely duplicate entities, "
                "normalization problems, and low-confidence extraction risks. "
                "Return only evidence-backed suggestions. Do not invent source facts."
            ),
            "records": [
                {
                    "entity_id": record.get("page_id"),
                    "title": record.get("title"),
                    "organization": record.get("organization") or record.get("publisher"),
                    "address": record.get("address"),
                    "opening_hours": record.get("opening_hours"),
                    "description": record.get("description"),
                    "target_groups": record.get("target_groups"),
                    "review_status": record.get("review_status"),
                    "validation_issues": record.get("validation_issues"),
                    "source_urls": record.get("source_urls") or [record.get("source_url")],
                    "source_document_refs": record.get("source_document_refs", []),
                }
                for record in changed_records[:50]
            ],
            "output_schema": {
                "suggestions": [
                    {
                        "entity_id": "page id",
                        "issue_type": "contradiction|duplicate_candidate|normalization|coverage_gap",
                        "summary": "short description",
                        "evidence_required": "what should be manually verified",
                    }
                ]
            },
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        suggestions = parsed.get("suggestions", [])
        if not isinstance(suggestions, list):
            return []
        return [item for item in suggestions if isinstance(item, dict) and item.get("entity_id")]


def create_build_quality_reviewer(
    *,
    enabled: bool,
    provider: str,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
) -> BuildQualityReviewer:
    if not enabled:
        return DisabledBuildQualityReviewer()
    if provider == "openai-compatible" and model and base_url and api_key:
        return OpenAICompatibleBuildQualityReviewer(base_url=base_url, api_key=api_key, model=model)
    return DisabledBuildQualityReviewer()
