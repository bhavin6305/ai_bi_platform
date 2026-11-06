from analytics.anomaly_detector import detect_kpi_anomalies
from analytics.kpi_comparison import KPIComparison


def test_revenue_decline_crossing_threshold_becomes_medium_alert():
    alerts = detect_kpi_anomalies(
        {
            "Total Revenue": KPIComparison(
                "Total Revenue", 68.6, 100.0, -31.4, -31.4, "down"
            )
        },
        "2025-03-01",
        "2025-03-30",
    )

    assert len(alerts) == 1
    assert alerts[0]["severity"] == "medium"
    assert alerts[0]["title"] == "Total Revenue decreased 31.4%"
    assert "2025-03-01 to 2025-03-30" in alerts[0]["message"]


def test_movement_at_base_threshold_is_low_priority():
    alerts = detect_kpi_anomalies(
        {
            "Total Revenue": KPIComparison(
                "Total Revenue", 78.0, 100.0, -22.0, -22.0, "down"
            )
        },
        "2025-03-01",
        "2025-03-30",
    )

    assert alerts[0]["severity"] == "low"


def test_large_kpi_movement_is_high_priority():
    alerts = detect_kpi_anomalies(
        {
            "Total Orders": KPIComparison(
                "Total Orders", 40.0, 100.0, -60.0, -60.0, "down"
            )
        },
        "2025-03-01",
        "2025-03-30",
    )

    assert alerts[0]["severity"] == "high"
    assert alerts[0]["event_type"] == "business_alert_high"


def test_rate_alert_uses_percentage_point_change():
    alerts = detect_kpi_anomalies(
        {
            "Delivery Rate": KPIComparison(
                "Delivery Rate", 75.0, 90.0, -15.0, -16.7, "down"
            )
        },
        "2025-03-01",
        "2025-03-30",
    )

    assert len(alerts) == 1
    assert alerts[0]["title"] == "Delivery Rate decreased 15.0 percentage points"


def test_revenue_alert_reports_related_kpi_movement_without_claiming_causation():
    alerts = detect_kpi_anomalies(
        {
            "Total Revenue": KPIComparison(
                "Total Revenue", 68.0, 100.0, -32.0, -32.0, "down"
            ),
            "Total Orders": KPIComparison(
                "Total Orders", 70.0, 100.0, -30.0, -30.0, "down"
            ),
        },
        "2025-03-01",
        "2025-03-30",
    )

    assert alerts[0]["related_movements"] == [
        {
            "kpi_name": "Total Orders",
            "direction": "down",
            "percent_change": -30.0,
            "absolute_change": -30.0,
            "unit": "%",
        }
    ]


def test_small_movements_and_zero_baselines_do_not_create_alerts():
    alerts = detect_kpi_anomalies(
        {
            "Total Revenue": KPIComparison(
                "Total Revenue", 110.0, 100.0, 10.0, 10.0, "up"
            ),
            "Total Orders": KPIComparison(
                "Total Orders", 10.0, 0.0, 10.0, None, "up"
            ),
        },
        "2025-03-01",
        "2025-03-30",
    )

    assert alerts == []
