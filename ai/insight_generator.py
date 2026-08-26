"""
insight_generator.py
--------------------
Generates plain-English business insights for auto-generated charts.

Called by: analytics engine after charts are configured.
Stores results in ai_insights table.
One insight per chart — shown below each chart in the dashboard.
"""

import os
import json
import logging

import pandas as pd
from groq import Groq
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import Engine

from analytics.chart_generator import generate_chart_data

logger = logging.getLogger(__name__)

MODEL  = "openai/gpt-oss-120b"
load_dotenv()


def _get_client() -> Groq | None:
    """Create the Groq client only when an API key is available."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY is not configured; skipping AI chart insights.")
        return None
    return Groq(api_key=api_key)


def generate_insights_for_session(
    session_id : str,
    charts     : list[dict],
    engine     : Engine,
) -> list[dict]:
    """
    Generate one AI insight per chart for a session.

    Parameters
    ----------
    session_id : str
    charts     : list of chart config dicts from chart_configs table
    engine     : Engine

    Returns
    -------
    list of insight dicts saved to ai_insights table
    """
    insights = []

    for chart in charts:
        chart_id    = chart.get("chart_id")
        chart_title = chart.get("chart_title", "")
        chart_type  = chart.get("chart_type", "")
        # Use the same query path as the dashboard so the explanation matches
        # the chart the user actually sees, including joined charts.
        chart_result = generate_chart_data(chart_id, session_id, engine)
        chart_data = _chart_result_to_rows(chart_result)
        if not chart_data:
            continue

        # Generate insight
        insight_text = _generate_insight(chart_title, chart_type, chart_data)
        if not insight_text:
            continue

        insights.append({
            "session_id"  : session_id,
            "insight_type": "chart_insight",
            "chart_id"    : chart_id,
            "question_asked": None,
            "sql_used"    : None,
            "insight_text": insight_text,
        })

    # Save to database
    if insights:
        _save_insights(insights, engine)

    logger.info("Generated %d chart insight(s) for session '%s'.", len(insights), session_id)
    return insights


def _chart_result_to_rows(chart_result: dict) -> list[dict] | None:
    """Convert Plotly-oriented chart data into compact rows for the LLM."""
    if not chart_result or chart_result.get("error"):
        return None
    if chart_result.get("z"):
        return [
            {"x": x, "y": y, "value": value}
            for y, values in zip(chart_result.get("y", []), chart_result["z"])
            for x, value in zip(chart_result.get("x", []), values)
        ][:30]
    if chart_result.get("labels"):
        return [
            {"label": label, "value": value}
            for label, value in zip(chart_result["labels"], chart_result.get("values", []))
        ][:30]
    if chart_result.get("x") is not None and chart_result.get("y") is not None:
        rows = []
        groups = chart_result.get("group", [None] * len(chart_result["x"]))
        for x, y, group in zip(chart_result["x"], chart_result["y"], groups):
            row = {"x": x, "value": y}
            if group is not None:
                row["group"] = group
            rows.append(row)
        return rows[:30]
    if chart_result.get("x") is not None:
        return [{"value": value} for value in chart_result["x"][:30]]
    if chart_result.get("y") is not None:
        return [{"value": value} for value in chart_result["y"][:30]]
    return None


def _fetch_chart_sample(
    table      : str,
    x_col      : str,
    y_col      : str | None,
    aggregation: str,
    chart_type : str,
    engine     : Engine,
) -> list[dict] | None:
    """Fetch a small sample of chart data for the LLM to analyse."""
    try:
        if chart_type == "heatmap":
            return None   # correlation matrices are not useful as prose samples

        if y_col and aggregation in ("sum", "avg", "count"):
            agg_func = {"sum": "SUM", "avg": "AVG", "count": "COUNT"}.get(aggregation, "SUM")
            if chart_type == "line":
                sql = f"""
                    SELECT DATE_TRUNC('month', "{x_col}"::timestamp) AS period,
                           {agg_func}("{y_col}") AS value
                    FROM "{table}"
                    WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
                    GROUP BY period ORDER BY period DESC LIMIT 6
                """
            else:
                sql = f"""
                    SELECT "{x_col}", {agg_func}("{y_col}") AS value
                    FROM "{table}"
                    WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
                    GROUP BY "{x_col}" ORDER BY value DESC LIMIT 8
                """
        elif chart_type == "pie":
            sql = f"""
                SELECT "{x_col}", COUNT(*) AS value
                FROM "{table}" WHERE "{x_col}" IS NOT NULL
                GROUP BY "{x_col}" ORDER BY value DESC LIMIT 8
            """
        elif chart_type in ("histogram", "box"):
            sql = f"""
                SELECT "{x_col}" AS value
                FROM "{table}" WHERE "{x_col}" IS NOT NULL
                ORDER BY RANDOM() LIMIT 100
            """
        elif chart_type == "funnel":
            if y_col:
                agg_func = {"sum": "SUM", "avg": "AVG", "count": "COUNT"}.get(aggregation, "SUM")
                sql = f"""
                    SELECT "{x_col}", {agg_func}("{y_col}") AS value
                    FROM "{table}"
                    WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL
                    GROUP BY "{x_col}" ORDER BY value DESC LIMIT 10
                """
            else:
                sql = f"""
                    SELECT "{x_col}", COUNT(*) AS value
                    FROM "{table}" WHERE "{x_col}" IS NOT NULL
                    GROUP BY "{x_col}" ORDER BY value DESC LIMIT 10
                """
        else:
            return None

        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows    = result.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    except Exception as e:
        logger.debug("Could not fetch chart sample for '%s': %s", table, e)
        return None

def _generate_insight(
    chart_title: str,
    chart_type : str,
    data       : list[dict],
) -> str | None:
    """Generate a detailed, useful business insight for a chart."""

    data_str  = json.dumps(data[:10], indent=2, default=str)
    row_count = len(data)

    # Build chart-type specific guidance
    chart_guidance = {
        "line"    : "Identify the trend direction (growing/declining), the peak period, and the lowest period.",
        "bar"     : "Name the top 2-3 performers and the bottom performer. Calculate what % the top item represents.",
        "treemap" : "Name the dominant category and its approximate share. Mention any surprising smaller segments.",
        "pie"     : "State what the largest segment is and its percentage. Note if distribution is healthy or concentrated.",
        "scatter" : "Describe the correlation direction (positive/negative/none) and any notable outliers.",
        "histogram": "Describe the distribution shape (normal/skewed). State the most common value range.",
    }.get(chart_type, "Identify the most important finding in the data.")

    prompt = f"""You are a senior business analyst generating an insight for a dashboard chart.

