"""
chart_selector.py
-----------------
Selects BUSINESS-RELEVANT charts for any uploaded dataset.

Core philosophy:
    - Every chart must answer a real business question
    - Never chart dimension/metadata columns (zip codes, weights, lengths)
    - Never box plot columns that are not business metrics
    - Prioritise cross-table insights when relationships exist
    - Cap charts per table to avoid overwhelming the dashboard
    - Dedup across tables — same concept from two tables = one chart

Business questions this engine answers:
    "How is revenue trending over time?"         → line chart
    "Which categories drive the most revenue?"   → bar / treemap
    "What is the order status breakdown?"        → pie chart
    "How do two metrics correlate?"              → scatter
    "What does the distribution look like?"      → histogram (currency only)
    "How do products/sellers compare?"           → bar chart
"""

import logging
import re
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ── Column blocklist — NEVER use these as chart axes ──────────────────────────
BLOCKED_COLUMNS = {
    # Product dimensions — not business metrics
    "product_name_lenght", "product_name_length",
    "product_description_lenght", "product_description_length",
    "product_photos_qty",
    "product_weight_g", "product_length_cm",
    "product_height_cm", "product_width_cm",
    # Geographic codes — too granular, not meaningful as chart axes
    "zip_code", "zip_code_prefix",
    "customer_zip_code_prefix", "seller_zip_code_prefix",
    "geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
    # Row identifiers — never chart these
    "order_item_id", "review_id",
}

# ── Category columns that are meaningful for grouping ─────────────────────────
GOOD_CATEGORY_HINTS = [
    "category", "status", "type", "segment", "region",
    "state", "city", "product_category",
]

# ── Category columns that are NOT useful for charting ─────────────────────────
BAD_CATEGORY_HINTS = [
    "zip", "code", "prefix", "geo", "uuid", "hash",
]

# ── Funnel keywords — these trigger funnel charts ─────────────────────────────
FUNNEL_KEYWORDS = ["status", "stage", "step", "phase", "level", "state"]

# ── Thresholds ────────────────────────────────────────────────────────────────
PIE_MAX_CATEGORIES    = 8    # more than this → bar chart
TREEMAP_MIN_CATEGORIES= 11   # more than this → treemap instead of bar
MAX_CHARTS_PER_TABLE  = 8    # prevent one table dominating the dashboard
MAX_TOTAL_CHARTS      = 25   # global cap


@dataclass
class ChartConfig:
    chart_type      : str
    chart_title     : str
    source_table    : str
    x_column        : str
    y_column        : str | None = None
    group_by_column : str | None = None
    aggregation     : str = "sum"
    chart_order     : int = 0
    rationale       : str = ""
    priority        : int = 5   # 1 = most important, higher = less important


def select_charts(
    session_id     : str,
    schema_profiles: dict[str, list[dict]],
    engine         : Engine,
    relationships  : list[dict] = None
) -> list[ChartConfig]:
    """
    Select business-relevant charts for all tables in a session.
    Deduplicates, prioritises, and caps the total number of charts.
    """
    all_charts : list[ChartConfig] = []

    for table_name, columns in schema_profiles.items():
        table_charts = _select_for_table(table_name, columns, engine)
        all_charts.extend(table_charts)
    if relationships:
        cross = _select_cross_table_charts(schema_profiles, relationships, engine)
        all_charts.extend(cross)

    # ── Global deduplication by title ────────────────────────────────────────
    seen_titles : set[str] = set()
    unique_charts : list[ChartConfig] = []
    for chart in all_charts:
        key = chart.chart_title.lower().strip()
        if key not in seen_titles:
            seen_titles.add(key)
            unique_charts.append(chart)

    # ── Sort by priority, then cap ────────────────────────────────────────────
    unique_charts.sort(key=lambda c: c.priority)
    unique_charts = unique_charts[:MAX_TOTAL_CHARTS]

    # ── Re-number chart_order after sorting ───────────────────────────────────
    for i, chart in enumerate(unique_charts):
        chart.chart_order = i + 1

    _save_charts(session_id, unique_charts, engine)

    logger.info("Selected %d chart(s) for session '%s'.", len(unique_charts), session_id)
    return unique_charts


