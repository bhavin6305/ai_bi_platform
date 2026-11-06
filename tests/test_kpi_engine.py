from sqlalchemy import create_engine, text

from analytics.kpi_engine import (
    KPIResult,
    _pick_revenue_column,
    calculate_kpis,
    simulate_kpi_scenario,
)


def test_revenue_picker_rejects_arbitrary_price_column_without_transaction_context():
    assert _pick_revenue_column(["price"], "products", None) is None


def test_revenue_picker_accepts_explicit_revenue_column_without_transaction_context():
    assert _pick_revenue_column(["revenue"], "products", None) == "revenue"


def test_revenue_picker_prefers_explicit_revenue_over_generic_amount():
    assert _pick_revenue_column(["amount", "revenue"], "orders", "order_id") == "revenue"


def test_kpis_use_transaction_grain_for_aov_and_preserve_negative_amounts():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE orders (
                order_id TEXT,
                customer_id TEXT,
                revenue REAL
            )
        """))
        conn.execute(text("""
            INSERT INTO orders(order_id, customer_id, revenue) VALUES
            ('o1', 'c1', 100.0),
            ('o1', 'c1', 20.0),
            ('o2', 'c2', 80.0),
            ('o3', 'c2', -10.0)
        """))

    profiles = {
        "orders": [
            {"column_name": "order_id", "detected_type": "id"},
            {"column_name": "customer_id", "detected_type": "id"},
            {"column_name": "revenue", "detected_type": "currency"},
        ]
    }

    kpis = calculate_kpis("test-session", profiles, engine, persist=False)
    values = {k.kpi_name: k.kpi_value for k in kpis}

    assert values["Total Revenue"] == 190.0
    assert values["Avg Order Value"] == 190.0 / 3.0
    assert values["Total Orders"] == 3.0
    assert values["Total Customers"] == 2.0


def test_kpi_result_includes_confidence_score():
    kpis = calculate_kpis("confidence-check", {
        "orders": [
            {"column_name": "order_id", "detected_type": "id"},
            {"column_name": "revenue", "detected_type": "currency"},
        ]
    }, create_engine("sqlite:///:memory:"), persist=False)

    assert kpis
    assert all(0.0 < kpi.confidence <= 1.0 for kpi in kpis)


def test_simulate_kpi_scenario_projects_impact_for_key_business_metrics():
    kpis = [
        KPIResult("Total Revenue", 1000.0, "currency", "sales", "${value:,.2f}"),
        KPIResult("Total Orders", 50.0, "count", "sales", "{value:,.0f}"),
    ]

    result = simulate_kpi_scenario(kpis, {"Total Revenue": 0.2, "Total Orders": -0.1})

    assert result["scenario"]["Total Revenue"]["projected_value"] == 1200.0
    assert result["scenario"]["Total Orders"]["projected_value"] == 45.0
    assert result["delta_pct"]["Total Revenue"] == 20.0
    assert result["summary"].startswith("Revenue")
