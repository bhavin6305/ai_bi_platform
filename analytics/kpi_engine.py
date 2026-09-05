"""
Business KPI engine.

Correctness rules:
- Never infer "revenue" from an arbitrary currency column.
- Average Order Value is revenue divided by distinct orders, not AVG(line values).
- Counts exclude NULL identifiers.
- Negative monetary values are preserved unless the metric explicitly requires
  positive-only values.
- Dashboard filters are applied to every KPI query whose source table contains
  the selected filter columns.
"""

from __future__ import annotations

import logging
import re
from contextvars import ContextVar
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from analytics.filters import DashboardFilters, filtered_query

logger = logging.getLogger(__name__)

BLOCKED_METRIC_COLUMNS = {
    "product_name_lenght", "product_name_length",
    "product_description_lenght", "product_description_length",
    "product_photos_qty",
    "product_weight_g", "product_length_cm",
    "product_height_cm", "product_width_cm",
    "zip_code", "zip_code_prefix", "customer_zip_code_prefix",
    "seller_zip_code_prefix", "geolocation_zip_code_prefix",
    "order_item_id",
}

CUSTOMER_HINTS = ["customer", "user", "client", "buyer", "member", "subscriber"]
ORDER_HINTS = ["order", "transaction", "invoice", "sale", "purchase"]
PRODUCT_HINTS = ["product", "item", "sku", "good", "merchandise"]
SELLER_HINTS = ["seller", "vendor", "merchant", "supplier", "store"]

# Strong semantic signals for a money metric that can reasonably represent
# revenue/transaction value. Generic "price" and "cost" are deliberately
# excluded because summing those across arbitrary tables is usually wrong.
REVENUE_EXACT_HINTS = (
    "revenue", "sales", "net_sales", "gross_sales", "gmv", "gross_merchandise_value",
    "payment_value", "order_total", "transaction_amount", "transaction_value",
    "sales_amount", "sales_value", "net_revenue", "gross_revenue",
)
REVENUE_WORD_HINTS = ("amount", "payment", "value", "total")
REVENUE_NEGATIVE_HINTS = (
    "cost", "price", "unit_price", "discount", "tax", "freight", "shipping",
    "weight", "margin", "profit", "fee", "commission",
)

MAX_KPIS = 10

_ACTIVE_FILTERS: ContextVar[DashboardFilters | None] = ContextVar(
    "active_dashboard_filters", default=None
)


@dataclass
class KPIResult:
    kpi_name: str
    kpi_value: float
    kpi_unit: str
    kpi_category: str
    display_format: str
    tier: int = 2


def calculate_kpis(
    session_id: str,
    schema_profiles: dict[str, list[dict]],
    engine: Engine,
    filters: DashboardFilters | None = None,
    persist: bool = True,
) -> list[KPIResult]:
    """Calculate, deduplicate, prioritise, and optionally persist KPIs."""
    token = _ACTIVE_FILTERS.set(filters)
    try:
        return _calculate_kpis(session_id, schema_profiles, engine, persist)
    finally:
        _ACTIVE_FILTERS.reset(token)


