"""Build downloadable, in-memory PDF reports for dashboard sessions."""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import text
from sqlalchemy.engine import Engine

from analytics.chart_generator import generate_chart_data
from analytics.filters import DashboardFilters
from analytics.kpi_engine import calculate_kpis


PAGE_MARGIN = 16 * mm
MAX_CHART_ROWS = 12


def build_pdf_report(
    session_id: str,
    engine: Engine,
    filters: DashboardFilters | None = None,
) -> BytesIO:
    """Build a complete report snapshot without writing files to disk."""
    filters = filters or DashboardFilters()
    session, files, profiles, quality, charts, insights = _load_report_data(session_id, engine)
    kpis = calculate_kpis(session_id, profiles, engine, filters=filters, persist=False)

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=PAGE_MARGIN,
        leftMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN,
        title=f"AIBI Report {session_id[:8]}",
        author="AIBI Platform",
    )
    styles = _styles()
    story: list[Any] = [
        Paragraph("AIBI Executive Report", styles["Title"]),
        Paragraph(f"Dataset session {session_id[:8]}", styles["Subtitle"]),
        Spacer(1, 8),
        Paragraph("Report Scope", styles["Heading"]),
        Paragraph(_scope_text(session, filters), styles["Body"]),
        Spacer(1, 8),
        Paragraph("Key Performance Indicators", styles["Heading"]),
        _kpi_table(kpis, styles),
        Spacer(1, 10),
        Paragraph("Uploaded Data", styles["Heading"]),
        _file_table(files, styles),
        Spacer(1, 10),
        Paragraph("Data Quality", styles["Heading"]),
        _quality_table(quality, styles),
        PageBreak(),
        Paragraph("Chart Analysis", styles["Title"]),
        Paragraph(
            "Each section uses the same data and filters as the dashboard snapshot.",
            styles["Body"],
        ),
    ]

    for chart in charts:
        result = generate_chart_data(chart["chart_id"], session_id, engine, filters=filters)
        story.extend(_chart_section(chart, result, insights.get(chart["chart_id"]), styles))

    document.build(story)
    output.seek(0)
    return output


def _load_report_data(session_id: str, engine):
    with engine.connect() as conn:
        session = conn.execute(
            text("""
                SELECT session_id, status, total_files, total_rows, created_at, completed_at
                FROM upload_sessions WHERE session_id = :sid
            """),
            {"sid": session_id},
        ).mappings().one_or_none()
        if not session:
            raise LookupError(f"Session '{session_id}' not found.")

        files = conn.execute(
            text("""
                SELECT original_filename, row_count, column_count, file_size_bytes
                FROM uploaded_files WHERE session_id = :sid ORDER BY file_id
            """),
            {"sid": session_id},
        ).mappings().all()
        profile_rows = conn.execute(
            text("""
                SELECT table_name, column_name, detected_type, unique_count
                FROM schema_profiles WHERE session_id = :sid ORDER BY table_name, column_order
            """),
            {"sid": session_id},
        ).fetchall()
        quality = conn.execute(
            text("""
                SELECT table_name, quality_score, total_rows, duplicate_rows,
                       columns_with_nulls, outlier_columns
                FROM quality_reports WHERE session_id = :sid ORDER BY table_name
            """),
            {"sid": session_id},
        ).mappings().all()
        charts = conn.execute(
            text("""
                SELECT chart_id, chart_type, chart_title, source_table, x_column,
                       y_column, group_by_column, aggregation, rationale
                FROM chart_configs WHERE session_id = :sid ORDER BY chart_order
            """),
            {"sid": session_id},
        ).mappings().all()
        insight_rows = conn.execute(
            text("""
                SELECT chart_id, insight_text FROM ai_insights
                WHERE session_id = :sid AND insight_type = 'chart_insight'
            """),
            {"sid": session_id},
        ).fetchall()

    profiles: dict[str, list[dict]] = {}
    for row in profile_rows:
        profiles.setdefault(row[0], []).append({
            "column_name": row[1],
            "detected_type": row[2],
            "unique_count": row[3],
        })
    return session, files, profiles, quality, charts, {row[0]: row[1] for row in insight_rows}


