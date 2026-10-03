"""Sharing, executive summaries, and scheduled report delivery."""

import asyncio
import hashlib
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from ai.insight_generator import _get_client
from api.database import get_engine
from api.routes.auth import auth_enabled, require_auth
from reports.pdf_report import build_pdf_report
from analytics.chart_generator import generate_chart_data

router = APIRouter()
PUBLIC_SHARE_CHART_TYPES = {"line", "bar", "pie", "treemap", "heatmap", "funnel"}


class ScheduleRequest(BaseModel):
    session_id: str
    recipient_email: str = Field(min_length=3, max_length=255)
    frequency: str = Field(pattern="^(daily|weekly|monthly)$")


def ensure_workspace_tables() -> None:
    with get_engine().begin() as conn:
        conn.execute(text(
            "ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS session_name VARCHAR(120)"
        ))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dashboard_shares (
                share_id SERIAL PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                token_hash VARCHAR(64) NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS report_schedules (
                schedule_id SERIAL PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                recipient_email VARCHAR(255) NOT NULL,
                frequency VARCHAR(20) NOT NULL,
                next_run_at TIMESTAMP NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))


def _require_session(session_id: str) -> None:
    with get_engine().connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM upload_sessions WHERE session_id = :session_id"),
            {"session_id": session_id},
        ).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Session not found.")


def _summary_payload(session_id: str) -> tuple[list[dict], list[str]]:
    with get_engine().connect() as conn:
        kpis = [dict(row) for row in conn.execute(text("""
            SELECT kpi_name AS name, kpi_value AS value, kpi_unit AS unit
            FROM kpi_results WHERE session_id = :session_id
            ORDER BY kpi_category, kpi_name
        """), {"session_id": session_id}).mappings()]
        insights = [row[0] for row in conn.execute(text("""
            SELECT insight_text FROM ai_insights
            WHERE session_id = :session_id AND insight_type = 'chart_insight'
            ORDER BY generated_at DESC LIMIT 5
        """), {"session_id": session_id}).fetchall()]
    return kpis, insights


def _fallback_summary(kpis: list[dict], insights: list[str]) -> str:
    headline = "The dashboard is ready for executive review."
    if kpis:
        top = kpis[0]
        headline = f"{top['name']} is {top['value']:,.2f} {top.get('unit') or ''}."
    detail = insights[0] if insights else "Review the KPI cards and charts for the strongest trends and opportunities."
    return f"{headline} {detail}"


def generate_executive_summary(session_id: str) -> str:
    kpis, insights = _summary_payload(session_id)
    fallback = _fallback_summary(kpis, insights)
    client = _get_client()
    if client is None:
        return fallback
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "Write a concise executive BI summary in 3 sentences. Use only supplied facts."},
                {"role": "user", "content": f"KPIs: {kpis}\nExisting insights: {insights}"},
            ],
            max_tokens=220,
            temperature=0.25,
        )
        return (response.choices[0].message.content or fallback).strip()
    except Exception:
        return fallback


@router.get("/analytics/{session_id}/executive-summary")
def executive_summary(session_id: str, authorization: str | None = Header(default=None)):
    if auth_enabled():
        require_auth(authorization)
    _require_session(session_id)
    return {"session_id": session_id, "summary": generate_executive_summary(session_id)}


