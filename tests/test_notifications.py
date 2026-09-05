from types import SimpleNamespace

from api.routes.notifications import anomaly_notification_details


def test_anomaly_notification_details_lists_affected_tables():
    tables = [
        SimpleNamespace(
            table_name="orders",
            cleaning_log=SimpleNamespace(outlier_columns=2),
        ),
        SimpleNamespace(
            table_name="customers",
            cleaning_log=SimpleNamespace(outlier_columns=0),
        ),
    ]

    assert anomaly_notification_details(tables) == (
        "Anomalies detected",
        "Extreme values were flagged for review in orders (2 column(s)).",
    )


def test_anomaly_notification_details_returns_none_without_outliers():
    tables = [
        SimpleNamespace(
            table_name="orders",
            cleaning_log=SimpleNamespace(outlier_columns=0),
        ),
    ]

    assert anomaly_notification_details(tables) is None


def test_anomaly_notification_details_ignores_empty_or_missing_table_inputs():
    assert anomaly_notification_details(None) is None
    assert anomaly_notification_details([None]) is None
    assert anomaly_notification_details([
        SimpleNamespace(
            table_name="orders",
            cleaning_log=SimpleNamespace(outlier_columns=0),
        ),
        None,
    ]) is None