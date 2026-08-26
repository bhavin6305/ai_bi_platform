"""Downloadable dashboard report endpoints."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from analytics.filters import DashboardFilters
from api.database import get_engine
from api.routes.analytics import _validated_filters
from reports.pdf_report import build_pdf_report

router = APIRouter()


@router.get("/reports/{session_id}.pdf")
def download_report(
    session_id: str,
    date_column: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category_column: str | None = Query(default=None),
    category_value: str | None = Query(default=None),
):
    """Generate an in-memory PDF matching the current dashboard filters."""
    engine = get_engine()
    filters = _validated_filters(
        session_id, engine, date_column, date_from, date_to, category_column, category_value
    )
    try:
        report = build_pdf_report(session_id, engine, filters)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not generate report: {error}")

    return StreamingResponse(
        report,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="aibi-report-{session_id[:8]}.pdf"',
            "Cache-Control": "no-store",
        },
    )
