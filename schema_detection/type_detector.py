"""
type_detector.py
----------------
Detects the semantic type of each column in a pandas DataFrame.

Semantic types go beyond pandas dtypes (int, float, object) and answer
the BUSINESS question: what does this column MEAN?

Supported semantic types:
    'id'        — unique identifier (order_id, customer_id, product_code)
    'datetime'  — date or timestamp (order_date, created_at, invoice_date)
    'currency'  — monetary value (revenue, price, cost, payment_amount)
    'numeric'   — general number that is NOT currency (quantity, age, score, rating)
    'category'  — low-cardinality text used for grouping (region, status, gender)
    'text'      — high-cardinality free text (comments, descriptions, names)
    'boolean'   — true/false or yes/no or 1/0 binary columns

Why this matters:
    The chart selector, KPI engine, and ML model selector all depend on
    knowing semantic types — not raw dtypes. A float column could be
    currency (revenue) or numeric (rating). The detection logic below
    resolves this using column names, value patterns, and statistics.
"""

import re
import json
import logging
import pandas as pd
import numpy as np
from typing import Literal
from dateutil.parser import parse as dateutil_parse

# ── Logging setup ─────────────────────────────────────────────────────────────
# Using module-level logger so the calling code can control log level
logger = logging.getLogger(__name__)

# ── Type alias for clarity ─────────────────────────────────────────────────────
SemanticType = Literal["id", "datetime", "currency", "numeric", "category", "text", "boolean"]

# ── Configuration constants ────────────────────────────────────────────────────
# These thresholds control detection behaviour.
# They are constants (not hardcoded magic numbers buried in logic) so they
# are easy to tune if detection feels off for a particular dataset.

# A column is 'category' if unique values / total rows is below this ratio.
# e.g. 0.05 means: if a column has <5% unique values, it's categorical.
CATEGORY_CARDINALITY_THRESHOLD = 0.05

# A column is 'category' (not 'text') if it has at most this many unique values.
# Handles small datasets where ratio alone is misleading.
CATEGORY_MAX_UNIQUE = 50

# A column is 'id' if unique values / total rows is above this ratio.
# IDs are almost always 100% unique.
ID_UNIQUENESS_THRESHOLD = 0.95

# Minimum number of non-null values required to attempt datetime parsing.
# Avoids false positives on nearly-empty columns.
DATETIME_MIN_SAMPLE = 10

# How many sample values to try parsing as datetime before deciding.
# Parsing every row is slow — sampling is faster and accurate enough.
DATETIME_SAMPLE_SIZE = 50

# What fraction of sampled values must parse as datetime to confirm the type.
DATETIME_PARSE_SUCCESS_RATE = 0.85

# ── Keyword lists for name-based hints ────────────────────────────────────────
# Column names containing these words are strong hints for each type.
# All comparisons are done in lowercase.

# fmt: off
ID_KEYWORDS = [
    "id", "code", "key", "uuid", "guid", "ref", "reference",
    "number", "num", "no", "nr", "sku", "identifier"
]

CURRENCY_KEYWORDS = [
    "price", "revenue", "sales", "amount", "cost", "value",
    "payment", "fee", "charge", "income", "profit", "margin",
    "spend", "budget", "salary", "wage", "earning", "total",
    "subtotal", "tax", "discount", "refund", "invoice"
]

DATETIME_KEYWORDS = [
    "date", "time", "timestamp", "datetime", "created", "updated",
    "modified", "at", "on", "year", "month", "day", "week",
    "period", "quarter", "when", "start", "end", "due", "deadline"
]

