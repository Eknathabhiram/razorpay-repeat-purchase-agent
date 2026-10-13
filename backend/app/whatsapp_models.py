import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class DemoInbound(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_key: uuid.UUID
    journey_id: uuid.UUID
    text: str = Field(min_length=1, max_length=2000)

class DemoStatus(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_key: uuid.UUID
    receipt_id: uuid.UUID
    status: Literal['queued','sending','sent','delivered','read','failed','undelivered']

class WhatsAppView(BaseModel):
    environment: str
    notice: str
    capabilities: dict
    journeys: list[dict]
    messages: list[dict]
    events: list[dict]
    identities: list[dict]

class IdentityReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    customer_id: uuid.UUID
    address: str = Field(pattern=r'^whatsapp:\+[1-9][0-9]{7,14}$')
    message_sid: str = Field(pattern=r'^SM[0-9a-fA-F]{32}$')
    confirmed_customer_identity: Literal[True]
