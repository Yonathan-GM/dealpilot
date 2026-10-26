import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.core.db import supabase
from app.models.schemas import DocumentOut, UploadResponse
from app.services.extract import SUPPORTED, extract_text
from app.services.ingestion import ingest_text

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut], summary="List ingested documents")
def list_documents() -> list[dict]:
    result = (
        supabase.table("documents")
        .select("id, filename, doc_type, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.post("", response_model=UploadResponse, summary="Upload and ingest a document")
def upload_document(file: UploadFile = File(...), doc_type: str = Form("other")) -> UploadResponse:
    filename = Path(file.filename or "").name  # strip any folder parts the client sent
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(415, f"Unsupported file type. Allowed: {', '.join(sorted(SUPPORTED))}")

    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB")

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / filename
        path.write_bytes(data)
        try:
            text = extract_text(path)
        except Exception as exc:  # corrupt or unreadable file
            raise HTTPException(422, "Could not read this file") from exc

    chunks = ingest_text(filename, text, doc_type)
    if chunks == 0:
        raise HTTPException(422, "No text could be extracted from this file")
    return UploadResponse(filename=filename, doc_type=doc_type, chunks=chunks)


@router.delete("/{document_id}", status_code=204, summary="Delete a document and its chunks")
def delete_document(document_id: UUID) -> None:
    existing = supabase.table("documents").select("id").eq("id", str(document_id)).execute()
    if not existing.data:
        raise HTTPException(404, "Document not found")
    supabase.table("documents").delete().eq("id", str(document_id)).execute()
