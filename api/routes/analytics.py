"""
analytics.py
------------
GET /api/analytics/{session_id} — returns KPIs + chart configs for a session.
GET /api/sessions — lists all upload sessions (for the Streamlit session picker).
"""

import logging
from datetime import date

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from api.database import get_engine
from api.routes.auth import ensure_session_access, resolve_request_user
from api.routes.notifications import create_notification_once, ensure_notifications_table
from analytics.anomaly_detector import default_monitoring_period, detect_kpi_anomalies
from analytics.chart_generator import generate_chart_data
from analytics.filters import DashboardFilters, validate_filter_identifiers
from analytics.kpi_comparison import compare_kpis
from analytics.kpi_engine import calculate_kpis, simulate_kpi_scenario

logger = logging.getLogger(__name__)
router = APIRouter()


class SessionRename(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WhatIfScenarioRequest(BaseModel):
    adjustments: dict[str, float | int | str] = Field(default_factory=dict)


def _ensure_session_name_column(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS session_name VARCHAR(120)"))
        conn.execute(text("ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS owner_user_id INTEGER"))


@router.get("/analytics/{session_id}")
def get_analytics(
    session_id: str,
    authorization: str | None = Header(default=None),
    date_column: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category_column: str | None = Query(default=None),
    category_value: str | None = Query(default=None),
):
    """
    Return full analytics output for a session:
        - KPI cards
        - Chart configurations (type, columns, title)

    Streamlit dashboard page reads this to render the auto-generated charts.
    """
    engine = get_engine()
    ensure_session_access(session_id, authorization, engine)

    filters = _validated_filters(
        session_id, engine, date_column, date_from, date_to, category_column, category_value
    )

    with engine.connect() as conn:
        session = conn.execute(
            text("SELECT session_id, status FROM upload_sessions WHERE session_id = :sid"),
            {"sid": session_id}
        ).fetchone()

        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

        # KPIs
        if filters.active:
            profiles = _schema_profiles(session_id, engine)
            kpis = calculate_kpis(session_id, profiles, engine, filters=filters, persist=False)
            kpi_rows = [
                (k.kpi_name, k.kpi_value, k.kpi_unit, k.kpi_category, k.confidence)
                for k in kpis
            ]
        else:
            kpi_rows = conn.execute(
                text("""
                SELECT kpi_name, kpi_value, kpi_unit, kpi_category, display_format
                FROM kpi_results WHERE session_id = :sid
                ORDER BY kpi_category, kpi_name
                """),
                {"sid": session_id}
            ).fetchall()
            kpi_rows = [
                (r[0], r[1], r[2], r[3], 0.75)
                for r in kpi_rows
            ]

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
            {"name": r[0], "value": r[1], "unit": r[2], "category": r[3], "confidence": r[4]}
            for r in kpi_rows
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


@router.post("/analytics/{session_id}/what-if")
def simulate_what_if(
    session_id: str,
    payload: WhatIfScenarioRequest,
    authorization: str | None = Header(default=None),
    date_column: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category_column: str | None = Query(default=None),
    category_value: str | None = Query(default=None),
):
    """Project KPI outcomes under a simple business scenario change."""
    engine = get_engine()
    ensure_session_access(session_id, authorization, engine)

    profiles = _schema_profiles(session_id, engine)
    if not profiles:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    filters = _validated_filters(
        session_id, engine, date_column, date_from, date_to, category_column, category_value
    )
    kpis = calculate_kpis(
        session_id, profiles, engine, filters=filters if filters.active else None, persist=False
    )
    result = simulate_kpi_scenario(kpis, payload.adjustments)
    return {
        "session_id": session_id,
        "scenario_name": "business_what_if",
        **result,
    }


@router.post("/analytics/{session_id}/alerts/evaluate")
def evaluate_business_alerts(
    session_id: str,
    authorization: str | None = Header(default=None),
    date_column: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category_column: str | None = Query(default=None),
    category_value: str | None = Query(default=None),
):
    """Compare equivalent periods, save material KPI movements, and return alert history."""
    engine = get_engine()
    ensure_session_access(session_id, authorization, engine)
    profiles = _schema_profiles(session_id, engine)
    if not profiles:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    if date_column:
        try:
            validate_filter_identifiers(DashboardFilters(date_column=date_column), engine)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
        if not any(
            column["column_name"] == date_column and column["detected_type"] == "datetime"
            for columns in profiles.values()
            for column in columns
        ):
            raise HTTPException(status_code=400, detail="date_column must be a detected datetime field.")

    if not date_from and not date_to:
        default_period = default_monitoring_period(profiles, engine, date_column)
        if default_period:
            date_column, date_from, date_to = default_period

    filters = _validated_filters(
        session_id, engine, date_column, date_from, date_to, category_column, category_value
    )
    comparisons = compare_kpis(session_id, profiles, engine, filters) if (
        filters.date_column and filters.date_from and filters.date_to
    ) else {}
    alerts = detect_kpi_anomalies(
        comparisons,
        str(filters.date_from) if filters.date_from else "",
        str(filters.date_to) if filters.date_to else "",
    )
    for alert in alerts:
        create_notification_once(
            session_id,
            str(alert["event_type"]),
            str(alert["title"]),
            str(alert["message"]),
        )

    try:
        ensure_notifications_table()
        with engine.connect() as conn:
            history = conn.execute(
                text("""
                    SELECT notification_id, event_type, title, message, created_at
                    FROM notifications
                    WHERE session_id = :session_id
                    ORDER BY created_at DESC, notification_id DESC
                    LIMIT 10
                """),
                {"session_id": session_id},
            ).fetchall()
    except Exception as error:
        logger.error("Could not load business alert history: %s", error)
        raise HTTPException(status_code=503, detail="Business alert history is unavailable.")

    return {
        "session_id": session_id,
        "comparison_available": bool(comparisons),
        "period": {
            "date_from": str(filters.date_from) if filters.date_from else None,
            "date_to": str(filters.date_to) if filters.date_to else None,
        },
        "alerts": alerts,
        "history": [
            {
                "id": row[0],
                "event_type": row[1],
                "severity": _alert_severity(row[1]),
                "title": row[2],
                "message": row[3],
                "created_at": str(row[4]) if row[4] else None,
            }
            for row in history
        ],
    }


def _alert_severity(event_type: str) -> str:
    if event_type.endswith("_high"):
        return "high"
    if event_type.endswith("_medium") or event_type == "anomaly_detected":
        return "medium"
    return "low"


@router.get("/sessions")
def list_sessions(authorization: str | None = Header(default=None)):
    """
    List all upload sessions with their status.
    Used by Streamlit to let users pick a previous session.
    """
    user = resolve_request_user(authorization)
    engine = get_engine()
    _ensure_session_name_column(engine)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT s.session_id, s.session_name, s.status, s.total_files,
                       GREATEST(COALESCE(s.total_rows, 0), COALESCE(f.total_rows, 0)) AS total_rows,
                       s.created_at, COALESCE(f.file_count, 0) AS file_count
                FROM upload_sessions s
                LEFT JOIN (
                    SELECT session_id, COUNT(*) AS file_count,
                           COALESCE(SUM(row_count), 0) AS total_rows
                    FROM uploaded_files
                    GROUP BY session_id
                ) f ON f.session_id = s.session_id
                WHERE (:owner_id IS NULL OR s.owner_user_id = :owner_id)
                ORDER BY s.created_at DESC
                LIMIT 50
            """)
            , {"owner_id": user["user_id"] if user else None}
        ).fetchall()

    return {
        "sessions": [
            {
                "session_id" : r[0],
                "name"       : r[1] or f"Dataset {r[0][:8]}",
                "status"     : r[2],
                "total_files": r[3],
                "total_rows": r[4],
                "created_at": str(r[5]) if r[5] else None,
                "file_count": r[6],
            }
            for r in rows
        ]
    }


@router.patch("/sessions/{session_id}")
def rename_session(
    session_id: str,
    payload: SessionRename,
    authorization: str | None = Header(default=None),
):
    user = ensure_session_access(session_id, authorization)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Session name cannot be empty.")
    engine = get_engine()
    _ensure_session_name_column(engine)
    with engine.begin() as conn:
        updated = conn.execute(
                        text("""
                                UPDATE upload_sessions SET session_name = :name
                                WHERE session_id = :session_id
                                    AND (:owner_id IS NULL OR owner_user_id = :owner_id)
                                RETURNING session_id
                        """),
                        {"name": name, "session_id": session_id, "owner_id": user["user_id"] if user else None},
        ).first()
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session_id": session_id, "name": name}
@router.get("/analytics/{session_id}/chart/{chart_id}")
def get_chart_data(
    session_id: str,
    chart_id: int,
    authorization: str | None = Header(default=None),
    date_column: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category_column: str | None = Query(default=None),
    category_value: str | None = Query(default=None),
):
    """
    Return Plotly-ready data for a specific chart.

    Member 2 calls this from Streamlit for each chart_id returned
    by GET /api/analytics/{session_id}.

    Example Streamlit usage:
        import plotly.express as px
        data = requests.get(f"/api/analytics/{sid}/chart/{cid}").json()
        if data['chart_type'] == 'line':
            fig = px.line(x=data['x'], y=data['y'], title=data['title'])
            st.plotly_chart(fig)
    """
    engine = get_engine()
    ensure_session_access(session_id, authorization, engine)
    filters = _validated_filters(
        session_id, engine, date_column, date_from, date_to, category_column, category_value
    )
    result = generate_chart_data(chart_id, session_id, engine, filters=filters)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/analytics/{session_id}/filters")
def get_filter_metadata(session_id: str, authorization: str | None = Header(default=None)):
    """Return validated date and category fields available for dashboard filters."""
    ensure_session_access(session_id, authorization)

    engine = get_engine()
    profiles = _schema_profiles(session_id, engine)
    if not profiles:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    fields = []
    with engine.connect() as conn:
        for table, columns in profiles.items():
            for column in columns:
                name = column["column_name"]
                detected_type = column["detected_type"]
                if detected_type == "datetime":
                    bounds = conn.execute(
                        text(f'SELECT MIN("{name}"), MAX("{name}") FROM "{table}"')
                    ).first()
                    if not bounds or not bounds[0] or not bounds[1]:
                        continue
                    fields.append({
                        "table": table,
                        "column": name,
                        "type": "date",
                        "min": str(bounds[0])[:10] if bounds and bounds[0] else None,
                        "max": str(bounds[1])[:10] if bounds and bounds[1] else None,
                    })
                elif detected_type == "category" and column.get("unique_count", 0) <= 50:
                    values = conn.execute(
                        text(f'SELECT DISTINCT "{name}" FROM "{table}" WHERE "{name}" IS NOT NULL ORDER BY "{name}" LIMIT 50')
                    ).scalars().all()
                    fields.append({
                        "table": table,
                        "column": name,
                        "type": "category",
                        "values": [str(value) for value in values],
                    })
    return {"session_id": session_id, "fields": fields}


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


def _validated_filters(
    session_id: str,
    engine,
    date_column: str | None,
    date_from: date | None,
    date_to: date | None,
    category_column: str | None,
    category_value: str | None,
) -> DashboardFilters:
    profiles = _schema_profiles(session_id, engine)
    if not profiles:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    fields = {column["column_name"]: column["detected_type"] for columns in profiles.values() for column in columns}
    if date_column and fields.get(date_column) != "datetime":
        raise HTTPException(status_code=400, detail="date_column must be a detected datetime field.")
    if date_column:
        has_values = False
        with engine.connect() as conn:
            for table, columns in profiles.items():
                if any(column["column_name"] == date_column for column in columns):
                    has_values = conn.execute(
                        text(f'SELECT EXISTS (SELECT 1 FROM "{table}" WHERE "{date_column}" IS NOT NULL)')
                    ).scalar()
                    if has_values:
                        break
        if not has_values:
            raise HTTPException(status_code=400, detail="date_column has no usable date values.")
    if category_column and fields.get(category_column) != "category":
        raise HTTPException(status_code=400, detail="category_column must be a detected category field.")
    filters = DashboardFilters(date_column, date_from, date_to, category_column, category_value)
    try:
        validate_filter_identifiers(filters, engine)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if (date_from or date_to) and not date_column:
        raise HTTPException(status_code=400, detail="date_column is required when filtering by date.")
    if category_value is not None and not category_column:
        raise HTTPException(status_code=400, detail="category_column is required when filtering by category.")
    return filters
@router.get("/analytics/{session_id}/views")
def get_analytical_views(session_id: str):
    """
    Return list of analytical SQL views created for this session.
    The AI chatbot uses these view names when generating SQL queries.
    """
    engine = get_engine()

    with engine.connect() as conn:
        short_id = session_id.replace("-", "")[:8]
        rows = conn.execute(
            text("""
                SELECT viewname
                FROM   pg_views
                WHERE  schemaname = 'public'
                  AND  viewname LIKE :pattern
                ORDER  BY viewname
            """),
            {"pattern": f"v_{short_id}%"}
        ).fetchall()

    return {
        "session_id": session_id,
        "views"     : [r[0] for r in rows],
        "count"     : len(rows),
    }
@router.get("/analytics/{session_id}/insights")
def get_insights(session_id: str):
    """
    Return AI-generated insights for all charts in a session.
    Frontend shows these below each chart card.
    """
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT chart_id, insight_text, generated_at
                FROM ai_insights
                WHERE session_id = :sid
                  AND insight_type = 'chart_insight'
                ORDER BY chart_id
            """),
            {"sid": session_id}
        ).fetchall()

    return {
        "session_id": session_id,
        "insights": [
            {
                "chart_id"    : r[0],
                "insight_text": r[1],
                "generated_at": str(r[2]) if r[2] else None,
            }
            for r in rows
        ]
    }