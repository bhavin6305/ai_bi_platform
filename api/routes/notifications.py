"""Session-scoped pipeline notifications."""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from api.database import get_engine

logger = logging.getLogger(__name__)
router = APIRouter()


def ensure_notifications_table() -> None:
    with get_engine().begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id SERIAL PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                event_type VARCHAR(40) NOT NULL,
                title VARCHAR(160) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                read_at TIMESTAMP NULL
            )
        """))


def create_notification(session_id: str, event_type: str, title: str, message: str) -> None:
    """Persist a pipeline event without ever interrupting the pipeline."""
    try:
        ensure_notifications_table()
        with get_engine().begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO notifications (session_id, event_type, title, message)
                    VALUES (:session_id, :event_type, :title, :message)
                """),
                {
                    "session_id": session_id,
                    "event_type": event_type,
                    "title": title,
                    "message": message,
                },
            )
    except Exception as error:
        logger.warning("Could not save notification for session '%s': %s", session_id, error)


@router.get("/notifications/{session_id}")
def list_notifications(session_id: str):
    try:
        ensure_notifications_table()
        with get_engine().connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT notification_id, event_type, title, message, created_at, read_at
                    FROM notifications
                    WHERE session_id = :session_id
                    ORDER BY created_at DESC, notification_id DESC
                    LIMIT 30
                """),
                {"session_id": session_id},
            ).fetchall()
    except Exception as error:
        logger.error("Could not load notifications: %s", error)
        raise HTTPException(status_code=503, detail="Notifications are unavailable.")

    return {
        "notifications": [
            {
                "id": row[0],
                "event_type": row[1],
                "title": row[2],
                "message": row[3],
                "created_at": str(row[4]) if row[4] else None,
                "read": row[5] is not None,
            }
            for row in rows
        ]
    }


@router.post("/notifications/{session_id}/read")
def mark_notifications_read(session_id: str):
    ensure_notifications_table()
    with get_engine().begin() as conn:
        conn.execute(
            text("""
                UPDATE notifications SET read_at = NOW()
                WHERE session_id = :session_id AND read_at IS NULL
            """),
            {"session_id": session_id},
        )
    return {"ok": True}