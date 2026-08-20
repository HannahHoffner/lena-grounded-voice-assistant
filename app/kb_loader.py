"""Lädt die kanonische JSON-Wissensbasis und unterstützt Markdown-Importe."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import Settings
from .curation import (
    CurationError,
    OrganizationAliasBinding,
    catalog_metadata,
    load_curation_catalog,
    project_runtime_offers,
)
from .models import OfferRecord
from .official_offer_source import OfficialSourceError, load_official_offer_source
from .resources import packaged_bootstrap_data_root
from .drinking_fountain_releases import (
    DrinkingFountainReleaseError,
    load_drinking_fountain_runtime,
)
from .drinking_fountain_source import DRINKING_FOUNTAIN_NORMALIZATION_VERSION
from .infrastructure import DrinkingFountainRecord, PublicToiletRecord, TOILET_NORMALIZATION_VERSION
from .toilet_releases import ToiletReleaseError, load_toilet_runtime
from .wfs_releases import (
    ActiveReleasePointer,
    VerifiedRelease,
    WfsReleaseError,
    WfsReleasePaths,
    load_active_release,
    verify_release,
)


SECTION_RE = re.compile(
    r"(?ms)^###\s+(?P<number>\d+)\.\s+(?P<title>[^\r\n]+)\r?\n"
    r"(?P<body>.*?)(?=^---\s*$|\Z)"
)
FIELD_RE = re.compile(r"^\*\*(?P<label>[^*]+):\*\*\s*(?P<inline>.*)$")
TIME_RE = re.compile(r"\b\d{1,2}\s*[:.]\s*\d{2}\b")
WEEKDAY_RE = re.compile(
    r"\b(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|wochenende|feiertag)\b",
    re.IGNORECASE,
)


class KnowledgeBaseError(RuntimeError):
    """Signalisiert einen sicheren, redigierbaren Fehler der Wissensbasis."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "runtime_kb_unavailable",
        source_status: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.source_status = source_status

@dataclass(frozen=True)
class KnowledgeBase:
    """Geladener, unveränderlicher Laufzeitdatenbestand mit Quellenmetadaten."""
    path: Path
    source_hash: str
    offers: list[OfferRecord]
    source_kind: str = "markdown"
    metadata: dict[str, object] = field(default_factory=dict)
    release_id: str | None = None
    organization_aliases: tuple[OrganizationAliasBinding, ...] = ()
    runtime_kb_fingerprint: str | None = None
    runtime_validated: bool = False
    public_toilets: tuple[PublicToiletRecord, ...] = ()
    drinking_fountains: tuple[DrinkingFountainRecord, ...] = ()

    def by_id(self) -> dict[str, OfferRecord]:
        return {offer.id: offer for offer in self.offers}


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = ascii_text.replace("ß", "ss")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:56] or "angebot"


def _clean_value(line: str) -> str:
    value = line.strip()
    if value.startswith("- "):
        return value[2:].strip()
    return value


