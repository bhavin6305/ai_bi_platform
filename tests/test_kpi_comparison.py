from datetime import date

from analytics.filters import DashboardFilters
from analytics.kpi_comparison import percent_change, previous_period


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


def test_percent_change_uses_absolute_previous_denominator():
    assert percent_change(150.0, 120.0) == 25.0
    assert percent_change(80.0, 100.0) == -20.0


def test_percent_change_returns_none_when_previous_is_zero():
    assert percent_change(100.0, 0.0) is None


def test_percent_change_handles_negative_baseline_without_flipping_direction():
    assert percent_change(-15.0, -10.0) == -50.0
