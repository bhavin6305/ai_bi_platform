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