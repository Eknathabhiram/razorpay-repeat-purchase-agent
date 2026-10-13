"""Stage 05 strict commerce commands. No browser payment-success authority."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field
from .planning_models import Strict


class CartRequest(Strict):
    journey_id: UUID
    quantity: int = Field(ge=1,le=20)
    confirmed_same_product: Literal[True]
    confirmed_whatsapp_handoff: Literal[True]
    offer_ref: str | None = Field(default=None,max_length=80)
    quote_digest: str | None = Field(default=None,pattern=r"^[a-f0-9]{64}$")


class CommerceCommand(Strict):
    action: Literal["prepare", "propose_link", "sync", "seed_offer"]
    cart: CartRequest | None = None
    preparation_id: UUID | None = None


class OfferPolicy(Strict):
    expected_revision: int = Field(ge=0)
    enabled: bool
    approved_offer_ref: Literal["DEMO-REORDER-25"] | None = None
    unit_cost_minor: int | None = Field(default=None,ge=0,le=10000000)
    fulfillment_cost_minor: int | None = Field(default=None,ge=0,le=10000000)
    minimum_margin_minor: int = Field(default=10000,ge=0,le=10000000)


class DemoPurchase(Strict):
    event_key: UUID
    journey_id: UUID
    preparation_id: UUID | None = None
    scenario: Literal["captured", "unmatched", "amount_mismatch", "authorized", "refunded", "outside_link"]


class CommerceView(Strict):
    environment: str
    source_notice: str
    storefront_available: bool
    plan_requires_review: bool
    last_sync_at: datetime | None
    mapping_version: str
    journeys: list[dict]
    preparations: list[dict]
    payments: list[dict]
    matches: list[dict]
    purchases: list[dict]
    cases: list[dict]
    adjustments: list[dict]
    offers: list[dict]
    offer_policy: dict | None
