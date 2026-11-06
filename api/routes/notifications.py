"""Session-scoped pipeline notifications."""

import logging

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from api.database import get_engine
from api.routes.auth import ensure_session_access
from analytics.anomaly_detector import default_monitoring_period, detect_kpi_anomalies
from analytics.filters import DashboardFilters
from analytics.kpi_comparison import compare_kpis

logger = logging.getLogger(__name__)
router = APIRouter()


def anomaly_notification_details(cleaned_tables: list | None) -> tuple[str, str] | None:
    """Build one session-level alert from tables with flagged outliers."""
    if not cleaned_tables:
        return None

    affected = []
    for cleaned in cleaned_tables:
        if cleaned is None:
            continue

        cleaning_log = getattr(cleaned, "cleaning_log", None)
        count = getattr(cleaning_log, "outlier_columns", 0) or 0
        table_name = getattr(cleaned, "table_name", "unknown")

        if count:
            affected.append(f"{table_name} ({count} column(s))")

    if not affected:
        return None

    return (
        "Anomalies detected",
        "Extreme values were flagged for review in " + ", ".join(affected) + ".",
    )


def create_anomaly_notification(session_id: str, cleaned_tables: list | None) -> None:
    """Persist an anomaly alert without interrupting the upload pipeline."""
    if not cleaned_tables:
        return

    details = anomaly_notification_details(cleaned_tables)
    if details:
        title, message = details
        create_notification(session_id, "anomaly_detected", title, message)


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


def create_notification_once(
    session_id: str,
    event_type: str,
    title: str,
    message: str,
) -> None:
    """Persist an identical alert only once for a session."""
    try:
        ensure_notifications_table()
        with get_engine().begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO notifications (session_id, event_type, title, message)
                    SELECT :session_id, :event_type, :title, :message
                    WHERE NOT EXISTS (
                        SELECT 1 FROM notifications
                        WHERE session_id = :session_id
                          AND event_type = :event_type
                          AND title = :title
                          AND message = :message
                    )
                """),
                {
                    "session_id": session_id,
                    "event_type": event_type,
                    "title": title,
                    "message": message,
                },
            )
    except Exception as error:
        logger.warning("Could not save business alert for session '%s': %s", session_id, error)


def create_business_anomaly_notifications(session_id: str) -> None:
    """Evaluate the latest comparable periods after an upload without failing ETL."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT table_name, column_name, detected_type, unique_count
                    FROM schema_profiles
                    WHERE session_id = :session_id
                    ORDER BY table_name, column_order
                """),
                {"session_id": session_id},
            ).fetchall()
        profiles: dict[str, list[dict]] = {}
        for table, column, detected_type, unique_count in rows:
            profiles.setdefault(table, []).append({
                "column_name": column,
                "detected_type": detected_type,
                "unique_count": unique_count,
            })

        period = default_monitoring_period(profiles, engine)
        if not period:
            return

        date_column, date_from, date_to = period
        filters = DashboardFilters(
            date_column=date_column,
            date_from=date_from,
            date_to=date_to,
        )
        comparisons = compare_kpis(session_id, profiles, engine, filters)
        alerts = detect_kpi_anomalies(comparisons, str(date_from), str(date_to))
        for alert in alerts:
            create_notification_once(
                session_id,
                str(alert["event_type"]),
                str(alert["title"]),
                str(alert["message"]),
            )
    except Exception as error:
        logger.warning(
            "Could not evaluate business alerts for session '%s': %s",
            session_id,
            error,
        )


@router.get("/notifications/{session_id}")
def list_notifications(session_id: str, authorization: str | None = Header(default=None)):
    ensure_session_access(session_id, authorization)

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
def mark_notifications_read(session_id: str, authorization: str | None = Header(default=None)):
    ensure_session_access(session_id, authorization)

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