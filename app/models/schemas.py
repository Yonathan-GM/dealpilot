"""Pydantic models: the shape of data going in and out of the API."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500, examples=["What is the minimum order for plastic pallets?"])
    k: int = Field(default=5, ge=1, le=10, description="How many chunks to retrieve")
    mode: Literal["hybrid", "vector", "keyword"] = "hybrid"


class SourceOut(BaseModel):
    id: UUID
    filename: str
    chunk_index: int
    content: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    doc_type: str | None = None
    created_at: datetime


class UploadResponse(BaseModel):
    filename: str
    doc_type: str
    chunks: int


# ---- CRM ------------------------------------------------------------------
CustomerStatus = Literal["lead", "active", "at_risk", "churned"]
Channel = Literal["email", "call", "meeting", "note"]


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    industry: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=200)
    status: CustomerStatus = "lead"
    notes: str | None = Field(default=None, max_length=2000)


class CustomerUpdate(BaseModel):
    """Every field is optional: send only what you want to change."""
    industry: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=200)
    status: CustomerStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


class CustomerOut(BaseModel):
    id: UUID
    name: str
    industry: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    status: CustomerStatus
    notes: str | None = None
    created_at: datetime


class InteractionCreate(BaseModel):
    channel: Channel
    content: str = Field(min_length=3, max_length=5000)
    occurred_at: datetime | None = Field(default=None, description="Defaults to now")


class InteractionOut(BaseModel):
    id: UUID
    customer_id: UUID
    channel: Channel
    content: str
    occurred_at: datetime
    memory_extracted: bool = False


class MemoryOut(BaseModel):
    id: UUID
    fact: str
    created_at: datetime
    similarity: float | None = Field(default=None, description="Only set when searching with ?query=")