# ─────────────────────────────────────────────────────────────────────────────
# Per-table chart selection
# ─────────────────────────────────────────────────────────────────────────────

def _select_for_table(
    table_name: str,
    columns   : list[dict],
    engine    : Engine,
) -> list[ChartConfig]:
    """Generate chart candidates for one table. Returns at most MAX_CHARTS_PER_TABLE."""

    # Filter out blocked columns
    clean_cols = [
        col for col in columns
        if col["column_name"] not in BLOCKED_COLUMNS
    ]
    type_map = {col["column_name"]: col["detected_type"] for col in clean_cols}

    currency_cols = [c for c, t in type_map.items() if t == "currency"]
    datetime_cols = [c for c, t in type_map.items() if t == "datetime"]
    id_cols       = [c for c, t in type_map.items() if t == "id"]
    category_cols = _filter_good_categories(
        [c for c, t in type_map.items() if t == "category"]
    )
    numeric_cols  = [
        c for c, t in type_map.items()
        if t == "numeric" and c not in BLOCKED_COLUMNS
    ]

    # Query unique counts for all category columns upfront
    cat_unique_counts = _get_unique_counts(table_name, category_cols, engine)

    charts: list[ChartConfig] = []

    # ── P1: Revenue trend over time (most important chart) ────────────────────
    if datetime_cols and currency_cols:
        date_col = _pick(datetime_cols, ["purchase", "order", "created", "date", "timestamp"])
        rev_col  = _pick(currency_cols, ["revenue", "total", "amount", "payment", "price", "value"])
        charts.append(ChartConfig(
            chart_type  = "line",
            chart_title = f"{_label(rev_col)} Over Time",
            source_table= table_name,
            x_column    = date_col,
            y_column    = rev_col,
            aggregation = "sum",
            rationale   = f"datetime + currency → revenue trend line chart",
            priority    = 1,
        ))

    # ── P2: Revenue by best category ──────────────────────────────────────────
    if category_cols and currency_cols:
        rev_col = _pick(currency_cols, ["revenue", "total", "amount", "payment", "price", "value"])

        # Pick the most business-meaningful category
        best_cat = _pick_best_category(category_cols, cat_unique_counts)
        if best_cat:
            unique_count = cat_unique_counts.get(best_cat, 999)
            if unique_count > TREEMAP_MIN_CATEGORIES:
                charts.append(ChartConfig(
                    chart_type  = "treemap",
                    chart_title = f"{_label(rev_col)} by {_label(best_cat)}",
                    source_table= table_name,
                    x_column    = best_cat,
                    y_column    = rev_col,
                    aggregation = "sum",
                    rationale   = f"category '{best_cat}' ({unique_count} values) + currency → treemap",
                    priority    = 2,
                ))
            else:
                charts.append(ChartConfig(
                    chart_type  = "bar",
                    chart_title = f"{_label(rev_col)} by {_label(best_cat)}",
                    source_table= table_name,
                    x_column    = best_cat,
                    y_column    = rev_col,
                    aggregation = "sum",
                    rationale   = f"category '{best_cat}' ({unique_count} values) + currency → bar chart",
                    priority    = 2,
                ))

            # Second meaningful category (if different from first)
            remaining_cats = [c for c in category_cols if c != best_cat]
            second_cat = _pick_best_category(remaining_cats, cat_unique_counts)
            if second_cat and len(charts) < MAX_CHARTS_PER_TABLE:
                unique_count2 = cat_unique_counts.get(second_cat, 999)
                if unique_count2 > TREEMAP_MIN_CATEGORIES:
                    charts.append(ChartConfig(
                        chart_type  = "treemap",
                        chart_title = f"{_label(rev_col)} by {_label(second_cat)}",
                        source_table= table_name,
                        x_column    = second_cat,
                        y_column    = rev_col,
                        aggregation = "sum",
                        rationale   = f"category '{second_cat}' ({unique_count2} values) + currency → treemap",
                        priority    = 3,
                    ))
                else:
                    charts.append(ChartConfig(
                        chart_type  = "bar",
                        chart_title = f"{_label(rev_col)} by {_label(second_cat)}",
                        source_table= table_name,
                        x_column    = second_cat,
                        y_column    = rev_col,
                        aggregation = "sum",
                        rationale   = f"category '{second_cat}' ({unique_count2} values) + currency → bar chart",
                        priority    = 3,
                    ))

    # ── P3: Order status or meaningful status distribution ────────────────────
    status_cols = [
        c for c in category_cols
        if any(kw in c.lower() for kw in ["status", "state", "type"])
        and cat_unique_counts.get(c, 999) <= PIE_MAX_CATEGORIES
    ]
    if status_cols and len(charts) < MAX_CHARTS_PER_TABLE:
        status_col = status_cols[0]
        unique_count = cat_unique_counts.get(status_col, 0)
        if 2 <= unique_count <= PIE_MAX_CATEGORIES:
            charts.append(ChartConfig(
                chart_type  = "pie",
                chart_title = f"{_label(status_col)} Distribution",
                source_table= table_name,
                x_column    = status_col,
                aggregation = "count",
                rationale   = f"status column '{status_col}' ({unique_count} values) → pie chart",
                priority    = 3,
            ))

    # ── P4: Revenue histogram (distribution of individual transaction values) ─
    if currency_cols and not datetime_cols and len(charts) < MAX_CHARTS_PER_TABLE:
        rev_col = _pick(currency_cols, ["price", "value", "amount", "revenue", "total"])
        charts.append(ChartConfig(
            chart_type  = "histogram",
            chart_title = f"{_label(rev_col)} Distribution",
            source_table= table_name,
            x_column    = rev_col,
            aggregation = "count",
            rationale   = f"currency column '{rev_col}' → value distribution histogram",
            priority    = 4,
        ))

    # ── P4: Revenue scatter — price vs freight (if both exist) ───────────────
    freight_cols = [c for c in currency_cols if "freight" in c.lower() or "shipping" in c.lower()]
    price_cols   = [c for c in currency_cols if "price" in c.lower() or "amount" in c.lower()]
    if freight_cols and price_cols and len(charts) < MAX_CHARTS_PER_TABLE:
        charts.append(ChartConfig(
            chart_type  = "scatter",
            chart_title = f"{_label(price_cols[0])} vs {_label(freight_cols[0])}",
            source_table= table_name,
            x_column    = price_cols[0],
            y_column    = freight_cols[0],
            aggregation = "none",
            rationale   = f"price vs freight → correlation scatter plot",
            priority    = 4,
        ))

    # ── P5: Correlation heatmap — only for 3+ BUSINESS numeric columns ────────
    # Exclude dimension columns explicitly
    business_numeric = [
        c for c in numeric_cols
        if not any(x in c.lower() for x in
                   ["weight", "length", "height", "width", "lenght",
                    "qty", "photos", "zip", "code", "prefix"])
        and c not in BLOCKED_COLUMNS
    ]
    if len(business_numeric) >= 3 and len(charts) < MAX_CHARTS_PER_TABLE:
        charts.append(ChartConfig(
            chart_type  = "heatmap",
            chart_title = "Numeric Correlation Matrix",
            source_table= table_name,
            x_column    = ",".join(business_numeric[:6]),
            aggregation = "correlation",
            rationale   = f"{len(business_numeric)} business numeric columns → correlation heatmap",
            priority    = 5,
        ))

    # ── P5: Grouped line — revenue over time by category ─────────────────────
    if datetime_cols and currency_cols and category_cols and len(charts) < MAX_CHARTS_PER_TABLE:
        date_col = _pick(datetime_cols, ["purchase", "order", "created", "date", "timestamp"])
        rev_col  = _pick(currency_cols, ["revenue", "total", "amount", "payment", "price"])
        # Only group by categories with ≤ 6 values — more becomes unreadable
        small_cats = [
            c for c in category_cols
            if 2 <= cat_unique_counts.get(c, 999) <= 6
            and any(kw in c.lower() for kw in ["status", "type", "category", "segment"])
        ]
        if small_cats:
            group_cat = small_cats[0]
            charts.append(ChartConfig(
                chart_type      = "line",
                chart_title     = f"{_label(rev_col)} by {_label(group_cat)} Over Time",
                source_table    = table_name,
                x_column        = date_col,
                y_column        = rev_col,
                group_by_column = group_cat,
                aggregation     = "sum",
                rationale       = f"datetime + currency + '{group_cat}' (≤6 values) → grouped line chart",
                priority        = 4,
            ))

    # Cap per table
    return charts[:MAX_CHARTS_PER_TABLE]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _filter_good_categories(category_cols: list[str]) -> list[str]:
    """
    Remove category columns that are not useful for charting.
    Keeps: status, type, category_name, region, state
    Removes: zip_code, code, prefix, geo identifiers
    """
    result = []
    for col in category_cols:
        col_lower = col.lower()
        # Skip bad categories
        if any(bad in col_lower for bad in BAD_CATEGORY_HINTS):
            continue
        if col in BLOCKED_COLUMNS:
            continue
        result.append(col)
    return result