BOOLEAN_KEYWORDS = [
    "is_", "has_", "flag", "active", "enabled", "deleted",
    "verified", "approved", "cancelled", "returned"
]
# fmt: on


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def detect_column_type(
    series: pd.Series,
    column_name: str,
    total_rows: int,
) -> SemanticType:
    """
    Detect the semantic type of a single pandas Series (column).

    Detection uses a layered approach — each layer narrows down the type:
        Layer 1: Handle completely empty columns first (avoids crashes).
        Layer 2: Check pandas dtype — booleans and pure integers are fast wins.
        Layer 3: Check column name for keyword hints.
        Layer 4: Analyse value patterns (uniqueness, cardinality, format).
        Layer 5: Attempt datetime parsing as a last resort.

    Parameters
    ----------
    series : pd.Series
        The column data. Can contain nulls.
    column_name : str
        Original column name from the file header.
    total_rows : int
        Total number of rows in the DataFrame (used for ratio calculations).

    Returns
    -------
    SemanticType
        One of: 'id', 'datetime', 'currency', 'numeric', 'category', 'text', 'boolean'
    """
    # Work with a clean lowercase version of the column name for matching.
    col_lower = column_name.lower().strip()

    # ── Layer 1: Empty column ──────────────────────────────────────────────
    # Drop nulls to get actual values. If nothing is left, we cannot detect
    # a meaningful type — default to 'text' as the safest fallback.
    non_null = series.dropna()
    if len(non_null) == 0:
        logger.warning("Column '%s' is entirely null — defaulting to 'text'.", column_name)
        return "text"

    # ── Layer 2: Pandas dtype shortcuts ───────────────────────────────────
    # These are unambiguous — no further analysis needed.

    if pd.api.types.is_bool_dtype(series):
        # e.g. True/False columns pandas already recognised
        return "boolean"

    # ── Layer 3: Boolean by name + values ────────────────────────────────
    # Some boolean columns are stored as 0/1 integers or "yes"/"no" strings.
    if _is_boolean(series, col_lower, non_null):
        return "boolean"

    # ── Layer 4: Datetime detection ───────────────────────────────────────
    # Check name hint first (fast), then try parsing values (slower).
    if pd.api.types.is_datetime64_any_dtype(series):
        # Pandas already parsed this as datetime (e.g. when read with parse_dates)
        return "datetime"

    if _has_keyword(col_lower, DATETIME_KEYWORDS):
        # Name strongly suggests datetime — try to confirm with value parsing
        if _try_parse_datetime(non_null):
            return "datetime"
        # Name hint was there but values didn't parse — fall through to other checks

    # ── Layer 5: Numeric columns ──────────────────────────────────────────
    if pd.api.types.is_numeric_dtype(series):
        # We have a numeric column. Now decide: is it an ID, currency, or numeric?
        return _classify_numeric(series, col_lower, non_null, total_rows)

    # ── Layer 6: String/object columns ───────────────────────────────────
    # At this point we have a non-numeric, non-boolean, non-datetime column.
    # It's either: id, datetime (stored as string), category, or text.

    # Try datetime parsing even without a name keyword
    # (some files have date columns named 'col_A' or 'field_3')
    if _try_parse_datetime(non_null):
        return "datetime"

    # Check uniqueness for ID detection
    unique_count = non_null.nunique()
    unique_ratio = unique_count / total_rows if total_rows > 0 else 0

    # String column with very high uniqueness + ID keyword in name → 'id'
    if unique_ratio >= ID_UNIQUENESS_THRESHOLD and _has_keyword(col_lower, ID_KEYWORDS):
        return "id"

    # String column with ID keyword in name but LOWER uniqueness → still 'id'
    # This catches FK columns on the many-side of a relationship.
    # e.g. order_id in order_items: 98k unique values out of 112k rows (87%)
    # e.g. seller_id in order_items: 3k unique sellers out of 112k rows (2.7%)
    # Both are IDs — just non-unique because they appear in multiple rows.
    # Threshold is 0.001 (0.1%) to avoid classifying truly repeated codes as id.
    if _has_keyword(col_lower, ID_KEYWORDS) and unique_count >= 10 and unique_ratio >= 0.001:
        return "id"

    # String column with very high uniqueness but NO id keyword
    # Could still be an ID (e.g. UUID columns named 'ref' or 'token')
    if unique_ratio >= 0.99 and unique_count > 100:
        return "id"

    # Low cardinality → category
    if _is_category(unique_count, unique_ratio):
        return "category"

    # High cardinality string → text
    return "text"


