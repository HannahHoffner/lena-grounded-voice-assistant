"""Strikter interner Vertrag der deterministischen Kandidatenstufe."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .interpreter import AgeGroup, Gender, Need, RequestedDay, ThreeWayStatus


CANDIDATE_CONTRACT_VERSION = "2"
EXCLUDED_SOURCE_IDS = {"1", "2", "3", "4"}


class SelectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CandidateRole(str, Enum):
    DIRECT_SERVICE = "direct_service"
    REFERRAL_CONTACT = "referral_contact"
    CONDITIONAL_CANDIDATE = "conditional_candidate"


class SelectionStatus(str, Enum):
    CANDIDATES_AVAILABLE = "candidates_available"
    CLARIFICATION_RECOMMENDED = "clarification_recommended"
    NO_ELIGIBLE_CANDIDATE = "no_eligible_candidate"
    UNSUPPORTED_NEED = "unsupported_need"
    INTERPRETER_UNAVAILABLE = "interpreter_unavailable"


class MissingFact(str, Enum):
    NEED = "need"
    AGE = "age"
    GENDER = "gender"
    DRUG_USE = "drug_use"
    SOCIAL_BENEFIT_ENTITLEMENT = "social_benefit_entitlement"
    DISTRICT = "district"
    REQUESTED_TIME = "requested_time"
    UNSUPPORTED_CONDITION = "unsupported_condition"


class ReasonCode(str, Enum):
    NEED_CAPABILITY_MATCH = "need_capability_match"
    REFERRAL_NEED_MATCH = "referral_need_match"
    ALIAS_MATCH = "alias_match"
    DISTRICT_ALIAS_MATCH = "district_alias_match"
    EXPLICIT_TARGET_MATCH = "explicit_target_match"
    GENERAL_SLEEP_CONTACT_PRIORITY = "general_sleep_contact_priority"
    U27_REFERRAL_PRIORITY = "u27_referral_priority"
    U27_SUPPLEMENTAL_ONLY = "u27_supplemental_only"
    CURATED_PRIORITY = "curated_priority"
    DOCUMENTED_SCHEDULE = "documented_schedule"
    NEED_NOT_SUPPORTED = "need_not_supported"
    TARGET_GROUP_MISMATCH = "target_group_mismatch"
    AGE_NOT_ESTABLISHED = "age_not_established"
    AGE_OUTSIDE_RANGE = "age_outside_range"
    GENDER_NOT_ESTABLISHED = "gender_not_established"
    DRUG_USE_NOT_EXPLICIT = "drug_use_not_explicit"
    DRUG_USE_MISMATCH = "drug_use_mismatch"
    HELENE_ACCESS_NOT_ESTABLISHED = "helene_access_not_established"
    TIME_CONDITION_NOT_MET = "time_condition_not_met"
    ALIAS_SCOPE_MISMATCH = "alias_scope_mismatch"
    AMBIGUOUS_ORGANIZATION_ALIAS = "ambiguous_organization_alias"


class RuleCode(str, Enum):
    RUNTIME_APPROVED_ONLY = "runtime_approved_only"
    CURRENT_INTERPRETATION_FIRST = "current_interpretation_first"
    UI_HINT_FALLBACK = "ui_hint_fallback"
    UI_HINT_OVERRIDDEN = "ui_hint_overridden"
    ALIAS_LIMIT = "alias_limit"
    NEED_AND_SERVICE_EVIDENCE = "need_and_service_evidence"
    U27_ROUTING = "u27_routing"
    GENERAL_SLEEP_RUECKE_FIRST = "general_sleep_ruecke_first"
    DRUG_SPECIFIC_REQUIRES_EXPLICIT = "drug_specific_requires_explicit"
    HELENE_RESTRICTED_ACCESS = "helene_restricted_access"
    DOCUMENTED_TIME_ONLY = "documented_time_only"
    GENERAL_HELP_REFERRAL = "general_help_referral"
    WATER_EVIDENCE_ONLY = "water_evidence_only"
    TOILET_UNSUPPORTED = "toilet_unsupported"
    STABLE_ID_SORT = "stable_id_sort"
    DISTRICT_RECORDED_NOT_VALIDATED = "district_recorded_not_validated"
    FOOD_AGE_UNRESTRICTED = "food_age_unrestricted"


class FactsUsed(SelectionModel):
    age: int | None
    age_group: AgeGroup = AgeGroup.UNKNOWN
    gender: Gender
    drug_use: ThreeWayStatus
    no_social_benefit_entitlement: ThreeWayStatus
    district: str | None
    requested_day: RequestedDay | None
    requested_time: str | None


class CandidateItem(SelectionModel):
    offer_id: str
    role: CandidateRole
    reason_codes: list[ReasonCode] = Field(min_length=1, max_length=8)
    missing_facts: list[MissingFact] = Field(default_factory=list, max_length=8)
    priority_tier: int = Field(ge=0, le=99)


class ExcludedItem(SelectionModel):
    offer_id: str
    reason_codes: list[ReasonCode] = Field(min_length=1, max_length=5)


class SelectionConflict(SelectionModel):
    field: Literal["need"]
    preferred_value: str = Field(max_length=40)
    ignored_value: str = Field(max_length=40)


class CandidateDecision(SelectionModel):
    contract_version: Literal[CANDIDATE_CONTRACT_VERSION]
    need: Need
    facts_used: FactsUsed
    mandatory_candidates: list[CandidateItem] = Field(default_factory=list, max_length=4)
    selectable_candidates: list[CandidateItem] = Field(default_factory=list, max_length=26)
    conditional_candidates: list[CandidateItem] = Field(default_factory=list, max_length=26)
    excluded_candidates: list[ExcludedItem] = Field(default_factory=list, max_length=26)
    missing_information: list[MissingFact] = Field(default_factory=list, max_length=8)
    clarification_recommended: bool
    selection_status: SelectionStatus
    applied_rules: list[RuleCode] = Field(max_length=20)
    conflicts: list[SelectionConflict] = Field(default_factory=list, max_length=4)
    unsupported_conditions: list[str] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def validate_ids_and_status(self) -> "CandidateDecision":
        all_ids = [
            item.offer_id
            for item in [
                *self.mandatory_candidates,
                *self.selectable_candidates,
                *self.conditional_candidates,
                *self.excluded_candidates,
            ]
        ]
        if EXCLUDED_SOURCE_IDS.intersection(all_ids):
            raise ValueError("excluded source ID in candidate decision")
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("candidate ID occurs in more than one decision class")
        if self.clarification_recommended != (self.selection_status == SelectionStatus.CLARIFICATION_RECOMMENDED):
            raise ValueError("clarification status and flag disagree")
        return self

    @property
    def candidates(self) -> list[CandidateItem]:
        """Kompatible Lesesicht in bereits deterministisch bindender Reihenfolge."""
        return [*self.mandatory_candidates, *self.selectable_candidates]

    @property
    def excluded(self) -> list[ExcludedItem]:
        """Kompatible Lesesicht; serialisiert wird nur der eindeutige neue Feldname."""
        return self.excluded_candidates


class AliasSelectionContext(SelectionModel):
    alias: str
    alias_kind: Literal["organization", "offer"]
    offer_ids: list[str] = Field(min_length=1, max_length=26)
    district_narrowed: bool = False


class CandidateSelectionContext(SelectionModel):
    ui_need_hint: Need | None = None
    alias: AliasSelectionContext | None = None
