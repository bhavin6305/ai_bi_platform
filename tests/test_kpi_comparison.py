from datetime import date

from analytics.filters import DashboardFilters
from analytics.kpi_comparison import previous_period


def test_previous_period_has_same_inclusive_length():
    filters = DashboardFilters(
        date_column="order_date",
        date_from=date(2025, 3, 10),
        date_to=date(2025, 3, 19),
        category_column="status",
        category_value="Delivered",
    )

    previous = previous_period(filters)

    assert previous is not None
    assert previous.date_from == date(2025, 2, 28)
    assert previous.date_to == date(2025, 3, 9)
    assert previous.category_column == "status"
    assert previous.category_value == "Delivered"


def test_previous_period_is_unavailable_without_complete_range():
    filters = DashboardFilters(date_column="order_date", date_from=date(2025, 3, 10))
    assert previous_period(filters) is None


def test_previous_period_preserves_exact_one_day_range():
    filters = DashboardFilters(
        date_column="order_date",
        date_from=date(2025, 3, 10),
        date_to=date(2025, 3, 10),
    )

    previous = previous_period(filters)

    assert previous is not None
    assert previous.date_from == date(2025, 3, 9)
    assert previous.date_to == date(2025, 3, 9)
