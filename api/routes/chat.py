"""
chat.py
-------
POST /api/chat — AI natural language chat endpoint.

Phase 3 placeholder. The actual Groq/Llama integration will be
built by Member 2 in Phase 3. For now this returns a placeholder
response so the frontend can be built without waiting.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request/Response models ────────────────────────────────────────────────────
# Pydantic models define the exact JSON structure the endpoint accepts.
# FastAPI validates incoming requests against these automatically.

class ChatRequest(BaseModel):
    session_id: str
    question  : str


class ChatResponse(BaseModel):
    session_id: str
    question  : str
    answer    : str
    sql_used  : str | None = None


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Accept a natural language question and return an AI-generated answer.

    Phase 3 placeholder — returns a mock response for now.
    Member 2 will replace the body of this function with:
        1. Call ai/sql_generator.py to convert question → SQL
        2. Run SQL against PostgreSQL
        3. Call ai/chat_assistant.py to explain the result
        4. Return the explanation

    Example request:
        POST /api/chat
        {
            "session_id": "d60ba6f1-...",
            "question": "What were the top 5 products by revenue?"
        }
    """
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty.")

    logger.info(
        "Chat request for session '%s': %s", request.session_id, request.question
    )

    # ── PLACEHOLDER — Member 2 replaces this in Phase 3 ───────────────────
    return ChatResponse(
        session_id = request.session_id,
        question   = request.question,
        answer     = (
            "AI chat is not yet configured. "
            "This endpoint will be implemented in Phase 3 using Groq API + Llama 3.1."
        ),
        sql_used   = None,
    )