"""KPI period-comparison API."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from api.database import get_engine
from analytics.filters import DashboardFilters, validate_filter_identifiers
from analytics.kpi_comparison import compare_kpis

router = APIRouter()


@router.get("/analytics/{session_id}/comparison")
def get_kpi_comparison(
    session_id: str,
    date_column: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category_column: str | None = Query(default=None),
    category_value: str | None = Query(default=None),
):
    """Return real KPI current-vs-previous-period comparisons.

    Comparisons require an explicit complete date range. The previous period
    has exactly the same inclusive number of days and carries category filters
    forward unchanged. If no valid comparison exists, the response is empty
    rather than fabricating a percentage.
    """
    engine = get_engine()

    with engine.connect() as conn:
        session = conn.execute(
            text("SELECT session_id FROM upload_sessions WHERE session_id = :sid"),
            {"sid": session_id},
        ).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    filters = DashboardFilters(
        date_column=date_column,
        date_from=date_from,
        date_to=date_to,
        category_column=category_column,
        category_value=category_value,
    )
    try:
        validate_filter_identifiers(filters, engine)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    if not filters.date_column and (filters.date_from or filters.date_to):
        raise HTTPException(status_code=400, detail="date_column is required when filtering by date.")
    if not filters.date_from or not filters.date_to:
        return {"session_id": session_id, "comparison_available": False, "comparisons": {}}

    profiles = _schema_profiles(session_id, engine)
    comparisons = compare_kpis(session_id, profiles, engine, filters)

    return {
        "session_id": session_id,
        "comparison_available": bool(comparisons),
        "comparisons": {
            name: {
                "kpi_name": result.kpi_name,
                "current_value": result.current_value,
                "previous_value": result.previous_value,
                "absolute_change": result.absolute_change,
                "percent_change": result.percent_change,
                "direction": result.direction,
                "comparison_available": result.comparison_available,
            }
            for name, result in comparisons.items()
        },
    }


def _schema_profiles(session_id: str, engine) -> dict[str, list[dict]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT table_name, column_name, detected_type, unique_count
                FROM schema_profiles
                WHERE session_id = :sid
                ORDER BY table_name, column_order
            """),
            {"sid": session_id},
        ).fetchall()

    profiles: dict[str, list[dict]] = {}
    for table, column, detected_type, unique_count in rows:
        profiles.setdefault(table, []).append({
            "column_name": column,
            "detected_type": detected_type,
            "unique_count": unique_count,
        })
    return profiles