def _calculate_kpis(
    session_id: str,
    schema_profiles: dict[str, list[dict]],
    engine: Engine,
    persist: bool,
) -> list[KPIResult]:
    all_kpis: list[KPIResult] = []

    for table_name, columns in schema_profiles.items():
        type_map = {
            col["column_name"]: col["detected_type"]
            for col in columns
            if col.get("column_name") not in BLOCKED_METRIC_COLUMNS
        }

        currency_cols = [c for c, t in type_map.items() if t == "currency"]
        datetime_cols = [c for c, t in type_map.items() if t == "datetime"]
        id_cols = [c for c, t in type_map.items() if t == "id"]
        category_cols = [c for c, t in type_map.items() if t == "category"]

        order_col = _first_matching(id_cols, ORDER_HINTS)
        customer_col = _first_matching(id_cols, CUSTOMER_HINTS)
        product_col = _first_matching(id_cols, PRODUCT_HINTS)
        seller_col = _first_matching(id_cols, SELLER_HINTS)

        revenue_col = _pick_revenue_column(currency_cols, table_name, order_col)

        # Revenue is only emitted when the currency column has a defensible
        # business meaning. A random currency/decimal column is not revenue.
        if revenue_col:
            total_revenue = _scalar(
                f'SELECT SUM("{revenue_col}") '
                f'FROM "{table_name}" '
                f'WHERE "{revenue_col}" IS NOT NULL',
                engine,
            )
            if total_revenue is not None:
                all_kpis.append(KPIResult(
                    "Total Revenue",
                    round(float(total_revenue), 2),
                    "currency",
                    "sales",
                    "${value:,.2f}",
                    1,
                ))

                if order_col:
                    # AOV must be computed from the transaction grain. AVG()
                    # on line-item amounts is not an order-value calculation.
                    aov = _scalar(
                        f'SELECT SUM("{revenue_col}") / '
                        f'NULLIF(COUNT(DISTINCT "{order_col}"), 0) '
                        f'FROM "{table_name}" '
                        f'WHERE "{revenue_col}" IS NOT NULL '
                        f'AND "{order_col}" IS NOT NULL',
                        engine,
                    )
                    if aov is not None:
                        all_kpis.append(KPIResult(
                            "Avg Order Value",
                            float(aov),
                            "currency",
                            "sales",
                            "${value:,.2f}",
                            1,
                        ))

                    max_val = _scalar(
                        f'SELECT MAX("{revenue_col}") '
                        f'FROM "{table_name}" '
                        f'WHERE "{revenue_col}" IS NOT NULL '
                        f'AND "{order_col}" IS NOT NULL',
                        engine,
                    )
                    if max_val is not None:
                        all_kpis.append(KPIResult(
                            "Max Transaction",
                            round(float(max_val), 2),
                            "currency",
                            "sales",
                            "${value:,.2f}",
                            2,
                        ))

        if order_col:
            order_count = _scalar(
                f'SELECT COUNT(DISTINCT "{order_col}") '
                f'FROM "{table_name}" '
                f'WHERE "{order_col}" IS NOT NULL',
                engine,
            )
            if order_count is not None:
                all_kpis.append(KPIResult(
                    "Total Orders",
                    float(order_count),
                    "count",
                    "sales",
                    "{value:,.0f}",
                    1,
                ))

        if customer_col:
            customer_count = _scalar(
                f'SELECT COUNT(DISTINCT "{customer_col}") '
                f'FROM "{table_name}" '
                f'WHERE "{customer_col}" IS NOT NULL',
                engine,
            )
            if customer_count is not None:
                all_kpis.append(KPIResult(
                    "Total Customers",
                    float(customer_count),
                    "count",
                    "customer",
                    "{value:,.0f}",
                    1,
                ))

        if product_col:
            product_count = _scalar(
                f'SELECT COUNT(DISTINCT "{product_col}") '
                f'FROM "{table_name}" '
                f'WHERE "{product_col}" IS NOT NULL',
                engine,
            )
            if product_count is not None:
                all_kpis.append(KPIResult(
                    "Total Products",
                    float(product_count),
                    "count",
                    "inventory",
                    "{value:,.0f}",
                    1,
                ))

        if seller_col:
            seller_count = _scalar(
                f'SELECT COUNT(DISTINCT "{seller_col}") '
                f'FROM "{table_name}" '
                f'WHERE "{seller_col}" IS NOT NULL',
                engine,
            )
            if seller_count is not None:
                all_kpis.append(KPIResult(
                    "Active Sellers",
                    float(seller_count),
                    "count",
                    "sales",
                    "{value:,.0f}",
                    1,
                ))

        # This ratio is only emitted when both measures share the same table
        # grain. We do not manufacture a cross-table ratio here.
        if revenue_col and customer_col:
            revenue_per_customer = _scalar(
                f'SELECT SUM("{revenue_col}") / '
                f'NULLIF(COUNT(DISTINCT "{customer_col}"), 0) '
                f'FROM "{table_name}" '
                f'WHERE "{revenue_col}" IS NOT NULL '
                f'AND "{customer_col}" IS NOT NULL',
                engine,
            )
            if revenue_per_customer is not None:
                all_kpis.append(KPIResult(
                    "Revenue per Customer",
                    round(float(revenue_per_customer), 2),
                    "currency",
                    "customer",
                    "${value:,.2f}",
                    1,
                ))

        if datetime_cols:
            date_col = _pick_best(datetime_cols, [
                "purchase", "order", "created", "date", "timestamp", "start"
            ])
            row = _row(
                f'SELECT MIN("{date_col}"), MAX("{date_col}") '
                f'FROM "{table_name}"',
                engine,
            )
            if row and row[0] is not None and row[1] is not None:
                try:
                    min_d = pd.to_datetime(str(row[0]))
                    max_d = pd.to_datetime(str(row[1]))
                    span = max(0, (max_d - min_d).days)
                    if span > 0:
                        all_kpis.append(KPIResult(
                            "Data Time Span",
                            float(span),
                            "days",
                            "general",
                            "{value:.0f} days",
                            2,
                        ))
                except (TypeError, ValueError):
                    logger.debug("Could not calculate date span for %s", table_name)

        meaningful_cats = [
            c for c in category_cols
            if not any(x in c.lower() for x in (
                "city", "state", "zip", "code", "prefix", "geo", "region_code"
            ))
            and "category" in c.lower()
        ]
        if meaningful_cats:
            cat_col = meaningful_cats[0]
            cat_count = _scalar(
                f'SELECT COUNT(DISTINCT "{cat_col}") '
                f'FROM "{table_name}" '
                f'WHERE "{cat_col}" IS NOT NULL',
                engine,
            )
            if cat_count is not None and cat_count > 1:
                all_kpis.append(KPIResult(
                    "Product Categories",
                    float(cat_count),
                    "count",
                    "inventory",
                    "{value:.0f}",
                    2,
                ))

        status_col = _find_status_column(type_map)
        if status_col:
            delivered_condition = (
                f'LOWER(TRIM("{status_col}"::text)) = \'delivered\''
            )
            if order_col:
                delivered = _scalar(
                    f'SELECT COUNT(DISTINCT "{order_col}") '
                    f'FROM "{table_name}" '
                    f'WHERE "{order_col}" IS NOT NULL '
                    f'AND {delivered_condition}',
                    engine,
                )
                total_orders = _scalar(
                    f'SELECT COUNT(DISTINCT "{order_col}") '
                    f'FROM "{table_name}" '
                    f'WHERE "{order_col}" IS NOT NULL',
                    engine,
                )
            else:
                delivered = _scalar(
                    f'SELECT COUNT(*) FROM "{table_name}" '
                    f'WHERE {delivered_condition}',
                    engine,
                )
                total_orders = _scalar(
                    f'SELECT COUNT(*) FROM "{table_name}"',
                    engine,
                )

            if delivered is not None and total_orders and total_orders > 0:
                all_kpis.append(KPIResult(
                    "Delivery Rate",
                    round(float(delivered) / float(total_orders) * 100, 1),
                    "percent",
                    "sales",
                    "{value:.1f}%",
                    1,
                ))

    # Same-named KPIs from multiple tables are not interchangeable just because
    # one has a larger numeric total. Until provenance is persisted, retain the
    # first strongest semantic candidate rather than choosing by magnitude.
    seen: dict[str, KPIResult] = {}
    for kpi in all_kpis:
        existing = seen.get(kpi.kpi_name)
        if existing is None or kpi.tier < existing.tier:
            seen[kpi.kpi_name] = kpi

    category_order = {"sales": 0, "customer": 1, "inventory": 2, "general": 3}
    final_kpis = sorted(
        seen.values(),
        key=lambda k: (k.tier, category_order.get(k.kpi_category, 9), k.kpi_name),
    )[:MAX_KPIS]

    if persist:
        _save_kpis(session_id, final_kpis, engine)

    logger.info("Calculated %d KPI(s) for session '%s'.", len(final_kpis), session_id)
    return final_kpis


