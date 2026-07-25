"""
chart_generator.py
------------------
Generates Plotly-ready chart data for a given chart_id.

Called by: GET /api/analytics/{session_id}/chart/{chart_id}

Supports: line, bar, pie, scatter, histogram, treemap, heatmap, box, funnel
"""

import logging

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

MAX_CHART_POINTS = 500


def generate_chart_data(
    chart_id   : int,
    session_id : str,
    engine     : Engine,
) -> dict:
    """
    Generate Plotly-ready chart data for a given chart_id.
    Reads config from chart_configs table, runs SQL, returns data dict.
    """
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
        elif chart_type == "treemap":
            return _generate_treemap_data(table, x_col, y_col, title, rationale, engine)
        elif chart_type == "heatmap":
            return _generate_heatmap_data(table, x_col, title, rationale, engine)
        elif chart_type == "box":
            return _generate_box_data(table, x_col, title, rationale, engine)
        elif chart_type == "funnel":
            return _generate_funnel_data(table, x_col, y_col, title, rationale, engine)
        else:
            return {"error": f"Unknown chart type: {chart_type}"}
    except Exception as e:
        logger.error("Chart generation failed for chart_id=%d: %s", chart_id, e)
        return {"error": str(e)}


def _generate_line_data(table, x_col, y_col, group_col, agg, title, rationale, engine):
    agg_func = "SUM" if agg == "sum" else ("AVG" if agg == "avg" else "COUNT")
    if group_col:
        sql = f"""
            SELECT DATE_TRUNC('month', "{x_col}"::timestamp) AS period,
                   "{group_col}", {agg_func}("{y_col}") AS value
            FROM "{table}"
            WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
            GROUP BY period, "{group_col}" ORDER BY period LIMIT {MAX_CHART_POINTS}
        """
    else:
        sql = f"""
            SELECT DATE_TRUNC('month', "{x_col}"::timestamp) AS period,
                   {agg_func}("{y_col}") AS value
            FROM "{table}"
            WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
            GROUP BY period ORDER BY period LIMIT {MAX_CHART_POINTS}
        """
    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available."}
    df["period"] = df["period"].astype(str)
    result = {"chart_type": "line", "title": title, "rationale": rationale,
              "x": df["period"].tolist(), "y": df["value"].tolist()}
    if group_col and group_col in df.columns:
        result["group"] = df[group_col].tolist()
    return result


def _generate_bar_data(table, x_col, y_col, agg, title, rationale, engine):
    agg_func = "SUM" if agg == "sum" else ("AVG" if agg == "avg" else "COUNT")
    if y_col:
        sql = f"""
            SELECT "{x_col}", {agg_func}("{y_col}") AS value
            FROM "{table}" WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
            GROUP BY "{x_col}" ORDER BY value DESC LIMIT 15
        """
    else:
        sql = f"""
            SELECT "{x_col}", COUNT(*) AS value
            FROM "{table}" WHERE "{x_col}" IS NOT NULL
            GROUP BY "{x_col}" ORDER BY value DESC LIMIT 15
        """
    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available."}
    return {"chart_type": "bar", "title": title, "rationale": rationale,
            "x": df[x_col].astype(str).tolist(), "y": df["value"].tolist()}


def _generate_pie_data(table, x_col, title, rationale, engine):
    sql = f"""
        SELECT "{x_col}", COUNT(*) AS count FROM "{table}"
        WHERE "{x_col}" IS NOT NULL
        GROUP BY "{x_col}" ORDER BY count DESC LIMIT 6
    """
    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available."}
    return {"chart_type": "pie", "title": title, "rationale": rationale,
            "labels": df[x_col].astype(str).tolist(), "values": df["count"].tolist()}


def _generate_scatter_data(table, x_col, y_col, title, rationale, engine):
    sql = f"""
        SELECT "{x_col}", "{y_col}" FROM "{table}"
        WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
        ORDER BY RANDOM() LIMIT {MAX_CHART_POINTS}
    """
    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available."}
    return {"chart_type": "scatter", "title": title, "rationale": rationale,
            "x": df[x_col].tolist(), "y": df[y_col].tolist()}


def _generate_histogram_data(table, x_col, title, rationale, engine):
    sql = f"""
        SELECT "{x_col}" FROM "{table}"
        WHERE "{x_col}" IS NOT NULL
        ORDER BY RANDOM() LIMIT {MAX_CHART_POINTS}
    """
    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available."}
    return {"chart_type": "histogram", "title": title, "rationale": rationale,
            "x": df[x_col].tolist()}


def _generate_treemap_data(table, x_col, y_col, title, rationale, engine):
    if y_col:
        sql = f"""
            SELECT "{x_col}", SUM("{y_col}") AS value FROM "{table}"
            WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
            GROUP BY "{x_col}" ORDER BY value DESC LIMIT 30
        """
    else:
        sql = f"""
            SELECT "{x_col}", COUNT(*) AS value FROM "{table}"
            WHERE "{x_col}" IS NOT NULL
            GROUP BY "{x_col}" ORDER BY value DESC LIMIT 30
        """
    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available."}
    return {"chart_type": "treemap", "title": title, "rationale": rationale,
            "labels": df[x_col].astype(str).tolist(),
            "values": df["value"].tolist(),
            "parents": [""] * len(df)}


def _generate_heatmap_data(table, x_col, title, rationale, engine):
    cols = [c.strip() for c in x_col.split(",") if c.strip()]
    if len(cols) < 2:
        return {"error": "Need at least 2 columns for heatmap."}
    col_select = ", ".join(f'"{c}"' for c in cols)
    sql = f'SELECT {col_select} FROM "{table}" LIMIT 5000'
    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available."}
    df_num = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
    if df_num.shape[1] < 2:
        return {"error": "Not enough numeric data for correlation."}
    corr = df_num.corr().round(3)
    return {"chart_type": "heatmap", "title": title, "rationale": rationale,
            "x": corr.columns.tolist(), "y": corr.index.tolist(),
            "z": corr.values.tolist()}


def _generate_box_data(table, x_col, title, rationale, engine):
    sql = f"""
        SELECT "{x_col}" FROM "{table}"
        WHERE "{x_col}" IS NOT NULL
        ORDER BY RANDOM() LIMIT {MAX_CHART_POINTS}
    """
    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available."}
    return {"chart_type": "box", "title": title, "rationale": rationale,
            "y": df[x_col].tolist(), "name": x_col}


def _generate_funnel_data(table, x_col, y_col, title, rationale, engine):
    if y_col:
        sql = f"""
            SELECT "{x_col}", SUM("{y_col}") AS value FROM "{table}"
            WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
            GROUP BY "{x_col}" ORDER BY value DESC LIMIT 10
        """
    else:
        sql = f"""
            SELECT "{x_col}", COUNT(*) AS value FROM "{table}"
            WHERE "{x_col}" IS NOT NULL
            GROUP BY "{x_col}" ORDER BY value DESC LIMIT 10
        """
    df = _query_df(sql, engine)
    if df is None or df.empty:
        return {"error": "No data available."}
    return {"chart_type": "funnel", "title": title, "rationale": rationale,
            "x": df["value"].tolist(), "y": df[x_col].astype(str).tolist()}


def _query_df(sql: str, engine: Engine) -> pd.DataFrame | None:
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn)
    except Exception as e:
        logger.error("Chart data query failed: %s", e)
        return None