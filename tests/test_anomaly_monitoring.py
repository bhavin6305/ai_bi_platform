from datetime import date

from sqlalchemy import create_engine, text

from analytics.anomaly_detector import default_monitoring_period


def test_default_monitoring_period_uses_latest_30_days_after_60_days_of_history():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE orders (order_date TEXT)"))
        connection.execute(text("""
            INSERT INTO orders (order_date) VALUES
                ('2025-01-01'), ('2025-03-01')
        """))

    profiles = {
        "orders": [{"column_name": "order_date", "detected_type": "datetime"}]
    }

    assert default_monitoring_period(profiles, engine, "order_date") == (
        "order_date",
        date(2025, 1, 31),
        date(2025, 3, 1),
    )


def test_default_monitoring_period_is_unavailable_without_two_periods():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE orders (order_date TEXT)"))
        connection.execute(text("""
            INSERT INTO orders (order_date) VALUES
                ('2025-01-01'), ('2025-02-28')
        """))

    profiles = {
        "orders": [{"column_name": "order_date", "detected_type": "datetime"}]
    }

    assert default_monitoring_period(profiles, engine, "order_date") is None
