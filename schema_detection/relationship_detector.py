"""
relationship_detector.py
------------------------
Detects foreign key / primary key relationships between multiple DataFrames
(i.e. multiple uploaded tables in the same session).

How it works:
    1. Collect all columns detected as 'id' type across all tables.
    2. For each pair of ID columns with the same or similar name across
       DIFFERENT tables, compute what percentage of values in one column
       appear in the other.
    3. If the match percentage exceeds the threshold → relationship found.

Example (Olist):
    orders.customer_id  ↔  customers.customer_id   → 100% match → HIGH confidence
    order_items.order_id  ↔  orders.order_id        → 100% match → HIGH confidence
    order_items.product_id  ↔  products.product_id  → 100% match → HIGH confidence

This works on ANY dataset — not just Olist. The detection is purely based on
column names and value overlap. No hardcoded table or column names.
"""

import logging
import re
import pandas as pd

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

# Minimum value-overlap % to consider a relationship 'high' confidence
HIGH_CONFIDENCE_THRESHOLD  = 0.80   # 80% of values in col_A exist in col_B

# Minimum value-overlap % to consider a relationship 'medium' confidence
MEDIUM_CONFIDENCE_THRESHOLD = 0.50  # 50% match

# If match is below this, we ignore the relationship entirely
MIN_MATCH_THRESHOLD = 0.50

# Maximum unique values in a column to attempt relationship detection.
# Very high-cardinality columns (like free text) are never IDs.
MAX_ID_UNIQUE_VALUES = 500_000


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def detect_relationships(
    tables: dict[str, pd.DataFrame],
    schema_profiles: dict[str, list[dict]],
) -> list[dict]:
    """
    Detect FK/PK relationships across multiple tables.

    Parameters
    ----------
    tables : dict[str, pd.DataFrame]
        Keys are table names (e.g. 'a3f2c1d4_orders').
        Values are the cleaned DataFrames for each table.

    schema_profiles : dict[str, list[dict]]
        Keys are table names (matching `tables`).
        Values are the output of type_detector.detect_all_columns() for that table.
        Used to filter down to 'id' columns only (fast path).

    Returns
    -------
    list[dict]
        Each dict represents one detected relationship:
        {
            'from_table'    : str,   # table that contains the foreign key
            'from_column'   : str,   # the FK column name
            'to_table'      : str,   # table that contains the primary key
            'to_column'     : str,   # the PK column name
            'confidence'    : str,   # 'high' | 'medium'
            'match_percent' : float, # e.g. 0.98 means 98% of FK values found in PK
            'view_name'     : str,   # suggested SQL VIEW name for this join
        }
    """
    if len(tables) < 2:
        # Need at least 2 tables to detect relationships
        logger.info("Only 1 table uploaded — no relationships to detect.")
        return []

    # Step 1: Build index of ID columns per table
    # id_columns_map[table_name] = list of column names that are type 'id'
    id_columns_map = _get_id_columns(schema_profiles)

    if not any(id_columns_map.values()):
        logger.info("No 'id' columns detected in any table — skipping relationship detection.")
        return []

    # Step 2: Find candidate pairs
    # A candidate pair is two ID columns from different tables with the same
    # or similar normalised name (e.g. 'customer_id' in both orders and customers)
    candidates = _find_candidate_pairs(id_columns_map)

    if not candidates:
        logger.info("No candidate column name matches found across tables.")
        return []

    # Step 3: Validate candidates by computing value overlap
    relationships = []
    seen_pairs    = set()  # avoid reporting the same relationship twice

    for from_table, from_col, to_table, to_col in candidates:
        # Create a canonical pair key to avoid A→B and B→A duplicates
        pair_key = tuple(sorted([f"{from_table}.{from_col}", f"{to_table}.{to_col}"]))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        # Compute value overlap
        match_pct = _compute_match_percent(
            tables[from_table][from_col],
            tables[to_table][to_col],
        )

        logger.debug(
            "Candidate: %s.%s → %s.%s | match=%.1f%%",
            from_table, from_col, to_table, to_col, match_pct * 100
        )

        if match_pct < MIN_MATCH_THRESHOLD:
            # Not enough overlap — not a real relationship
            continue

        confidence = _get_confidence(match_pct)
        view_name  = _build_view_name(from_table, to_table)

        relationships.append({
            "from_table"    : from_table,
            "from_column"   : from_col,
            "to_table"      : to_table,
            "to_column"     : to_col,
            "confidence"    : confidence,
            "match_percent" : round(match_pct * 100, 2),  # store as percentage e.g. 98.5
            "view_name"     : view_name,
        })

        logger.info(
            "Relationship found: %s.%s → %s.%s | confidence=%s | match=%.1f%%",
            from_table, from_col, to_table, to_col, confidence, match_pct * 100
        )

    # Sort by match_percent descending — strongest relationships first
    relationships.sort(key=lambda r: r["match_percent"], reverse=True)

    return relationships


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_id_columns(
    schema_profiles: dict[str, list[dict]],
) -> dict[str, list[str]]:
    """
    Extract all columns detected as type 'id' from schema profiles.

    Returns
    -------
    dict[str, list[str]]
        {table_name: [list of id column names]}
    """
    id_columns_map = {}
    for table_name, columns in schema_profiles.items():
        id_cols = [
            col["column_name"]
            for col in columns
            if col["detected_type"] == "id"
        ]
        id_columns_map[table_name] = id_cols
        if id_cols:
            logger.debug("Table '%s' ID columns: %s", table_name, id_cols)
    return id_columns_map


