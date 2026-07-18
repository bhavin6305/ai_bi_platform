"""
chart_generator.py
------------------
Generates actual Plotly chart data for a given ChartConfig.

When Streamlit calls GET /api/analytics/{session_id}, it gets chart configs.
For each config, it can call GET /api/analytics/{session_id}/chart/{chart_id}
to get the actual Plotly-ready data (x values, y values, layout).

Member 2 renders these using:
    import plotly.express as px
    fig = px.line(x=chart_data['x'], y=chart_data['y'], title=chart_data['title'])
    st.plotly_chart(fig)
"""

import logging

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Max data points to return per chart — avoids sending huge JSON responses
MAX_CHART_POINTS = 500


def generate_chart_data(
    chart_id    : int,
    session_id  : str,
    engine      : Engine,
) -> dict:
    """
    Generate Plotly-ready chart data for a given chart_id.

    Reads the chart config from chart_configs table, runs the appropriate
    SQL query against the dynamic business data table, and returns
    the data in a format Plotly can render directly.

    Parameters
    ----------
    chart_id   : int    — from chart_configs.chart_id
    session_id : str
    engine     : Engine

    Returns
    -------
    dict with keys: chart_type, title, x, y, labels (for pie), rationale
    """
    # Load chart config from DB
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT chart_type, chart_title, source_table,
                       x_column, y_column, group_by_column,
                       aggregation, rationale
                FROM chart_configs
                WHERE chart_id = :cid AND session_id = :sid
            """),
            {"cid": chart_id, "sid": session_id}
        ).fetchone()

    if not row:
        return {"error": f"Chart {chart_id} not found for session {session_id}"}

    chart_type, title, table, x_col, y_col, group_col, agg, rationale = row

    # Generate data based on chart type
    try:
        if chart_type == "line":
            return _generate_line_data(table, x_col, y_col, group_col, agg, title, rationale, engine)
        elif chart_type == "bar":
            return _generate_bar_data(table, x_col, y_col, agg, title, rationale, engine)
        elif chart_type == "pie":
            return _generate_pie_data(table, x_col, title, rationale, engine)
        elif chart_type == "scatter":
            return _generate_scatter_data(table, x_col, y_col, title, rationale, engine)
        elif chart_type == "histogram":
            return _generate_histogram_data(table, x_col, title, rationale, engine)
        else:
            return {"error": f"Unknown chart type: {chart_type}"}
    except Exception as e:
        logger.error("Chart generation failed for chart_id=%d: %s", chart_id, e)
        return {"error": str(e)}


def _generate_line_data(table, x_col, y_col, group_col, agg, title, rationale, engine):
    """Generate line chart data — aggregated by time period."""
    agg_func = "SUM" if agg == "sum" else ("AVG" if agg == "avg" else "COUNT")

    if group_col:
        sql = f"""
            SELECT
                DATE_TRUNC('month', "{x_col}"::timestamp) as period,
                "{group_col}",
                {agg_func}("{y_col}") as value
            FROM "{table}"
            WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
            GROUP BY period, "{group_col}"
            ORDER BY period
            LIMIT {MAX_CHART_POINTS}
        """
    else:
        sql = f"""
            SELECT
                DATE_TRUNC('month', "{x_col}"::timestamp) as period,
                {agg_func}("{y_col}") as value
            FROM "{table}"
            WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
            GROUP BY period
            ORDER BY period
            LIMIT {MAX_CHART_POINTS}
        """

    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available for this chart."}

    df["period"] = df["period"].astype(str)

    result = {
        "chart_type": "line",
        "title"     : title,
        "rationale" : rationale,
        "x"         : df["period"].tolist(),
        "y"         : df["value"].tolist(),
    }

    if group_col and group_col in df.columns:
        result["group"] = df[group_col].tolist()

    return result


def _generate_bar_data(table, x_col, y_col, agg, title, rationale, engine):
    """Generate bar chart data — top 15 categories by value."""
    agg_func = "SUM" if agg == "sum" else ("AVG" if agg == "avg" else "COUNT")

    sql = f"""
        SELECT "{x_col}", {agg_func}("{y_col}") as value
        FROM "{table}"
        WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
        GROUP BY "{x_col}"
        ORDER BY value DESC
        LIMIT 15
    """

    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available for this chart."}

    return {
        "chart_type": "bar",
        "title"     : title,
        "rationale" : rationale,
        "x"         : df[x_col].astype(str).tolist(),
        "y"         : df["value"].tolist(),
    }


def _generate_pie_data(table, x_col, title, rationale, engine):
    """Generate pie chart data — top 10 categories by count."""
    sql = f"""
        SELECT "{x_col}", COUNT(*) as count
        FROM "{table}"
        WHERE "{x_col}" IS NOT NULL
        GROUP BY "{x_col}"
        ORDER BY count DESC
        LIMIT 10
    """

    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available for this chart."}

    return {
        "chart_type": "pie",
        "title"     : title,
        "rationale" : rationale,
        "labels"    : df[x_col].astype(str).tolist(),
        "values"    : df["count"].tolist(),
    }


def _generate_scatter_data(table, x_col, y_col, title, rationale, engine):
    """Generate scatter plot data — sample of up to MAX_CHART_POINTS rows."""
    sql = f"""
        SELECT "{x_col}", "{y_col}"
        FROM "{table}"
        WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
        ORDER BY RANDOM()
        LIMIT {MAX_CHART_POINTS}
    """

    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available for this chart."}

    return {
        "chart_type": "scatter",
        "title"     : title,
        "rationale" : rationale,
        "x"         : df[x_col].tolist(),
        "y"         : df[y_col].tolist(),
    }


def _generate_histogram_data(table, x_col, title, rationale, engine):
    """Generate histogram data."""
    sql = f"""
        SELECT "{x_col}"
        FROM "{table}"
        WHERE "{x_col}" IS NOT NULL
        ORDER BY RANDOM()
        LIMIT {MAX_CHART_POINTS}
    """

    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available for this chart."}

    return {
        "chart_type": "histogram",
        "title"     : title,
        "rationale" : rationale,
        "x"         : df[x_col].tolist(),
    }


def _query_df(sql: str, engine: Engine) -> pd.DataFrame | None:
    """Run a SQL query and return result as a DataFrame."""
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn)
    except Exception as e:
        logger.error("Chart data query failed: %s", e)
        return None