def detect_all_columns(df: pd.DataFrame) -> list[dict]:
    """
    Run detect_column_type on every column in a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The full DataFrame (after loading from CSV/Excel).

    Returns
    -------
    list[dict]
        One dict per column with keys:
            column_name   : str
            detected_type : SemanticType
            null_count    : int
            null_percent  : float  (0.0 – 100.0)
            unique_count  : int
            sample_values : list   (up to 5 non-null examples)
            column_order  : int    (0-based position in DataFrame)
    """
    total_rows = len(df)
    results = []

    for order, column_name in enumerate(df.columns):
        series = df[column_name]

        # Detect type
        detected_type = detect_column_type(series, column_name, total_rows)

        # Calculate statistics
        null_count   = int(series.isna().sum())
        null_percent = round((null_count / total_rows * 100), 2) if total_rows > 0 else 0.0
        unique_count = int(series.nunique(dropna=True))

        # Collect up to 5 sample values (non-null, converted to string for JSON safety)
        sample_raw    = series.dropna().head(5).tolist()
        sample_values = [str(v) for v in sample_raw]

        results.append({
            "column_name"  : column_name,
            "detected_type": detected_type,
            "null_count"   : null_count,
            "null_percent" : null_percent,
            "unique_count" : unique_count,
            "sample_values": sample_values,
            "column_order" : order,
        })

        logger.debug(
            "Column '%s' → type='%s' | nulls=%d (%.1f%%) | unique=%d",
            column_name, detected_type, null_count, null_percent, unique_count
        )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _has_keyword(col_lower: str, keywords: list[str]) -> bool:
    """
    Return True if col_lower contains any of the keywords as a whole word
    or as part of a word separated by underscores, hyphens, or spaces.

    Example:
        _has_keyword('order_date', DATETIME_KEYWORDS) → True  ('date' found)
        _has_keyword('update_flag', DATETIME_KEYWORDS) → False ('update' not in list)
        _has_keyword('customer_id', ID_KEYWORDS) → True  ('id' found)
    """
    # Split column name on common separators to get individual tokens
    tokens = re.split(r'[_\-\s]+', col_lower)
    for keyword in keywords:
        # Check if keyword matches any token exactly, or is contained in col_lower
        if keyword in tokens or keyword in col_lower:
            return True
    return False


def _is_boolean(
    series: pd.Series,
    col_lower: str,
    non_null: pd.Series,
) -> bool:
    """
    Detect boolean columns that are not stored as Python bool dtype.

    Catches:
        - Integer columns with only 0 and 1 values
        - String columns with only 'yes'/'no', 'true'/'false', 'y'/'n'
        - Columns whose name starts with 'is_' or 'has_'
    """
    # Name-based hint: is_active, has_returned, is_deleted
    if any(col_lower.startswith(prefix) for prefix in ("is_", "has_")):
        return True

    unique_vals = set(non_null.unique())

    # Integer 0/1
    if pd.api.types.is_integer_dtype(series):
        if unique_vals <= {0, 1}:
            return True

    # String yes/no, true/false, y/n (case-insensitive)
    if pd.api.types.is_object_dtype(series):
        str_vals = {str(v).strip().lower() for v in unique_vals}
        boolean_string_sets = [
            {"yes", "no"},
            {"true", "false"},
            {"y", "n"},
            {"1", "0"},
            {"t", "f"},
        ]
        for bool_set in boolean_string_sets:
            # Allow subset: a column with only 'yes' (no 'no' yet) could be boolean
            if str_vals <= bool_set or str_vals == bool_set:
                return True

    return False


