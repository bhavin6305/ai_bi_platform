import json

import pandas as pd

from ml.churn_model import train_churn_model


def test_train_churn_model_saves_artifacts(tmp_path):
    df = pd.DataFrame(
        {
            "customer_unique_id": [f"C{i}" for i in range(200)],
            "total_orders": [5 + (i % 7) for i in range(200)],
            "total_spend": [50.0 + i * 1.5 for i in range(200)],
            "avg_order_value": [10.0 + (i % 5) * 2 for i in range(200)],
            "days_since_last_order": [30 + (i % 30) for i in range(200)],
            "customer_tenure_days": [200 + i for i in range(200)],
            "avg_review_score": [4.5 + (i % 3) * 0.2 for i in range(200)],
            "churn_label": [0, 1] * 100,
        }
    )

    model_path, feature_path = train_churn_model(df=df, output_dir=tmp_path)

    assert model_path.exists()
    assert feature_path.exists()

    feature_cols = json.loads(feature_path.read_text())
    assert "customer_unique_id" not in feature_cols
    assert "churn_label" not in feature_cols
    assert "total_orders" in feature_cols
    assert "avg_review_score" in feature_cols
