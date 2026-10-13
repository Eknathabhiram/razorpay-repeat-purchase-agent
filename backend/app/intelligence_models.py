from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)

Intent=Literal['opt_out','support','refusal','reminder','offer_enquiry','purchase_interest','purchase_claim','clarification']
class IntentItem(Strict):
    kind: Intent
    evidence: str = Field(min_length=1,max_length=300)
class IntentProposal(Strict):
    intents: list[IntentItem] = Field(min_length=1,max_length=6)
    quantity: int | None = Field(ge=1,le=20)
    requested_product: str | None = Field(max_length=160)
    date_text: str | None = Field(max_length=160)
    confidence: float = Field(ge=0,le=1)

class StartSession(BaseModel):
    model_config=ConfigDict(extra='forbid')
    journey_id: UUID
    confirmed_browser_test_consent: Literal[True]
    confirmed_provider_processing: bool = False
    provider: Literal['baseline','together'] = 'baseline'
class TextTurn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    sequence: int = Field(ge=1,le=20)
    text: str = Field(min_length=1,max_length=2000)
class ConfirmTranscript(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text: str = Field(min_length=1,max_length=2000)
    confirmed_transcript: Literal[True]
class SessionCommand(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)
class ReminderConfirmation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    due_at: datetime
    confirmed_date_and_whatsapp: Literal[True]
    @field_validator('due_at')
    @classmethod
    def require_zone(cls,value):
        if not value.tzinfo:raise ValueError('An explicit timezone is required.')
        return value
class VoiceCheckout(BaseModel):
    model_config=ConfigDict(extra='forbid')
    quantity: int = Field(ge=1,le=20)
    confirmed_same_product: Literal[True]
    confirmed_whatsapp_handoff: Literal[True]
    quote_digest: str | None = Field(default=None,pattern=r'^[a-f0-9]{64}$')
class IntelligenceView(BaseModel):
    environment: str
    provider: dict
    notice: str
    journeys: list[dict]
    sessions: list[dict]
    turns: list[dict]