def _find_candidate_pairs(
    id_columns_map: dict[str, list[str]],
) -> list[tuple[str, str, str, str]]:
    """
    Find pairs of ID columns across different tables that have the same
    normalised name. These are relationship candidates.

    Normalisation removes the table name prefix that some datasets include:
        'order_items.order_id' → normalised = 'order'
        'orders.order_id'      → normalised = 'order'
        Both normalise to 'order' → candidate pair found.

    Returns
    -------
    list of tuples: (from_table, from_col, to_table, to_col)
    """
    table_names = list(id_columns_map.keys())
    candidates  = []

    for i in range(len(table_names)):
        for j in range(i + 1, len(table_names)):
            table_a = table_names[i]
            table_b = table_names[j]
            cols_a  = id_columns_map[table_a]
            cols_b  = id_columns_map[table_b]

            for col_a in cols_a:
                norm_a = _normalise_column_name(col_a)
                for col_b in cols_b:
                    norm_b = _normalise_column_name(col_b)

                    if _names_match(norm_a, norm_b):
                        # Found a name match — this is a candidate
                        candidates.append((table_a, col_a, table_b, col_b))
                        logger.debug(
                            "Name match candidate: %s.%s ↔ %s.%s (norm: '%s' ↔ '%s')",
                            table_a, col_a, table_b, col_b, norm_a, norm_b
                        )

    return candidates


def _normalise_column_name(col_name: str) -> str:
    """
    Normalise a column name for comparison.

    Steps:
        1. Lowercase
        2. Remove common suffixes: _id, _key, _code, _ref
        3. Remove session ID prefix if present (e.g. 'a3f2c1d4_' prefix)
        4. Strip leading/trailing underscores

    Examples:
        'customer_id'    → 'customer'
        'CUSTOMER_ID'    → 'customer'
        'order_key'      → 'order'
        'product_code'   → 'product'
        'customerid'     → 'customerid'  (no separator — left as is)
    """
    name = col_name.lower().strip()

    # Remove common ID suffixes with a word boundary before them
    # Using regex to avoid removing 'id' from the middle of a word like 'field'
    name = re.sub(r'[_\-]?(id|key|code|ref|no|num|number|uuid|guid)$', '', name)

    # Strip any leftover underscores at start/end
    name = name.strip('_')

    return name


