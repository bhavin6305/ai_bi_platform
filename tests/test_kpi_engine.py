from sqlalchemy import create_engine, text

from analytics.kpi_engine import _pick_revenue_column, calculate_kpis


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