def _styles():
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle("ReportTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=colors.HexColor("#172554"), alignment=TA_CENTER, spaceAfter=5),
        "Subtitle": ParagraphStyle("ReportSubtitle", parent=base["Normal"], fontSize=10, textColor=colors.HexColor("#64748b"), alignment=TA_CENTER, spaceAfter=14),
        "Heading": ParagraphStyle("ReportHeading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#1e3a8a"), spaceBefore=7, spaceAfter=6),
        "Body": ParagraphStyle("ReportBody", parent=base["BodyText"], fontSize=9, leading=13, textColor=colors.HexColor("#334155")),
        "Small": ParagraphStyle("ReportSmall", parent=base["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#475569")),
    }


def _scope_text(session, filters: DashboardFilters) -> str:
    scope = [f"Status: {session['status']}", f"Rows: {session['total_rows'] or 0:,}"]
    if filters.active:
        if filters.date_from or filters.date_to:
            scope.append(f"Date filter: {filters.date_from or 'any'} to {filters.date_to or 'any'}")
        if filters.category_value:
            scope.append(f"Category filter: {filters.category_value}")
    else:
        scope.append("Filters: none")
    return " | ".join(scope) + "."


def _kpi_table(kpis, styles):
    rows = [["KPI", "Value", "Unit", "Category"]]
    rows.extend([[k.kpi_name, _format_value(k.kpi_value), k.kpi_unit, k.kpi_category] for k in kpis])
    return _table(rows, [58 * mm, 35 * mm, 28 * mm, 35 * mm], styles)


def _file_table(files, styles):
    rows = [["File", "Rows", "Columns", "Size"]]
    rows.extend([[f["original_filename"], f["row_count"] or 0, f["column_count"] or 0, _bytes(f["file_size_bytes"])] for f in files])
    return _table(rows, [78 * mm, 25 * mm, 25 * mm, 28 * mm], styles)


def _quality_table(quality, styles):
    rows = [["Table", "Score", "Rows", "Duplicates", "Null columns", "Outlier columns"]]
    rows.extend([[q["table_name"], q["quality_score"], q["total_rows"] or 0, q["duplicate_rows"] or 0, q["columns_with_nulls"] or 0, q["outlier_columns"] or 0] for q in quality])
    return _table(rows, [52 * mm, 20 * mm, 24 * mm, 25 * mm, 28 * mm, 28 * mm], styles)


def _chart_section(chart, result, insight, styles):
    title = chart["chart_title"]
    story: list[Any] = [Spacer(1, 7), Paragraph(title, styles["Heading"])]
    if chart["rationale"]:
        story.append(Paragraph(str(chart["rationale"]), styles["Small"]))
    if result.get("error"):
        story.append(Paragraph(f"Chart data unavailable: {result['error']}", styles["Small"]))
        return story
    if insight:
        story.extend([Spacer(1, 3), Paragraph(f"AI explanation: {insight}", styles["Body"])])
    rows = _chart_rows(result)
    if rows:
        story.extend([Spacer(1, 4), _table(rows, [68 * mm, 45 * mm, 45 * mm], styles)])
    return story


def _chart_rows(result):
    if result.get("labels"):
        rows = [["Label", "Value"]]
        rows.extend([[str(label), _format_value(value)] for label, value in zip(result["labels"], result.get("values", []))][:MAX_CHART_ROWS])
        return rows
    if result.get("x") is not None and result.get("y") is not None:
        rows = [["Period / Category", "Value"]]
        rows.extend([[str(x), _format_value(y)] for x, y in zip(result["x"], result["y"] )][:MAX_CHART_ROWS])
        return rows
    if result.get("x") is not None:
        return [["Values"]] + [[_format_value(value)] for value in result["x"][:MAX_CHART_ROWS]]
    return []


def _table(rows, widths, styles):
    converted = [[Paragraph(str(cell), styles["Small"]) for cell in row] for row in rows]
    table = Table(converted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _format_value(value):
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _bytes(value):
    if not value:
        return "-"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"
