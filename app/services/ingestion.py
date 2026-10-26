"""Ingestion pipeline: file -> text -> chunks -> embeddings -> database."""
from pathlib import Path

from app.core.db import supabase
from app.core.llm import embed_many
from app.services.chunking import chunk_text
from app.services.extract import extract_text

INSERT_BATCH = 50


def ingest_text(
    filename: str, text: str, doc_type: str, customer_id: str | None = None
) -> int:
    """Chunk, embed and store already-extracted text. Returns the chunk count.

    Re-running with the same filename replaces the old version (idempotent).
    """
    chunks = chunk_text(text, title=Path(filename).stem)
    if not chunks:
        return 0

    # Embed first: if this fails, the old version of the document is untouched.
    embeddings = embed_many([c.text for c in chunks], task_type="RETRIEVAL_DOCUMENT")

    supabase.table("documents").delete().eq("filename", filename).execute()
    doc = (
        supabase.table("documents")
        .insert({"filename": filename, "doc_type": doc_type, "customer_id": customer_id})
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


def ingest_file(path: Path, doc_type: str, customer_id: str | None = None) -> int:
    """Read a file from disk and ingest it."""
    return ingest_text(path.name, extract_text(path), doc_type, customer_id)
