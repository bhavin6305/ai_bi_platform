"""
kpi_engine.py
-------------
Detects which KPIs apply to any uploaded dataset and calculates them.

Works generically on ANY dataset — no hardcoded column names.
Uses the detected schema types to decide what is calculable:

    If currency column exists        → Total Revenue, Avg Order Value
    If currency + datetime exist     → MoM Growth %, Revenue Trend
    If id column exists              → Total Records count
    If category + currency exist     → Revenue by Category breakdown
    If multiple id columns exist     → potential customer + transaction split

KPI results are stored in the kpi_results table for the API to serve.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# KPI definitions — what to calculate and when
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class KPIResult:
    """One calculated KPI value."""
    kpi_name      : str
    kpi_value     : float
    kpi_unit      : str     # 'currency' | 'count' | 'percent' | 'days' | 'ratio'
    kpi_category  : str     # 'sales' | 'customer' | 'inventory' | 'general'
    display_format: str     # e.g. '${value:,.2f}' shown in Streamlit


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def calculate_kpis(
    session_id    : str,
    schema_profiles: dict[str, list[dict]],
    engine        : Engine,
) -> list[KPIResult]:
    """
    Detect applicable KPIs and calculate them for a session.

    Parameters
    ----------
    session_id : str
    schema_profiles : dict[str, list[dict]]
        {table_name: [column profiles]} — output of type_detector
    engine : Engine

    Returns
    -------
    list[KPIResult]
        All calculated KPIs. Also saves them to kpi_results table.
    """
    all_kpis = []

    for table_name, columns in schema_profiles.items():
        logger.info("Calculating KPIs for table '%s'.", table_name)

        # Build type map for this table
        type_map = {col["column_name"]: col["detected_type"] for col in columns}

        # Get column names by type
        currency_cols = [c for c, t in type_map.items() if t == "currency"]
        datetime_cols = [c for c, t in type_map.items() if t == "datetime"]
        id_cols       = [c for c, t in type_map.items() if t == "id"]
        category_cols = [c for c, t in type_map.items() if t == "category"]
        numeric_cols  = [c for c, t in type_map.items() if t == "numeric"]

        # ── KPI 1: Total Records ───────────────────────────────────────────
        # Always calculable — every table has a row count
        total = _query_scalar(
            f'SELECT COUNT(*) FROM "{table_name}"', engine
        )
        if total is not None:
            all_kpis.append(KPIResult(
                kpi_name      = "Total Records",
                kpi_value     = float(total),
                kpi_unit      = "count",
                kpi_category  = "general",
                display_format= "{value:,.0f}",
            ))

        # ── KPI 2: Total Revenue ───────────────────────────────────────────
        # Requires at least one currency column
        if currency_cols:
            rev_col = _pick_best_column(currency_cols, ["revenue", "total", "amount", "price", "value", "sales"])
            total_rev = _query_scalar(
                f'SELECT SUM("{rev_col}") FROM "{table_name}" WHERE "{rev_col}" IS NOT NULL',
                engine
            )
            if total_rev is not None:
                all_kpis.append(KPIResult(
                    kpi_name      = "Total Revenue",
                    kpi_value     = round(float(total_rev), 2),
                    kpi_unit      = "currency",
                    kpi_category  = "sales",
                    display_format= "${value:,.2f}",
                ))

                # ── KPI 3: Average Order Value ─────────────────────────────
                avg_val = _query_scalar(
                    f'SELECT AVG("{rev_col}") FROM "{table_name}" WHERE "{rev_col}" IS NOT NULL',
                    engine
                )
                if avg_val is not None:
                    all_kpis.append(KPIResult(
                        kpi_name      = "Average Value",
                        kpi_value     = round(float(avg_val), 2),
                        kpi_unit      = "currency",
                        kpi_category  = "sales",
                        display_format= "${value:,.2f}",
                    ))

                # ── KPI 4: Max Single Value ────────────────────────────────
                max_val = _query_scalar(
                    f'SELECT MAX("{rev_col}") FROM "{table_name}" WHERE "{rev_col}" IS NOT NULL',
                    engine
                )
                if max_val is not None:
                    all_kpis.append(KPIResult(
                        kpi_name      = "Max Transaction Value",
                        kpi_value     = round(float(max_val), 2),
                        kpi_unit      = "currency",
                        kpi_category  = "sales",
                        display_format= "${value:,.2f}",
                    ))

        # ── KPI 5: Unique Entities ─────────────────────────────────────────
        # For each id column, count unique values
        for id_col in id_cols[:2]:   # limit to first 2 id columns
            unique_count = _query_scalar(
                f'SELECT COUNT(DISTINCT "{id_col}") FROM "{table_name}"',
                engine
            )
            if unique_count is not None:
                # Humanise the column name for display
                label = _humanise_column_name(id_col)
                all_kpis.append(KPIResult(
                    kpi_name      = f"Unique {label}s",
                    kpi_value     = float(unique_count),
                    kpi_unit      = "count",
                    kpi_category  = "customer" if "customer" in id_col.lower() else "general",
                    display_format= "{value:,.0f}",
                ))

        # ── KPI 6: Date range ─────────────────────────────────────────────
        # If datetime column exists — calculate date range of the data
        if datetime_cols:
            date_col = _pick_best_column(
                datetime_cols,
                ["date", "created", "timestamp", "purchase", "order"]
            )
            date_range = _query_row(
                f'SELECT MIN("{date_col}"), MAX("{date_col}") FROM "{table_name}"',
                engine
            )
            if date_range and date_range[0] and date_range[1]:
                try:
                    min_date = pd.to_datetime(str(date_range[0]))
                    max_date = pd.to_datetime(str(date_range[1]))
                    days_span = (max_date - min_date).days
                    all_kpis.append(KPIResult(
                        kpi_name      = "Data Time Span",
                        kpi_value     = float(days_span),
                        kpi_unit      = "days",
                        kpi_category  = "general",
                        display_format= "{value:.0f} days",
                    ))
                except Exception:
                    pass

        # ── KPI 7: Category count ─────────────────────────────────────────
        if category_cols:
            cat_col = category_cols[0]
            cat_count = _query_scalar(
                f'SELECT COUNT(DISTINCT "{cat_col}") FROM "{table_name}"',
                engine
            )
            if cat_count is not None:
                label = _humanise_column_name(cat_col)
                all_kpis.append(KPIResult(
                    kpi_name      = f"Unique {label}s",
                    kpi_value     = float(cat_count),
                    kpi_unit      = "count",
                    kpi_category  = "general",
                    display_format= "{value:.0f}",
                ))

        # ── KPI 8: Null rate across table ─────────────────────────────────
        total_cells  = total * len(columns) if total else 0
        total_nulls  = sum(col["null_count"] for col in columns)
        if total_cells > 0:
            null_rate = (total_nulls / total_cells) * 100
            all_kpis.append(KPIResult(
                kpi_name      = "Data Completeness",
                kpi_value     = round(100 - null_rate, 1),
                kpi_unit      = "percent",
                kpi_category  = "general",
                display_format= "{value:.1f}%",
            ))

    # Save all KPIs to database
    _save_kpis(session_id, all_kpis, engine)

    logger.info(
        "Calculated %d KPI(s) for session '%s'.", len(all_kpis), session_id
    )
    return all_kpis


def _save_kpis(
    session_id : str,
    kpis       : list[KPIResult],
    engine     : Engine,
) -> None:
    """Save KPI results to the kpi_results table."""
    if not kpis:
        return

    rows = [
        {
            "session_id"    : session_id,
            "kpi_name"      : k.kpi_name,
            "kpi_value"     : k.kpi_value,
            "kpi_unit"      : k.kpi_unit,
            "kpi_category"  : k.kpi_category,
            "display_format": k.display_format,
        }
        for k in kpis
    ]

    import pandas as pd
    df = pd.DataFrame(rows)
    df.to_sql(
        name      = "kpi_results",
        con       = engine,
        if_exists = "append",
        index     = False,
    )
    logger.info("Saved %d KPI(s) to kpi_results table.", len(rows))


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _query_scalar(sql: str, engine: Engine):
    """Run a SQL query and return the single scalar result. Returns None on error."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.warning("KPI query failed: %s | Error: %s", sql[:80], e)
        return None


def _query_row(sql: str, engine: Engine):
    """Run a SQL query and return the first row. Returns None on error."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            return result.fetchone()
    except Exception as e:
        logger.warning("KPI row query failed: %s | Error: %s", sql[:80], e)
        return None


def _pick_best_column(columns: list[str], preferred_keywords: list[str]) -> str:
    """
    From a list of columns, pick the one whose name contains a preferred keyword.
    Falls back to the first column if no keyword matches.

    Example:
        columns = ['freight_value', 'price', 'order_total']
        keywords = ['revenue', 'total', 'price']
        → returns 'price' (first keyword match found)
    """
    for keyword in preferred_keywords:
        for col in columns:
            if keyword in col.lower():
                return col
    return columns[0]


def _humanise_column_name(col_name: str) -> str:
    """
    Convert a snake_case column name to a readable label.
    Examples:
        'customer_id'  → 'Customer'
        'product_id'   → 'Product'
        'order_status' → 'Order Status'
    """
    # Remove common suffixes
    import re
    name = re.sub(r'[_\-]?(id|key|code|ref)$', '', col_name, flags=re.IGNORECASE)
    # Replace underscores with spaces and title case
    name = name.replace('_', ' ').strip().title()
    return name if name else col_name