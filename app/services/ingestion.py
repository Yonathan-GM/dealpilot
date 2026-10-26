"""Ingestion pipeline: file -> text -> chunks -> embeddings -> database."""
from pathlib import Path

from app.core.db import supabase
from app.core.llm import embed_many
from app.services.chunking import chunk_text
from app.services.extract import extract_text

INSERT_BATCH = 50


def ingest_file(path: Path, doc_type: str, customer_id: str | None = None) -> int:
    """Ingest one file. Returns the number of chunks stored.

    Re-running on the same filename replaces the old version (idempotent).
    """
    text = extract_text(path)
    chunks = chunk_text(text, title=path.stem)
    if not chunks:
        return 0

    # Embed first: if this fails, the old version of the document is untouched.
    embeddings = embed_many([c.text for c in chunks], task_type="RETRIEVAL_DOCUMENT")

    supabase.table("documents").delete().eq("filename", path.name).execute()
    doc = (
        supabase.table("documents")
        .insert({"filename": path.name, "doc_type": doc_type, "customer_id": customer_id})
        .execute()
    )
    document_id = doc.data[0]["id"]

    rows = [
        {
            "document_id": document_id,
            "chunk_index": c.index,
            "content": c.text,
            "embedding": vector,
        }
        for c, vector in zip(chunks, embeddings)
    ]
    for start in range(0, len(rows), INSERT_BATCH):
        supabase.table("chunks").insert(rows[start : start + INSERT_BATCH]).execute()
    return len(rows)
