"""
chart_selector.py
-----------------
Selects the most appropriate chart type for each column combination
in an uploaded dataset.

Rules (in priority order):
    datetime + currency column      → line chart (trend over time)
    datetime + numeric column       → line chart (metric over time)
    category + currency column      → horizontal bar chart
    category + numeric column       → horizontal bar chart
    category column alone           → pie chart (distribution)
    two currency/numeric columns    → scatter plot (correlation)
    single numeric column           → histogram (distribution)
    multiple numeric columns        → correlation heatmap

Each rule generates one ChartConfig. All configs are saved to
the chart_configs table for the API to serve and Streamlit to render.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.engine import Engine

import pandas as pd

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Output data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ChartConfig:
    """Configuration for one auto-generated chart."""
    chart_type      : str    # 'line' | 'bar' | 'pie' | 'scatter' | 'histogram' | 'heatmap'
    chart_title     : str
    source_table    : str
    x_column        : str
    y_column        : str | None = None
    group_by_column : str | None = None
    aggregation     : str = "sum"    # 'sum' | 'count' | 'avg'
    chart_order     : int = 0
    rationale       : str = ""       # why this chart was selected (shown in UI)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def select_charts(
    session_id     : str,
    schema_profiles: dict[str, list[dict]],
    engine         : Engine,
) -> list[ChartConfig]:
    """
    Select appropriate charts for all tables in a session.

    Parameters
    ----------
    session_id : str
    schema_profiles : dict[str, list[dict]]
        {table_name: [column profiles]}
    engine : Engine

    Returns
    -------
    list[ChartConfig]
        All selected chart configurations. Also saves to chart_configs table.
    """
    all_charts = []
    chart_order = 1

    for table_name, columns in schema_profiles.items():
        type_map = {col["column_name"]: col["detected_type"] for col in columns}

        currency_cols = [c for c, t in type_map.items() if t == "currency"]
        datetime_cols = [c for c, t in type_map.items() if t == "datetime"]
        category_cols = [c for c, t in type_map.items() if t == "category"]
        numeric_cols  = [c for c, t in type_map.items() if t == "numeric"]
        id_cols       = [c for c, t in type_map.items() if t == "id"]

        # ── Rule 1: datetime + currency → line chart (highest priority) ───
        if datetime_cols and currency_cols:
            date_col = _pick_primary_date(datetime_cols)
            rev_col  = _pick_primary_currency(currency_cols)
            all_charts.append(ChartConfig(
                chart_type   = "line",
                chart_title  = f"{_label(rev_col)} Over Time",
                source_table = table_name,
                x_column     = date_col,
                y_column     = rev_col,
                aggregation  = "sum",
                chart_order  = chart_order,
                rationale    = f"datetime column '{date_col}' + currency column '{rev_col}' → line chart (trend over time)",
            ))
            chart_order += 1

        # ── Rule 2: category + currency → bar chart ────────────────────────
        if category_cols and currency_cols:
            cat_col = category_cols[0]
            rev_col = _pick_primary_currency(currency_cols)
            all_charts.append(ChartConfig(
                chart_type   = "bar",
                chart_title  = f"{_label(rev_col)} by {_label(cat_col)}",
                source_table = table_name,
                x_column     = cat_col,
                y_column     = rev_col,
                aggregation  = "sum",
                chart_order  = chart_order,
                rationale    = f"category column '{cat_col}' + currency column '{rev_col}' → bar chart",
            ))
            chart_order += 1

            # If there's a second category column, add another bar chart
            if len(category_cols) > 1:
                cat_col2 = category_cols[1]
                all_charts.append(ChartConfig(
                    chart_type   = "bar",
                    chart_title  = f"{_label(rev_col)} by {_label(cat_col2)}",
                    source_table = table_name,
                    x_column     = cat_col2,
                    y_column     = rev_col,
                    aggregation  = "sum",
                    chart_order  = chart_order,
                    rationale    = f"category column '{cat_col2}' + currency column '{rev_col}' → bar chart",
                ))
                chart_order += 1

        # ── Rule 3: category alone → pie chart ────────────────────────────
        if category_cols and not currency_cols:
            cat_col = category_cols[0]
            all_charts.append(ChartConfig(
                chart_type   = "pie",
                chart_title  = f"Distribution of {_label(cat_col)}",
                source_table = table_name,
                x_column     = cat_col,
                y_column     = None,
                aggregation  = "count",
                chart_order  = chart_order,
                rationale    = f"category column '{cat_col}' with no currency column → pie chart (distribution)",
            ))
            chart_order += 1

        # ── Rule 4: two currency columns → scatter plot ────────────────────
        if len(currency_cols) >= 2:
            all_charts.append(ChartConfig(
                chart_type   = "scatter",
                chart_title  = f"{_label(currency_cols[0])} vs {_label(currency_cols[1])}",
                source_table = table_name,
                x_column     = currency_cols[0],
                y_column     = currency_cols[1],
                aggregation  = "none",
                chart_order  = chart_order,
                rationale    = f"two currency columns → scatter plot (correlation analysis)",
            ))
            chart_order += 1

        # ── Rule 5: single currency/numeric → histogram ────────────────────
        if currency_cols and not datetime_cols and not category_cols:
            rev_col = currency_cols[0]
            all_charts.append(ChartConfig(
                chart_type   = "histogram",
                chart_title  = f"Distribution of {_label(rev_col)}",
                source_table = table_name,
                x_column     = rev_col,
                y_column     = None,
                aggregation  = "count",
                chart_order  = chart_order,
                rationale    = f"single currency column '{rev_col}' without datetime/category → histogram",
            ))
            chart_order += 1

        # ── Rule 6: datetime + category → grouped line chart ───────────────
        if datetime_cols and category_cols and currency_cols:
            date_col = _pick_primary_date(datetime_cols)
            cat_col  = category_cols[0]
            rev_col  = _pick_primary_currency(currency_cols)
            all_charts.append(ChartConfig(
                chart_type      = "line",
                chart_title     = f"{_label(rev_col)} Over Time by {_label(cat_col)}",
                source_table    = table_name,
                x_column        = date_col,
                y_column        = rev_col,
                group_by_column = cat_col,
                aggregation     = "sum",
                chart_order     = chart_order,
                rationale       = f"datetime + currency + category → grouped line chart by {cat_col}",
            ))
            chart_order += 1

    # Save to database
    _save_charts(session_id, all_charts, engine)

    logger.info(
        "Selected %d chart(s) for session '%s'.", len(all_charts), session_id
    )
    return all_charts


def _save_charts(
    session_id : str,
    charts     : list[ChartConfig],
    engine     : Engine,
) -> None:
    """Save chart configs to the chart_configs table."""
    if not charts:
        return

    rows = [
        {
            "session_id"     : session_id,
            "chart_type"     : c.chart_type,
            "chart_title"    : c.chart_title,
            "source_table"   : c.source_table,
            "x_column"       : c.x_column,
            "y_column"       : c.y_column,
            "group_by_column": c.group_by_column,
            "aggregation"    : c.aggregation,
            "chart_order"    : c.chart_order,
            "rationale"      : c.rationale,
        }
        for c in charts
    ]

    df = pd.DataFrame(rows)
    df.to_sql(
        name      = "chart_configs",
        con       = engine,
        if_exists = "append",
        index     = False,
    )
    logger.info("Saved %d chart config(s) to chart_configs table.", len(rows))


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pick_primary_date(datetime_cols: list[str]) -> str:
    """Pick the most likely primary date column."""
    preferred = ["purchase", "order", "created", "date", "timestamp", "start"]
    for keyword in preferred:
        for col in datetime_cols:
            if keyword in col.lower():
                return col
    return datetime_cols[0]


def _pick_primary_currency(currency_cols: list[str]) -> str:
    """Pick the most likely primary revenue/currency column."""
    preferred = ["revenue", "total", "amount", "sales", "price", "value", "payment"]
    for keyword in preferred:
        for col in currency_cols:
            if keyword in col.lower():
                return col
    return currency_cols[0]


def _label(col_name: str) -> str:
    """Convert snake_case column name to a readable chart label."""
    import re
    name = re.sub(r'[_\-]?(id|key|code|ref)$', '', col_name, flags=re.IGNORECASE)
    return name.replace('_', ' ').strip().title()