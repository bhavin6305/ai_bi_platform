"""
schema.py
---------
GET /api/schema/{session_id} — returns detected schema for a session.
GET /api/status/{session_id} — returns current pipeline status.

The Streamlit frontend polls /api/status/{session_id} to show a
live progress bar while the pipeline runs.
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from api.database import get_engine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/schema/{session_id}")
def get_schema(session_id: str):
    """
    Return the full schema profile for a session.

    Reads from: schema_profiles, detected_relationships, quality_reports tables.

    Returns:
        session_id    : str
        tables        : list of table profiles (columns, types, quality)
        relationships : list of FK/PK relationships detected
    """
    engine = get_engine()

    with engine.connect() as conn:
        # Check session exists
        session = conn.execute(
            text("SELECT session_id, status FROM upload_sessions WHERE session_id = :sid"),
            {"sid": session_id}
        ).fetchone()

        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{session_id}' not found."
            )

        # Get schema profiles grouped by table
        profiles = conn.execute(
            text("""
                SELECT table_name, column_name, detected_type,
                       null_count, null_percent, unique_count,
                       sample_values, column_order
                FROM schema_profiles
                WHERE session_id = :sid
                ORDER BY table_name, column_order
            """),
            {"sid": session_id}
        ).fetchall()

        # Get relationships
        relationships = conn.execute(
            text("""
                SELECT from_table, from_column, to_table, to_column,
                       confidence, match_percent, view_name
                FROM detected_relationships
                WHERE session_id = :sid
            """),
            {"sid": session_id}
        ).fetchall()

        # Get quality reports
        quality = conn.execute(
            text("""
                SELECT table_name, quality_score, total_rows,
                       duplicate_rows, columns_with_nulls, outlier_columns,
                       issues_found, actions_taken
                FROM quality_reports
                WHERE session_id = :sid
            """),
            {"sid": session_id}
        ).fetchall()

    # Group profiles by table_name
    tables_dict = {}
    for row in profiles:
        tname = row[0]
        if tname not in tables_dict:
            tables_dict[tname] = {"table_name": tname, "columns": []}
        tables_dict[tname]["columns"].append({
            "column_name"  : row[1],
            "detected_type": row[2],
            "null_count"   : row[3],
            "null_percent" : row[4],
            "unique_count" : row[5],
            "sample_values": json.loads(row[6]) if row[6] else [],
            "column_order" : row[7],
        })

    # Attach quality report to each table
    quality_map = {row[0]: row for row in quality}
    for tname, tdata in tables_dict.items():
        qr = quality_map.get(tname)
        if qr:
            tdata["quality"] = {
                "score"              : qr[1],
                "total_rows"         : qr[2],
                "duplicate_rows"     : qr[3],
                "columns_with_nulls" : qr[4],
                "outlier_columns"    : qr[5],
                "issues_found"       : json.loads(qr[6]) if qr[6] else [],
                "actions_taken"      : json.loads(qr[7]) if qr[7] else [],
            }

    return {
        "session_id"   : session_id,
        "tables"       : list(tables_dict.values()),
        "relationships": [
            {
                "from_table"   : r[0], "from_column": r[1],
                "to_table"     : r[2], "to_column"  : r[3],
                "confidence"   : r[4], "match_percent": r[5],
                "view_name"    : r[6],
            }
            for r in relationships
        ],
    }


@router.get("/status/{session_id}")
def get_status(session_id: str):
    """
    Return the current pipeline status for a session.
    Streamlit polls this to show a live progress bar.

    Status values:
        'pending'    → upload received, not started
        'profiling'  → schema detection running
        'extracting' → extraction running
        'cleaning'   → ETL cleaning running
        'loading'    → loading into PostgreSQL
        'joining'    → creating SQL VIEWs
        'done'       → pipeline complete
        'error'      → pipeline failed
    """
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT session_id, status, total_files, total_rows,
                       error_message, created_at, completed_at
                FROM upload_sessions
                WHERE session_id = :sid
            """),
            {"sid": session_id}
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return {
        "session_id"   : row[0],
        "status"       : row[1],
        "total_files"  : row[2],
        "total_rows"   : row[3],
        "error_message": row[4],
        "created_at"   : str(row[5]) if row[5] else None,
        "completed_at" : str(row[6]) if row[6] else None,
    }