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

import json
from pathlib import Path

import joblib
import pandas as pd


def train_forecast_model(
	df: pd.DataFrame,
	output_dir: str | Path = "ml/models",
	horizon: int = 3,
) -> tuple[Path, Path, dict[str, float | None]]:
	"""Train a monthly Prophet model and persist its forecast for API use."""
	if horizon < 1:
		raise ValueError("horizon must be at least 1")
	required = {"month", "total_revenue"}
	missing = required.difference(df.columns)
	if missing:
		raise ValueError(f"Missing forecast training columns: {', '.join(sorted(missing))}")

	training = df[["month", "total_revenue"]].rename(
		columns={"month": "ds", "total_revenue": "y"}
	).copy()
	training["ds"] = pd.to_datetime(training["ds"], errors="coerce")
	training["y"] = pd.to_numeric(training["y"], errors="coerce")
	training = training.dropna().sort_values("ds").drop_duplicates("ds")
	if len(training) < 6:
		raise ValueError("Forecast training requires at least 6 monthly observations")

	from prophet import Prophet

	holdout_size = min(horizon, max(1, len(training) // 4)) if len(training) >= 8 else 0
	fit_data = training.iloc[:-holdout_size] if holdout_size else training
	model = Prophet(
		yearly_seasonality=True,
		weekly_seasonality=False,
		daily_seasonality=False,
		changepoint_prior_scale=0.05,
	)
	model.fit(fit_data)
	future = model.make_future_dataframe(periods=horizon, freq="MS")
	forecast = model.predict(future)
	result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(horizon)

	metrics: dict[str, float | None] = {"mae": None, "mape": None}
	if holdout_size:
		actual = training.iloc[-holdout_size:][["ds", "y"]]
		evaluated = actual.merge(forecast[["ds", "yhat"]], on="ds")
		if not evaluated.empty:
			errors = (evaluated["y"] - evaluated["yhat"]).abs()
			metrics["mae"] = float(errors.mean())
			non_zero = evaluated["y"].abs() > 1e-9
			if non_zero.any():
				metrics["mape"] = float(
					(errors[non_zero] / evaluated.loc[non_zero, "y"].abs()).mean() * 100
				)

	artifact_dir = Path(output_dir)
	artifact_dir.mkdir(parents=True, exist_ok=True)
	model_path = artifact_dir / "forecast_model.pkl"
	result_path = artifact_dir / "forecast_results.json"
	joblib.dump(model, model_path)
	serializable = result.assign(ds=result["ds"].astype(str))
	result_path.write_text(
		json.dumps(serializable.to_dict(orient="records")), encoding="utf-8"
	)
	return model_path, result_path, metrics
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