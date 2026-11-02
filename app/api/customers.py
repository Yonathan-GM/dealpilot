import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from postgrest.exceptions import APIError as PostgrestError

from app.core.db import supabase
from app.models.schemas import (
    CustomerCreate,
    CustomerOut,
    CustomerStatus,
    CustomerUpdate,
    InteractionCreate,
    InteractionOut,
    MemoryOut,
)
from app.services.memory import process_interaction, recall

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/customers", tags=["customers"])


def _get_customer(customer_id: UUID) -> dict:
    result = supabase.table("customers").select("*").eq("id", str(customer_id)).execute()
    if not result.data:
        raise HTTPException(404, "Customer not found")
    return result.data[0]


def _extract_memories_safely(interaction_id: str, customer_id: str, name: str, content: str) -> None:
    """Runs after the response is sent. A failure is logged and can be retried later."""
    try:
        saved = process_interaction(interaction_id, customer_id, name, content)
        logger.info("Saved %s memories from interaction %s", saved, interaction_id)
    except Exception:
        logger.exception("Memory extraction failed for interaction %s", interaction_id)


@router.get("", response_model=list[CustomerOut], summary="List customers")
def list_customers(status: CustomerStatus | None = None) -> list[dict]:
    query = supabase.table("customers").select("*").order("name")
    if status:
        query = query.eq("status", status)
    return query.execute().data


@router.post("", response_model=CustomerOut, status_code=201, summary="Create a customer")
def create_customer(body: CustomerCreate) -> dict:
    try:
        result = supabase.table("customers").insert(body.model_dump()).execute()
    except PostgrestError as exc:
        if exc.code == "23505":  # unique violation
            raise HTTPException(409, "A customer with this name already exists") from exc
        raise
    return result.data[0]


@router.get("/{customer_id}", response_model=CustomerOut, summary="Get one customer")
def get_customer(customer_id: UUID) -> dict:
    return _get_customer(customer_id)


@router.patch("/{customer_id}", response_model=CustomerOut, summary="Update a customer")
def update_customer(customer_id: UUID, body: CustomerUpdate) -> dict:
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "Send at least one field to change")
    result = supabase.table("customers").update(changes).eq("id", str(customer_id)).execute()
    if not result.data:
        raise HTTPException(404, "Customer not found")
    return result.data[0]


@router.get("/{customer_id}/interactions", response_model=list[InteractionOut], summary="Interaction history")
def list_interactions(customer_id: UUID) -> list[dict]:
    _get_customer(customer_id)
    result = (
        supabase.table("interactions")
        .select("*")
        .eq("customer_id", str(customer_id))
        .order("occurred_at", desc=True)
        .execute()
    )
    return result.data


@router.post(
    "/{customer_id}/interactions",
    response_model=InteractionOut,
    status_code=201,
    summary="Log an interaction (memories are extracted in the background)",
)
def log_interaction(customer_id: UUID, body: InteractionCreate, background: BackgroundTasks) -> dict:
    customer = _get_customer(customer_id)
    payload = body.model_dump(mode="json", exclude_none=True)
    payload["customer_id"] = str(customer_id)
    row = supabase.table("interactions").insert(payload).execute().data[0]
    background.add_task(
        _extract_memories_safely, row["id"], str(customer_id), customer["name"], row["content"]
    )
    return row


@router.get("/{customer_id}/memories", response_model=list[MemoryOut], summary="What we remember about a customer")
def list_memories(
    customer_id: UUID,
    query: str | None = Query(default=None, min_length=2, max_length=300, description="Search memories by meaning"),
    k: int = Query(default=5, ge=1, le=20),
) -> list[dict]:
    _get_customer(customer_id)
    if query:
        return recall(str(customer_id), query, k=k)
    result = (
        supabase.table("memories")
        .select("id, fact, created_at")
        .eq("customer_id", str(customer_id))
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return result.data