@router.post("/analytics/{session_id}/share")
def create_share_link(session_id: str, authorization: str | None = Header(default=None)):
    if auth_enabled():
        require_auth(authorization)
    _require_session(session_id)
    ensure_workspace_tables()
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO dashboard_shares (session_id, token_hash, expires_at)
            VALUES (:session_id, :token_hash, :expires_at)
        """), {"session_id": session_id, "token_hash": token_hash, "expires_at": expires_at})
    return {"session_id": session_id, "token": raw_token, "expires_at": expires_at.isoformat()}


@router.get("/shared/{token}")
def get_shared_dashboard(token: str):
    ensure_workspace_tables()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with get_engine().connect() as conn:
        row = conn.execute(text("""
            SELECT session_id FROM dashboard_shares
            WHERE token_hash = :token_hash AND expires_at > NOW()
        """), {"token_hash": token_hash}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Share link is invalid or expired.")
    session_id = row[0]
    kpis, insights = _summary_payload(session_id)
    engine = get_engine()
    with engine.connect() as conn:
        dashboard_name = conn.execute(text("""
            SELECT COALESCE(
                NULLIF(s.session_name, ''),
                (SELECT f.original_filename FROM uploaded_files f
                 WHERE f.session_id = s.session_id
                 ORDER BY f.uploaded_at LIMIT 1),
                'Shared dashboard'
            )
            FROM upload_sessions s
            WHERE s.session_id = :session_id
        """), {"session_id": session_id}).scalar()
        chart_rows = conn.execute(text("""
            SELECT chart_id, chart_type, chart_title, rationale
            FROM chart_configs
            WHERE session_id = :session_id
            ORDER BY chart_order, chart_id
            LIMIT 12
        """), {"session_id": session_id}).mappings().all()

    charts = []
    for chart in chart_rows:
        if chart["chart_type"] not in PUBLIC_SHARE_CHART_TYPES:
            continue
        chart_data = generate_chart_data(chart["chart_id"], session_id, engine)
        if "error" not in chart_data:
            charts.append({
                "chart_id": chart["chart_id"],
                "chart_type": chart["chart_type"],
                "title": chart["chart_title"] or chart_data.get("title") or "Chart",
                "rationale": chart["rationale"],
                "data": chart_data,
            })

    return {
        "session_id": session_id,
        "dashboard_name": dashboard_name or "Shared dashboard",
        "read_only": True,
        "kpis": kpis,
        "charts": charts,
        "insights": insights,
    }


@router.post("/report-schedules")
def create_report_schedule(payload: ScheduleRequest, authorization: str | None = Header(default=None)):
    if auth_enabled():
        require_auth(authorization)
    _require_session(payload.session_id)
    ensure_workspace_tables()
    next_run = datetime.now(timezone.utc).replace(tzinfo=None) + _frequency_delta(payload.frequency)
    with get_engine().begin() as conn:
        row = conn.execute(text("""
            INSERT INTO report_schedules (session_id, recipient_email, frequency, next_run_at)
            VALUES (:session_id, :recipient_email, :frequency, :next_run_at)
            RETURNING schedule_id, next_run_at
        """), {**payload.model_dump(), "next_run_at": next_run}).mappings().one()
    return {"schedule_id": row["schedule_id"], "next_run_at": row["next_run_at"].isoformat()}


def _frequency_delta(frequency: str) -> timedelta:
    return {"daily": timedelta(days=1), "weekly": timedelta(days=7), "monthly": timedelta(days=30)}[frequency]


def _send_report_email(recipient: str, pdf: bytes, session_id: str) -> None:
    host = os.getenv("SMTP_HOST")
    if not host:
        raise RuntimeError("SMTP_HOST is not configured")
    message = EmailMessage()
    message["Subject"] = "Your AI BI Platform report"
    message["From"] = os.getenv("SMTP_FROM", "reports@example.com")
    message["To"] = recipient
    message.set_content("Your scheduled AI BI Platform report is attached.")
    message.add_attachment(pdf, maintype="application", subtype="pdf", filename=f"aibi-report-{session_id[:8]}.pdf")
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=20) as smtp:
        if os.getenv("SMTP_TLS", "true").lower() in {"1", "true", "yes"}:
            smtp.starttls()
        username = os.getenv("SMTP_USERNAME")
        if username:
            smtp.login(username, os.getenv("SMTP_PASSWORD", ""))
        smtp.send_message(message)


def run_due_report_schedules() -> None:
    ensure_workspace_tables()
    with get_engine().begin() as conn:
        schedules = conn.execute(text("""
            SELECT schedule_id, session_id, recipient_email, frequency
            FROM report_schedules WHERE active = TRUE AND next_run_at <= NOW()
        """)).mappings().all()
    for schedule in schedules:
        try:
            pdf = build_pdf_report(schedule["session_id"], get_engine(), None)
            _send_report_email(schedule["recipient_email"], pdf.read(), schedule["session_id"])
            with get_engine().begin() as conn:
                conn.execute(text("""
                    UPDATE report_schedules SET next_run_at = :next_run_at WHERE schedule_id = :schedule_id
                """), {"schedule_id": schedule["schedule_id"], "next_run_at": datetime.now() + _frequency_delta(schedule["frequency"])})
        except Exception:
            continue


async def schedule_worker() -> None:
    while True:
        await asyncio.to_thread(run_due_report_schedules)
        await asyncio.sleep(60)