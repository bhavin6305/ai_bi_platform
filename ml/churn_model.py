# You are a senior ML engineer. Build a complete customer churn prediction notebook.

# TASK:
# Train an XGBoost binary classifier to predict customer churn using the uploaded
# customer_features.csv file.

# COLUMNS IN THE FILE:
# - customer_unique_id: string ID (drop this before training)
# - total_orders: integer
# - total_spend: float
# - avg_order_value: float
# - days_since_last_order: float
# - customer_tenure_days: float
# - avg_review_score: float (may have nulls — fill with median)
# - churn_label: 0 or 1 (TARGET variable — 1 = churned, 0 = active)

# STEPS TO IMPLEMENT:
# 1. Load customer_features.csv with pandas
# 2. Drop customer_unique_id column
# 3. Fill nulls with column median (not mean)
# 4. Split: X = all columns except churn_label, y = churn_label
# 5. Train/test split: 80/20, random_state=42, stratify=y
# 6. Train XGBClassifier:
#    - n_estimators=200
#    - max_depth=5
#    - learning_rate=0.1
#    - scale_pos_weight = (count of 0s / count of 1s)  # handles class imbalance
#    - random_state=42
# 7. Evaluate:
#    - Print accuracy, precision, recall, F1-score
#    - Print confusion matrix
#    - Print feature importances (sorted)
# 8. Save the trained model:
#    import joblib
#    joblib.dump(model, 'churn_model.pkl')
# 9. Save the feature column names (needed for inference):
#    import json
#    feature_cols = list(X.columns)
#    with open('churn_features.json', 'w') as f:
#        json.dump(feature_cols, f)

# DOWNLOAD: churn_model.pkl and churn_features.json
# PUT IN: ml/models/ folder in the GitHub repo