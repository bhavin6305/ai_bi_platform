"""Explainable threshold-based business KPI anomaly detection."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from sqlalchemy import text

from analytics.kpi_comparison import KPIComparison

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def default_monitoring_period(
    profiles: dict[str, list[dict]],
    engine,
    date_column: str | None = None,
) -> tuple[str, date, date] | None:
    """Choose the latest 30-day period when at least 60 days of history exist."""
    if not date_column:
        date_column = next(
            (
                column["column_name"]
                for columns in profiles.values()
                for column in columns
                if column["detected_type"] == "datetime"
            ),
            None,
        )
    if not date_column or not _IDENTIFIER.fullmatch(date_column):
        return None

    for table, columns in profiles.items():
        if not _IDENTIFIER.fullmatch(table):
            continue
        if not any(
            column["column_name"] == date_column and column["detected_type"] == "datetime"
            for column in columns
        ):
            continue
        with engine.connect() as conn:
            bounds = conn.execute(
                text(f'SELECT MIN("{date_column}"), MAX("{date_column}") FROM "{table}"')
            ).first()
        if not bounds or not bounds[0] or not bounds[1]:
            return None

        minimum = _as_date(bounds[0])
        maximum = _as_date(bounds[1])
        if (maximum - minimum).days < 59:
            return None
        return date_column, maximum - timedelta(days=29), maximum
    return None


def detect_kpi_anomalies(
    comparisons: dict[str, KPIComparison],
    date_from: str,
    date_to: str,
) -> list[dict[str, object]]:
    """Flag material KPI movements using simple, reviewable thresholds."""
    alerts: list[dict[str, object]] = []
    for comparison in comparisons.values():
        if comparison.percent_change is None:
            continue

        name = comparison.kpi_name
        normalized_name = name.lower()
        if "rate" in normalized_name or "percent" in normalized_name:
            threshold = 10.0
            movement = abs(comparison.absolute_change)
            medium_threshold = 15.0
            high_threshold = 20.0
            unit = "percentage points"
        else:
            threshold = 20.0 if "revenue" in normalized_name else 25.0
            movement = abs(comparison.percent_change)
            medium_threshold = threshold * 1.5
            high_threshold = threshold * 2
            unit = "%"

        if movement < threshold:
            continue

        if movement >= high_threshold:
            severity = "high"
        elif movement >= medium_threshold:
            severity = "medium"
        else:
            severity = "low"
        direction = "increased" if comparison.direction == "up" else "decreased"
        change = (
            f"{movement:.1f} percentage points"
            if unit == "percentage points"
            else f"{abs(comparison.percent_change):.1f}%"
        )
        alerts.append({
            "event_type": f"business_alert_{severity}",
            "severity": severity,
            "kpi_name": name,
            "title": f"{name} {direction} {change}",
            "message": (
                f"{name} {direction} {change} from "
                f"{comparison.previous_value:,.2f} to {comparison.current_value:,.2f} "
                f"for {date_from} to {date_to}, compared with the previous period."
            ),
            "current_value": comparison.current_value,
            "previous_value": comparison.previous_value,
            "percent_change": comparison.percent_change,
            "absolute_change": comparison.absolute_change,
            "recommendation": _recommendation(normalized_name, comparison.direction),
            "related_movements": _related_movements(
                name, comparison.direction, comparisons
            ),
            "period_from": date_from,
            "period_to": date_to,
        })

    return alerts


def _recommendation(kpi_name: str, direction: str) -> str:
    if "revenue" in kpi_name:
        return "Review sales by product and region to locate the largest movement."
    if "order" in kpi_name:
        return "Check demand, order fulfillment, and cancellation trends."
    if "rate" in kpi_name or "percent" in kpi_name:
        return "Review the operational process represented by this rate."
    if direction == "down":
        return "Check the affected business area and validate the source data."
    return "Review the affected business area and validate the source data."


def _related_movements(
    kpi_name: str,
    direction: str,
    comparisons: dict[str, KPIComparison],
) -> list[dict[str, object]]:
    normalized_name = kpi_name.lower()
    if "revenue" in normalized_name:
        related_terms = ("order", "avg order", "delivery rate")
    elif "order" in normalized_name:
        related_terms = ("revenue", "delivery rate")
    elif "rate" in normalized_name:
        related_terms = ("order", "revenue")
    else:
        return []

    related = []
    for name, comparison in comparisons.items():
        if name == kpi_name or comparison.direction != direction:
            continue
        if not any(term in name.lower() for term in related_terms):
            continue
        related.append({
            "kpi_name": name,
            "direction": comparison.direction,
            "percent_change": comparison.percent_change,
            "absolute_change": comparison.absolute_change,
            "unit": "percentage points" if "rate" in name.lower() else "%",
        })
    return related


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    return value