def _pick_best_category(
    category_cols    : list[str],
    cat_unique_counts: dict[str, int],
) -> str | None:
    """
    Pick the most business-meaningful category column.
    Prefers: product_category_name, order_status, seller_state
    Avoids: city (too many values), zip_code, state abbreviations
    """
    if not category_cols:
        return None

    # Priority 1: explicit category name columns
    for hint in ["category_name", "category", "product_category"]:
        for col in category_cols:
            if hint in col.lower():
                return col

    # Priority 2: status/type columns with reasonable cardinality
    for col in category_cols:
        count = cat_unique_counts.get(col, 999)
        if any(kw in col.lower() for kw in ["status", "type", "segment"]) and count <= 20:
            return col

    # Priority 3: state/region (useful geographic grouping)
    for col in category_cols:
        count = cat_unique_counts.get(col, 999)
        if any(kw in col.lower() for kw in ["state", "region"]) and count <= 50:
            return col

    # Priority 4: city (skip if too many values)
    for col in category_cols:
        count = cat_unique_counts.get(col, 999)
        if "city" in col.lower() and count <= 30:
            return col

    # Fallback: pick lowest cardinality column (most useful for grouping)
    valid = [(col, cat_unique_counts.get(col, 999)) for col in category_cols]
    valid.sort(key=lambda x: x[1])
    return valid[0][0] if valid else None


