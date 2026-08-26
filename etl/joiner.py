"""
joiner.py
---------
Join layer of the ETL pipeline.

After tables are cleaned and loaded into PostgreSQL, this module creates
SQL VIEWs that represent the joins between related tables.

Why SQL VIEWs instead of physical joined tables?
    - Views are dynamic — they always reflect the latest data
    - No data duplication in storage
    - The AI chatbot can query views just like tables
    - Power BI can connect to views directly
    - Professional pattern used in real data warehouses
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Output data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class JoinResult:
    """Result of the join step for one session."""
    session_id       : str
    views_created    : list[str] = field(default_factory=list)
    master_view_name : str = None
    join_log         : list[str] = field(default_factory=list)
    errors           : list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def create_join_views(
    session_id    : str,
    relationships : list[dict],
    engine        : Engine,
) -> JoinResult:
    """
    Create SQL VIEWs in PostgreSQL for all detected relationships.

    Also creates one master VIEW that joins all tables together
    for use by the KPI engine and AI chatbot.
    """
    result = JoinResult(session_id=session_id)

    if not relationships:
        logger.info("No relationships detected for session '%s' — no views to create.", session_id)
        result.join_log.append("No relationships detected — single table session.")
        return result

    logger.info(
        "Creating SQL VIEWs for %d relationship(s) in session '%s'.",
        len(relationships), session_id
    )

    # ── Step 1: Create one VIEW per relationship ───────────────────────────
    for rel in relationships:
        if rel["confidence"] == "low":
            result.join_log.append(
                f"Skipped low-confidence relationship: "
                f"{rel['from_table']}.{rel['from_column']} → "
                f"{rel['to_table']}.{rel['to_column']}"
            )
            continue

        view_name = rel["view_name"]

        # Build SQL — pass engine so we can introspect t2 columns
        sql = _build_join_view_sql(
            view_name  = view_name,
            from_table = rel["from_table"],
            from_col   = rel["from_column"],
            to_table   = rel["to_table"],
            to_col     = rel["to_column"],
            engine     = engine,
        )

        success = _execute_view_sql(sql, view_name, engine)
        if success:
            result.views_created.append(view_name)
            result.join_log.append(
                f"Created VIEW '{view_name}': "
                f"{rel['from_table']}.{rel['from_column']} → "
                f"{rel['to_table']}.{rel['to_column']} "
                f"({rel['confidence']} confidence, {rel['match_percent']}% match)"
            )
        else:
            result.errors.append(f"Failed to create VIEW '{view_name}'.")

    # ── Step 2: Create master VIEW joining all tables ──────────────────────
    if len(relationships) > 1:
        master_view = _create_master_view(session_id, relationships, engine, result)
        if master_view:
            result.master_view_name = master_view
    elif len(result.views_created) == 1:
        result.master_view_name = result.views_created[0]

    logger.info(
        "Join step complete for session '%s'. %d view(s) created. Master view: '%s'.",
        session_id, len(result.views_created), result.master_view_name
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_join_view_sql(
    view_name  : str,
    from_table : str,
    from_col   : str,
    to_table   : str,
    to_col     : str,
    engine     : Engine,
) -> str:
    """
    Build LEFT JOIN VIEW SQL.

    The fix for DuplicateColumn error:
        When both tables share a column name (e.g. customer_id), doing
        SELECT t1.*, t2.* causes PostgreSQL to complain about duplicate columns.
        Solution: introspect t2's columns from information_schema and
        explicitly exclude the join key column from t2's select list.

    Example output:
        CREATE OR REPLACE VIEW "view_abc_orders_customers" AS
        SELECT
            t1.*,
            t2."customer_unique_id",
            t2."customer_zip_code_prefix",
            t2."customer_city",
            t2."customer_state"
        FROM "orders" t1
        LEFT JOIN "customers" t2
            ON t1."customer_id" = t2."customer_id";
    """
    # Introspect t2 columns from PostgreSQL — exclude the join key to avoid duplicate
    try:
        with engine.connect() as conn:
            query_result = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :tname AND table_schema = 'public' "
                    "ORDER BY ordinal_position"
                ),
                {"tname": to_table}
            )
            # Exclude every column already present in t1. PostgreSQL views cannot
            # expose duplicate output names when the source tables share fields.
            from_columns = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :tname AND table_schema = 'public'"
                ),
                {"tname": from_table}
            )
            from_col_names = {row[0] for row in from_columns}
            to_cols = [row[0] for row in query_result if row[0] not in from_col_names]
    except Exception as e:
        logger.warning("Could not introspect columns for '%s': %s — using t2.*", to_table, e)
        to_cols = None

    # Build the SELECT clause
    if to_cols:
        # Explicitly list t2 columns (minus the join key)
        t2_select    = ",\n    ".join(f't2."{c}"' for c in to_cols)
        select_clause = f"t1.*,\n    {t2_select}"
    else:
        # Fallback — may fail if join key is duplicated, but we tried
        select_clause = "t1.*,\n    t2.*"

    sql = f"""
