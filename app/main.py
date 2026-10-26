from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from google.genai import errors as genai_errors

from app.api import ask, documents
from app.api.deps import require_api_key
from app.core.config import settings

app = FastAPI(
    title="DealPilot API",
    version="0.1.0",
    description="AI sales assistant for a B2B distributor: document Q&A with citations.",
)


@app.exception_handler(genai_errors.APIError)
def handle_gemini_error(request: Request, exc: genai_errors.APIError) -> JSONResponse:
    """If Gemini fails (e.g. rate limit), tell the client clearly instead of crashing."""
    return JSONResponse(
        status_code=502,
        content={"detail": "The AI service returned an error. Please try again shortly."},
    )


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "auth": "enabled" if settings.api_key else "disabled"}


app.include_router(ask.router, dependencies=[Depends(require_api_key)])
app.include_router(documents.router, dependencies=[Depends(require_api_key)])
