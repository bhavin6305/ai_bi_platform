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

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from etl.pipeline import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
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
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    # Validate file types before running the pipeline
    supported = {".csv", ".xlsx", ".xls", ".zip"}
    for f in files:
        suffix = "." + f.filename.split(".")[-1].lower() if "." in f.filename else ""
        if suffix not in supported:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}' for file '{f.filename}'. "
                       f"Supported: {', '.join(supported)}"
            )

    logger.info("Received %d file(s) for upload: %s", len(files), [f.filename for f in files])

    try:
        # Run the full pipeline — this is synchronous and may take 10-60 seconds
        # for large files. In production you would use a background task queue.
        result = run_pipeline(files=files)

        return JSONResponse(
            status_code = 200 if result.status == "done" else 207,
            content     = result.to_api_response()
        )

    except Exception as e:
        logger.error("Upload pipeline failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")