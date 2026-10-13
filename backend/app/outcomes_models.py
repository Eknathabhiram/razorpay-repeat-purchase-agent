from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field

class AccountingReview(BaseModel):
    model_config=ConfigDict(extra='forbid')
    purchase_id: UUID
    expected_revision: int = Field(ge=0)
    product_cost_minor: int | None = Field(default=None,ge=0)
    fulfillment_cost_minor: int | None = Field(default=None,ge=0)
    gateway_fee_minor: int | None = Field(default=None,ge=0)
    contact_cost_minor: int | None = Field(default=None,ge=0)
    agent_cost_minor: int | None = Field(default=None,ge=0)
    retained_tax_minor: int | None = Field(default=None,ge=0)
    confirmed_demo_return_maturity: bool = False
class SuggestionDecision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision: Literal['accept','reject']
    expected_policy_revision: int = Field(ge=1)
class OutcomeView(BaseModel):
    environment: str
    totals: list[dict]
    purchases: list[dict]
    cohorts: list[dict]
    learning: list[dict]
    suggestions: list[dict]
    interventions: list[dict]
    notice: str
    evidence_limits: list[str]
