from fastapi import APIRouter

from app.models.schemas import AskRequest, AskResponse, SourceOut
from app.services.rag import answer_question

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse, summary="Ask a question about the documents")
def ask(body: AskRequest) -> AskResponse:
    result = answer_question(body.question, k=body.k, mode=body.mode)
    return AskResponse(
        answer=result.answer,
        sources=[
            SourceOut(
                id=s["id"],
                filename=s["filename"],
                chunk_index=s["chunk_index"],
                content=s["content"],
                score=s["score"],
            )
            for s in result.sources
        ],
    )
