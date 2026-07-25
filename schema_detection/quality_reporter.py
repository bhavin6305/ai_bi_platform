"""
quality_reporter.py
-------------------
Generates a data quality report for a single DataFrame (table).

Quality score is a number from 0 to 100:
    100 = perfect data — no nulls, no duplicates, no outliers
      0 = extremely poor data

The report also lists:
    - Specific issues found (what's wrong)
    - Actions recommended (what the ETL cleaner should fix)

This report is shown to the user in Streamlit BEFORE the ETL pipeline runs,
so they understand what the system found and what it will do about it.
It is also stored in the 'quality_reports' database table.
"""

import logging
import json
import pandas as pd
import numpy as np
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# ── Quality score deduction rules ─────────────────────────────────────────────
# Each rule defines how many points to deduct for a specific data quality issue.
# Stored as constants so they are easy to adjust without touching logic.

DEDUCT_PER_NULL_COLUMN      = 5   # per column with >5% nulls
DEDUCT_HIGH_NULL_COLUMN     = 10  # per column with >30% nulls (on top of above)
DEDUCT_DUPLICATE_ROWS       = 15  # if duplicate rows > 1% of total
DEDUCT_OUTLIER_COLUMN       = 5   # per numeric column with detected outliers
DEDUCT_MIXED_TYPE_COLUMN    = 8   # per column with inconsistent data types

# Thresholds
NULL_WARNING_THRESHOLD      = 0.05  # >5% nulls → flag this column
NULL_CRITICAL_THRESHOLD     = 0.30  # >30% nulls → extra deduction
DUPLICATE_ROW_THRESHOLD     = 0.01  # >1% duplicate rows → deduct points
OUTLIER_IQR_MULTIPLIER      = 3.0   # values beyond 3×IQR from Q1/Q3 = outlier


# ─────────────────────────────────────────────────────────────────────────────
# Data classes for structured output
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ColumnIssue:
    """Represents a quality issue found in a specific column."""
    column_name : str
    issue_type  : str    # 'nulls' | 'outliers' | 'mixed_types' | 'all_null'
    severity    : str    # 'warning' | 'critical'
    description : str    # human-readable description
    action      : str    # what the ETL cleaner will do about it


