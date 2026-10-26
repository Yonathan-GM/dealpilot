"""Find the document chunks most relevant to a question."""
from typing import Literal

from app.core.db import supabase
from app.core.llm import embed
from app.services.ranking import build_keyword_query, reciprocal_rank_fusion

Mode = Literal["vector", "keyword", "hybrid"]
CANDIDATES = 10  # how many results to pull from each search before merging


def vector_search(query: str, limit: int = CANDIDATES) -> list[dict]:
    """Search by meaning: compare the question's embedding with every chunk."""
    result = supabase.rpc(
        "match_chunks",
        {"query_embedding": embed(query), "match_count": limit, "match_threshold": 0.0},
    ).execute()
    return result.data or []


def keyword_search(query: str, limit: int = CANDIDATES) -> list[dict]:
    """Search by exact words (good for product codes like SF-500-23)."""
    text = build_keyword_query(query)
    if not text:
        return []
    result = supabase.rpc("keyword_chunks", {"query_text": text, "match_count": limit}).execute()
    return result.data or []


def retrieve(query: str, k: int = 5, mode: Mode = "hybrid") -> list[dict]:
    """Return the top-k chunks. Each has: id, filename, chunk_index, content, score."""
    if mode == "vector":
        return [{**r, "score": r["similarity"]} for r in vector_search(query)[:k]]
    if mode == "keyword":
        return [{**r, "score": r["rank"]} for r in keyword_search(query)[:k]]
    fused = reciprocal_rank_fusion([vector_search(query), keyword_search(query)])
    return fused[:k]