def _parse_fields(body: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    current_label: str | None = None
    for raw_line in body.splitlines():
        line = raw_line.strip()
        match = FIELD_RE.match(line)
        if match:
            current_label = match.group("label").strip()
            fields.setdefault(current_label, [])
            inline = match.group("inline").strip()
            if inline:
                fields[current_label].append(inline)
            continue
        if current_label and line:
            fields[current_label].append(_clean_value(line))
    return fields


def _first(fields: dict[str, list[str]], label: str) -> str | None:
    values = fields.get(label, [])
    return values[0] if values else None


def _extract_standzeiten(fields: dict[str, list[str]]) -> list[str]:
    extracted: list[str] = []
    for label in ("Angebote", "Öffnungszeiten", "Sonstige Hinweise"):
        active = False
        for value in fields.get(label, []):
            if "standzeit" in value.casefold():
                active = True
                extracted.append(value)
                continue
            if active and (TIME_RE.search(value) or WEEKDAY_RE.search(value)):
                extracted.append(value)
                continue
            if active:
                active = False
    return list(dict.fromkeys(extracted))


def parse_markdown(markdown: str) -> list[OfferRecord]:
    """Parst nummerierte Angebotsabschnitte aus dem unterstützten Markdownformat.

    Args:
        markdown: Vollständiger Inhalt der Wissensbasisdatei.

    Returns:
        Normalisierte Angebote in der Reihenfolge des Quelldokuments.

    Raises:
        KnowledgeBaseError: Wenn keine gültigen Angebotsabschnitte vorhanden sind.
    """
    offers: list[OfferRecord] = []
    for match in SECTION_RE.finditer(markdown):
        source_index = int(match.group("number"))
        source_title = match.group("title").strip()
        body = match.group("body").rstrip()
        raw_text = f"### {source_index}. {source_title}\n{body}".rstrip()
        fields = _parse_fields(body)
        name = _first(fields, "Name")
        category = _first(fields, "Kategorie")
        description = _first(fields, "Kurzbeschreibung")
        if not name or not category or not description or not raw_text:
            raise KnowledgeBaseError(f"Offer section {source_index} lacks a required source field")
        offers.append(
            OfferRecord(
                id=f"offer-{source_index:03d}-{_slugify(source_title)}",
                source_index=source_index,
                source_title=source_title,
                name=name,
                source_category=category,
                short_description=description,
                district=_first(fields, "Stadtbezirk / Ortsteil"),
                address=_first(fields, "Adresse"),
                header_address=_first(fields, "Adresse laut Kopfzeile"),
                services=list(fields.get("Angebote", [])),
                opening_hours_raw=list(fields.get("Öffnungszeiten", [])),
                standzeiten_raw=_extract_standzeiten(fields),
                phone_numbers=list(fields.get("Telefon", [])),
                emails=list(fields.get("E-Mail", [])),
                website=_first(fields, "Internetseite"),
                notes=list(fields.get("Sonstige Hinweise", [])),
                raw_fields=fields,
                raw_text=raw_text,
            )
        )
    if not offers:
        raise KnowledgeBaseError("No offer sections were parsed")
    ids = [offer.id for offer in offers]
    if len(ids) != len(set(ids)):
        raise KnowledgeBaseError("Parsed offer IDs are not unique")
    return offers


def load_knowledge_base(path: Path) -> KnowledgeBase:
    """Lädt JSON oder Markdown anhand des Dateiinhalts in eine Wissensbasis.

    Raises:
        KnowledgeBaseError: Wenn die Datei fehlt, nicht lesbar oder ungültig ist.
    """
    if not path.is_file():
        raise KnowledgeBaseError(f"Markdown source not found: {path}")
    source_bytes = path.read_bytes()
    if path.suffix.casefold() == ".json":
        try:
            payload = json.loads(source_bytes.decode("utf-8"))
            offers = [OfferRecord.model_validate(item) for item in payload["offers"]]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise KnowledgeBaseError("Canonical JSON source is invalid") from exc
        if not offers or len({offer.id for offer in offers}) != len(offers):
            raise KnowledgeBaseError("Canonical JSON contains no offers or duplicate IDs")
        source = payload.get("source", {})
        source_hash = str(source.get("content_hash") or hashlib.sha256(source_bytes).hexdigest())
        return KnowledgeBase(
            path=path,
            source_hash=source_hash,
            offers=offers,
            source_kind="wfs",
            metadata={key: value for key, value in payload.items() if key != "offers"},
        )
    try:
        markdown = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise KnowledgeBaseError("Markdown source is not valid UTF-8") from exc
    return KnowledgeBase(
        path=path,
        source_hash=hashlib.sha256(source_bytes).hexdigest(),
        offers=parse_markdown(markdown),
        source_kind="markdown",
    )


def load_normalized_source_release(settings: Settings) -> KnowledgeBase:
    """Lädt Pointer und Daten aus genau einem WFS-Release oder dem Legacy-Pfad."""
    try:
        release = load_active_release(settings)
    except WfsReleaseError as exc:
        raise KnowledgeBaseError("Active WFS release is invalid") from exc
    if release is None:
        knowledge_base = load_knowledge_base(settings.kb_path)
        active = KnowledgeBase(
            path=knowledge_base.path,
            source_hash=knowledge_base.source_hash,
            offers=knowledge_base.offers,
            source_kind=knowledge_base.source_kind,
            metadata=knowledge_base.metadata,
            release_id=f"bootstrap-{knowledge_base.source_hash[:12]}",
        )
    else:
        knowledge_base = load_knowledge_base(release.offers_path)
        active = KnowledgeBase(
            path=knowledge_base.path,
            source_hash=knowledge_base.source_hash,
            offers=knowledge_base.offers,
            source_kind=knowledge_base.source_kind,
            metadata=knowledge_base.metadata,
            release_id=release.release_id,
        )
    return active


class _BootstrapFileDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class _BootstrapRuntimeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    release_id: str = Field(
        pattern=r"^(?:\d{8}T\d{6}Z-[0-9a-f]{12}-[0-9a-f]{8}|legacy-[0-9a-f]{12})$"
    )
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    files: dict[str, _BootstrapFileDescriptor]


def _runtime_curation_path(settings: Settings) -> Path:
    """Loest None ausschliesslich auf den paketierten Standardkatalog auf."""

    if settings.curation_path is None:
        return packaged_bootstrap_data_root() / "curation" / "social_offers.json"
    return settings.curation_path


def _inspect_active_release(
    settings: Settings,
    *,
    approved_release_id: str,
    approved_source_hash: str,
) -> tuple[VerifiedRelease | None, str, str | None, str | None]:
    """Liefert redigierte Zustandsdaten; Pointerfehler blockieren keinen Fallback."""

    pointer_path = WfsReleasePaths.from_settings(settings).pointer
    if not pointer_path.is_file():
        return None, "pointer_error", None, None
    try:
        pointer = ActiveReleasePointer.model_validate_json(pointer_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "pointer_error", None, None
    try:
        release = load_active_release(settings)
    except WfsReleaseError:
        return None, "release_error", pointer.release_id, None
    if release is None:
        return None, "pointer_error", None, None
    source_hash = release.manifest.content_hash
    status = (
        "current"
        if release.release_id == approved_release_id and source_hash == approved_source_hash
        else "change_pending"
    )
    return release, status, release.release_id, source_hash


def _load_verified_local_bound_release(
    settings: Settings,
    release_id: str,
    source_hash: str,
) -> KnowledgeBase:
    release_path = WfsReleasePaths.from_settings(settings).releases / release_id
    if not release_path.is_dir():
        raise WfsReleaseError("Bound local release is unavailable")
    release = verify_release(settings, release_id)
    if release.manifest.content_hash != source_hash:
        raise WfsReleaseError("Bound release hash differs from curation catalog")
    source = load_knowledge_base(release.offers_path)
    if source.source_hash != source_hash:
        raise WfsReleaseError("Bound release source hash differs from curation catalog")
    return KnowledgeBase(
        path=source.path,
        source_hash=source.source_hash,
        offers=source.offers,
        source_kind=source.source_kind,
        metadata=source.metadata,
        release_id=release.release_id,
    )


def _load_verified_packaged_bound_release(release_id: str, source_hash: str) -> KnowledgeBase:
    root = packaged_bootstrap_data_root()
    try:
        manifest_path = root / "curation" / "runtime_manifest.json"
        manifest = _BootstrapRuntimeManifest.model_validate_json(manifest_path.read_bytes())
        if manifest.release_id != release_id or manifest.source_hash != source_hash:
            raise ValueError("Packaged bootstrap is not bound to the curation catalog")
        if set(manifest.files) != {"canonical/offers.json"}:
            raise ValueError("Packaged bootstrap file inventory is invalid")
        for relative, descriptor in manifest.files.items():
            content = (root / relative).read_bytes()
            if len(content) != descriptor.size_bytes or hashlib.sha256(content).hexdigest() != descriptor.sha256:
                raise ValueError("Packaged bootstrap file hash mismatch")
        source = load_knowledge_base(root / "canonical" / "offers.json")
        if source.source_hash != source_hash:
            raise ValueError("Packaged bootstrap source hash differs from catalog")
    except (OSError, ValueError, KnowledgeBaseError) as exc:
        raise KnowledgeBaseError(
            "Verified packaged bound release is unavailable",
            code="bound_release_unavailable",
            source_status="release_error",
        ) from exc
    return KnowledgeBase(
        path=source.path,
        source_hash=source.source_hash,
        offers=source.offers,
        source_kind=source.source_kind,
        metadata=source.metadata,
        release_id=release_id,
    )


def _runtime_fingerprint(
    *,
    release_id: str,
    source_hash: str,
    catalog_version: str,
    catalog_hash: str,
    official_source_hash: str,
    toilet_release_id: str,
    toilet_source_hash: str,
    toilet_normalization_version: str,
    drinking_fountain_release_id: str,
    drinking_fountain_material_hash: str,
    drinking_fountain_normalization_version: str,
) -> str:
    payload = json.dumps(
        {
            "catalog_hash": catalog_hash,
            "catalog_version": catalog_version,
            "source_hash": source_hash,
            "source_release_id": release_id,
            "official_source_hash": official_source_hash,
            "toilet_normalization_version": toilet_normalization_version,
            "toilet_release_id": toilet_release_id,
            "toilet_source_hash": toilet_source_hash,
            "drinking_fountain_material_hash": drinking_fountain_material_hash,
            "drinking_fountain_normalization_version": drinking_fountain_normalization_version,
            "drinking_fountain_release_id": drinking_fountain_release_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_active_knowledge_base(settings: Settings) -> KnowledgeBase:
    """Laedt ausschliesslich die validierte, kuratierte Runtime-Projektion."""

    try:
        catalog = load_curation_catalog(_runtime_curation_path(settings))
    except CurationError as exc:
        raise KnowledgeBaseError(
            "Curated runtime catalog is unavailable",
            code=exc.code,
        ) from exc

    active, source_status, active_release_id, active_source_hash = _inspect_active_release(
        settings,
        approved_release_id=catalog.approved_source_release_id,
        approved_source_hash=catalog.approved_source_hash,
    )
    runtime_source = "active_bound_release"
    runtime_status = "ok"
    approved: KnowledgeBase | None = None

    if active is not None and source_status == "current":
        try:
            approved = _load_verified_local_bound_release(
                settings,
                catalog.approved_source_release_id,
                catalog.approved_source_hash,
            )
        except WfsReleaseError:
            source_status = "release_error"
    if approved is None:
        runtime_source = "bound_release_fallback"
        runtime_status = "degraded"
        try:
            approved = _load_verified_local_bound_release(
                settings,
                catalog.approved_source_release_id,
                catalog.approved_source_hash,
            )
        except WfsReleaseError:
            runtime_source = "packaged_bootstrap"
            approved = _load_verified_packaged_bound_release(
                catalog.approved_source_release_id,
                catalog.approved_source_hash,
            )

    try:
        official_source, official_source_hash = load_official_offer_source(
            packaged_bootstrap_data_root() / "official" / "verified_offers.json"
        )
        if (
            catalog.approved_official_source_hash is not None
            and official_source_hash != catalog.approved_official_source_hash
        ):
            raise CurationError("Official offer source hash does not match curation")
        source_offers = [*approved.offers, *official_source.offers]
        offers, aliases = project_runtime_offers(source_offers, catalog)
    except (CurationError, OfficialSourceError) as exc:
        raise KnowledgeBaseError(
            "Curated runtime projection is invalid",
            code="runtime_kb_unavailable",
            source_status=source_status,
        ) from exc
    if any(offer.id in {"1", "2", "3", "4"} for offer in offers):
        raise KnowledgeBaseError(
            "Curated runtime projection contains excluded source records",
            code="runtime_kb_unavailable",
            source_status=source_status,
        )

    curation = catalog_metadata(catalog)
    curation["review_monitoring"]["review_required_due_to_source_change"] = source_status != "current"
    curation["review_monitoring"]["source_review_status"] = (
        "current"
        if source_status == "current"
        else (
            "stale_due_to_source_change"
            if source_status == "change_pending"
            else "source_verification_error"
        )
    )
    try:
        toilet_runtime = load_toilet_runtime(settings)
        public_toilets = tuple(toilet_runtime.collection.records)
        toilet_release_id = toilet_runtime.release_id
        toilet_source_hash = toilet_runtime.source_hash
        toilet_metadata: dict[str, object] = {
            "runtime_status": toilet_runtime.runtime_status,
            "source_status": toilet_runtime.source_status,
            "runtime_source": toilet_runtime.runtime_source,
            "release_id": toilet_runtime.release_id,
            "source_hash": toilet_runtime.source_hash,
            "normalization_version": toilet_runtime.collection.normalization_version,
            "record_count": len(public_toilets),
            "eligible_record_count": sum(
                record.availability_status.value == "available"
                and record.coordinates_status.value == "valid"
                for record in public_toilets
            ),
            "valid_geometry_count": sum(
                record.coordinates_status.value == "valid" for record in public_toilets
            ),
            "missing_geometry_count": sum(
                record.coordinates_status.value != "valid" for record in public_toilets
            ),
            "fee_free_count": sum(record.fee_status.value == "free" for record in public_toilets),
            "fee_paid_count": sum(record.fee_status.value == "paid" for record in public_toilets),
            "fee_unknown_count": sum(record.fee_status.value == "unknown" for record in public_toilets),
        }
    except ToiletReleaseError as exc:
        public_toilets = ()
        toilet_release_id = "unavailable"
        toilet_source_hash = "unavailable"
        toilet_metadata = {
            "runtime_status": "error",
            "source_status": "release_error",
            "runtime_source": None,
            "release_id": None,
            "source_hash": None,
            "normalization_version": TOILET_NORMALIZATION_VERSION,
            "record_count": 0,
            "eligible_record_count": 0,
            "valid_geometry_count": 0,
            "missing_geometry_count": 0,
            "fee_free_count": 0,
            "fee_paid_count": 0,
            "fee_unknown_count": 0,
            "error_code": exc.code,
        }
    try:
        fountain_runtime = load_drinking_fountain_runtime(settings)
        fountain_source_records = tuple(fountain_runtime.collection.records)
        drinking_fountains = tuple(
            record for record in fountain_source_records if record.runtime_eligible
        )
        fountain_release_id = fountain_runtime.release_id
        fountain_material_hash = fountain_runtime.material_hash
        fountain_metadata: dict[str, object] = {
            "runtime_status": fountain_runtime.runtime_status,
            "source_status": fountain_runtime.source_status,
            "runtime_source": fountain_runtime.runtime_source,
            "release_id": fountain_runtime.release_id,
            "last_verified_release": fountain_runtime.release_id,
            "source_hash": fountain_runtime.source_hash,
            "material_hash": fountain_runtime.material_hash,
            "normalization_version": fountain_runtime.collection.normalization_version,
            "source_retrieved_at": fountain_runtime.collection.source.retrieved_at.isoformat(),
            "record_count": len(fountain_source_records),
            "runtime_eligible_count": len(drinking_fountains),
            "valid_geometry_count": sum(
                record.geometry_status.value == "valid" for record in fountain_source_records
            ),
            "excluded_count": sum(not record.runtime_eligible for record in fountain_source_records),
            "outside_leipzig_count": sum(
                record.exclusion_reason is not None
                and record.exclusion_reason.value == "outside_leipzig"
                for record in fountain_source_records
            ),
            "mobile_excluded_count": sum(
                record.installation_type.value == "mobile" for record in fountain_source_records
            ),
            "operation_status_unknown_count": sum(
                record.operation_status.value == "unknown" for record in drinking_fountains
            ),
            "license_status": fountain_runtime.collection.source.license_status,
            "usage_scope": fountain_runtime.collection.source.usage_scope,
        }
    except DrinkingFountainReleaseError as exc:
        drinking_fountains = ()
        fountain_release_id = "unavailable"
        fountain_material_hash = "unavailable"
        fountain_metadata = {
            "runtime_status": "error",
            "source_status": "release_error",
            "runtime_source": None,
            "release_id": None,
            "last_verified_release": None,
            "source_hash": None,
            "material_hash": None,
            "normalization_version": DRINKING_FOUNTAIN_NORMALIZATION_VERSION,
            "source_retrieved_at": None,
            "record_count": 0,
            "runtime_eligible_count": 0,
            "valid_geometry_count": 0,
            "excluded_count": 0,
            "outside_leipzig_count": 0,
            "mobile_excluded_count": 0,
            "operation_status_unknown_count": 0,
            "license_status": "not_explicitly_specified",
            "usage_scope": "reviewed_prototype_source",
            "error_code": exc.code,
        }
    fingerprint = _runtime_fingerprint(
        release_id=catalog.approved_source_release_id,
        source_hash=catalog.approved_source_hash,
        catalog_version=catalog.catalog_version,
        catalog_hash=catalog.content_hash or catalog.approved_source_hash,
        official_source_hash=official_source_hash,
        toilet_release_id=toilet_release_id,
        toilet_source_hash=toilet_source_hash,
        toilet_normalization_version=TOILET_NORMALIZATION_VERSION,
        drinking_fountain_release_id=fountain_release_id,
        drinking_fountain_material_hash=fountain_material_hash,
        drinking_fountain_normalization_version=DRINKING_FOUNTAIN_NORMALIZATION_VERSION,
    )
    metadata = {
        **approved.metadata,
        "curation": curation,
        "active_source_release_id": active_release_id,
        "active_source_hash": active_source_hash,
        "source_change_pending": source_status != "current",
        "source_status": source_status,
        "runtime_kb_status": (
            "degraded"
            if runtime_status == "degraded"
            or toilet_metadata["runtime_status"] != "ok"
            or fountain_metadata["runtime_status"] != "ok"
            else "ok"
        ),
        "runtime_source": runtime_source,
        "runtime_kb_fingerprint": fingerprint,
        "public_toilets": toilet_metadata,
        "drinking_fountains": fountain_metadata,
        "official_offer_source": {
            "source_version": official_source.source_version,
            "source_hash": official_source_hash,
            "record_count": len(official_source.offers),
        },
    }
    return KnowledgeBase(
        path=approved.path,
        source_hash=approved.source_hash,
        offers=offers,
        source_kind="curated_wfs",
        metadata=metadata,
        release_id=f"curation-{catalog.catalog_version}-{(catalog.content_hash or catalog.approved_source_hash)[:12]}",
        organization_aliases=aliases,
        runtime_kb_fingerprint=fingerprint,
        runtime_validated=True,
        public_toilets=public_toilets,
        drinking_fountains=drinking_fountains,
    )