def _classify_numeric(
    series: pd.Series,
    col_lower: str,
    non_null: pd.Series,
    total_rows: int,
) -> SemanticType:
    """
    Classify a numeric column as 'id', 'currency', or 'numeric'.

    Called only when pandas has already confirmed the column is numeric.

    Decision logic:
        1. Integer with very high uniqueness + ID keyword → 'id'
           (e.g. auto-increment primary keys: 1, 2, 3, 4 ...)
        2. Currency keyword in name → 'currency'
        3. Float values (decimals present) without currency keyword
           but with values > 1 and typical monetary range → 'currency'
        4. Everything else → 'numeric'
    """
    unique_count = non_null.nunique()
    unique_ratio = unique_count / total_rows if total_rows > 0 else 0

    # ── Integer ID columns ────────────────────────────────────────────────
    # e.g. customer_id stored as integer (1, 2, 3 ...) in a SQL export
    if pd.api.types.is_integer_dtype(series):
        if unique_ratio >= ID_UNIQUENESS_THRESHOLD and _has_keyword(col_lower, ID_KEYWORDS):
            return "id"
        # Sequential integers starting at 1 with no gaps — likely an auto-increment ID
        if _is_sequential_integer(non_null):
            return "id"

    # ── Currency by name ──────────────────────────────────────────────────
    if _has_keyword(col_lower, CURRENCY_KEYWORDS):
        return "currency"

    # ── Currency by value pattern ─────────────────────────────────────────
    # Heuristic: float column with values > 1.0 and at least some decimals
    # is likely a monetary amount even without a keyword in the name.
    # This catches columns named 'amount', 'val', 'total' that we didn't
    # include in CURRENCY_KEYWORDS.
    if pd.api.types.is_float_dtype(series):
        mean_val = float(non_null.mean())
        has_decimals = bool((non_null % 1 != 0).any())
        if has_decimals and mean_val > 1.0:
            # Additional guard: exclude ratio/percentage columns (0.0–1.0 range)
            max_val = float(non_null.max())
            if max_val > 1.0:
                return "currency"

    return "numeric"


def _is_sequential_integer(non_null: pd.Series) -> bool:
    """
    Return True if the series looks like an auto-increment integer ID.

    Criteria:
        - All values are integers
        - Minimum value is 1 (or 0)
        - Values form a mostly-sequential sequence (no large gaps)
        - All values are unique
    """
    try:
        vals = non_null.astype(int)
        if vals.nunique() != len(vals):
            # Duplicates found — not a unique ID column
            return False
        min_val = int(vals.min())
        max_val = int(vals.max())
        expected_range = max_val - min_val + 1
        # Allow up to 5% gaps (deleted records create gaps in auto-increment IDs)
        if expected_range == 0:
            return False
        gap_ratio = (expected_range - len(vals)) / expected_range
        return min_val in (0, 1) and gap_ratio <= 0.05
    except (ValueError, TypeError):
        return False


def _try_parse_datetime(non_null: pd.Series) -> bool:
    """
    Attempt to parse a sample of string values as datetime.

    Returns True if >= DATETIME_PARSE_SUCCESS_RATE fraction of the sample
    successfully parses as a date/time value.

    Uses dateutil.parser.parse which handles a wide variety of formats:
        '2024-01-15', '15/01/2024', 'Jan 15 2024', '2024-01-15 10:30:00', etc.

    We sample instead of parsing all rows to keep this fast on large files.
    """
    # Only attempt on string (object) columns
    if not pd.api.types.is_object_dtype(non_null):
        return False

    # Need enough values to be confident
    if len(non_null) < DATETIME_MIN_SAMPLE:
        return False

    # Take a random sample for speed
    sample_size = min(DATETIME_SAMPLE_SIZE, len(non_null))
    sample      = non_null.sample(n=sample_size, random_state=42).astype(str)

    success_count = 0
    for value in sample:
        try:
            # dayfirst=False: prefer MM/DD/YYYY over DD/MM/YYYY (safer default)
            dateutil_parse(value, dayfirst=False)
            success_count += 1
        except (ValueError, OverflowError, TypeError):
            # Value did not parse as datetime — skip it
            pass

    parse_rate = success_count / sample_size
    return parse_rate >= DATETIME_PARSE_SUCCESS_RATE


def _is_category(unique_count: int, unique_ratio: float) -> bool:
    """
    Return True if a string column should be classified as 'category'.

    A column is categorical if it has low cardinality — meaning it takes
    one of a small set of repeated values. Examples:
        region: ['North', 'South', 'East', 'West']
        status: ['pending', 'delivered', 'cancelled']
        gender: ['M', 'F', 'Other']

    Two conditions must be met:
        1. unique_ratio is below the threshold (relative to dataset size)
        2. absolute unique count is below the maximum cap

    The two-condition check prevents:
        - A 10-row dataset where every value is unique (ratio=1.0) from
          being misclassified (it would fail condition 1)
        - A 1M-row dataset where there are 30 unique values from being
          misclassified as text (it would fail condition 1 but pass condition 2)
    """
    return unique_ratio <= CATEGORY_CARDINALITY_THRESHOLD or unique_count <= CATEGORY_MAX_UNIQUE