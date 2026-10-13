"""Strict Stage 03 contracts. No execution or approval authority."""
from datetime import datetime, date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PolicyConfig(Strict):
    variant_ids: list[str] = Field(min_length=1, max_length=100)
    fallback_days: int | None = Field(default=None, ge=1, le=730)
    recent_purchase_days: int = Field(default=14, ge=1, le=90)
    contact_start: str = Field(default="10:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    contact_end: str = Field(default="18:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timezone: Literal["Asia/Kolkata"] = "Asia/Kolkata"
    contact_cap: int = Field(default=2, ge=1, le=10)
    budget_minor: int = Field(default=50000, ge=0, le=100000000)
    currency: Literal["INR"] = "INR"
    mode: Literal["review", "bounded"] = "review"
    conversation_automation: bool = False
    contextual_replies: bool = False
    provider_processing: bool = False
    offers_enabled: bool = False
    approved_offer_refs: list[str] = Field(default_factory=list,max_length=10)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.conversation_automation and self.mode != 'bounded':
            raise ValueError('Automated conversations require a bounded mandate')
        if self.contextual_replies and not (self.conversation_automation and self.provider_processing):
            raise ValueError('Contextual replies require automation and explicit provider processing authority')
        if self.contact_end <= self.contact_start:
            raise ValueError("Contact end must be later than start time")
        if len(set(self.variant_ids)) != len(self.variant_ids):
            raise ValueError("Variant scope must not contain duplicates")
        if self.offers_enabled != bool(self.approved_offer_refs):
            raise ValueError("Enabled offers require explicit approved references; disabled offers require an empty list")
        return self


class PolicyChange(Strict):
    expected_revision: int = Field(ge=0)
    config: PolicyConfig


class AudienceFilters(Strict):
    search: str = Field(default='',max_length=120)
    city: str = Field(default='',max_length=120)
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode='after')
    def date_order(self):
        if self.date_from and self.date_to and self.date_from>self.date_to:raise ValueError('End date must follow start date')
        return self

class DraftChange(Strict):
    expected_revision: int = Field(ge=0)
    selected: list[UUID] = Field(max_length=20000)
    audience_filters: AudienceFilters | None = None


class PlanningCommand(Strict):
    action: Literal["seed_demo", "seed_scale_demo", "sync", "refresh"]


class PlanningView(Strict):
    environment: str
    facts_version: int
    fact_counts: dict[str, int]
    coverage_complete: bool
    coverage_notes: list[str]
    synced_at: datetime | None
    policy: dict | None
    variants: list[dict]
    opportunities: list[dict]
    draft: dict | None
    notice: str
