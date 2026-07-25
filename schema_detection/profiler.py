"""
profiler.py
-----------
Entry point for the schema detection module.

This is the ONLY file the rest of the system (FastAPI route, ETL pipeline)
needs to import from schema_detection. It orchestrates:

    1. Load file(s) into DataFrames  (handles single file AND folder/zip)
    2. Detect column types           (type_detector.py)
    3. Detect relationships          (relationship_detector.py)
    4. Generate quality reports      (quality_reporter.py)
    5. Return a single SessionProfile object

Usage from FastAPI upload route:
    from schema_detection.profiler import profile_upload

    result = profile_upload(
        files       = [uploaded_file_1, uploaded_file_2],
        session_id  = "a3f2c1d4-...",
    )
    # result is a SessionProfile — convert to dict for JSON response

Usage from ETL pipeline:
    # ETL reads result.tables (the DataFrames) directly — no re-reading files
    for table_name, df in result.tables.items():
        etl_pipeline.process(df, table_name)
"""

import io
import logging
import re
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

import chardet
import pandas as pd

from schema_detection.type_detector       import detect_all_columns
from schema_detection.relationship_detector import detect_relationships
from schema_detection.quality_reporter    import generate_quality_report, QualityReport

logger = logging.getLogger(__name__)

# ── Supported file extensions ──────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


# ─────────────────────────────────────────────────────────────────────────────
# Output data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FileProfile:
    """Profile for one uploaded file/table."""
    original_filename : str
    table_name        : str               # dynamic name: '{short_session_id}_{stem}'
    row_count         : int
    column_count      : int
    encoding          : str
    columns           : list[dict]        # output of detect_all_columns()
    quality_report    : QualityReport