Chart title: "{chart_title}"
Chart type: {chart_type}
Data ({row_count} data points):
{data_str}

Analysis focus: {chart_guidance}

Write a clear, specific business insight in exactly 2-3 sentences:
- Sentence 1: State the main finding with specific numbers (include actual values from the data)
- Sentence 2: Provide context or comparison (e.g. what this means, which items stand out)
- Sentence 3 (optional): One actionable takeaway or observation worth noting

Rules:
- Always use specific numbers from the data — never say "some" or "many"
- Write for a business executive, not a data scientist
- No mention of SQL, tables, columns, or technical terms
- Do not start with "This chart shows" — start directly with the insight

Insight:"""

    try:
        groq_client = _get_client()
        if groq_client is None:
            return _fallback_insight(chart_title, chart_type, data)
        response = groq_client.chat.completions.create(
            model    = MODEL,
            messages = [
                {
                    "role"   : "system",
                    "content": (
                        "You are a senior business analyst who writes sharp, specific "
                        "chart insights for executive dashboards. Every insight must include "
                        "actual numbers from the data. You never use vague language."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens = 280,
            temperature= 0.35,
        )
        content = response.choices[0].message.content
        if not content:
            logger.warning("Groq returned an empty insight for '%s'.", chart_title)
            return _fallback_insight(chart_title, chart_type, data)
        content = content.strip()
        if len(content) < 40 or content[-1] not in ".!?%":
            logger.warning("Groq returned an incomplete insight for '%s'.", chart_title)
            return _fallback_insight(chart_title, chart_type, data)
        return content
    except Exception as e:
        logger.warning("Insight generation failed for '%s': %s", chart_title, e)
        return _fallback_insight(chart_title, chart_type, data)


def _fallback_insight(chart_title: str, chart_type: str, data: list[dict]) -> str:
    """Provide a useful explanation when the model is unavailable or empty."""
    values = [row.get("value") for row in data if isinstance(row.get("value"), (int, float))]
    if not values:
        return f"{chart_title} contains {len(data)} data points. Review the chart for the categories or periods represented."

    if chart_type in ("bar", "pie", "treemap", "funnel"):
        top = data[0]
        label = top.get("label", top.get("x", "the leading item"))
        total = sum(values)
        share = (float(top["value"]) / total * 100) if total else 0
        return f"{label} is the largest segment at {top['value']:,.2f}, representing {share:.1f}% of the total. The chart compares {len(data)} segments and highlights where performance is concentrated."

    highest = max(values)
    lowest = min(values)
    return f"The chart ranges from {lowest:,.2f} to {highest:,.2f}, with the highest value at {highest:,.2f}. Across the {len(data)} data points, the pattern shows the main variation that should guide further investigation."


def _save_insights(insights: list[dict], engine: Engine) -> None:
    try:
        session_id = insights[0]["session_id"]
        with engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM ai_insights "
                    "WHERE session_id = :sid AND insight_type = 'chart_insight'"
                ),
                {"sid": session_id},
            )
        pd.DataFrame(insights).to_sql(
            name="ai_insights", con=engine, if_exists="append", index=False
        )
    except Exception as e:
        logger.error("Failed to save insights: %s", e)