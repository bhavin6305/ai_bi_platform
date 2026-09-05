"""
loader.py
---------
Load layer of the ETL pipeline.

Loads cleaned DataFrames into PostgreSQL and saves all session metadata
(schema profiles, quality reports, relationships, upload session record)
into the platform's Layer 1 metadata tables.

Two types of writes happen:
    1. Business data → dynamic tables ({short_id}_{filename})
    2. Platform metadata → fixed tables (upload_sessions, schema_profiles, etc.)
"""

import json
import logging
import uuid
from dataclasses import asdict
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_session(
    session_id     : str,
    cleaned_tables : list,          # list[CleanedTable] from cleaner.py
    relationships  : list[dict],    # from relationship_detector
    session_profile: object,        # SessionProfile from profiler.py
    engine         : Engine,
) -> dict:
    """
    Load everything for one upload session into PostgreSQL.

    Steps:
        1. Insert upload_session record (status = 'loading')
        2. Load each cleaned DataFrame as a dynamic table
        3. Save schema profiles to schema_profiles table
        4. Save quality reports to quality_reports table
        5. Save relationships to detected_relationships table
        6. Update upload_session status to 'done'

    Parameters
    ----------
    session_id      : str
    cleaned_tables  : list[CleanedTable]   — from cleaner.clean_all_tables()
    relationships   : list[dict]           — from relationship_detector
    session_profile : SessionProfile       — from profiler.profile_upload()
    engine          : Engine               — SQLAlchemy engine

    Returns
    -------
    dict with load summary:
        {
            'session_id': str,
            'tables_loaded': int,
            'total_rows': int,
            'status': 'done' | 'partial' | 'error',
            'errors': list[str],
        }
    """
    errors       = []
    tables_loaded = 0
    total_rows    = 0

    # ── Step 1: Create upload_session record ───────────────────────────────
    _upsert_upload_session(
        session_id   = session_id,
        status       = "loading",
        total_files  = len(cleaned_tables),
        engine       = engine,
    )

    # ── Step 2: Load each cleaned business data table ──────────────────────
    for cleaned in cleaned_tables:
        try:
            rows = _load_dataframe(
                df         = cleaned.df,
                table_name = cleaned.table_name,
                engine     = engine,
            )
            tables_loaded += 1
            total_rows    += rows
            logger.info(
                "Loaded table '%s' — %d rows into PostgreSQL.", cleaned.table_name, rows
            )
        except Exception as e:
            error_msg = f"Failed to load table '{cleaned.table_name}': {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    # ── Step 3: Save schema profiles ───────────────────────────────────────
    try:
        _save_schema_profiles(session_id, cleaned_tables, engine)
    except Exception as e:
        error_msg = f"Failed to save schema profiles: {e}"
        logger.error(error_msg)
        errors.append(error_msg)

    # ── Step 4: Save quality reports ───────────────────────────────────────
    try:
        _save_quality_reports(session_id, cleaned_tables, engine)
    except Exception as e:
        error_msg = f"Failed to save quality reports: {e}"
        logger.error(error_msg)
        errors.append(error_msg)

    # ── Step 5: Save detected relationships ────────────────────────────────
    try:
        _save_relationships(session_id, relationships, engine)
    except Exception as e:
        error_msg = f"Failed to save relationships: {e}"
        logger.error(error_msg)
        errors.append(error_msg)

    # ── Step 6: Save uploaded_files records ───────────────────────────────
    try:
        _save_uploaded_files(session_id, cleaned_tables, session_profile, engine)
    except Exception as e:
        error_msg = f"Failed to save uploaded_files records: {e}"
        logger.error(error_msg)
        errors.append(error_msg)

    # ── Step 7: Update session status ─────────────────────────────────────
    final_status = "done" if not errors else ("partial" if tables_loaded > 0 else "error")
    _upsert_upload_session(
        session_id   = session_id,
        status       = final_status,
        total_files  = len(cleaned_tables),
        total_rows   = total_rows,
        completed_at = datetime.utcnow(),
        engine       = engine,
    )

    summary = {
        "session_id"    : session_id,
        "tables_loaded" : tables_loaded,
        "total_rows"    : total_rows,
        "status"        : final_status,
        "errors"        : errors,
    }

    logger.info(
        "Load complete for session '%s'. Status: %s | %d tables | %d rows | %d errors.",
        session_id, final_status, tables_loaded, total_rows, len(errors)
    )

    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_dataframe(
    df         : pd.DataFrame,
    table_name : str,
    engine     : Engine,
) -> int:
    """
    Load a cleaned DataFrame into PostgreSQL as a dynamic table.

    Uses pandas to_sql with if_exists='replace' — if a table with this
    name already exists (re-upload of same file), it is replaced entirely.

    Returns the number of rows loaded.
    """
    # Convert datetime columns to string before loading to avoid
    # timezone-related issues with different PostgreSQL configurations
    df_to_load = df.copy()
    for col in df_to_load.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
        df_to_load[col] = df_to_load[col].astype(str).replace("NaT", None)

    df_to_load.to_sql(
        name       = table_name,
        con        = engine,
        if_exists  = "replace",   # overwrite if same session re-uploads
        index      = False,       # don't add pandas index as a column
        chunksize  = 5000,        # write in batches to avoid memory issues on large files
        method     = "multi",     # faster than default single-row inserts
    )

    return len(df_to_load)


