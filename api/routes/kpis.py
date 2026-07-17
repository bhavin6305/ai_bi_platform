"""
kpis.py
-------
GET /api/kpis/{session_id} — returns calculated KPI values.

For now this reads from the kpi_results table (populated by the
analytics engine in Phase 2). If no KPIs have been calculated yet,
it calculates basic ones on the fly from the session's data.
"""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from api.database import get_engine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/kpis/{session_id}")
def get_kpis(session_id: str):
    """
    Return all KPI values calculated for a session.

    Returns:
        session_id : str
        kpis       : list of {kpi_name, kpi_value, kpi_unit, kpi_category}
    """
    engine = get_engine()

    with engine.connect() as conn:
        # Check session exists
        session = conn.execute(
            text("SELECT session_id FROM upload_sessions WHERE session_id = :sid"),
            {"sid": session_id}
        ).fetchone()

        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

        # Read from kpi_results table
        rows = conn.execute(
            text("""
                SELECT kpi_name, kpi_value, kpi_unit, kpi_category, display_format
                FROM kpi_results
                WHERE session_id = :sid
                ORDER BY kpi_category, kpi_name
            """),
            {"sid": session_id}
        ).fetchall()

    if not rows:
        return {
            "session_id": session_id,
            "kpis"      : [],
            "message"   : "No KPIs calculated yet for this session. "
                          "Run the analytics engine first."
        }

    return {
        "session_id": session_id,
        "kpis": [
            {
                "kpi_name"      : r[0],
                "kpi_value"     : r[1],
                "kpi_unit"      : r[2],
                "kpi_category"  : r[3],
                "display_format": r[4],
            }
            for r in rows
        ]
    }