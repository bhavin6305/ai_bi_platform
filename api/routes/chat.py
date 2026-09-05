"""
chat.py
-------
POST /api/chat — AI natural language chat endpoint.
Now uses Groq + Llama 3.1 for real Text-to-SQL answers.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from api.database import get_engine
from ai.sql_generator  import generate_sql, execute_sql
from ai.chat_assistant import explain_results, suggest_followup_questions

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    question  : str


class ChatResponse(BaseModel):
    session_id       : str
    question         : str
    answer           : str
    sql_used         : str | None = None
    row_count        : int = 0
    followup_questions : list[str] = []  # ← add


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Accept a natural language question, convert to SQL,
    execute it, and return an AI-generated explanation.
    """
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty.")

    engine = get_engine()

    # Step 1: Generate SQL from natural language
    try:
        sql = generate_sql(
            question   = request.question,
            session_id = request.session_id,
            engine     = engine,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Could not generate SQL: {e}")

    # Step 2: Execute SQL
    try:
        results = execute_sql(sql, engine)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Query failed: {e}")

    # Step 3: Generate explanation
    answer = explain_results(
        question = request.question,
        sql_used = sql,
        results  = results,
    )
    followup_questions = suggest_followup_questions(
        question = request.question,
        answer   = answer,
        results  = results,
    )

    # Step 4: Save to ai_insights table
    try:
        import pandas as pd
        pd.DataFrame([{
            "session_id"    : request.session_id,
            "insight_type"  : "chat_response",
            "chart_id"      : None,
            "question_asked": request.question,
            "sql_used"      : sql,
            "insight_text"  : answer,
        }]).to_sql("ai_insights", con=engine, if_exists="append", index=False)
    except Exception as error:
        logger.warning("Could not save chat response for session '%s': %s", request.session_id, error)

    return ChatResponse(
        session_id = request.session_id,
        question   = request.question,
        answer     = answer,
        sql_used   = sql,
        row_count  = len(results),
        followup_questions = followup_questions,
    )


@router.get("/chat/{session_id}/history")
def chat_history(session_id: str):
    """Return saved chat responses for one uploaded dataset session."""
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")

    engine = get_engine()
    with engine.connect() as conn:
        session_exists = conn.execute(
            text("SELECT 1 FROM upload_sessions WHERE session_id = :sid"),
            {"sid": session_id},
        ).scalar()
        if not session_exists:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

        rows = conn.execute(
            text("""
                SELECT insight_id, question_asked, insight_text, sql_used, generated_at
                FROM ai_insights
                WHERE session_id = :sid AND insight_type = 'chat_response'
                ORDER BY generated_at, insight_id
            """),
            {"sid": session_id},
        ).mappings().all()

    return {
        "session_id": session_id,
        "messages": [
            {
                "insight_id": row["insight_id"],
                "question": row["question_asked"],
                "answer": row["insight_text"],
                "sql_used": row["sql_used"],
                "generated_at": row["generated_at"].isoformat() if row["generated_at"] else None,
            }
            for row in rows
        ],
    }