def _save_kpis(session_id: str, kpis: list[KPIResult], engine: Engine) -> None:
    """Replace a session's persisted KPI snapshot atomically."""
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM kpi_results WHERE session_id = :sid"),
            {"sid": session_id},
        )
        if not kpis:
            return
        conn.execute(
            text("""
                INSERT INTO kpi_results
                    (session_id, kpi_name, kpi_value, kpi_unit,
                     kpi_category, display_format)
                VALUES
                    (:session_id, :kpi_name, :kpi_value, :kpi_unit,
                     :kpi_category, :display_format)
            """),
            [
                {
                    "session_id": session_id,
                    "kpi_name": k.kpi_name,
                    "kpi_value": k.kpi_value,
                    "kpi_unit": k.kpi_unit,
                    "kpi_category": k.kpi_category,
                    "display_format": k.display_format,
                }
                for k in kpis
            ],
        )


def _scalar(sql: str, engine: Engine):
    try:
        sql, params = _apply_active_filters(sql, engine)
        with engine.connect() as conn:
            row = conn.execute(text(sql), params).fetchone()
            return row[0] if row else None
    except Exception as exc:
        logger.debug("KPI scalar query failed: %s", exc)
        return None


def _row(sql: str, engine: Engine):
    try:
        sql, params = _apply_active_filters(sql, engine)
        with engine.connect() as conn:
            return conn.execute(text(sql), params).fetchone()
    except Exception as exc:
        logger.debug("KPI row query failed: %s", exc)
        return None


