from datetime import datetime
from typing import Generic, Literal, TypeVar
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Meta(BaseModel):
    correlation_id: UUID
    generated_at: datetime


class Envelope(BaseModel, Generic[T]):
    data: T
    meta: Meta


class WorkspaceSummary(BaseModel):
    id: UUID
    name: str
    environment: Literal["demo", "development", "live"]
    version: int
    role: Literal["owner", "operator", "viewer"]


class Me(BaseModel):
    login: str
    workspaces: list[WorkspaceSummary]


class Capability(BaseModel):
    capability: str
    status: Literal["unverified", "available", "blocked", "revoked"]
    verified_at: datetime | None
    reason: str | None
    evidence_ref: str | None


class Connector(BaseModel):
    id: UUID
    provider: str
    source_mode: Literal["simulated", "test", "live"]
    provider_environment: str
    state: str
    last_checked_at: datetime | None
    version: int
    capabilities: list[Capability]


class PolicyPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = 3
    start: str = Field(default="10:00", pattern=r"^\d{2}:\d{2}$")
    end: str = Field(default="18:00", pattern=r"^\d{2}:\d{2}$")
    cap: int = Field(default=2, ge=1, le=10)
    budget: int = Field(default=500, ge=0, le=100000)
    mode: Literal["review", "bounded"] = "review"


class DemoState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["operating", "first-plan", "setup", "disconnected"] = "operating"
    installed: bool = True
    paused: bool = False
    plan_approved: bool = True
    plan_needs_review: bool = False
    selected: list[Literal["ananya", "rahul", "meera"]] = Field(default_factory=lambda: ["ananya", "rahul", "meera"])
    assigned: list[str] = Field(default_factory=lambda: ["ananya", "rahul", "meera"])
    checkout_sent: bool = False
    order_confirmed: bool = True
    taken_over: bool = False
    support_assigned: bool = False
    disconnected: bool = False
    policy: PolicyPreview = Field(default_factory=PolicyPreview)
    events: list[str] = Field(default_factory=list)


class UIReadModel(BaseModel):
    source_mode: Literal["simulated", "unavailable"]
    version: int
    state: DemoState | None
    notice: str


class DemoCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    action: Literal["reset", "pause", "resume", "takeover", "handback", "approve_plan",
                    "reject_plan", "save_policy", "approve_checkout", "assign_support", "install"]
    scenario: Literal["operating", "first-plan", "setup", "disconnected"] | None = None
    selected: list[Literal["ananya", "rahul", "meera"]] | None = None
    policy: PolicyPreview | None = None


def initial_demo(scenario="operating"):
    return DemoState(scenario=scenario, installed=scenario != "setup",
                     plan_approved=scenario == "operating", order_confirmed=scenario == "operating",
                     assigned=["ananya", "rahul", "meera"] if scenario == "operating" else [],
                     disconnected=scenario == "disconnected")
