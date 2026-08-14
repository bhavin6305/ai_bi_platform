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
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL  = "llama-3.1-8b-instant"


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
        source_table= chart.get("source_table", "")
        x_col       = chart.get("x_column", "")
        y_col       = chart.get("y_column", "")
        aggregation = chart.get("aggregation", "sum")

        # Fetch a sample of the chart's actual data
        chart_data = _fetch_chart_sample(
            source_table, x_col, y_col, aggregation, chart_type, engine
        )
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
        if chart_type in ("heatmap", "histogram", "box"):
            return None   # skip non-business charts

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
        else:
            return None

        with engine.connect() as conn:
            rows = conn.execute(text(sql)).fetchall()
            keys = conn.execute(text(sql)).keys() if rows else []

        # Re-execute to get both keys and rows cleanly
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
        response = client.chat.completions.create(
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
            max_tokens = 180,
            temperature= 0.35,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Insight generation failed for '%s': %s", chart_title, e)
        return None


def _save_insights(insights: list[dict], engine: Engine) -> None:
    import pandas as pd
    try:
        pd.DataFrame(insights).to_sql(
            name="ai_insights", con=engine, if_exists="append", index=False
        )
    except Exception as e:
        logger.error("Failed to save insights: %s", e)