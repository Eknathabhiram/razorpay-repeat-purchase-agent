"""Stage 04 requests. Demo events never claim provider authenticity."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field, model_validator
from .planning_models import Strict


class ExecutionCommand(Strict):
    action: Literal["approve_plan", "reject_plan", "approve_action", "reject_action", "pause", "resume", "takeover", "handback", "assign_support", "resolve_support", "propose_reply"]
    expected_version: int = Field(ge=0)
    subject_id: UUID | None = None
    digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class DemoEvent(Strict):
    event_key: UUID
    journey_id: UUID
    kind: Literal["opt_out", "support", "reminder", "outside_purchase"]
    due_at: datetime | None = None
    timezone: Literal["Asia/Kolkata"] = "Asia/Kolkata"
    channel: Literal["whatsapp"] = "whatsapp"

    @model_validator(mode="after")
    def absolute_date(self):
        if self.kind == "reminder" and (not self.due_at or not self.due_at.tzinfo):
            raise ValueError("Confirm an absolute reminder date with timezone")
        return self


class Tick(Strict):
    outcome: Literal["accepted", "definite_failure", "unknown"] = "accepted"
    limit: int = Field(default=10, ge=1, le=10)


class ExecutionView(Strict):
    environment: str
    version: int
    paused: bool
    plan_review: dict | None
    journeys: list[dict]
    actions: list[dict]
    jobs: list[dict]
    receipts: list[dict]
    support_cases: list[dict]
    reminders: list[dict]
    budgets: list[dict]
    cohort_count: int
    notice: str
