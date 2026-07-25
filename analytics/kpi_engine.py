"""
kpi_engine.py
-------------
Detects and calculates BUSINESS-RELEVANT KPIs for any uploaded dataset.

Priority system:
    TIER 1 — Business KPIs (always show if applicable):
        Total Revenue, Total Orders, Avg Order Value, Total Customers,
        Unique Products, Revenue per Customer, Repeat Purchase Rate

    TIER 2 — Operational KPIs (show if no better alternative):
        Date range span, Category count, Max transaction value

    TIER 3 — Data quality metrics (NEVER shown as dashboard KPIs):
        Data Completeness, Null rates — these belong in the upload page only

Rules:
    - Never show "Total Records" if a better count KPI exists (e.g. Total Orders)
    - Never show "Data Completeness" on the dashboard
    - Never show dimension metrics (product_length, product_weight) as KPIs
    - Deduplicate across tables — if both orders and order_items have revenue,
      pick the one with the higher total (more complete)
    - Max 8 KPIs shown — prioritize Tier 1
"""

import logging
import re
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ── Column name blocklist — these should NEVER become KPIs ────────────────────
# Dimension/metadata columns that are not business metrics
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

# ── Columns that hint at business-meaningful IDs ───────────────────────────────
CUSTOMER_HINTS = ["customer", "user", "client", "buyer", "member", "subscriber"]
ORDER_HINTS    = ["order", "transaction", "invoice", "sale", "purchase"]
PRODUCT_HINTS  = ["product", "item", "sku", "good", "merchandise"]
SELLER_HINTS   = ["seller", "vendor", "merchant", "supplier", "store"]

# ── Max KPIs to return ─────────────────────────────────────────────────────────
MAX_KPIS = 10


@dataclass
class KPIResult:
    kpi_name      : str
    kpi_value     : float
    kpi_unit      : str      # currency | count | percent | days | ratio
    kpi_category  : str      # sales | customer | inventory | general
    display_format: str
    tier          : int = 2  # 1 = most important, 3 = least — used for sorting