def _get_unique_counts(
    table_name   : str,
    category_cols: list[str],
    engine       : Engine,
) -> dict[str, int]:
    """Query actual unique count per category column from PostgreSQL."""
    counts: dict[str, int] = {}
    if not category_cols:
        return counts
    try:
        with engine.connect() as conn:
            for col in category_cols:
                row = conn.execute(
                    text(f'SELECT COUNT(DISTINCT "{col}") FROM "{table_name}"')
                ).fetchone()
                counts[col] = int(row[0]) if row else 999
    except Exception as e:
        logger.warning("Could not get unique counts for '%s': %s", table_name, e)
        # Default to 999 so pie chart is NOT selected for unknown cardinality
        for col in category_cols:
            counts.setdefault(col, 999)
    return counts


def _save_charts(
    session_id: str,
    charts    : list[ChartConfig],
    engine    : Engine,
) -> None:
    if not charts:
        return
    # Clear existing charts for this session
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM chart_configs WHERE session_id = :sid"),
                {"sid": session_id}
            )
    except Exception as e:
        logger.warning("Could not clear old chart configs: %s", e)

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
    pd.DataFrame(rows).to_sql(
        name="chart_configs", con=engine, if_exists="append", index=False
    )
    logger.info("Saved %d chart config(s) to chart_configs.", len(rows))


