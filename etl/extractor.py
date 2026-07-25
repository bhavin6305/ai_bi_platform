"""
extractor.py
------------
Extraction layer of the ETL pipeline.

In a normal ETL, the extractor reads raw files from disk or an API.
In our platform, the files have ALREADY been read into DataFrames by
the schema detection profiler (profiler.py).

So the extractor's job here is:
    1. Accept the SessionProfile produced by profiler.py
    2. Return the raw DataFrames + their metadata in a clean structure
       that the cleaner can consume
    3. Optionally re-read files from disk if called standalone (for testing)

This avoids reading the same files twice — profiler already loaded them
into memory. We just pass them through.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from schema_detection import profile_upload, SessionProfile

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Output data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExtractedTable:
    """
    One extracted table ready for cleaning.
    Carries everything the cleaner needs alongside the DataFrame.
    """
    table_name        : str            # dynamic name: 'a3f2c1d4_orders'
    original_filename : str            # 'orders.csv'
    df                : pd.DataFrame   # raw DataFrame — NOT yet cleaned
    schema_columns    : list[dict]     # output of type_detector for this table
    quality_report    : object         # QualityReport dataclass instance
    row_count         : int
    column_count      : int


@dataclass
class ExtractResult:
    """
    Full extraction result for one upload session.
    Passed directly to the cleaner.
    """
    session_id    : str
    tables        : list[ExtractedTable]
    relationships : list[dict]    # detected FK/PK relationships
    session_profile: SessionProfile  # full profile for DB storage


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def extract_from_profile(session_profile: SessionProfile) -> ExtractResult:
    """
    Build an ExtractResult from an already-computed SessionProfile.

    This is the PRIMARY path used by the FastAPI upload route:
        1. FastAPI calls profile_upload() → SessionProfile
        2. FastAPI calls extract_from_profile(profile) → ExtractResult
        3. ExtractResult is passed to the cleaner

    No files are re-read from disk. DataFrames come from profile.tables.

    Parameters
    ----------
    session_profile : SessionProfile
        Output of schema_detection.profile_upload()

    Returns
    -------
    ExtractResult
    """
    logger.info(
        "Extracting %d table(s) from session profile '%s'.",
        len(session_profile.files), session_profile.session_id
    )

    extracted_tables = []

    for file_profile in session_profile.files:
        table_name = file_profile.table_name

        # Get the DataFrame from the profile's tables dict
        if table_name not in session_profile.tables:
            logger.error(
                "Table '%s' found in profile but missing from profile.tables dict. Skipping.",
                table_name
            )
            continue

        df = session_profile.tables[table_name]

        extracted_table = ExtractedTable(
            table_name        = table_name,
            original_filename = file_profile.original_filename,
            df                = df.copy(),   # copy so original profile.tables is untouched
            schema_columns    = file_profile.columns,
            quality_report    = file_profile.quality_report,
            row_count         = file_profile.row_count,
            column_count      = file_profile.column_count,
        )

        extracted_tables.append(extracted_table)

        logger.info(
            "Extracted table '%s' — %d rows × %d cols.",
            table_name, file_profile.row_count, file_profile.column_count
        )

    return ExtractResult(
        session_id     = session_profile.session_id,
        tables         = extracted_tables,
        relationships  = session_profile.relationships,
        session_profile= session_profile,
    )


def extract_from_files(file_paths: list[str], session_id: str = None) -> ExtractResult:
    """
    Extract directly from file paths on disk.

    Used for:
        - Running the ETL pipeline from the command line
        - Testing without a FastAPI upload
        - Reprocessing files that were already uploaded

    Parameters
    ----------
    file_paths : list[str]
        List of absolute or relative file paths to CSV/Excel files.
    session_id : str, optional
        If not provided, a new UUID is generated.

    Returns
    -------
    ExtractResult
    """
    logger.info("Extracting %d file(s) from disk.", len(file_paths))

    # Validate all paths exist before starting
    for path in file_paths:
        if not Path(path).exists():
            raise FileNotFoundError(f"File not found: '{path}'")

    # Reuse the profiler — it handles file loading internally
    session_profile = profile_upload(
        files      = file_paths,
        session_id = session_id,
    )

    return extract_from_profile(session_profile)