def calculate_kpis(
    session_id     : str,
    schema_profiles: dict[str, list[dict]],
    engine         : Engine,
) -> list[KPIResult]:
    """
    Calculate business-relevant KPIs across all tables in a session.
    Returns deduplicated, prioritised list of KPIResult objects.
    Also saves to kpi_results table.
    """
    all_kpis: list[KPIResult] = []

    for table_name, columns in schema_profiles.items():
        type_map = {
            col["column_name"]: col["detected_type"]
            for col in columns
            if col["column_name"] not in BLOCKED_METRIC_COLUMNS
        }

        currency_cols = [c for c, t in type_map.items() if t == "currency"]
        datetime_cols = [c for c, t in type_map.items() if t == "datetime"]
        id_cols       = [c for c, t in type_map.items() if t == "id"]
        category_cols = [c for c, t in type_map.items() if t == "category"]
        numeric_cols  = [
            c for c, t in type_map.items()
            if t == "numeric" and c not in BLOCKED_METRIC_COLUMNS
        ]

        # ── TIER 1: Revenue KPIs ───────────────────────────────────────────
        if currency_cols:
            rev_col = _pick_best(currency_cols,
                ["revenue", "total", "amount", "payment", "price", "sales", "value"])

            total_rev = _scalar(f'SELECT SUM("{rev_col}") FROM "{table_name}" '
                                f'WHERE "{rev_col}" IS NOT NULL AND "{rev_col}" > 0', engine)
            if total_rev and total_rev > 0:
                all_kpis.append(KPIResult(
                    kpi_name      = "Total Revenue",
                    kpi_value     = round(float(total_rev), 2),
                    kpi_unit      = "currency",
                    kpi_category  = "sales",
                    display_format= "${value:,.2f}",
                    tier          = 1,
                ))

                avg_val = _scalar(f'SELECT AVG("{rev_col}") FROM "{table_name}" '
                                  f'WHERE "{rev_col}" IS NOT NULL AND "{rev_col}" > 0', engine)
                if avg_val:
                    all_kpis.append(KPIResult(
                        kpi_name      = "Avg Order Value",
                        kpi_value     = round(float(avg_val), 2),
                        kpi_unit      = "currency",
                        kpi_category  = "sales",
                        display_format= "${value:,.2f}",
                        tier          = 1,
                    ))

                max_val = _scalar(f'SELECT MAX("{rev_col}") FROM "{table_name}" '
                                  f'WHERE "{rev_col}" IS NOT NULL', engine)
                if max_val:
                    all_kpis.append(KPIResult(
                        kpi_name      = "Max Transaction",
                        kpi_value     = round(float(max_val), 2),
                        kpi_unit      = "currency",
                        kpi_category  = "sales",
                        display_format= "${value:,.2f}",
                        tier          = 2,
                    ))

        # ── TIER 1: Order / transaction count ─────────────────────────────
        order_id_cols = [c for c in id_cols if _matches(c, ORDER_HINTS)]
        if order_id_cols:
            order_col   = order_id_cols[0]
            order_count = _scalar(f'SELECT COUNT(DISTINCT "{order_col}") FROM "{table_name}"', engine)
            if order_count:
                all_kpis.append(KPIResult(
                    kpi_name      = "Total Orders",
                    kpi_value     = float(order_count),
                    kpi_unit      = "count",
                    kpi_category  = "sales",
                    display_format= "{value:,.0f}",
                    tier          = 1,
                ))

        # ── TIER 1: Customer count ─────────────────────────────────────────
        cust_id_cols = [c for c in id_cols if _matches(c, CUSTOMER_HINTS)]
        if cust_id_cols:
            cust_col   = cust_id_cols[0]
            cust_count = _scalar(f'SELECT COUNT(DISTINCT "{cust_col}") FROM "{table_name}"', engine)
            if cust_count:
                all_kpis.append(KPIResult(
                    kpi_name      = "Total Customers",
                    kpi_value     = float(cust_count),
                    kpi_unit      = "count",
                    kpi_category  = "customer",
                    display_format= "{value:,.0f}",
                    tier          = 1,
                ))

        # ── TIER 1: Product count ─────────────────────────────────────────
        prod_id_cols = [c for c in id_cols if _matches(c, PRODUCT_HINTS)]
        if prod_id_cols:
            prod_col   = prod_id_cols[0]
            prod_count = _scalar(f'SELECT COUNT(DISTINCT "{prod_col}") FROM "{table_name}"', engine)
            if prod_count:
                all_kpis.append(KPIResult(
                    kpi_name      = "Total Products",
                    kpi_value     = float(prod_count),
                    kpi_unit      = "count",
                    kpi_category  = "inventory",
                    display_format= "{value:,.0f}",
                    tier          = 1,
                ))

        # ── TIER 1: Seller count ──────────────────────────────────────────
        seller_id_cols = [c for c in id_cols if _matches(c, SELLER_HINTS)]
        if seller_id_cols:
            seller_col   = seller_id_cols[0]
            seller_count = _scalar(f'SELECT COUNT(DISTINCT "{seller_col}") FROM "{table_name}"', engine)
            if seller_count:
                all_kpis.append(KPIResult(
                    kpi_name      = "Active Sellers",
                    kpi_value     = float(seller_count),
                    kpi_unit      = "count",
                    kpi_category  = "sales",
                    display_format= "{value:,.0f}",
                    tier          = 1,
                ))

        # ── TIER 1: Revenue per customer (cross-table metric) ─────────────
        # Only if both revenue and customer exist in the same table
        if currency_cols and cust_id_cols:
            rev_col  = _pick_best(currency_cols, ["revenue", "total", "amount", "payment", "price"])
            cust_col = cust_id_cols[0]
            rev_per_cust = _scalar(
                f'SELECT SUM("{rev_col}") / NULLIF(COUNT(DISTINCT "{cust_col}"), 0) '
                f'FROM "{table_name}" WHERE "{rev_col}" IS NOT NULL AND "{rev_col}" > 0',
                engine
            )
            if rev_per_cust and rev_per_cust > 0:
                all_kpis.append(KPIResult(
                    kpi_name      = "Revenue per Customer",
                    kpi_value     = round(float(rev_per_cust), 2),
                    kpi_unit      = "currency",
                    kpi_category  = "customer",
                    display_format= "${value:,.2f}",
                    tier          = 1,
                ))

        # ── TIER 2: Date range ────────────────────────────────────────────
        if datetime_cols:
            date_col = _pick_best(datetime_cols,
                ["purchase", "order", "created", "date", "timestamp", "start"])
            row = _row(f'SELECT MIN("{date_col}"), MAX("{date_col}") FROM "{table_name}"', engine)
            if row and row[0] and row[1]:
                try:
                    min_d  = pd.to_datetime(str(row[0]))
                    max_d  = pd.to_datetime(str(row[1]))
                    span   = (max_d - min_d).days
                    if span > 0:
                        all_kpis.append(KPIResult(
                            kpi_name      = "Data Time Span",
                            kpi_value     = float(span),
                            kpi_unit      = "days",
                            kpi_category  = "general",
                            display_format= "{value:.0f} days",
                            tier          = 2,
                        ))
                except Exception:
                    pass

        # ── TIER 2: Category diversity (only meaningful categories) ───────
        # e.g. product categories — not city/state/zip
        meaningful_cats = [
            c for c in category_cols
            if not any(x in c.lower() for x in
                       ["city", "state", "zip", "code", "prefix", "geo", "region_code"])
            and "category" in c.lower()
        ]
        if meaningful_cats:
            cat_col   = meaningful_cats[0]
            cat_count = _scalar(f'SELECT COUNT(DISTINCT "{cat_col}") FROM "{table_name}" '
                                f'WHERE "{cat_col}" IS NOT NULL', engine)
            if cat_count and cat_count > 1:
                label = _label(cat_col)
                all_kpis.append(KPIResult(
                    kpi_name      = f"Product Categories",
                    kpi_value     = float(cat_count),
                    kpi_unit      = "count",
                    kpi_category  = "inventory",
                    display_format= "{value:.0f}",
                    tier          = 2,
                ))

        # ── TIER 2: Order status breakdown (only if order_status exists) ──
        if "order_status" in type_map:
            delivered = _scalar(
                f"""SELECT COUNT(*) FROM "{table_name}"
                    WHERE LOWER("{{}}"order_status"{{}}" ::text) IN ('delivered', 'Delivered')"""
                .replace("{{}}", ""),
                engine
            )
            total_orders = _scalar(f'SELECT COUNT(*) FROM "{table_name}"', engine)
            if delivered and total_orders and total_orders > 0:
                rate = (delivered / total_orders) * 100
                all_kpis.append(KPIResult(
                    kpi_name      = "Delivery Rate",
                    kpi_value     = round(rate, 1),
                    kpi_unit      = "percent",
                    kpi_category  = "sales",
                    display_format= "{value:.1f}%",
                    tier          = 1,
                ))

    # ── Deduplicate by name — keep highest tier (lowest number) ──────────────
    seen: dict[str, KPIResult] = {}
    for k in all_kpis:
        if k.kpi_name not in seen or k.tier < seen[k.kpi_name].tier:
            seen[k.kpi_name] = k

    # ── Sort: Tier 1 first, then by category priority ────────────────────────
    category_order = {"sales": 0, "customer": 1, "inventory": 2, "general": 3}
    final_kpis = sorted(
        seen.values(),
        key=lambda k: (k.tier, category_order.get(k.kpi_category, 9))
    )

    # ── Cap at MAX_KPIS ───────────────────────────────────────────────────────
    final_kpis = final_kpis[:MAX_KPIS]

    _save_kpis(session_id, final_kpis, engine)

    logger.info("Calculated %d KPI(s) for session '%s'.", len(final_kpis), session_id)
    return final_kpis