@dataclass
class QualityReport:
    """
    Complete quality report for one table.
    Stored in the quality_reports database table.
    Can be serialised to dict with asdict(report).
    """
    table_name          : str
    total_rows          : int
    total_columns       : int
    duplicate_rows      : int
    columns_with_nulls  : int
    outlier_columns     : int
    quality_score       : int           # 0–100
    issues_found        : list[str]     # human-readable issue list (for display)
    actions_taken       : list[str]     # what ETL will do (for display)
    column_issues       : list[dict]    # detailed per-column issues
    summary             : str           # one-sentence summary for the UI


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_quality_report(
    df         : pd.DataFrame,
    table_name : str,
    schema_profile: list[dict],
) -> QualityReport:
    """
    Generate a full quality report for a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The raw (uncleaned) DataFrame loaded from the user's file.
    table_name : str
        The dynamic table name (e.g. 'a3f2c1d4_orders').
    schema_profile : list[dict]
        Output of type_detector.detect_all_columns() for this DataFrame.
        Used to know which columns are numeric (for outlier detection).

    Returns
    -------
    QualityReport
        Full structured report. Call asdict(report) to convert to plain dict.
    """
    total_rows    = len(df)
    total_columns = len(df.columns)
    issues_found  = []
    actions_taken = []
    column_issues = []
    score         = 100   # start perfect, deduct as issues are found

    logger.info("Generating quality report for table '%s' (%d rows).", table_name, total_rows)

    # ── Check 1: Duplicate rows ────────────────────────────────────────────
    duplicate_count = int(df.duplicated().sum())
    duplicate_ratio = duplicate_count / total_rows if total_rows > 0 else 0

    if duplicate_count > 0:
        issue_text  = f"{duplicate_count} duplicate rows found ({duplicate_ratio * 100:.1f}% of data)"
        action_text = f"Will remove {duplicate_count} duplicate rows automatically"
        issues_found.append(issue_text)
        actions_taken.append(action_text)

        if duplicate_ratio > DUPLICATE_ROW_THRESHOLD:
            score -= DEDUCT_DUPLICATE_ROWS
            logger.debug("Deducted %d points for duplicate rows.", DEDUCT_DUPLICATE_ROWS)

    # ── Check 2: Null values per column ───────────────────────────────────
    columns_with_nulls = 0

    for col_info in schema_profile:
        col_name     = col_info["column_name"]
        null_pct     = col_info["null_percent"] / 100  # convert back to ratio
        null_count   = col_info["null_count"]
        detected_type = col_info["detected_type"]

        if null_count == 0:
            continue  # perfect column — skip

        if null_pct == 1.0:
            # Completely empty column — critical issue
            severity    = "critical"
            description = f"Column '{col_name}' is entirely null — no usable data"
            action      = f"Column '{col_name}' will be dropped (100% null)"
            score      -= DEDUCT_HIGH_NULL_COLUMN
            issues_found.append(description)
            actions_taken.append(action)
            column_issues.append(asdict(ColumnIssue(
                column_name = col_name,
                issue_type  = "all_null",
                severity    = severity,
                description = description,
                action      = action,
            )))
            columns_with_nulls += 1
            continue

        if null_pct > NULL_WARNING_THRESHOLD:
            columns_with_nulls += 1
            severity = "critical" if null_pct > NULL_CRITICAL_THRESHOLD else "warning"

            # Determine appropriate imputation strategy based on column type
            imputation_strategy = _get_imputation_strategy(detected_type)

            description = (
                f"Column '{col_name}' has {null_count} missing values "
                f"({null_pct * 100:.1f}%)"
            )
            action = f"Column '{col_name}': {imputation_strategy}"

            issues_found.append(description)
            actions_taken.append(action)
            column_issues.append(asdict(ColumnIssue(
                column_name = col_name,
                issue_type  = "nulls",
                severity    = severity,
                description = description,
                action      = action,
            )))

            # Deduct points
            score -= DEDUCT_PER_NULL_COLUMN
            if null_pct > NULL_CRITICAL_THRESHOLD:
                score -= DEDUCT_HIGH_NULL_COLUMN

    # ── Check 3: Outliers in numeric columns ───────────────────────────────
    outlier_columns = 0
    numeric_cols = [
        col_info["column_name"]
        for col_info in schema_profile
        if col_info["detected_type"] in ("numeric", "currency")
    ]

    for col_name in numeric_cols:
        if col_name not in df.columns:
            continue

        outlier_count = _count_outliers(df[col_name])
        if outlier_count > 0:
            outlier_columns += 1
            outlier_pct = outlier_count / total_rows * 100

            description = (
                f"Column '{col_name}' has {outlier_count} outlier values "
                f"({outlier_pct:.1f}%)"
            )
            action = (
                f"Column '{col_name}': outliers will be flagged with an "
                f"'is_outlier_{col_name}' boolean column (not removed)"
            )
            issues_found.append(description)
            actions_taken.append(action)
            column_issues.append(asdict(ColumnIssue(
                column_name = col_name,
                issue_type  = "outliers",
                severity    = "warning",
                description = description,
                action      = action,
            )))
            score -= DEDUCT_OUTLIER_COLUMN

    # ── Check 4: Mixed type columns ────────────────────────────────────────
    # Some CSV files have columns where most values are numbers but a few
    # rows contain strings like 'N/A', 'null', 'unknown'.
    # Pandas loads these as 'object' dtype — we detect and flag them.
    for col_info in schema_profile:
        col_name     = col_info["column_name"]
        detected_type = col_info["detected_type"]

        if detected_type in ("numeric", "currency") and col_name in df.columns:
            if pd.api.types.is_object_dtype(df[col_name]):
                # Declared numeric by our detector but stored as object → mixed types
                description = (
                    f"Column '{col_name}' contains mixed types — "
                    f"numeric values mixed with text (e.g. 'N/A', 'unknown')"
                )
                action = (
                    f"Column '{col_name}': non-numeric values will be replaced "
                    f"with null, then imputed"
                )
                issues_found.append(description)
                actions_taken.append(action)
                column_issues.append(asdict(ColumnIssue(
                    column_name = col_name,
                    issue_type  = "mixed_types",
                    severity    = "warning",
                    description = description,
                    action      = action,
                )))
                score -= DEDUCT_MIXED_TYPE_COLUMN

    # ── Clamp score to valid range ─────────────────────────────────────────
    score = max(0, min(100, score))

    # ── Generate summary sentence ──────────────────────────────────────────
    summary = _build_summary(score, duplicate_count, columns_with_nulls, outlier_columns)

    logger.info(
        "Quality report for '%s': score=%d | duplicates=%d | null_cols=%d | outlier_cols=%d",
        table_name, score, duplicate_count, columns_with_nulls, outlier_columns
    )

    return QualityReport(
        table_name          = table_name,
        total_rows          = total_rows,
        total_columns       = total_columns,
        duplicate_rows      = duplicate_count,
        columns_with_nulls  = columns_with_nulls,
        outlier_columns     = outlier_columns,
        quality_score       = score,
        issues_found        = issues_found,
        actions_taken       = actions_taken,
        column_issues       = column_issues,
        summary             = summary,
    )


