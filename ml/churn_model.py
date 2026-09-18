import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier


FEATURE_COLUMNS = [
	"total_orders",
	"total_spend",
	"avg_order_value",
	"days_since_last_order",
	"customer_tenure_days",
	"avg_review_score",
]


def train_churn_model(
	df: pd.DataFrame,
	output_dir: str | Path = "ml/models",
) -> tuple[Path, Path]:
	"""Train the churn classifier and save its model and feature metadata."""
	required_columns = {*FEATURE_COLUMNS, "churn_label"}
	missing_columns = required_columns.difference(df.columns)
	if missing_columns:
		missing = ", ".join(sorted(missing_columns))
		raise ValueError(f"Missing churn training columns: {missing}")

	features = df[FEATURE_COLUMNS].copy()
	for column in FEATURE_COLUMNS:
		features[column] = pd.to_numeric(features[column], errors="coerce")
		features[column] = features[column].fillna(features[column].median())

	target = pd.to_numeric(df["churn_label"], errors="raise")
	if target.nunique() != 2:
		raise ValueError("churn_label must contain exactly two classes")

	features_train, _, target_train, _ = train_test_split(
		features,
		target,
		test_size=0.2,
		random_state=42,
		stratify=target,
	)
	negative_count = int((target_train == 0).sum())
	positive_count = int((target_train == 1).sum())
	if positive_count == 0:
		raise ValueError("churn_label must contain positive examples")

	model = XGBClassifier(
		n_estimators=200,
		max_depth=5,
		learning_rate=0.1,
		scale_pos_weight=negative_count / positive_count,
		random_state=42,
		eval_metric="logloss",
	)
	model.fit(features_train, target_train)

	artifact_dir = Path(output_dir)
	artifact_dir.mkdir(parents=True, exist_ok=True)
	model_path = artifact_dir / "churn_model.pkl"
	feature_path = artifact_dir / "churn_features.json"
	joblib.dump(model, model_path)
	feature_path.write_text(json.dumps(FEATURE_COLUMNS), encoding="utf-8")

	return model_path, feature_path


def predict_churn(
	df: pd.DataFrame,
	model_path: str | Path = "ml/models/churn_model.pkl",
) -> pd.DataFrame:
	"""Return churn probabilities and labels using a trained artifact."""
	missing_columns = set(FEATURE_COLUMNS).difference(df.columns)
	if missing_columns:
		missing = ", ".join(sorted(missing_columns))
		raise ValueError(f"Missing churn prediction columns: {missing}")
	features = df[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
	features = features.fillna(features.median()).fillna(0)
	model = joblib.load(model_path)
	probabilities = model.predict_proba(features)[:, 1]
	result = df.copy()
	result["churn_probability"] = probabilities
	result["churn_prediction"] = (probabilities >= 0.5).astype(int)
	return result