def _apply_active_filters(sql: str, engine: Engine) -> tuple[str, dict[str, object]]:
    filters = _ACTIVE_FILTERS.get()
    if not filters or not filters.active:
        return sql, {}

    match = re.search(
        r'\bFROM\s+"([A-Za-z_][A-Za-z0-9_]*)"',
        sql,
        re.IGNORECASE,
    )
    if not match:
        return sql, {}

    return filtered_query(sql, match.group(1), filters, engine)


def _pick_revenue_column(
    columns: list[str],
    table_name: str,
    order_col: str | None,
) -> str | None:
    """Choose a money column only when its business meaning is defensible."""
    if not columns:
        return None

    table_lower = table_name.lower()
    transaction_context = bool(order_col) or any(
        hint in table_lower for hint in ("order", "transaction", "sale", "invoice", "payment")
    )

    scored: list[tuple[int, str]] = []
    for column in columns:
        name = column.lower()
        score = 0

        if name in REVENUE_EXACT_HINTS:
            score += 100
        for hint in REVENUE_EXACT_HINTS:
            if hint != name and hint in name:
                score += 35

        if any(hint in name for hint in REVENUE_NEGATIVE_HINTS):
            score -= 80

        if any(hint in name for hint in REVENUE_WORD_HINTS):
            score += 15

        # A bare "total", "amount", "payment", or "value" is only acceptable
        # in a transaction context. This prevents summing product prices,
        # inventory values, weights, etc. as "Total Revenue".
        if name in REVENUE_WORD_HINTS and not transaction_context:
            score -= 100

        if transaction_context:
            score += 10

        if score > 0:
            scored.append((score, column))

    if not scored:
        return None

    scored.sort(key=lambda item: (-item[0], item[1].lower()))
    return scored[0][1]


def _pick_best(columns: list[str], keywords: list[str]) -> str:
    for keyword in keywords:
        for column in columns:
            if keyword in column.lower():
                return column
    return columns[0]


def _first_matching(columns: list[str], hints: list[str]) -> str | None:
    for hint in hints:
        for column in columns:
            if hint in column.lower():
                return column
    return None


def _find_status_column(type_map: dict[str, str]) -> str | None:
    candidates = [
        name for name in type_map
        if "status" in name.lower()
        and (
            "order" in name.lower()
            or "delivery" in name.lower()
            or "shipment" in name.lower()
        )
    ]
    return candidates[0] if candidates else None
