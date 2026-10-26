"""Shared dependencies, e.g. API-key protection."""
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str | None = Security(api_key_header)) -> None:
    """Reject requests without the right X-API-Key header (if a key is configured)."""
    expected = settings.api_key
    if not expected:  # local development mode
        return
    if not key or not secrets.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
