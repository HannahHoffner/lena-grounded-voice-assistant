"""Schema-validierte öffentliche Angebotsquellen außerhalb des städtischen WFS."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .models import OfferRecord


class OfficialSourceError(RuntimeError):
    """Signalisiert fehlende oder ungültige paketierte Betreiberangaben."""


class OfficialSourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    url: HttpUrl
    retrieved_at: datetime


class OfficialOfferSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    source_version: str
    sources: list[OfficialSourceReference]
    offers: list[OfferRecord]


def load_official_offer_source(path: Path) -> tuple[OfficialOfferSource, str]:
    """Lädt Betreiberangaben strikt und liefert ihren unveränderten Dateihash."""

    if not path.is_file():
        raise OfficialSourceError("Official offer source is missing")
    try:
        payload = path.read_bytes()
        source = OfficialOfferSource.model_validate_json(payload)
    except (OSError, ValueError) as exc:
        raise OfficialSourceError("Official offer source is invalid") from exc
    source_hash = hashlib.sha256(payload).hexdigest()
    ids = [offer.id for offer in source.offers]
    if len(ids) != len(set(ids)):
        raise OfficialSourceError("Official offer source contains duplicate IDs")
    reference_ids = {reference.id for reference in source.sources}
    for offer in source.offers:
        if not set(offer.source_reference_ids) <= reference_ids:
            raise OfficialSourceError("Official offer has an unknown source reference")
        if offer.raw_fields or offer.raw_properties:
            raise OfficialSourceError("Official offer must not imitate WFS raw fields")
    source = source.model_copy(
        update={
            "offers": [
                offer.model_copy(update={"source_hash": source_hash})
                for offer in source.offers
            ]
        }
    )
    return source, source_hash
