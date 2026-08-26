"""Validated dashboard filter utilities shared by KPI and chart queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

from sqlalchemy import text
from sqlalchemy.engine import Engine


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class DashboardFilters:
    """User-selected filters accepted by dashboard analytics endpoints."""

    date_column: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    category_column: str | None = None
    category_value: str | None = None

    @property
    def active(self) -> bool:
        return any((self.date_from, self.date_to, self.category_value))


def validate_filter_identifiers(filters: DashboardFilters, engine: Engine) -> None:
    """Reject malformed identifiers before they can enter SQL identifiers."""
    for identifier in (filters.date_column, filters.category_column):
        if identifier and not _IDENTIFIER.fullmatch(identifier):
            raise ValueError("Invalid filter column.")

    if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
        raise ValueError("date_from must be before or equal to date_to.")

    if filters.category_value is not None and not filters.category_value.strip():
        raise ValueError("category_value cannot be empty.")


def filtered_query(
    sql: str,
    table: str,
    filters: DashboardFilters | None,
    engine: Engine,
) -> tuple[str, dict[str, object]]:
    """Add only applicable, parameterized predicates to an analytics query."""
    if not filters or not filters.active:
        return sql, {}

    columns = _table_columns(table, engine)
    predicates: list[str] = []
    params: dict[str, object] = {}

    if filters.date_column in columns:
        if filters.date_from:
            predicates.append(f'"{filters.date_column}"::date >= :filter_date_from')
            params["filter_date_from"] = filters.date_from
        if filters.date_to:
            predicates.append(f'"{filters.date_column}"::date <= :filter_date_to')
            params["filter_date_to"] = filters.date_to

    if filters.category_column in columns and filters.category_value is not None:
        predicates.append(f'"{filters.category_column}"::text = :filter_category_value')
        params["filter_category_value"] = filters.category_value

    if not predicates:
        return sql, {}

    condition = " AND ".join(predicates)
    if re.search(r"\bWHERE\b", sql, flags=re.IGNORECASE):
        return re.sub(r"\bWHERE\b", f"WHERE {condition} AND", sql, count=1, flags=re.IGNORECASE), params

    insertion = re.search(r"\b(GROUP BY|ORDER BY|LIMIT|;)", sql, flags=re.IGNORECASE)
    if insertion:
        return f"{sql[:insertion.start()]}WHERE {condition} {sql[insertion.start():]}", params
    return f"{sql.rstrip()} WHERE {condition}", params


def _table_columns(table: str, engine: Engine) -> set[str]:
    if not _IDENTIFIER.fullmatch(table):
        return set()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :table"
                ),
                {"table": table},
            ).fetchall()
        return {row[0] for row in rows}
    except Exception:
        return set()
