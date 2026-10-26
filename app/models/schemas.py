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
