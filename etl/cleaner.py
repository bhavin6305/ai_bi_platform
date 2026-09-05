"""
cleaner.py
----------
Transformation layer of the ETL pipeline.

Takes a raw DataFrame + its schema profile and produces a clean DataFrame.

Cleaning steps (in order):
    1. Remove duplicate rows
    2. Fix mixed-type columns (numeric columns containing 'N/A', 'null' strings)
    3. Impute missing values — strategy depends on semantic type
    4. Standardise datetime columns to a single consistent format
    5. Flag outliers with a boolean column (does NOT remove them)
    6. Strip whitespace from all string columns
    7. Standardise category column values (consistent casing)

Design principles:
    - NEVER drop rows except for true duplicates and missing ID values
      (dropping data is destructive and hard to explain to business users)
    - ALWAYS explain what was done via a cleaning log
    - Works on any DataFrame regardless of column names or domain
"""

import logging
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from dateutil.parser import parse as dateutil_parse

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

# Strings commonly used to represent missing values in CSV files
# that pandas does NOT catch by default
EXTRA_NULL_VALUES = {
    "n/a", "na", "n.a.", "null", "none", "nil", "missing",
    "unknown", "-", "--", "---", "?", "not available",
    "not applicable", "#n/a", "#null!", "nan",
}

# IQR multiplier for outlier flagging (same as quality_reporter for consistency)
OUTLIER_IQR_MULTIPLIER = 3.0

# Datetime output format — all datetime columns standardised to this
STANDARD_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ─────────────────────────────────────────────────────────────────────────────
# Output data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CleaningLog:
    """
    Records every action taken during cleaning for one table.
    Stored in quality_reports.actions_taken and shown in Streamlit UI.
    """
    table_name        : str
    original_rows     : int
    final_rows        : int
    rows_removed      : int = 0
    outlier_columns   : int = 0
    actions           : list[str] = field(default_factory=list)
    warnings          : list[str] = field(default_factory=list)

    def add_action(self, message: str):
        self.actions.append(message)
        logger.info("[%s] %s", self.table_name, message)

    def add_warning(self, message: str):
        self.warnings.append(message)
        logger.warning("[%s] %s", self.table_name, message)


@dataclass
class CleanedTable:
    """One cleaned table ready for joining and loading."""
    table_name    : str
    df            : pd.DataFrame    # cleaned DataFrame
    cleaning_log  : CleaningLog
    schema_columns: list[dict]      # same schema profile, passed through


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def clean_table(
    df            : pd.DataFrame,
    table_name    : str,
    schema_columns: list[dict],
) -> CleanedTable:
    """
    Clean a single DataFrame using its detected schema profile.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame from the extractor.
    table_name : str
        Dynamic table name (e.g. 'a3f2c1d4_orders').
    schema_columns : list[dict]
        Output of type_detector.detect_all_columns() for this table.
        Each dict has: column_name, detected_type, null_count, null_percent, etc.

    Returns
    -------
    CleanedTable
        Cleaned DataFrame + full cleaning log.
    """
    # Work on a copy — never mutate the input DataFrame
    df = df.copy()

    log = CleaningLog(
        table_name    = table_name,
        original_rows = len(df),
        final_rows    = len(df),    # will be updated after drops
    )

    # Build a quick lookup: column_name → detected_type
    type_map = {col["column_name"]: col["detected_type"] for col in schema_columns}

    logger.info("Cleaning table '%s' (%d rows).", table_name, len(df))

    # ── Step 1: Replace extra null representations ─────────────────────────
    # Before anything else, replace strings like 'N/A', 'null', '--' with
    # actual NaN so all subsequent steps treat them as missing values.
    df = _replace_extra_nulls(df, log)

    # ── Step 2: Fix mixed-type columns ────────────────────────────────────
    # Columns detected as currency/numeric but stored as object dtype
    # (because some rows contain strings like 'N/A'). Coerce to numeric.
    df = _fix_mixed_type_columns(df, type_map, log)

    # ── Step 3: Remove duplicate rows ─────────────────────────────────────
    df = _remove_duplicates(df, log)

    # ── Step 4: Drop rows with missing ID values ───────────────────────────
    # A row with no ID cannot be joined to other tables — it's useless.
    df = _drop_missing_ids(df, type_map, log)

    # ── Step 5: Impute missing values ─────────────────────────────────────
    df = _impute_missing_values(df, type_map, log)

    # ── Step 6: Standardise datetime columns ──────────────────────────────
    df = _standardise_datetimes(df, type_map, log)

    # ── Step 7: Strip whitespace from string columns ───────────────────────
    df = _strip_whitespace(df, type_map, log)

    # ── Step 8: Standardise category casing ───────────────────────────────
    df = _standardise_categories(df, type_map, log)

    # ── Step 9: Flag outliers ──────────────────────────────────────────────
    df = _flag_outliers(df, type_map, log)

    # Update final row count in log
    log.final_rows   = len(df)
    log.rows_removed = log.original_rows - log.final_rows

    logger.info(
        "Cleaning complete for '%s'. %d → %d rows (%d removed). %d actions taken.",
        table_name, log.original_rows, log.final_rows, log.rows_removed, len(log.actions)
    )

    return CleanedTable(
        table_name    = table_name,
        df            = df,
        cleaning_log  = log,
        schema_columns= schema_columns,
    )


