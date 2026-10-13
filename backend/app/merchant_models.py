from typing import Literal
from uuid import UUID
from pydantic import Field
from .planning_models import Strict, AudienceFilters

class AudienceSelection(Strict):
    expected_revision: int = Field(ge=0)
    facts_version: int = Field(ge=0)
    policy_id: UUID
    mode: Literal['explicit','eligible','saved']
    selected: list[UUID] = Field(default_factory=list, max_length=20000)
    excluded: list[UUID] = Field(default_factory=list, max_length=20000)
    filters: AudienceFilters = Field(default_factory=AudienceFilters)

class DemoChoice(Strict):
    event_key: UUID
    action_id: UUID
    button_id: str = Field(min_length=1, max_length=30)