def report_to_db_dict(report: QualityReport, session_id: str) -> dict:
    """
    Convert a QualityReport to a flat dict ready to INSERT into quality_reports table.

    Serialises list fields (issues_found, actions_taken, column_issues) to JSON strings
    because PostgreSQL columns for these are TEXT (not JSON type).

    Parameters
    ----------
    report : QualityReport
    session_id : str

    Returns
    -------
    dict matching quality_reports table columns
    """
    return {
        "session_id"         : session_id,
        "table_name"         : report.table_name,
        "quality_score"      : report.quality_score,
        "total_rows"         : report.total_rows,
        "duplicate_rows"     : report.duplicate_rows,
        "columns_with_nulls" : report.columns_with_nulls,
        "outlier_columns"    : report.outlier_columns,
        "issues_found"       : json.dumps(report.issues_found),
        "actions_taken"      : json.dumps(report.actions_taken),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _count_outliers(series: pd.Series) -> int:
    """
    Count outliers in a numeric series using the IQR method.

    IQR (Interquartile Range) method:
        Q1 = 25th percentile
        Q3 = 75th percentile
        IQR = Q3 - Q1
        Lower bound = Q1 - (OUTLIER_IQR_MULTIPLIER × IQR)
        Upper bound = Q3 + (OUTLIER_IQR_MULTIPLIER × IQR)
        Anything outside [lower, upper] = outlier

    We use 3×IQR (instead of the common 1.5×IQR) to be less aggressive —
    we flag only extreme outliers, not borderline cases.
    Business data often has legitimately large values (e.g. a single huge order).
    """
    try:
        numeric = pd.to_numeric(series, errors='coerce').dropna()
        if len(numeric) < 10:
            # Too few values to meaningfully detect outliers
            return 0

        Q1  = float(numeric.quantile(0.25))
        Q3  = float(numeric.quantile(0.75))
        IQR = Q3 - Q1

        if IQR == 0:
            # All values are the same — no outliers possible
            return 0

        lower_bound = Q1 - (OUTLIER_IQR_MULTIPLIER * IQR)
        upper_bound = Q3 + (OUTLIER_IQR_MULTIPLIER * IQR)

        outlier_mask = (numeric < lower_bound) | (numeric > upper_bound)
        return int(outlier_mask.sum())

    except Exception as e:
        logger.warning("Outlier detection failed for column — skipping. Error: %s", e)
        return 0


def _get_imputation_strategy(detected_type: str) -> str:
    """
    Return a human-readable description of how nulls will be handled
    for a given semantic type.

    These match what etl/cleaner.py will actually do.
    """
    strategies = {
        "currency": "missing values will be filled with the column median",
        "numeric" : "missing values will be filled with the column median",
        "category": "missing values will be filled with the most frequent value (mode)",
        "text"    : "missing values will be filled with 'Unknown'",
        "datetime": "rows with missing dates will be flagged but not removed",
        "id"      : "rows with missing IDs will be dropped (cannot join without a key)",
        "boolean" : "missing values will be filled with False",
    }
    return strategies.get(detected_type, "missing values will be reviewed manually")


def _build_summary(
    score              : int,
    duplicate_count    : int,
    columns_with_nulls : int,
    outlier_columns    : int,
) -> str:
    """Build a one-sentence quality summary for display in Streamlit."""
    if score >= 90:
        level = "excellent"
    elif score >= 75:
        level = "good"
    elif score >= 50:
        level = "moderate"
    else:
        level = "poor"

    parts = []
    if duplicate_count > 0:
        parts.append(f"{duplicate_count} duplicate rows")
    if columns_with_nulls > 0:
        parts.append(f"{columns_with_nulls} columns with missing values")
    if outlier_columns > 0:
        parts.append(f"{outlier_columns} columns with outliers")

    if not parts:
        return f"Data quality is {level} (score: {score}/100). No issues detected."

    issues_str = ", ".join(parts)
    return (
        f"Data quality is {level} (score: {score}/100). "
        f"Issues found: {issues_str}. "
        f"The ETL pipeline will handle these automatically."
    )