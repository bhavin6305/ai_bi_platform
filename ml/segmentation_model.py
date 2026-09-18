# You are a senior ML engineer. Build a customer segmentation notebook using
# RFM analysis and KMeans clustering.

# TASK:
# Segment customers into 4 business groups using KMeans on RFM features
# from customer_features.csv.

# RFM = Recency, Frequency, Monetary

# COLUMNS TO USE (from customer_features.csv):
# - days_since_last_order → Recency (lower = better)
# - total_orders          → Frequency (higher = better)
# - total_spend           → Monetary (higher = better)
# STEPS TO IMPLEMENT:
# 1. Load customer_features.csv
# 2. Select only RFM columns: days_since_last_order, total_orders, total_spend
# 3. Fill nulls with median
# 4. Scale features using StandardScaler
# 5. Find optimal K using elbow method (try K=2 to 8, plot inertia)
# 6. Train KMeans with K=4, random_state=42, n_init=10
# 7. Add cluster labels back to the dataframe
# 8. Calculate mean RFM values per cluster:
#    print(df.groupby('cluster')[rfm_cols].mean().round(2))
# 9. Label clusters by business meaning based on RFM means:
#    - Highest spend + lowest recency → 'Champions'
#    - High orders + moderate recency → 'Loyal'
#    - High recency (inactive) + low spend → 'At Risk'
#    - Very high recency + very low spend → 'Lost'
#    Print the mapping you chose and why.
# 10. Save both model and scaler together:
#     import joblib
#     joblib.dump({
#         'model': kmeans,
#         'scaler': scaler,
#         'feature_cols': ['days_since_last_order', 'total_orders', 'total_spend'],
#         'cluster_labels': {0: 'Champions', 1: 'Loyal', 2: 'At Risk', 3: 'Lost'}
#         # adjust mapping based on actual cluster means
#     }, 'segmentation_model.pkl')
# 11. Print segment distribution (count per segment)

from pathlib import Path

import joblib
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


RFM_COLUMNS = ["days_since_last_order", "total_orders", "total_spend"]


def train_segmentation_model(
	df: pd.DataFrame,
	output_dir: str | Path = "ml/models",
	n_clusters: int = 4,
) -> tuple[Path, pd.DataFrame]:
	"""Train RFM clustering and assign stable business segment names."""
	missing = set(RFM_COLUMNS).difference(df.columns)
	if missing:
		raise ValueError(f"Missing segmentation columns: {', '.join(sorted(missing))}")
	if n_clusters != 4:
		raise ValueError("The business segment mapping requires exactly 4 clusters")

	features = df[RFM_COLUMNS].apply(pd.to_numeric, errors="coerce")
	if len(features) < n_clusters:
		raise ValueError("Segmentation requires at least four customer rows")
	features = features.fillna(features.median()).fillna(0)
	scaler = StandardScaler()
	model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
	clusters = model.fit_predict(scaler.fit_transform(features))

	enriched = df.copy()
	enriched["cluster"] = clusters
	means = features.assign(cluster=clusters).groupby("cluster")[RFM_COLUMNS].mean()
	score = (
		means["total_spend"].rank(pct=True)
		+ means["total_orders"].rank(pct=True)
		+ (1 - means["days_since_last_order"].rank(pct=True))
	)
	champions = int(score.idxmax())
	remaining = [cluster for cluster in means.index if cluster != champions]
	loyal = int(means.loc[remaining, "total_orders"].idxmax())
	remaining = [cluster for cluster in remaining if cluster != loyal]
	lost = int((means.loc[remaining, "days_since_last_order"] + means.loc[remaining, "total_spend"].rank()).idxmax())
	at_risk = next(int(cluster) for cluster in remaining if int(cluster) != lost)
	labels = {champions: "Champions", loyal: "Loyal", at_risk: "At Risk", lost: "Lost"}
	enriched["segment"] = enriched["cluster"].map(labels)

	artifact_dir = Path(output_dir)
	artifact_dir.mkdir(parents=True, exist_ok=True)
	model_path = artifact_dir / "segmentation_model.pkl"
	joblib.dump({"model": model, "scaler": scaler, "feature_cols": RFM_COLUMNS, "cluster_labels": labels}, model_path)
	return model_path, enriched
# You are a senior ML engineer. Build a customer segmentation notebook using
# RFM analysis and KMeans clustering.

# TASK:
# Segment customers into 4 business groups using KMeans on RFM features
# from customer_features.csv.

# RFM = Recency, Frequency, Monetary

# COLUMNS TO USE (from customer_features.csv):
# - days_since_last_order → Recency (lower = better)
# - total_orders          → Frequency (higher = better)
# - total_spend           → Monetary (higher = better)

# STEPS TO IMPLEMENT:
# 1. Load customer_features.csv
# 2. Select only RFM columns: days_since_last_order, total_orders, total_spend
# 3. Fill nulls with median
# 4. Scale features using StandardScaler
# 5. Find optimal K using elbow method (try K=2 to 8, plot inertia)
# 6. Train KMeans with K=4, random_state=42, n_init=10
# 7. Add cluster labels back to the dataframe
# 8. Calculate mean RFM values per cluster:
#    print(df.groupby('cluster')[rfm_cols].mean().round(2))
# 9. Label clusters by business meaning based on RFM means:
#    - Highest spend + lowest recency → 'Champions'
#    - High orders + moderate recency → 'Loyal'
#    - High recency (inactive) + low spend → 'At Risk'
#    - Very high recency + very low spend → 'Lost'
#    Print the mapping you chose and why.
# 10. Save both model and scaler together:
#     import joblib
#     joblib.dump({
#         'model': kmeans,
#         'scaler': scaler,
#         'feature_cols': ['days_since_last_order', 'total_orders', 'total_spend'],
#         'cluster_labels': {0: 'Champions', 1: 'Loyal', 2: 'At Risk', 3: 'Lost'}
#         # adjust mapping based on actual cluster means
#     }, 'segmentation_model.pkl')
# 11. Print segment distribution (count per segment)

# DOWNLOAD: segmentation_model.pkl
# PUT IN: ml/models/ folder in the GitHub repo




# What Member 2 pushes to GitHub
# ml/
# └── models/
#     ├── churn_model.pkl          ← from Notebook 1
#     ├── churn_features.json      ← from Notebook 1
#     ├── forecast_model.pkl       ← from Notebook 2
#     ├── forecast_results.json    ← from Notebook 2
#     └── segmentation_model.pkl   ← from Notebook 3