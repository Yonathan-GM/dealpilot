"""Customer memory: turn interactions into short facts, store them, recall them later."""
from google.genai import errors as genai_errors
from google.genai import types

from app.core.db import supabase
from app.core.llm import chat, chat_json, embed, embed_many
from app.services.memory_logic import build_extraction_prompt, dedupe_facts, parse_fact_list

FACTS_SCHEMA = types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING))


def extract_facts(customer_name: str, content: str) -> list[str]:
    prompt = build_extraction_prompt(customer_name, content)
    try:
        raw = chat_json(prompt, FACTS_SCHEMA)
    except genai_errors.ClientError as exc:
        if exc.code != 400:
            raise
        raw = chat(prompt + "\n\nReply with a JSON array of strings and nothing else.")
    return parse_fact_list(raw)


def save_memories(customer_id: str, interaction_id: str, facts: list[str]) -> int:
    existing = supabase.table("memories").select("fact").eq("customer_id", customer_id).execute()
    new_facts = dedupe_facts(facts, [row["fact"] for row in existing.data or []])
    if not new_facts:
        return 0
    vectors = embed_many(new_facts, task_type="RETRIEVAL_DOCUMENT")
    rows = [
        {
            "customer_id": customer_id,
            "fact": fact,
            "embedding": vector,
            "source_interaction_id": interaction_id,
        }
        for fact, vector in zip(new_facts, vectors)
    ]
    supabase.table("memories").insert(rows).execute()
    return len(rows)


def process_interaction(interaction_id: str, customer_id: str, customer_name: str, content: str) -> int:
    """Extract facts from one interaction and store them. Returns how many were saved.

    The interaction is only marked as processed AFTER everything succeeded, so a
    failure can be retried later with scripts/build_memories.py.
    """
    facts = extract_facts(customer_name, content)
    saved = save_memories(customer_id, interaction_id, facts)
    supabase.table("interactions").update({"memory_extracted": True}).eq("id", interaction_id).execute()
    return saved


def recall(customer_id: str, query: str, k: int = 5) -> list[dict]:
    """Find the remembered facts about a customer that best match the query."""
    result = supabase.rpc(
        "match_memories",
        {"query_embedding": embed(query), "p_customer_id": customer_id, "match_count": k},
    ).execute()
    return result.data or []