def _save_kpis(session_id: str, kpis: list[KPIResult], engine: Engine) -> None:
    if not kpis:
        return
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM kpi_results WHERE session_id = :sid"),
                {"sid": session_id}
            )
    except Exception as e:
        logger.warning("Could not clear old KPIs: %s", e)

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
    pd.DataFrame(rows).to_sql(
        name="kpi_results", con=engine, if_exists="append", index=False
    )
    logger.info("Saved %d KPI(s) to kpi_results.", len(rows))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _scalar(sql: str, engine: Engine):
    try:
        with engine.connect() as conn:
            row = conn.execute(text(sql)).fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.debug("KPI scalar query failed: %s", e)
        return None


def _row(sql: str, engine: Engine):
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql)).fetchone()
    except Exception as e:
        logger.debug("KPI row query failed: %s", e)
        return None


def _pick_best(columns: list[str], keywords: list[str]) -> str:
    for kw in keywords:
        for col in columns:
            if kw in col.lower():
                return col
    return columns[0]


def _matches(col_name: str, hints: list[str]) -> bool:
    col_lower = col_name.lower()
    return any(h in col_lower for h in hints)


def _label(col_name: str) -> str:
    name = re.sub(r'[_\-]?(id|key|code|ref)$', '', col_name, flags=re.IGNORECASE)
    return name.replace('_', ' ').strip().title()