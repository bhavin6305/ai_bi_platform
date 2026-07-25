"""
pipeline.py
-----------
Orchestrator for the full ETL pipeline.

This is the single entry point that the FastAPI upload route calls.
It runs all steps in sequence and returns a complete result.

Full flow:
    profile_upload()          ← schema_detection module
         ↓
    extract_from_profile()    ← etl/extractor.py
         ↓
    clean_all_tables()        ← etl/cleaner.py
         ↓
    load_session()            ← etl/loader.py
         ↓
    create_join_views()       ← etl/joiner.py
         ↓
    PipelineResult            ← returned to FastAPI route

The pipeline updates the upload_session.status at each step so
the Streamlit frontend can show a live progress indicator by
polling GET /api/status/{session_id}.
"""

import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from schema_detection import profile_upload, SessionProfile
from etl.extractor import extract_from_profile, ExtractResult
from etl.cleaner   import clean_all_tables
from etl.loader    import load_session, _upsert_upload_session
from etl.joiner    import create_join_views
from analytics import run_analytics
load_dotenv()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Output data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """
    Complete result of running the ETL pipeline for one upload session.
    Returned to the FastAPI route which converts it to a JSON response.
    """
    session_id       : str
    status           : str           # 'done' | 'partial' | 'error'
    tables_loaded    : int
    total_rows       : int
    views_created    : list[str] = field(default_factory=list)
    master_view_name : str = None
    errors           : list[str] = field(default_factory=list)
    schema_summary   : dict = field(default_factory=dict)    # for API response

    def to_api_response(self) -> dict:
        return {
            "session_id"      : self.session_id,
            "status"          : self.status,
            "tables_loaded"   : self.tables_loaded,
            "total_rows"      : self.total_rows,
            "views_created"   : self.views_created,
            "master_view_name": self.master_view_name,
            "errors"          : self.errors,
            "schema_summary"  : self.schema_summary,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Database engine
# ─────────────────────────────────────────────────────────────────────────────

def get_engine() -> Engine:
    """
    Create a SQLAlchemy engine from environment variables.

    Reads from .env file:
        DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

    Connection pool settings:
        pool_size=5      — keep 5 connections open (good for FastAPI)
        max_overflow=10  — allow up to 10 extra connections under load
        pool_pre_ping=True — test connections before using (prevents stale conn errors)
    """
    db_url = (
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', '')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'ai_bi_platform')}"
    )

    engine = create_engine(
        db_url,
        pool_size      = 5,
        max_overflow   = 10,
        pool_pre_ping  = True,
    )

    return engine


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(
    files      : list,
    session_id : str = None,
    engine     : Engine = None,
) -> PipelineResult:
    """
    Run the full ETL pipeline for one upload session.

    Parameters
    ----------
    files : list
        List of FastAPI UploadFile objects OR file paths (for CLI/testing).
    session_id : str, optional
        If not provided, generated inside profile_upload().
    engine : Engine, optional
        If not provided, created from .env variables.

    Returns
    -------
    PipelineResult
    """
    if engine is None:
        engine = get_engine()

    # ── Step 1: Schema Detection ───────────────────────────────────────────
    logger.info("Pipeline Step 1/5: Schema Detection")
    try:
        session_profile = profile_upload(files=files, session_id=session_id)
        session_id      = session_profile.session_id

        # Update status immediately so frontend can show progress
        _upsert_upload_session(
            session_id  = session_id,
            status      = "profiling",
            total_files = len(session_profile.files),
            engine      = engine,
        )
    except Exception as e:
        logger.error("Pipeline failed at schema detection: %s", e)
        return PipelineResult(
            session_id    = session_id or "unknown",
            status        = "error",
            tables_loaded = 0,
            total_rows    = 0,
            errors        = [f"Schema detection failed: {e}"],
        )

    # ── Step 2: Extraction ─────────────────────────────────────────────────
    logger.info("Pipeline Step 2/5: Extraction")
    _upsert_upload_session(session_id=session_id, status="extracting", engine=engine)
    try:
        extract_result = extract_from_profile(session_profile)
    except Exception as e:
        logger.error("Pipeline failed at extraction: %s", e)
        _upsert_upload_session(session_id=session_id, status="error", engine=engine)
        return PipelineResult(
            session_id    = session_id,
            status        = "error",
            tables_loaded = 0,
            total_rows    = 0,
            errors        = [f"Extraction failed: {e}"],
        )

    # ── Step 3: Cleaning ───────────────────────────────────────────────────
    logger.info("Pipeline Step 3/5: Cleaning")
    _upsert_upload_session(session_id=session_id, status="cleaning", engine=engine)
    try:
        cleaned_tables = clean_all_tables(extract_result.tables)
    except Exception as e:
        logger.error("Pipeline failed at cleaning: %s", e)
        _upsert_upload_session(session_id=session_id, status="error", engine=engine)
        return PipelineResult(
            session_id    = session_id,
            status        = "error",
            tables_loaded = 0,
            total_rows    = 0,
            errors        = [f"Cleaning failed: {e}"],
        )

    # ── Step 4: Loading ────────────────────────────────────────────────────
    logger.info("Pipeline Step 4/5: Loading into PostgreSQL")
    _upsert_upload_session(session_id=session_id, status="loading", engine=engine)
    try:
        load_summary = load_session(
            session_id      = session_id,
            cleaned_tables  = cleaned_tables,
            relationships   = extract_result.relationships,
            session_profile = session_profile,
            engine          = engine,
        )
    except Exception as e:
        logger.error("Pipeline failed at loading: %s", e)
        _upsert_upload_session(session_id=session_id, status="error", engine=engine)
        return PipelineResult(
            session_id    = session_id,
            status        = "error",
            tables_loaded = 0,
            total_rows    = 0,
            errors        = [f"Loading failed: {e}"],
        )

    # ── Step 5: Creating Join Views ────────────────────────────────────────
    logger.info("Pipeline Step 5/5: Creating SQL Views")
    _upsert_upload_session(session_id=session_id, status="joining", engine=engine)
    try:
        join_result = create_join_views(
            session_id    = session_id,
            relationships = extract_result.relationships,
            engine        = engine,
        )
    except Exception as e:
        # Non-fatal — views are a convenience feature
        logger.warning("View creation failed (non-fatal): %s", e)
        join_result = None
# ── Step 6: Run Analytics Engine ──────────────────────────────────────
    logger.info("Pipeline Step 6/6: Running Analytics Engine")
    _upsert_upload_session(session_id=session_id, status="analyzing", engine=engine)
    try:
        # Build schema_profiles dict from the session profile
        schema_profiles = {
            fp.table_name: fp.columns
            for fp in session_profile.files
        }
        
        analytics_result = run_analytics(
            session_id      = session_id,
            schema_profiles = schema_profiles,
            engine          = engine,
        )

        # Also create analytical SQL views for AI chatbot to query
        from analytics.sql_views import create_analytical_views
        analytical_views = create_analytical_views(
            session_id      = session_id,
            schema_profiles = schema_profiles,
            relationships   = extract_result.relationships,
            engine          = engine,
        )
        logger.info("Created %d analytical view(s).", len(analytical_views))
        logger.info("Analytics: %s", analytics_result)
    except Exception as e:
        # Non-fatal — analytics failure should not fail the whole upload
        logger.warning("Analytics engine failed (non-fatal): %s", e)
    # ── Build final result ─────────────────────────────────────────────────
    _upsert_upload_session(session_id=session_id, status="done", engine=engine)

    return PipelineResult(
        session_id       = session_id,
        status           = load_summary.get("status", "done"),
        tables_loaded    = load_summary.get("tables_loaded", 0),
        total_rows       = load_summary.get("total_rows", 0),
        views_created    = join_result.views_created if join_result else [],
        master_view_name = join_result.master_view_name if join_result else None,
        errors           = load_summary.get("errors", []),
        schema_summary   = session_profile.to_api_response(),
    )


def run_pipeline_from_paths(file_paths: list[str]) -> PipelineResult:
    """
    Convenience wrapper — run the pipeline directly from file paths.
    Used for CLI testing and development.

    Example:
        result = run_pipeline_from_paths([
            'data/raw/olist_orders_dataset.csv',
            'data/raw/olist_customers_dataset.csv',
        ])
        print(result.status)
    """
    return run_pipeline(files=file_paths)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point for manual testing
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Run the full ETL pipeline from the command line on Olist test data.

    Usage (from project root with venv active):
        python etl/pipeline.py
    """
    import logging
    logging.basicConfig(
        level  = logging.INFO,
        format = "%(levelname)s | %(name)s | %(message)s"
    )

    TEST_FILES = [
        "data/raw/olist_orders_dataset.csv",
        "data/raw/olist_customers_dataset.csv",
        "data/raw/olist_order_items_dataset.csv",
        "data/raw/olist_products_dataset.csv",
    ]

    print("\n" + "=" * 60)
    print("Running full ETL pipeline on Olist test data...")
    print("=" * 60 + "\n")

    result = run_pipeline_from_paths(TEST_FILES)

    print("\n" + "=" * 60)
    print("PIPELINE RESULT")
    print("=" * 60)
    print(f"Session ID    : {result.session_id}")
    print(f"Status        : {result.status}")
    print(f"Tables loaded : {result.tables_loaded}")
    print(f"Total rows    : {result.total_rows:,}")
    print(f"Views created : {result.views_created}")
    print(f"Master view   : {result.master_view_name}")
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for err in result.errors:
            print(f"  - {err}")
    else:
        print("\n✓ No errors.")
    print("=" * 60)