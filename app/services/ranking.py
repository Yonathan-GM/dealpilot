"""Pure helper functions for search (no API calls, no database) - easy to test."""
import re

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-]*")


def build_keyword_query(text: str) -> str:
    """Turn a question into an OR-query for Postgres full-text search.

    "What is the minimum order for plastic pallets?"
        -> "What or is or the or minimum or order or ..."
    (Postgres drops common stop-words like "the" and "is" by itself.)
    """
    seen: set[str] = set()
    words: list[str] = []
    for raw in _WORD.findall(text):
        word = raw.rstrip(".-")
        if not word or word.lower() == "or" or word.lower() in seen:
            continue
        seen.add(word.lower())
        words.append(word)
    return " or ".join(words)


def reciprocal_rank_fusion(rankings: list[list[dict]], k: int = 60) -> list[dict]:
    """Merge several ranked result lists into one (Reciprocal Rank Fusion).

    Each item earns 1 / (k + rank) from every list it appears in, so chunks that
    rank well in BOTH vector and keyword search float to the top.
    """
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for ranking in rankings:
        for position, item in enumerate(ranking, start=1):
            key = item["id"]
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + position)
            items.setdefault(key, item)
    ordered = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return [{**items[key], "score": score} for key, score in ordered]
