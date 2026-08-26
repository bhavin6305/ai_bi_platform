"""
analytics
---------
Analytics engine for the AI-Powered BI Platform.

Public API:
    from analytics import run_analytics, calculate_kpis, select_charts
"""

from analytics.kpi_engine     import calculate_kpis
from analytics.chart_selector import select_charts
from analytics.chart_generator import generate_chart_data


def run_analytics(
    session_id     : str,
    schema_profiles: dict,
    engine,
    relationships  : list[dict] = None,
) -> dict:
    """
    Run the full analytics pipeline for a session.
    Calculates KPIs and selects charts in one call.

    Called by the ETL pipeline after loading data.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("Running analytics for session '%s'.", session_id)

    kpis   = calculate_kpis(session_id, schema_profiles, engine)
    charts = select_charts(session_id, schema_profiles, engine, relationships or [])

    logger.info(
        "Analytics complete: %d KPIs, %d charts for session '%s'.",
        len(kpis), len(charts), session_id
    )

    return {
        "kpis_calculated"  : len(kpis),
        "charts_configured": len(charts),
    }


__all__ = [
    "run_analytics",
    "calculate_kpis",
    "select_charts",
    "generate_chart_data",
]
