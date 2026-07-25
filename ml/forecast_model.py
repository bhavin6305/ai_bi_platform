# You are a senior ML engineer. Build a complete sales forecasting notebook using Prophet.

# TASK:
# Train a Facebook Prophet time series model on monthly_revenue.csv to forecast
# the next 3 months of revenue.

# COLUMNS IN THE FILE:
# - month: date string (YYYY-MM-DD format, first day of each month)
# - total_revenue: float (TARGET)
# - total_orders: integer (can be used as an additional regressor)

# STEPS TO IMPLEMENT:
# 1. Load monthly_revenue.csv with pandas
# 2. Rename columns for Prophet: month → ds, total_revenue → y
# 3. Convert ds to datetime
# 4. Drop the last 3 rows (hold out for validation)
# 5. Train Prophet model:
#    - yearly_seasonality=True
#    - weekly_seasonality=False
#    - daily_seasonality=False
#    - changepoint_prior_scale=0.05
# 6. Fit on training data
# 7. Make forecast for next 6 months (3 training validation + 3 future):
#    future = model.make_future_dataframe(periods=3, freq='MS')
#    forecast = model.predict(future)
# 8. Print the last 6 rows of forecast showing ds, yhat, yhat_lower, yhat_upper
# 9. Plot the forecast (model.plot)
# 10. Evaluate on holdout: calculate MAE and MAPE
# 11. Save the model:
#     import joblib
#     joblib.dump(model, 'forecast_model.pkl')
# 12. Save the forecast results as JSON for the API to serve:
#     import json
#     forecast_result = forecast[['ds','yhat','yhat_lower','yhat_upper']].tail(6)
#     forecast_result['ds'] = forecast_result['ds'].astype(str)
#     with open('forecast_results.json', 'w') as f:
#         json.dump(forecast_result.to_dict(orient='records'), f)

# DOWNLOAD: forecast_model.pkl and forecast_results.json
# PUT IN: ml/models/ folder in the GitHub repo