def _pick(columns: list[str], keywords: list[str]) -> str:
    for kw in keywords:
        for col in columns:
            if kw in col.lower():
                return col
    return columns[0]


def _label(col_name: str) -> str:
    name = re.sub(r'[_\-]?(id|key|code|ref)$', '', col_name, flags=re.IGNORECASE)
    return name.replace('_', ' ').strip().title()

def _select_cross_table_charts(
    schema_profiles: dict[str, list[dict]],
    relationships  : list[dict],
    engine         : Engine,
) -> list[ChartConfig]:
    """
    Generate charts that JOIN related tables.
    e.g. orders (datetime) + order_items (currency) → revenue over time

    This is why Olist generates few charts per table individually —
    the datetime and currency are in DIFFERENT tables.
    """
    cross_charts = []

    # Find tables with datetime cols and tables with currency cols
    datetime_tables = {}   # {table_name: [datetime_cols]}
    currency_tables = {}   # {table_name: [currency_cols]}

    for table_name, columns in schema_profiles.items():
        type_map = {c["column_name"]: c["detected_type"] for c in columns}
        dt_cols  = [c for c, t in type_map.items() if t == "datetime"]
        cur_cols = [c for c, t in type_map.items() if t == "currency"
                    and c not in BLOCKED_COLUMNS]
        cat_cols = _filter_good_categories(
            [c for c, t in type_map.items() if t == "category"]
        )
        if dt_cols:
            datetime_tables[table_name] = {"datetime": dt_cols, "category": cat_cols}
        if cur_cols:
            currency_tables[table_name] = {"currency": cur_cols, "category": cat_cols}

    # Find pairs connected by a relationship
    for rel in relationships:
        from_t = rel.get("from_table", "")
        to_t   = rel.get("to_table", "")
        from_c = rel.get("from_column", "")
        to_c   = rel.get("to_column", "")

        # Case: from_table has datetime, to_table has currency
        if from_t in datetime_tables and to_t in currency_tables:
            dt_t  = from_t
            cur_t = to_t
            join_col_dt  = from_c
            join_col_cur = to_c
        elif to_t in datetime_tables and from_t in currency_tables:
            dt_t  = to_t
            cur_t = from_t
            join_col_dt  = to_c
            join_col_cur = from_c
        else:
            continue

        date_col = _pick(datetime_tables[dt_t]["datetime"],
                         ["purchase", "order", "created", "date", "timestamp"])
        rev_col  = _pick(currency_tables[cur_t]["currency"],
                         ["price", "value", "amount", "revenue", "total", "payment"])

        # Cross-table revenue over time
        sql = f"""
            SELECT
                DATE_TRUNC('month', t1."{date_col}"::timestamp) AS period,
                SUM(t2."{rev_col}")                              AS value
            FROM "{dt_t}" t1
            JOIN "{cur_t}" t2 ON t1."{join_col_dt}" = t2."{join_col_cur}"
            WHERE t1."{date_col}" IS NOT NULL AND t2."{rev_col}" IS NOT NULL
            GROUP BY period ORDER BY period
            LIMIT 30
        """

        # Verify the join works before adding the chart
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text(sql))
                rows   = result.fetchall()
                if rows:
                    # Store the SQL so chart_generator can use it directly
                    cross_charts.append(ChartConfig(
                        chart_type  = "line",
                        chart_title = f"{_label(rev_col)} Over Time",
                        source_table= rel["view_name"],
                        x_column    = date_col,
                        y_column    = rev_col,
                        aggregation = "sum",
                        rationale   = f"cross-table: {dt_t}.{date_col} + {cur_t}.{rev_col} joined on {join_col_dt}={join_col_cur}",
                        priority    = 1,
                    ))
        except Exception as e:
            logger.debug("Cross-table chart failed: %s", e)

    return cross_charts