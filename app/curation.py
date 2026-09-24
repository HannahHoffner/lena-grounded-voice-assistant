"""Validiert den Kurationskatalog und erzeugt freigegebene Runtime-Angebote."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from .models import OfferRecord


class CurationError(RuntimeError):
    """Signalisiert einen fehlenden oder widerspruechlichen Kurationsstand."""

    def __init__(self, message: str, *, code: str = "curation_catalog_invalid") -> None:
        super().__init__(message)
        self.code = code

class CurationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Organization(CurationModel):
    id: str
    source_name: str
    display_name: str | None = None


class Location(CurationModel):
    id: str
    address: str


PlaceType = Literal[
    "overnight_accommodation",
    "emergency_accommodation",
    "day_center",
    "contact_cafe",
    "adult_streetwork",
    "youth_streetwork",
    "medical_contact",
    "mobile_support",
    "food_distribution",
    "help_bus",
    "station_support",
    "public_toilet",
    "drinking_fountain",
    "youth_emergency_service",
]
Capability = Literal[
    "overnight_stay",
    "food",
    "drinking_water",
    "hygiene",
    "shower",
    "laundry",
    "clothing",
    "postal",
    "medical_care",
    "medical_access",
    "wound_care",
    "counselling",
    "referral",
    "day_stay",
    "contact",
    "mobile_outreach",
    "protection",
]
TargetGroup = Literal[
    "adults",
    "under_27",
    "men",
    "women",
    "people_who_use_drugs",
    "people_experiencing_homelessness",
    "people_without_regular_healthcare",
    "minors",
]
ReferralNeed = Literal["food", "drinking_water", "sleep", "medical", "advice", "general_help"]
PriorityRule = Literal[
    "general_sleep_contact_first",
    "general_help_referral_first",
    "minor_sleep_first",
    "minor_crisis_first",
    "youth_explicit_only",
]
ScheduleRule = Literal[
    "tuesday_17_18",
    "thursday_16_1730",
    "thursday_16_19",
    "sunday_20_21",
    "daily_18_23",
    "mobile_alternative_stands",
    "medibus_and_clinics",
]
AccessRule = Literal["helene_after_21_or_no_social_benefit_entitlement"]


class ServiceOffer(CurationModel):
    id: str
    source_id: str
    organization_id: str
    location_id: str
    offer_type: str
    include_in_runtime: bool = True
    display_name: str | None = None
    search_phrases: list[str] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)
    place_type: PlaceType
    capabilities: list[Capability] = Field(default_factory=list)
    target_groups: list[TargetGroup] = Field(default_factory=list)
    minimum_age: int | None = Field(default=None, ge=0, le=120)
    maximum_age: int | None = Field(default=None, ge=0, le=120)
    eligible_genders: list[Literal["female", "male", "non_binary", "diverse"]] = Field(default_factory=list)
    requires_explicit_drug_use: bool = False
    referral_needs: list[ReferralNeed] = Field(default_factory=list)
    priority_rules: list[PriorityRule] = Field(default_factory=list)
    service_schedules: dict[Capability, ScheduleRule] = Field(default_factory=dict)
    access_rules: list[AccessRule] = Field(default_factory=list)
    curation_decision_ids: list[str] = Field(default_factory=list)
    source_reference_ids: list[str] = Field(default_factory=list)
    coordinates_status: Literal[
        "verified_from_official_source",
        "verified_from_open_geodata",
        "not_verified_after_address_change",
    ] | None = None
    runtime_overrides: dict[str, object] = Field(default_factory=dict)


class OrganizationAlias(CurationModel):
    alias: str
    organization_id: str


class OfferAlias(CurationModel):
    alias: str
    service_offer_id: str


class SourceReference(CurationModel):
    id: str
    source_type: Literal["wfs_release", "methodology", "official_website", "open_geodata"]
    title: str
    url: HttpUrl | None = None
    retrieved_at: date | datetime | None = None
    content_hash: str | None = None
    release_id: str | None = None
    evidence_reference: str | None = None


class CurationDecision(CurationModel):
    id: str
    decision_type: Literal["include", "exclude", "alias", "override", "priority", "review_policy"]
    affected_source_ids: list[str] = Field(default_factory=list)
    reason: str
    source_reference_ids: list[str] = Field(default_factory=list)
    review_status: Literal["reviewed_for_prototype", "externally_verified", "source_normalized"]
    reviewed_by_role: str | None = None
    evidence_type: str
    recorded_by_role: str
    evidence_reference: str
    reviewed_at: date | datetime | None = None


class ReviewPolicy(CurationModel):
    review_interval: str | None = None
    review_policy_status: Literal["not_yet_formally_defined"]
    review_required_before_final_evaluation: bool
    review_on_source_change: bool
    formal_approval_status: Literal["not_granted"]


class CurationCatalog(CurationModel):
    schema_version: int = 1
    catalog_version: str
    approved_source_release_id: str
    approved_source_hash: str
    approved_official_source_hash: str | None = None
    review_policy: ReviewPolicy
    organizations: list[Organization]
    locations: list[Location]
    service_offers: list[ServiceOffer]
    organization_aliases: list[OrganizationAlias] = Field(default_factory=list)
    offer_aliases: list[OfferAlias] = Field(default_factory=list)
    source_references: list[SourceReference]
    curation_decisions: list[CurationDecision]
    content_hash: str | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def validate_references(self) -> "CurationCatalog":
        def unique(values: list[str], label: str) -> set[str]:
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label}")
            return set(values)

        organization_ids = unique([item.id for item in self.organizations], "organization IDs")
        location_ids = unique([item.id for item in self.locations], "location IDs")
        service_ids = unique([item.id for item in self.service_offers], "service offer IDs")
        source_ids = unique([item.source_id for item in self.service_offers], "source offer IDs")
        reference_ids = unique([item.id for item in self.source_references], "source reference IDs")
        decision_ids = unique([item.id for item in self.curation_decisions], "curation decision IDs")
        if any(offer.id != offer.source_id for offer in self.service_offers):
            raise ValueError("service offer IDs must equal their immutable WFS source IDs")
        for offer in self.service_offers:
            if offer.organization_id not in organization_ids or offer.location_id not in location_ids:
                raise ValueError(f"unknown organization or location on service offer {offer.id}")
            if not set(offer.source_reference_ids) <= reference_ids:
                raise ValueError(f"unknown source reference on service offer {offer.id}")
            if not set(offer.curation_decision_ids) <= decision_ids:
                raise ValueError(f"unknown curation decision on service offer {offer.id}")
            if offer.minimum_age is not None and offer.maximum_age is not None and offer.minimum_age > offer.maximum_age:
                raise ValueError(f"invalid age range on service offer {offer.id}")
            if not set(offer.service_schedules) <= set(offer.capabilities):
                raise ValueError(f"schedule without capability on service offer {offer.id}")
        for alias in self.organization_aliases:
            if alias.organization_id not in organization_ids:
                raise ValueError(f"unknown organization on alias {alias.alias}")
        for alias in self.offer_aliases:
            if alias.service_offer_id not in service_ids:
                raise ValueError(f"unknown service offer on alias {alias.alias}")
        for decision in self.curation_decisions:
            if not set(decision.source_reference_ids) <= reference_ids:
                raise ValueError(f"unknown source reference on decision {decision.id}")
            if not set(decision.affected_source_ids) <= source_ids:
                raise ValueError(f"unknown affected offer on decision {decision.id}")
        return self


@dataclass(frozen=True)
class OrganizationAliasBinding:
    alias: str
    organization_id: str
    offer_ids: tuple[str, ...]


ALLOWED_OVERRIDE_FIELDS = {
    "short_description",
    "district",
    "address",
    "header_address",
    "services",
    "opening_hours_raw",
    "standzeiten_raw",
    "phone_numbers",
    "emails",
    "website",
    "notes",
    "geometry",
}


def load_curation_catalog(path: Path) -> CurationCatalog:
    """Lädt und validiert den vollständigen Katalog ohne Quelldaten zu verändern."""
    if not path.is_file():
        raise CurationError("Curation catalog not found", code="curation_catalog_missing")
    try:
        source = path.read_bytes()
        catalog = CurationCatalog.model_validate_json(source)
        catalog.content_hash = hashlib.sha256(source).hexdigest()
        return catalog
    except (OSError, ValueError) as exc:
        raise CurationError("Curation catalog is invalid") from exc


def project_runtime_offers(
    source_offers: list[OfferRecord],
    catalog: CurationCatalog,
) -> tuple[list[OfferRecord], tuple[OrganizationAliasBinding, ...]]:
    """Projiziert einen vollständig geprüften WFS-Stand in die Runtime-Sicht."""
    source_by_id = {offer.id: offer for offer in source_offers}
    configured_ids = {offer.source_id for offer in catalog.service_offers}
    if configured_ids != set(source_by_id):
        missing = sorted(set(source_by_id) - configured_ids)
        unknown = sorted(configured_ids - set(source_by_id))
        raise CurationError(f"Curation/source ID mismatch; missing={missing}, unknown={unknown}")

    organization_aliases: dict[str, list[str]] = {}
    for alias in catalog.organization_aliases:
        organization_aliases.setdefault(alias.organization_id, []).append(alias.alias)
    offer_aliases: dict[str, list[str]] = {}
    for alias in catalog.offer_aliases:
        offer_aliases.setdefault(alias.service_offer_id, []).append(alias.alias)
    decisions = {decision.id: decision for decision in catalog.curation_decisions}
    organizations_by_id = {organization.id: organization for organization in catalog.organizations}

    projected: list[OfferRecord] = []
    for configured in catalog.service_offers:
        if not configured.include_in_runtime:
            continue
        invalid_overrides = set(configured.runtime_overrides) - ALLOWED_OVERRIDE_FIELDS
        if invalid_overrides:
            raise CurationError(f"Unsupported runtime overrides for {configured.id}: {sorted(invalid_overrides)}")
        source = source_by_id[configured.source_id]
        aliases = offer_aliases.get(configured.id, [])
        org_aliases = organization_aliases.get(configured.organization_id, [])
        review_statuses = [decisions[item].review_status for item in configured.curation_decision_ids]
        # Ein Angebot ohne eigenen kuratierten display_name (z. B. "Scharni" statt
        # "Advent-Wohlfahrtswerk e. V.") uebernimmt den kuratierten Kurznamen seiner
        # Organisation. Vorher wurde `catalog.organizations[].display_name` an
        # keiner Stelle der Runtime gelesen -- Formulator, Karten und Vorlesetext
        # zitierten dadurch den vollen Rechtsnamen aus der WFS-Quelle
        # (z. B. "Caritasverband Leipzig e. V. Oekumenische Bahnhofsmission"
        # statt "Bahnhofsmission Leipzig").
        organization = organizations_by_id.get(configured.organization_id)
        effective_display_name = configured.display_name or (organization.display_name if organization else None)
        update = {
            **configured.runtime_overrides,
            "organization_id": configured.organization_id,
            "location_id": configured.location_id,
            "offer_type": configured.offer_type,
            "display_name": effective_display_name,
            "organization_aliases": org_aliases,
            "offer_aliases": aliases,
            "search_phrases": configured.search_phrases,
            "needs": configured.needs,
            "place_type": configured.place_type,
            "capabilities": configured.capabilities,
            "target_groups": configured.target_groups,
            "minimum_age": configured.minimum_age,
            "maximum_age": configured.maximum_age,
            "eligible_genders": configured.eligible_genders,
            "requires_explicit_drug_use": configured.requires_explicit_drug_use,
            "referral_needs": configured.referral_needs,
            "priority_rules": configured.priority_rules,
            "service_schedules": configured.service_schedules,
            "access_rules": configured.access_rules,
            "curation_decision_ids": configured.curation_decision_ids,
            "source_reference_ids": configured.source_reference_ids,
            "review_status": review_statuses[-1] if review_statuses else None,
            "coordinates_status": configured.coordinates_status,
        }
        if configured.runtime_overrides:
            override_bytes = json.dumps(
                configured.runtime_overrides,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            update["curation_hash"] = hashlib.sha256(override_bytes).hexdigest()
        if effective_display_name:
            update["name"] = effective_display_name
        projected.append(OfferRecord.model_validate({**source.model_dump(mode="python"), **update}))

    bindings: list[OrganizationAliasBinding] = []
    for alias in catalog.organization_aliases:
        ids = tuple(
            offer.id
            for offer in projected
            if offer.organization_id == alias.organization_id
        )
        if ids:
            bindings.append(OrganizationAliasBinding(alias.alias, alias.organization_id, ids))
    return projected, tuple(bindings)


def catalog_metadata(catalog: CurationCatalog) -> dict[str, object]:
    """Liefert nicht sensible Freigabe- und Review-Metadaten für Health/Monitoring."""
    unknown_review_dates = [
        decision.id
        for decision in catalog.curation_decisions
        if decision.reviewed_by_role and decision.reviewed_at is None
    ]
    return json.loads(
        json.dumps(
            {
                "catalog_version": catalog.catalog_version,
                "catalog_content_hash": catalog.content_hash,
                "approved_source_release_id": catalog.approved_source_release_id,
                "approved_source_hash": catalog.approved_source_hash,
                "review_policy": catalog.review_policy.model_dump(mode="json"),
                "approval_status": {
                    "technical_validation_status": "validated",
                    "prototype_review_status": "reviewed_for_prototype",
                    "formal_approval_status": catalog.review_policy.formal_approval_status,
                    "production_approval_status": "not_granted",
                },
                "review_monitoring": {
                    "review_due": None,
                    "decisions_with_unknown_review_date": unknown_review_dates,
                    "review_required_before_final_evaluation": (
                        catalog.review_policy.review_required_before_final_evaluation
                    ),
                },
                "runtime_offer_count": sum(item.include_in_runtime for item in catalog.service_offers),
                "excluded_source_ids": [item.source_id for item in catalog.service_offers if not item.include_in_runtime],
                "coordinates_status": {
                    item.source_id: item.coordinates_status
                    for item in catalog.service_offers
                    if item.coordinates_status is not None
                },
            },
            ensure_ascii=False,
        )
    )
