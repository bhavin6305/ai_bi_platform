"""
analytics.py
------------
GET /api/analytics/{session_id} — returns KPIs + chart configs for a session.
GET /api/sessions — lists all upload sessions (for the Streamlit session picker).
"""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from api.database import get_engine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/analytics/{session_id}")
def get_analytics(session_id: str):
    """
    Return full analytics output for a session:
        - KPI cards
        - Chart configurations (type, columns, title)

    Streamlit dashboard page reads this to render the auto-generated charts.
    """
    engine = get_engine()

    with engine.connect() as conn:
        session = conn.execute(
            text("SELECT session_id, status FROM upload_sessions WHERE session_id = :sid"),
            {"sid": session_id}
        ).fetchone()

        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

        # KPIs
        kpis = conn.execute(
            text("""
                SELECT kpi_name, kpi_value, kpi_unit, kpi_category
                FROM kpi_results WHERE session_id = :sid
                ORDER BY kpi_category, kpi_name
            """),
            {"sid": session_id}
        ).fetchall()

        # Chart configs
        charts = conn.execute(
            text("""
                SELECT chart_id, chart_type, chart_title,
                       source_table, x_column, y_column,
                       group_by_column, aggregation, chart_order, rationale
                FROM chart_configs WHERE session_id = :sid
                ORDER BY chart_order
            """),
            {"sid": session_id}
        ).fetchall()

    return {
        "session_id": session_id,
        "kpis": [
            {"name": r[0], "value": r[1], "unit": r[2], "category": r[3]}
            for r in kpis
        ],
        "charts": [
            {
                "chart_id"       : r[0],
                "chart_type"     : r[1],
                "chart_title"    : r[2],
                "source_table"   : r[3],
                "x_column"       : r[4],
                "y_column"       : r[5],
                "group_by_column": r[6],
                "aggregation"    : r[7],
                "chart_order"    : r[8],
                "rationale"      : r[9],
            }
            for r in charts
        ],
    }


@router.get("/sessions")
def list_sessions():
    """
    List all upload sessions with their status.
    Used by Streamlit to let users pick a previous session.
    """
    engine = get_engine()

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT s.session_id, s.status, s.total_files,
                       s.total_rows, s.created_at,
                       COUNT(DISTINCT f.file_id) as file_count
                FROM upload_sessions s
                LEFT JOIN uploaded_files f ON s.session_id = f.session_id
                GROUP BY s.session_id, s.status, s.total_files,
                         s.total_rows, s.created_at
                ORDER BY s.created_at DESC
                LIMIT 50
            """)
        ).fetchall()

    return {
        "sessions": [
            {
                "session_id" : r[0],
                "status"     : r[1],
                "total_files": r[2],
                "total_rows" : r[3],
                "created_at" : str(r[4]) if r[4] else None,
                "file_count" : r[5],
            }
            for r in rows
        ]
    }