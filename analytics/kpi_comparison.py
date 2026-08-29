"""Correct, reusable KPI period comparison utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from analytics.filters import DashboardFilters
from analytics.kpi_engine import KPIResult, calculate_kpis


@dataclass(frozen=True)
class KPIComparison:
    """Comparison of one KPI over two equivalent periods."""

    kpi_name: str
    current_value: float
    previous_value: float
    absolute_change: float
    percent_change: float | None
    direction: str
    comparison_available: bool = True


def previous_period(filters: DashboardFilters) -> DashboardFilters | None:
    """Return the immediately preceding period of identical inclusive length.

    A comparison is intentionally unavailable unless both endpoints are
    explicitly selected. This avoids inventing a period when the user only
    supplied a lower or upper bound.
    """
    if not filters.date_column or not filters.date_from or not filters.date_to:
        return None

    period_days = (filters.date_to - filters.date_from).days + 1
    previous_to = filters.date_from - timedelta(days=1)
    previous_from = previous_to - timedelta(days=period_days - 1)

    return DashboardFilters(
        date_column=filters.date_column,
        date_from=previous_from,
        date_to=previous_to,
        category_column=filters.category_column,
        category_value=filters.category_value,
    )


def compare_kpis(
    session_id: str,
    schema_profiles: dict[str, list[dict]],
    engine,
    filters: DashboardFilters,
) -> dict[str, KPIComparison]:
    """Calculate current and previous KPI snapshots using the same definitions.

    Only KPIs whose source table actually contains the selected date column are
    eligible. This is critical for multi-table datasets: a customer table must
    not inherit an order-date filter merely because both tables exist.
    """
    previous = previous_period(filters)
    if previous is None:
        return {}

    current_values: dict[str, float] = {}
    previous_values: dict[str, float] = {}

    for table_name, columns in schema_profiles.items():
        column_names = {column["column_name"] for column in columns}
        if filters.date_column not in column_names:
            continue

        table_profiles = {table_name: columns}
        current = calculate_kpis(
            session_id,
            table_profiles,
            engine,
            filters=filters,
            persist=False,
        )
        prior = calculate_kpis(
            session_id,
            table_profiles,
            engine,
            filters=previous,
            persist=False,
        )

        for kpi in current:
            current_values.setdefault(kpi.kpi_name, float(kpi.kpi_value))
        for kpi in prior:
            previous_values.setdefault(kpi.kpi_name, float(kpi.kpi_value))

    results: dict[str, KPIComparison] = {}
    for name, current_value in current_values.items():
        if name not in previous_values:
            continue

        previous_value = previous_values[name]
        absolute_change = current_value - previous_value

        if previous_value == 0:
            percent_change = None
        else:
            percent_change = (absolute_change / abs(previous_value)) * 100

        if absolute_change > 0:
            direction = "up"
        elif absolute_change < 0:
            direction = "down"
        else:
            direction = "flat"

        results[name] = KPIComparison(
            kpi_name=name,
            current_value=current_value,
            previous_value=previous_value,
            absolute_change=absolute_change,
            percent_change=percent_change,
            direction=direction,
        )

    return results