def _upsert_upload_session(
    session_id   : str,
    status       : str,
    total_files  : int = 0,
    total_rows   : int = 0,
    completed_at : datetime = None,
    error_message: str = None,
    engine       : Engine = None,
) -> None:
    """
    Insert or update the upload_sessions record for this session.

    Uses INSERT ... ON CONFLICT DO UPDATE (PostgreSQL upsert) so we can
    call this multiple times (at start with 'loading', at end with 'done')
    without duplicate key errors.
    """
    sql = text("""
        INSERT INTO upload_sessions
            (session_id, status, total_files, total_rows, error_message, completed_at)
        VALUES
            (:session_id, :status, :total_files, :total_rows, :error_message, :completed_at)
        ON CONFLICT (session_id) DO UPDATE SET
            status        = EXCLUDED.status,
            total_files   = EXCLUDED.total_files,
            total_rows    = EXCLUDED.total_rows,
            error_message = EXCLUDED.error_message,
            completed_at  = EXCLUDED.completed_at;
    """)

    with engine.connect() as conn:
        conn.execute(sql, {
            "session_id"   : session_id,
            "status"       : status,
            "total_files"  : total_files,
            "total_rows"   : total_rows,
            "error_message": error_message,
            "completed_at" : completed_at,
        })
        conn.commit()


def _save_schema_profiles(
    session_id     : str,
    cleaned_tables : list,
    engine         : Engine,
) -> None:
    """
    Save column-level schema profiles to the schema_profiles table.
    One row per column per table.
    """
    rows = []
    for cleaned in cleaned_tables:
        for col_info in cleaned.schema_columns:
            rows.append({
                "session_id"   : session_id,
                "table_name"   : cleaned.table_name,
                "column_name"  : col_info["column_name"],
                "detected_type": col_info["detected_type"],
                "null_count"   : col_info["null_count"],
                "null_percent" : col_info["null_percent"],
                "unique_count" : col_info.get("unique_count"),
                # Serialise sample_values list to JSON string for TEXT column
                "sample_values": json.dumps(col_info.get("sample_values", [])),
                "column_order" : col_info.get("column_order"),
            })

    if rows:
        df_profiles = pd.DataFrame(rows)
        df_profiles.to_sql(
            name      = "schema_profiles",
            con       = engine,
            if_exists = "append",   # append — don't overwrite the whole table
            index     = False,
        )
        logger.info("Saved %d schema profile row(s) to schema_profiles.", len(rows))


def _save_quality_reports(
    session_id     : str,
    cleaned_tables : list,
    engine         : Engine,
) -> None:
    """
    Save quality reports to the quality_reports table.
    One row per table.
    """
    rows = []
    for cleaned in cleaned_tables:
        qr = cleaned.cleaning_log   # CleaningLog from cleaner.py
        rows.append({
            "session_id"         : session_id,
            "table_name"         : cleaned.table_name,
            # Use final quality score from the original quality_report if available
            "quality_score"      : getattr(cleaned, "quality_score", 100),
            "total_rows"         : qr.original_rows,
            "duplicate_rows"     : qr.rows_removed,
            "columns_with_nulls" : 0,   # populated from cleaning_log.actions
            "outlier_columns"    : qr.outlier_columns,
            "issues_found"       : json.dumps(qr.warnings),
            "actions_taken"      : json.dumps(qr.actions),
        })

    if rows:
        df_reports = pd.DataFrame(rows)
        df_reports.to_sql(
            name      = "quality_reports",
            con       = engine,
            if_exists = "append",
            index     = False,
        )
        logger.info("Saved %d quality report row(s) to quality_reports.", len(rows))


def _save_relationships(
    session_id    : str,
    relationships : list[dict],
    engine        : Engine,
) -> None:
    """
    Save detected relationships to the detected_relationships table.
    One row per relationship.
    """
    if not relationships:
        return

    rows = []
    for rel in relationships:
        rows.append({
            "session_id"    : session_id,
            "from_table"    : rel["from_table"],
            "from_column"   : rel["from_column"],
            "to_table"      : rel["to_table"],
            "to_column"     : rel["to_column"],
            "confidence"    : rel["confidence"],
            "match_percent" : rel["match_percent"],
            "view_name"     : rel.get("view_name"),
        })

    df_rels = pd.DataFrame(rows)
    df_rels.to_sql(
        name      = "detected_relationships",
        con       = engine,
        if_exists = "append",
        index     = False,
    )
    logger.info("Saved %d relationship(s) to detected_relationships.", len(rows))


def _save_uploaded_files(
    session_id     : str,
    cleaned_tables : list,
    session_profile: object,
    engine         : Engine,
) -> None:
    """
    Save one record per uploaded file to the uploaded_files table.
    """
    # Build a quick lookup from table_name → FileProfile for size/encoding info
    profile_map = {
        fp.table_name: fp
        for fp in session_profile.files
    }

    rows = []
    for cleaned in cleaned_tables:
        fp = profile_map.get(cleaned.table_name)
        rows.append({
            "session_id"       : session_id,
            "original_filename": cleaned.cleaning_log.table_name,
            "table_name"       : cleaned.table_name,
            "file_size_bytes"  : None,        # not stored in CleanedTable
            "row_count"        : cleaned.cleaning_log.final_rows,
            "column_count"     : len(cleaned.df.columns),
            "encoding"         : fp.encoding if fp else None,
        })

    if rows:
        df_files = pd.DataFrame(rows)
        df_files.to_sql(
            name      = "uploaded_files",
            con       = engine,
            if_exists = "append",
            index     = False,
        )
        logger.info("Saved %d uploaded_files record(s).", len(rows))