CREATE OR REPLACE VIEW "{view_name}" AS
SELECT
    {select_clause}
FROM "{from_table}" t1
LEFT JOIN "{to_table}" t2
    ON t1."{from_col}" = t2."{to_col}";
""".strip()

    return sql


def _create_master_view(
    session_id    : str,
    relationships : list[dict],
    engine        : Engine,
    result        : JoinResult,
) -> str | None:
    """
    Create a master VIEW that chains all relationships together.

    Finds the most-connected table (fact table) and builds a
    multi-table LEFT JOIN starting from it.
    Only selects fact_table.* to avoid any duplicate column issues.
    """
    # Count how many relationships each table appears in
    table_counts: dict[str, int] = {}
    for rel in relationships:
        table_counts[rel["from_table"]] = table_counts.get(rel["from_table"], 0) + 1
        table_counts[rel["to_table"]]   = table_counts.get(rel["to_table"], 0) + 1

    if not table_counts:
        return None

    # Most-connected table = fact table
    fact_table       = max(table_counts, key=lambda t: table_counts[t])
    short_id         = session_id.replace("-", "")[:8]
    master_view_name = f"master_view_{short_id}"

    join_clauses  = []
    joined_tables = {fact_table}

    for rel in relationships:
        if rel["from_table"] == fact_table and rel["to_table"] not in joined_tables:
            alias_idx = len(joined_tables) + 1
            join_clauses.append(
                f'LEFT JOIN "{rel["to_table"]}" t{alias_idx} '
                f'ON "{fact_table}"."{rel["from_column"]}" = '
                f't{alias_idx}."{rel["to_column"]}"'
            )
            joined_tables.add(rel["to_table"])

        elif rel["to_table"] == fact_table and rel["from_table"] not in joined_tables:
            alias_idx = len(joined_tables) + 1
            join_clauses.append(
                f'LEFT JOIN "{rel["from_table"]}" t{alias_idx} '
                f'ON "{fact_table}"."{rel["to_column"]}" = '
                f't{alias_idx}."{rel["from_column"]}"'
            )
            joined_tables.add(rel["from_table"])

    if not join_clauses:
        return None

    joins_sql = "\n    ".join(join_clauses)

    # Only select fact_table.* — avoids ALL duplicate column issues in master view
    sql = f"""
CREATE OR REPLACE VIEW "{master_view_name}" AS
SELECT
    "{fact_table}".*
FROM "{fact_table}"
    {joins_sql};
""".strip()

    success = _execute_view_sql(sql, master_view_name, engine)
    if success:
        result.join_log.append(
            f"Created master VIEW '{master_view_name}' joining "
            f"{len(joined_tables)} table(s) from fact table '{fact_table}'."
        )
        return master_view_name
    else:
        result.errors.append(f"Failed to create master VIEW '{master_view_name}'.")
        return None


def _execute_view_sql(sql: str, view_name: str, engine: Engine) -> bool:
    """
    Execute a CREATE OR REPLACE VIEW statement in PostgreSQL.
    Returns True on success, False on failure.
    Does not raise — caller handles failure gracefully.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        logger.info("VIEW '%s' created successfully.", view_name)
        return True
    except Exception as e:
        logger.error("Failed to create VIEW '%s': %s", view_name, e)
        logger.debug("SQL that failed:\n%s", sql)
        return False