def clean_all_tables(extracted_tables: list) -> list[CleanedTable]:
    """
    Clean all extracted tables in a session.

    Parameters
    ----------
    extracted_tables : list[ExtractedTable]
        Output of extractor.extract_from_profile()

    Returns
    -------
    list[CleanedTable]
    """
    cleaned = []
    for extracted in extracted_tables:
        cleaned_table = clean_table(
            df             = extracted.df,
            table_name     = extracted.table_name,
            schema_columns = extracted.schema_columns,
        )
        cleaned.append(cleaned_table)
    return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# Private cleaning steps
# ─────────────────────────────────────────────────────────────────────────────

def _replace_extra_nulls(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """
    Replace common null-representation strings with actual NaN.

    Many real-world CSV files use 'N/A', 'null', '-', '?' etc.
    Pandas only catches a subset of these by default.
    This step ensures all downstream null-handling works correctly.
    """
    # Only apply to object (string) columns — no point checking numeric columns
    obj_cols = df.select_dtypes(include="object").columns.tolist()
    if not obj_cols:
        return df

    total_replaced = 0
    for col in obj_cols:
        # Create a mask: values that match our extra null set (case-insensitive)
        mask = df[col].astype(str).str.strip().str.lower().isin(EXTRA_NULL_VALUES)
        count = int(mask.sum())
        if count > 0:
            df.loc[mask, col] = np.nan
            total_replaced += count

    if total_replaced > 0:
        log.add_action(
            f"Replaced {total_replaced} extra null representations "
            f"('N/A', 'null', '--', etc.) with NaN across {len(obj_cols)} string columns."
        )

    return df


def _fix_mixed_type_columns(
    df      : pd.DataFrame,
    type_map: dict[str, str],
    log     : CleaningLog,
) -> pd.DataFrame:
    """
    Coerce columns detected as currency/numeric but stored as object dtype.

    Example: A 'revenue' column where most values are '1234.56' but a few
    rows contain 'N/A' (now NaN after step 1) or other strings.
    pd.to_numeric with errors='coerce' converts valid numbers and leaves
    non-numeric values as NaN for imputation in the next step.
    """
    for col, dtype in type_map.items():
        if col not in df.columns:
            continue
        if dtype in ("currency", "numeric") and pd.api.types.is_object_dtype(df[col]):
            before_nulls = int(df[col].isna().sum())
            df[col] = pd.to_numeric(df[col], errors="coerce")
            after_nulls = int(df[col].isna().sum())
            new_nulls = after_nulls - before_nulls
            if new_nulls > 0:
                log.add_action(
                    f"Column '{col}': coerced to numeric — {new_nulls} non-numeric "
                    f"values converted to NaN for imputation."
                )
            else:
                log.add_action(f"Column '{col}': coerced mixed-type to numeric successfully.")

    return df


def _remove_duplicates(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """
    Remove fully duplicate rows (all columns identical).

    We use keep='first' — keep the first occurrence and remove subsequent
    duplicates. This is the safest strategy for business data.
    """
    before = len(df)
    df = df.drop_duplicates(keep="first")
    removed = before - len(df)

    if removed > 0:
        log.add_action(f"Removed {removed} duplicate rows (kept first occurrence).")
    else:
        log.add_action("No duplicate rows found.")

    return df


def _drop_missing_ids(
    df      : pd.DataFrame,
    type_map: dict[str, str],
    log     : CleaningLog,
) -> pd.DataFrame:
    """
    Drop rows where an ID column is null.

    A row with no ID is useless for joining and analytics:
        - It cannot be linked to related tables
        - It cannot be uniquely identified
        - Including it would corrupt join results

    We only drop rows where the PRIMARY-KEY-like ID column is null
    (very high uniqueness ones). FK columns (like order_id in order_items)
    are also dropped if null since a line item with no parent order is invalid.
    """
    id_cols = [col for col, dtype in type_map.items() if dtype == "id" and col in df.columns]

    for col in id_cols:
        null_count = int(df[col].isna().sum())
        if null_count > 0:
            df = df[df[col].notna()].copy()
            log.add_action(
                f"Dropped {null_count} rows with missing values in ID column '{col}' "
                f"(rows without an ID cannot be used for analysis or joining)."
            )

    return df


def _impute_missing_values(
    df      : pd.DataFrame,
    type_map: dict[str, str],
    log     : CleaningLog,
) -> pd.DataFrame:
    """
    Fill missing values using a strategy appropriate for each semantic type.

    Strategies:
        currency / numeric → median  (robust to outliers, unlike mean)
        category / text    → mode    (most frequent value)
        boolean            → False   (safest default for flags)
        datetime           → NaT     (left as missing — flagged, not filled)
        id                 → already handled in _drop_missing_ids

    Why median instead of mean for numeric?
        Mean is pulled by outliers. If revenue has one row with 10M and
        most rows are around 1K, the mean is misleading. Median is not.
    """
    for col, dtype in type_map.items():
        if col not in df.columns:
            continue

        null_count = int(df[col].isna().sum())
        if null_count == 0:
            continue    # nothing to impute

        if dtype in ("currency", "numeric"):
            # Median imputation
            median_val = df[col].median()
            df[col]    = df[col].fillna(median_val)
            log.add_action(
                f"Column '{col}': filled {null_count} missing values with median "
                f"({median_val:.4f})."
            )

        elif dtype in ("category", "text"):
            # Mode imputation — most frequent value
            mode_series = df[col].mode()
            if len(mode_series) > 0:
                mode_val = mode_series.iloc[0]
                df[col]  = df[col].fillna(mode_val)
                log.add_action(
                    f"Column '{col}': filled {null_count} missing values with mode "
                    f"('{mode_val}')."
                )
            else:
                # No mode (all values are null — shouldn't happen after _drop_missing_ids)
                df[col] = df[col].fillna("Unknown")
                log.add_action(
                    f"Column '{col}': filled {null_count} missing values with 'Unknown' "
                    f"(no mode available)."
                )

        elif dtype == "boolean":
            df[col] = df[col].fillna(False)
            log.add_action(
                f"Column '{col}': filled {null_count} missing boolean values with False."
            )

        elif dtype == "datetime":
            # Do NOT fill missing datetimes — they carry meaning
            # (e.g. order_delivered_date is null if order not yet delivered)
            log.add_action(
                f"Column '{col}': {null_count} missing datetime values left as NaT "
                f"(missing dates carry business meaning — not imputed)."
            )

    return df


def _standardise_datetimes(
    df      : pd.DataFrame,
    type_map: dict[str, str],
    log     : CleaningLog,
) -> pd.DataFrame:
    """
    Parse all datetime columns and standardise to a single format.

    Converts any date/time string format to pandas Timestamp, then
    formats as 'YYYY-MM-DD HH:MM:SS' for consistent storage in PostgreSQL.

    Handles mixed date formats within the same column gracefully —
    dateutil.parser handles most formats automatically.
    """
    datetime_cols = [
        col for col, dtype in type_map.items()
        if dtype == "datetime" and col in df.columns
    ]

    for col in datetime_cols:
        # Skip if pandas already parsed it as datetime
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            log.add_action(f"Column '{col}': already datetime dtype — no conversion needed.")
            continue

        try:
            # infer_datetime_format=True speeds up parsing when format is consistent
            df[col] = pd.to_datetime(df[col], errors="coerce")
            failed_count = int(df[col].isna().sum())

            if failed_count > 0:
                log.add_warning(
                    f"Column '{col}': {failed_count} values could not be parsed as datetime — "
                    f"left as NaT."
                )
            else:
                log.add_action(
                    f"Column '{col}': all values successfully parsed and standardised to "
                    f"'{STANDARD_DATETIME_FORMAT}'."
                )
        except Exception as e:
            log.add_warning(f"Column '{col}': datetime standardisation failed — {e}. Skipped.")

    return df


def _strip_whitespace(
    df      : pd.DataFrame,
    type_map: dict[str, str],
    log     : CleaningLog,
) -> pd.DataFrame:
    """
    Strip leading and trailing whitespace from all string (object) columns.

    This is a surprisingly common issue in real-world CSVs — values like
    ' delivered ' vs 'delivered' cause duplicates in groupby operations.
    """
    obj_cols = df.select_dtypes(include="object").columns.tolist()
    if not obj_cols:
        return df

    stripped_cols = []
    for col in obj_cols:
        before = df[col].copy()
        df[col] = df[col].astype(str).str.strip()
        # Put NaN back (astype(str) converts NaN to the string 'nan')
        df[col] = df[col].replace("nan", np.nan)
        # Check if anything actually changed
        if not before.equals(df[col]):
            stripped_cols.append(col)

    if stripped_cols:
        log.add_action(
            f"Stripped leading/trailing whitespace from {len(stripped_cols)} "
            f"string column(s): {', '.join(stripped_cols)}."
        )

    return df


def _standardise_categories(
    df      : pd.DataFrame,
    type_map: dict[str, str],
    log     : CleaningLog,
) -> pd.DataFrame:
    """
    Standardise category column values to consistent title case.

    Without this, groupby operations produce separate groups for:
        'north', 'North', 'NORTH' — all meaning the same thing.

    We use title case (e.g. 'north' → 'North') as the standard.
    IDs are excluded — they must not be modified (case-sensitive UUIDs).
    """
    category_cols = [
        col for col, dtype in type_map.items()
        if dtype == "category" and col in df.columns
    ]

    standardised = []
    for col in category_cols:
        non_null_mask = df[col].notna()
        # Check if there are any mixed-case values worth standardising
        original_vals = df.loc[non_null_mask, col].astype(str)
        standardised_vals = original_vals.str.strip().str.title()

        if not original_vals.equals(standardised_vals):
            df.loc[non_null_mask, col] = standardised_vals
            standardised.append(col)

    if standardised:
        log.add_action(
            f"Standardised casing to title case in {len(standardised)} "
            f"category column(s): {', '.join(standardised)}."
        )

    return df


def _flag_outliers(
    df      : pd.DataFrame,
    type_map: dict[str, str],
    log     : CleaningLog,
) -> pd.DataFrame:
    """
    Add a boolean flag column for outliers in numeric and currency columns.

    Creates a new column: 'is_outlier_{original_col_name}'
    Value is True if the row's value is an extreme outlier, False otherwise.

    We FLAG rather than REMOVE because:
        - Business users should decide what to do with outliers
        - A large order might be legitimate (bulk purchase)
        - Removing data without user consent is bad practice
        - The flag lets Power BI / Streamlit filter outliers optionally

    Uses IQR method with 3× multiplier (same as quality_reporter).
    """
    numeric_types = ("currency", "numeric")
    numeric_cols  = [
        col for col, dtype in type_map.items()
        if dtype in numeric_types and col in df.columns
    ]

    flagged_cols = []
    for col in numeric_cols:
        numeric_series = pd.to_numeric(df[col], errors="coerce")
        non_null       = numeric_series.dropna()

        if len(non_null) < 10:
            # Too few values for meaningful outlier detection
            continue

        Q1  = float(non_null.quantile(0.25))
        Q3  = float(non_null.quantile(0.75))
        IQR = Q3 - Q1

        if IQR == 0:
            # No spread — all values are the same, no outliers possible
            continue

        lower_bound = Q1 - (OUTLIER_IQR_MULTIPLIER * IQR)
        upper_bound = Q3 + (OUTLIER_IQR_MULTIPLIER * IQR)

        flag_col_name = f"is_outlier_{col}"
        df[flag_col_name] = (
            (numeric_series < lower_bound) | (numeric_series > upper_bound)
        ).fillna(False)   # NaN values are not outliers — flag as False

        outlier_count = int(df[flag_col_name].sum())
        if outlier_count > 0:
            flagged_cols.append(col)
            log.outlier_columns += 1
            log.add_action(
                f"Column '{col}': flagged {outlier_count} outlier values "
                f"(outside [{lower_bound:.2f}, {upper_bound:.2f}]) "
                f"in new column '{flag_col_name}'."
            )

    if not flagged_cols:
        log.add_action("No outliers detected in any numeric column.")

    return df