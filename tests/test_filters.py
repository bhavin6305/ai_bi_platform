from datetime import date

import pytest

from analytics.filters import DashboardFilters, filtered_query, validate_filter_identifiers


def test_filter_range_requires_valid_order():
    filters = DashboardFilters(
        date_column="Order_Date",
        date_from=date(2025, 1, 1),
        date_to=date(2024, 1, 1),
    )

    with pytest.raises(ValueError, match="date_from"):
        validate_filter_identifiers(filters, engine=None)


def test_filter_values_are_parameterized_and_predicates_are_scoped():
    filters = DashboardFilters(
        date_column="Order_Date",
        date_from=date(2024, 1, 1),
        category_column="Order_Status",
        category_value="Delivered",
    )

    class FakeConnection:
        def execute(self, *_args, **_kwargs):
            class Result:
                def fetchall(self):
                    return [("Order_Date",), ("Order_Status",)]

            return Result()

    class FakeEngine:
        def connect(self):
            class Context:
                def __enter__(self):
                    return FakeConnection()

                def __exit__(self, *_args):
                    return False

            return Context()

    sql, params = filtered_query(
        'SELECT * FROM "orders" WHERE "Revenue" IS NOT NULL GROUP BY "Category"',
        "orders",
        filters,
        FakeEngine(),
    )

    assert ":filter_date_from" in sql
    assert ":filter_category_value" in sql
    assert params == {
        "filter_date_from": date(2024, 1, 1),
        "filter_category_value": "Delivered",
    }
    assert "Delivered" not in sql


def test_inactive_filters_leave_query_unchanged():
    sql = 'SELECT * FROM "orders"'

    assert filtered_query(sql, "orders", DashboardFilters(), engine=None) == (sql, {})