def _names_match(norm_a: str, norm_b: str) -> bool:
    """
    Decide whether two normalised column names are the same concept.

    Exact match after normalisation is the primary check.
    Also handles common abbreviation pairs that mean the same thing.

    Examples:
        'customer' == 'customer'  → True  (exact match)
        'cust'     == 'customer'  → True  (abbreviation match)
        'prod'     == 'product'   → True  (abbreviation match)
        'order'    == 'invoice'   → False (different concepts)
    """
    if not norm_a or not norm_b:
        return False

    # Exact match (most common case)
    if norm_a == norm_b:
        return True

    # Known abbreviation mappings: (short, full)
    abbreviations = [
        ("cust", "customer"),
        ("prod", "product"),
        ("ord",  "order"),
        ("inv",  "invoice"),
        ("emp",  "employee"),
        ("dept", "department"),
        ("cat",  "category"),
        ("addr", "address"),
    ]

    for short, full in abbreviations:
        if (norm_a == short and norm_b == full) or (norm_a == full and norm_b == short):
            return True

    # One name is a prefix of the other (e.g. 'user' and 'user_account')
    if norm_a.startswith(norm_b) or norm_b.startswith(norm_a):
        # Only accept if the shorter name is at least 3 chars (avoid false positives)
        shorter = min(norm_a, norm_b, key=len)
        if len(shorter) >= 3:
            return True

    return False


def _compute_match_percent(
    fk_series: pd.Series,
    pk_series: pd.Series,
) -> float:
    """
    Compute what fraction of non-null values in fk_series exist in pk_series.

    This is the core validation step. A true FK→PK relationship will have
    close to 100% of FK values present in the PK column.

    Parameters
    ----------
    fk_series : pd.Series  — the potential foreign key column (many-side)
    pk_series : pd.Series  — the potential primary key column (one-side)

    Returns
    -------
    float: value between 0.0 and 1.0
    """
    fk_non_null = fk_series.dropna()
    pk_non_null = pk_series.dropna()

    if len(fk_non_null) == 0 or len(pk_non_null) == 0:
        return 0.0

    # Optimisation: if either column has too many unique values, skip
    # (very large ID sets take a long time to compute set intersection)
    if pk_non_null.nunique() > MAX_ID_UNIQUE_VALUES:
        logger.debug("Skipping match check — PK column has too many unique values.")
        return 0.0

    # Convert both to sets of strings for consistent comparison
    # (avoids int vs string type mismatch in mixed-type files)
    fk_set = set(fk_non_null.astype(str).str.strip())
    pk_set = set(pk_non_null.astype(str).str.strip())

    if not fk_set:
        return 0.0

    # What fraction of FK values can be found in PK?
    matched = fk_set.intersection(pk_set)
    return len(matched) / len(fk_set)


def _get_confidence(match_percent: float) -> str:
    """Map a match percentage to a confidence label."""
    if match_percent >= HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    elif match_percent >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    else:
        return "low"


def _build_view_name(from_table: str, to_table: str) -> str:
    """
    Build a SQL VIEW name for the join between two tables.

    Strips the session ID prefix from both table names to keep the view name readable.

    Example:
        from_table = 'a3f2c1d4_orders'
        to_table   = 'a3f2c1d4_customers'
        result     = 'view_a3f2c1d4_orders_customers'
    """
    # Extract the session prefix (first token before the first underscore after 8 chars)
    # Both tables in the same session share the same prefix
    parts      = from_table.split('_', 1)
    prefix     = parts[0] if len(parts) > 1 else ""
    from_clean = parts[1] if len(parts) > 1 else from_table

    to_parts   = to_table.split('_', 1)
    to_clean   = to_parts[1] if len(to_parts) > 1 else to_table

    if prefix:
        return f"view_{prefix}_{from_clean}_{to_clean}"
    else:
        return f"view_{from_table}_{to_table}"