"""
upload.py
---------
POST /api/upload — accepts file(s) and runs the full ETL pipeline.

This is the trigger for the entire platform:
    1. User uploads 1 CSV or multiple CSVs (or a ZIP)
    2. Schema detection runs
    3. ETL cleaning runs
    4. Data loads into PostgreSQL
    5. SQL VIEWs created
    6. Returns session_id + schema profile to the frontend
"""

import logging
import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Header, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from api.config import retry_with_backoff
from api.routes.auth import auth_enabled, require_auth
from etl.pipeline import run_pipeline
from etl.job_queue import ETLJob, get_etl_queue
from etl.loader import _upsert_upload_session
from etl.pipeline import get_engine
from etl.storage import get_upload_storage

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SUPPORTED_TYPES = {".csv", ".xlsx", ".xls", ".zip"}


def async_etl_enabled() -> bool:
    return os.getenv("ETL_ASYNC", "false").strip().lower() in {"1", "true", "yes"}


async def stage_upload_files(files: list[UploadFile], session_id: str) -> list[str]:
    staging_dir = Path(os.getenv("UPLOAD_STAGING_DIR", "data/staging"))
    staging_dir.mkdir(parents=True, exist_ok=True)
    storage = get_upload_storage()
    staged_paths = []
    for file in files:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(file.filename or "upload").name)
        destination = staging_dir / f"{session_id}_{safe_name}"
        await file.seek(0)
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)
        staged_paths.append(storage.put(destination, destination.name))
    return staged_paths


def validate_upload_files(files: list[UploadFile]) -> None:
    """Reject unsupported file types and excessive upload sizes before the ETL runs."""
    if not files:
        raise ValueError("No files provided.")

    for f in files:
        filename = getattr(f, "filename", "") or ""
        suffix = "." + filename.split(".")[-1].lower() if "." in filename else ""
        if suffix not in SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported file type '{suffix}' for file '{filename}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_TYPES))}"
            )

        stream = getattr(f, "file", None)
        if stream is not None:
            try:
                size = None
                try:
                    current_pos = stream.tell()
                except (AttributeError, OSError, ValueError):
                    current_pos = None

                try:
                    if hasattr(stream, "seek"):
                        stream.seek(0, 2)
                        size = stream.tell()
                        if current_pos is not None:
                            stream.seek(current_pos)
                        else:
                            stream.seek(0)
                    else:
                        size = len(stream.read())
                except (AttributeError, OSError, ValueError):
                    size = len(stream.read())

                if size is not None and size > MAX_UPLOAD_BYTES:
                    raise ValueError(
                        f"File '{filename}' is too large ({size} bytes). "
                        f"Maximum supported size is {MAX_UPLOAD_BYTES} bytes."
                    )
            except (AttributeError, OSError):
                pass


@router.post("/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    authorization: str | None = Header(default=None),
):
    """
    Upload one or more CSV/Excel files (or a ZIP containing them).
    Triggers the full ETL pipeline and returns the session profile.

    How to call this from Thunder Client or Streamlit:
        Method  : POST
        URL     : http://localhost:8000/api/upload
        Body    : form-data
        Key     : files (type = File)
        Value   : select your CSV file(s)

    Returns:
        session_id      : use this for all subsequent API calls
        status          : 'done' | 'partial' | 'error'
        tables_loaded   : number of tables created in PostgreSQL
        total_rows      : total rows across all tables
        views_created   : list of SQL VIEW names created
        schema_summary  : full schema profile (column types, quality scores, relationships)
    """
    if auth_enabled():
        require_auth(authorization)

    try:
        validate_upload_files(files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("Received %d file(s) for upload: %s", len(files), [f.filename for f in files])

    try:
        if async_etl_enabled():
            session_id = str(uuid4())
            staged_paths = await stage_upload_files(files, session_id)
            engine = get_engine()
            _upsert_upload_session(
                session_id=session_id,
                status="pending",
                total_files=len(files),
                engine=engine,
            )
            get_etl_queue().enqueue(ETLJob(session_id, staged_paths))
            return JSONResponse(
                status_code=202,
                content={
                    "session_id": session_id,
                    "status": "pending",
                    "tables_loaded": 0,
                    "total_rows": 0,
                    "views_created": [],
                    "master_view_name": None,
                    "errors": [],
                    "schema_summary": {"files": [], "relationships": [], "total_rows": 0},
                },
            )

        # Run the full pipeline — this is synchronous and may take 10-60 seconds
        # for large files. In production you would use a background task queue.
        result = retry_with_backoff(run_pipeline, files=files, max_attempts=2)

        return JSONResponse(
            status_code = 200 if result.status == "done" else 207,
            content     = result.to_api_response()
        )

    except Exception as e:
        logger.error("Upload pipeline failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")