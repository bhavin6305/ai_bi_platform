"""
sql_views.py
------------
Dynamically creates analytical SQL views for any uploaded dataset.
Views created per session for the AI chatbot to query.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def create_analytical_views(
    session_id     : str,
    schema_profiles: dict[str, list[dict]],
    relationships  : list[dict],
    engine         : Engine,
) -> list[str]:
    """Create analytical SQL views for all tables in a session."""
    short_id      = session_id.replace("-", "")[:8]
    views_created = []

    for table_name, columns in schema_profiles.items():
        type_map = {col["column_name"]: col["detected_type"] for col in columns}

        currency_cols = [c for c, t in type_map.items() if t == "currency"]
        datetime_cols = [c for c, t in type_map.items() if t == "datetime"]
        category_cols = [c for c, t in type_map.items() if t == "category"]
        id_cols       = [c for c, t in type_map.items() if t == "id"]

        # ── View 1: Time series ────────────────────────────────────────────
        if datetime_cols and currency_cols:
            date_col  = _pick_col(datetime_cols, ["date", "created", "purchase", "timestamp"])
            val_col   = _pick_col(currency_cols, ["revenue", "total", "amount", "price", "value"])
            view_name = f"v_{short_id}_time_series"
            sql = f"""
CREATE OR REPLACE VIEW "{view_name}" AS
SELECT
    DATE_TRUNC('month', "{date_col}"::timestamp) AS period,
    COUNT(*)                                      AS record_count,
    ROUND(SUM("{val_col}")::numeric, 2)           AS total_value,
    ROUND(AVG("{val_col}")::numeric, 2)           AS avg_value,
    ROUND(MIN("{val_col}")::numeric, 2)           AS min_value,
    ROUND(MAX("{val_col}")::numeric, 2)           AS max_value
FROM "{table_name}"
WHERE "{date_col}" IS NOT NULL AND "{val_col}" IS NOT NULL
GROUP BY period ORDER BY period;
            """.strip()
            if _execute_view(sql, view_name, engine):
                views_created.append(view_name)

        # ── View 2: Category breakdown ─────────────────────────────────────
        if category_cols and currency_cols:
            cat_col   = category_cols[0]
            val_col   = _pick_col(currency_cols, ["revenue", "total", "amount", "price", "value"])
            view_name = f"v_{short_id}_by_category"
            sql = f"""
CREATE OR REPLACE VIEW "{view_name}" AS
SELECT
    "{cat_col}"                         AS category,
    COUNT(*)                            AS record_count,
    ROUND(SUM("{val_col}")::numeric, 2) AS total_value,
    ROUND(AVG("{val_col}")::numeric, 2) AS avg_value,
    ROUND(SUM("{val_col}") * 100.0 / NULLIF(SUM(SUM("{val_col}")) OVER (), 0), 2) AS value_share_pct
FROM "{table_name}"
WHERE "{cat_col}" IS NOT NULL AND "{val_col}" IS NOT NULL
GROUP BY "{cat_col}" ORDER BY total_value DESC;
            """.strip()
            if _execute_view(sql, view_name, engine):
                views_created.append(view_name)

        # ── View 3: Entity summary ─────────────────────────────────────────
        if id_cols and currency_cols:
            id_col    = _pick_col(id_cols, ["customer", "user", "client", "entity"])
            val_col   = _pick_col(currency_cols, ["revenue", "total", "amount", "price", "value"])
            view_name = f"v_{short_id}_entity_summary"
            sql = f"""
CREATE OR REPLACE VIEW "{view_name}" AS
SELECT
    "{id_col}"                          AS entity_id,
    COUNT(*)                            AS transaction_count,
    ROUND(SUM("{val_col}")::numeric, 2) AS total_value,
    ROUND(AVG("{val_col}")::numeric, 2) AS avg_value,
    ROUND(MIN("{val_col}")::numeric, 2) AS min_value,
    ROUND(MAX("{val_col}")::numeric, 2) AS max_value
FROM "{table_name}"
WHERE "{id_col}" IS NOT NULL AND "{val_col}" IS NOT NULL
GROUP BY "{id_col}" ORDER BY total_value DESC;
            """.strip()
            if _execute_view(sql, view_name, engine):
                views_created.append(view_name)

        # ── View 4: Summary (DROP first to avoid column mismatch error) ────
        view_name = f"v_{short_id}_summary"
        col_list  = ", ".join(
            f'COUNT("{col["column_name"]}") AS "{col["column_name"]}_count"'
            for col in columns[:10]
        )
        # DROP separately first — then CREATE — avoids the two-statement error
        _execute_view(f'DROP VIEW IF EXISTS "{view_name}";', f"drop_{view_name}", engine)
        sql = f"""
CREATE VIEW "{view_name}" AS
SELECT COUNT(*) AS total_rows, {col_list} FROM "{table_name}";
        """.strip()
        if _execute_view(sql, view_name, engine):
            views_created.append(view_name)

    logger.info("Created %d analytical view(s) for session '%s'.", len(views_created), session_id)
    return views_created


def _pick_col(columns: list[str], preferred_keywords: list[str]) -> str:
    for keyword in preferred_keywords:
        for col in columns:
            if keyword in col.lower():
                return col
    return columns[0]


def _execute_view(sql: str, view_name: str, engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        return True
    except Exception as e:
        logger.error("Failed to create view '%s': %s", view_name, e)
        return False