@dataclass
class SessionProfile:
    """
    Complete profile for one upload session (one or many files).
    This is what gets returned to the FastAPI route and stored in the DB.
    """
    session_id      : str
    files           : list[FileProfile]
    relationships   : list[dict]          # output of detect_relationships()
    overall_quality : int                 # average quality score across all files
    tables          : dict                # {table_name: pd.DataFrame} — for ETL to consume
                                         # NOT serialised to JSON (DataFrames are not JSON-safe)

    def to_api_response(self) -> dict:
        """
        Convert to a JSON-serialisable dict for the API response.
        Excludes 'tables' (DataFrames cannot be serialised).
        """
        return {
            "session_id"      : self.session_id,
            "overall_quality" : self.overall_quality,
            "files": [
                {
                    "original_filename" : f.original_filename,
                    "table_name"        : f.table_name,
                    "row_count"         : f.row_count,
                    "column_count"      : f.column_count,
                    "encoding"          : f.encoding,
                    "columns"           : f.columns,
                    "quality": {
                        "score"              : f.quality_report.quality_score,
                        "summary"            : f.quality_report.summary,
                        "duplicate_rows"     : f.quality_report.duplicate_rows,
                        "columns_with_nulls" : f.quality_report.columns_with_nulls,
                        "outlier_columns"    : f.quality_report.outlier_columns,
                        "issues_found"       : f.quality_report.issues_found,
                        "actions_taken"      : f.quality_report.actions_taken,
                    },
                }
                for f in self.files
            ],
            "relationships": self.relationships,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def profile_upload(
    files      : list,          # list of FastAPI UploadFile objects OR file paths
    session_id : str = None,
) -> SessionProfile:
    """
    Profile one or more uploaded files and return a complete SessionProfile.

    Handles:
        - Single CSV or Excel file
        - Multiple CSV/Excel files uploaded together
        - A ZIP file containing multiple CSVs/Excel files

    Parameters
    ----------
    files : list
        List of FastAPI UploadFile objects.
        Each has .filename (str) and .file (file-like object).
    session_id : str, optional
        If not provided, a new UUID4 is generated automatically.

    Returns
    -------
    SessionProfile
        Complete profile including DataFrames, column types, relationships,
        and quality reports for all uploaded files.
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    short_id = _get_short_id(session_id)
    logger.info("Starting profile for session '%s' (%d file(s) received).", session_id, len(files))

    # ── Step 1: Load all files into DataFrames ─────────────────────────────
    # This handles CSV, Excel, and ZIP files transparently.
    loaded = _load_all_files(files, short_id)

    if not loaded:
        raise ValueError("No supported files found in upload. Supported: .csv, .xlsx, .xls, .zip")

    # ── Step 2: Run detection on each table ────────────────────────────────
    file_profiles   = []
    all_tables      = {}        # {table_name: df} — for relationship detection + ETL
    all_profiles    = {}        # {table_name: columns} — for relationship detection

    for table_name, original_filename, df, encoding in loaded:
        logger.info("Profiling table '%s' (%d rows, %d cols).", table_name, len(df), len(df.columns))

        # Detect column types
        columns = detect_all_columns(df)

        # Generate quality report
        quality_report = generate_quality_report(df, table_name, columns)

        file_profile = FileProfile(
            original_filename = original_filename,
            table_name        = table_name,
            row_count         = len(df),
            column_count      = len(df.columns),
            encoding          = encoding,
            columns           = columns,
            quality_report    = quality_report,
        )

        file_profiles.append(file_profile)
        all_tables[table_name]   = df
        all_profiles[table_name] = columns

    # ── Step 3: Detect relationships across tables ─────────────────────────
    relationships = []
    if len(all_tables) >= 2:
        relationships = detect_relationships(all_tables, all_profiles)
        logger.info("%d relationship(s) detected.", len(relationships))
    else:
        logger.info("Single table upload — skipping relationship detection.")

    # ── Step 4: Calculate overall quality score ────────────────────────────
    # Simple average across all tables
    if file_profiles:
        overall_quality = int(
            sum(fp.quality_report.quality_score for fp in file_profiles) / len(file_profiles)
        )
    else:
        overall_quality = 0

    session_profile = SessionProfile(
        session_id      = session_id,
        files           = file_profiles,
        relationships   = relationships,
        overall_quality = overall_quality,
        tables          = all_tables,
    )

    logger.info(
        "Session '%s' profiling complete. %d table(s), %d relationship(s), overall quality=%d.",
        session_id, len(file_profiles), len(relationships), overall_quality
    )

    return session_profile


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_short_id(session_id: str) -> str:
    """
    Extract first 8 characters of the session UUID (without hyphens).
    Used as the prefix for dynamic table names.

    Example:
        'a3f2c1d4-9b8e-4f2a-b1c3-d4e5f6a7b8c9' → 'a3f2c1d4'
    """
    return session_id.replace('-', '')[:8]


def _make_table_name(short_id: str, filename: str) -> str:
    """
    Build a safe PostgreSQL table name from session short ID + filename.

    Rules:
        - Lowercase
        - Replace spaces, hyphens, dots with underscores
        - Remove any character that is not alphanumeric or underscore
        - Remove the file extension
        - Prefix with short session ID

    Example:
        short_id = 'a3f2c1d4'
        filename = 'Sales Data 2024.csv'
        result   = 'a3f2c1d4_sales_data_2024'
    """
    stem = Path(filename).stem                        # remove extension
    stem = stem.lower()
    stem = re.sub(r'[\s\-\.]+', '_', stem)           # spaces/hyphens/dots → underscore
    stem = re.sub(r'[^a-z0-9_]', '', stem)           # remove invalid chars
    stem = stem.strip('_')                            # remove leading/trailing underscores
    stem = re.sub(r'_+', '_', stem)                  # collapse multiple underscores

    if not stem:
        # Filename had no usable characters — use a generic name
        stem = "table"

    return f"{short_id}_{stem}"


def _detect_encoding(raw_bytes: bytes) -> str:
    """
    Detect the character encoding of a file's raw bytes using chardet.

    Falls back to 'utf-8' if detection fails or confidence is low.
    """
    result = chardet.detect(raw_bytes)
    encoding   = result.get("encoding") or "utf-8"
    confidence = result.get("confidence") or 0.0

    if confidence < 0.7:
        logger.debug(
            "Low encoding confidence (%.0f%%) — defaulting to utf-8.", confidence * 100
        )
        encoding = "utf-8"

    return encoding


def _read_csv(raw_bytes: bytes, encoding: str) -> pd.DataFrame:
    """
    Read a CSV file from raw bytes, trying multiple fallback encodings.

    The fallback chain handles the most common encoding issues in real-world files:
        1. Detected encoding (e.g. 'utf-8', 'iso-8859-1', 'windows-1252')
        2. utf-8 with BOM (common in Excel-exported CSVs)
        3. latin-1 (covers most Western European special characters)

    Parameters
    ----------
    raw_bytes : bytes  — raw file content
    encoding  : str    — encoding detected by chardet

    Returns
    -------
    pd.DataFrame
    """
    fallback_encodings = [encoding, "utf-8-sig", "latin-1"]

    for enc in fallback_encodings:
        try:
            df = pd.read_csv(
                io.BytesIO(raw_bytes),
                encoding      = enc,
                low_memory    = False,   # avoids mixed-type warnings on large files
                on_bad_lines  = 'warn',  # skip malformed rows with a warning (not error)
            )
            logger.debug("CSV read successfully with encoding '%s'.", enc)
            return df
        except (UnicodeDecodeError, pd.errors.ParserError) as e:
            logger.debug("Encoding '%s' failed: %s", enc, e)
            continue

    raise ValueError(f"Could not read CSV file with any of: {fallback_encodings}")


def _read_excel(raw_bytes: bytes) -> pd.DataFrame:
    """
    Read the first sheet of an Excel file from raw bytes.

    Uses openpyxl engine (handles .xlsx) with xlrd fallback for .xls.
    """
    try:
        df = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=0, engine='openpyxl')
        return df
    except Exception:
        # .xls format (older Excel) — openpyxl doesn't support it
        df = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=0)
        return df


def _load_single_file(
    raw_bytes        : bytes,
    original_filename: str,
    short_id         : str,
) -> tuple[str, str, pd.DataFrame, str]:
    """
    Load one file (CSV or Excel) from raw bytes into a DataFrame.

    Returns
    -------
    tuple: (table_name, original_filename, df, encoding)
    """
    ext = Path(original_filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}' for file '{original_filename}'. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    table_name = _make_table_name(short_id, original_filename)

    if ext == ".csv":
        encoding = _detect_encoding(raw_bytes)
        df       = _read_csv(raw_bytes, encoding)
    else:
        # Excel — encoding is not applicable (binary format)
        encoding = "binary"
        df       = _read_excel(raw_bytes)

    # Standardise column names: strip whitespace, no leading/trailing spaces
    df.columns = [str(col).strip() for col in df.columns]

    logger.info(
        "Loaded '%s' → table '%s' | %d rows × %d cols | encoding: %s",
        original_filename, table_name, len(df), len(df.columns), encoding
    )

    return table_name, original_filename, df, encoding


def _load_all_files(
    files    : list,
    short_id : str,
) -> list[tuple[str, str, pd.DataFrame, str]]:
    """
    Load all uploaded files. Handles:
        - Direct CSV/Excel files
        - ZIP file containing multiple CSV/Excel files

    Returns
    -------
    list of tuples: [(table_name, original_filename, df, encoding), ...]
    """
    results = []

    for upload_file in files:
        # Support both FastAPI UploadFile objects and plain file paths (for testing)
        if hasattr(upload_file, 'filename'):
            # FastAPI UploadFile
            filename  = upload_file.filename
            raw_bytes = upload_file.file.read()
        elif isinstance(upload_file, (str, Path)):
            # File path (used in tests and CLI usage)
            path      = Path(upload_file)
            filename  = path.name
            raw_bytes = path.read_bytes()
        else:
            logger.warning("Unknown file type in upload list — skipping: %s", type(upload_file))
            continue

        ext = Path(filename).suffix.lower()

        if ext == ".zip":
            # Extract and load all CSV/Excel files from inside the ZIP
            zip_results = _load_from_zip(raw_bytes, short_id, parent_zip=filename)
            results.extend(zip_results)
        elif ext in SUPPORTED_EXTENSIONS:
            result = _load_single_file(raw_bytes, filename, short_id)
            results.append(result)
        else:
            logger.warning("Skipping unsupported file: '%s'", filename)

    return results


def _load_from_zip(
    zip_bytes  : bytes,
    short_id   : str,
    parent_zip : str,
) -> list[tuple[str, str, pd.DataFrame, str]]:
    """
    Extract and load all CSV/Excel files from a ZIP archive.

    Ignores:
        - Hidden files (starting with '.')
        - macOS metadata files ('__MACOSX' folder)
        - Files in subdirectories (only reads top-level files)
        - Unsupported file types

    Parameters
    ----------
    zip_bytes  : bytes  — raw bytes of the ZIP file
    short_id   : str    — session short ID for table naming
    parent_zip : str    — name of the ZIP file (for logging)

    Returns
    -------
    list of (table_name, filename, df, encoding) tuples
    """
    results = []

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for zip_info in zf.infolist():
                filename = zip_info.filename

                # Skip directories, hidden files, and macOS metadata
                if (
                    zip_info.is_dir()
                    or filename.startswith('.')
                    or '__MACOSX' in filename
                    or Path(filename).name.startswith('.')
                ):
                    continue

                ext = Path(filename).suffix.lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    logger.debug("Skipping non-data file in ZIP: '%s'", filename)
                    continue

                # Use only the base filename (not the full path inside ZIP)
                base_filename = Path(filename).name
                raw_bytes     = zf.read(zip_info.filename)

                try:
                    result = _load_single_file(raw_bytes, base_filename, short_id)
                    results.append(result)
                except Exception as e:
                    logger.warning(
                        "Failed to load '%s' from ZIP '%s': %s",
                        filename, parent_zip, e
                    )

    except zipfile.BadZipFile:
        raise ValueError(f"'{parent_zip}' is not a valid ZIP file.")

    logger.info(
        "Loaded %d file(s) from ZIP '%s'.", len(results), parent_zip
    )
    return results