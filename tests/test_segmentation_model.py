import pandas as pd
import pytest

from ml.segmentation_model import train_segmentation_model


def test_train_segmentation_model_saves_artifact(tmp_path):
    df = pd.DataFrame(
        {
            "days_since_last_order": [2, 5, 20, 80] * 10,
            "total_orders": [20, 15, 5, 1] * 10,
            "total_spend": [1000, 700, 150, 20] * 10,
        }
    )
    path, enriched = train_segmentation_model(df, tmp_path)
    assert path.exists()
    assert set(enriched["segment"]) == {"Champions", "Loyal", "At Risk", "Lost"}


def test_segmentation_requires_rfm_columns():
    with pytest.raises(ValueError, match="Missing segmentation columns"):
        train_segmentation_model(pd.DataFrame({"total_spend": [1, 2, 3, 4]}))