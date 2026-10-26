"""Retrieval-Augmented Generation: retrieve chunks, then answer from them."""
from dataclasses import dataclass

from app.core.llm import chat
from app.services.prompts import NOT_FOUND, build_rag_prompt
from app.services.retrieval import Mode, retrieve


@dataclass
class RagAnswer:
    answer: str
    sources: list[dict]


def answer_question(question: str, k: int = 5, mode: Mode = "hybrid") -> RagAnswer:
    sources = retrieve(question, k=k, mode=mode)
    if not sources:
        return RagAnswer(answer=NOT_FOUND, sources=[])
    answer = chat(build_rag_prompt(question, sources))
    return RagAnswer(answer=answer.strip(), sources=sources)
