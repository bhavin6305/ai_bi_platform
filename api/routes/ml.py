"""Training endpoints for the platform's supervised and unsupervised models."""

import os
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile

from api.routes.auth import auth_enabled, require_auth
from ml.churn_model import train_churn_model
from ml.forecast_model import train_forecast_model
from ml.segmentation_model import train_segmentation_model

router = APIRouter()
MODEL_DIR = Path(os.getenv("ML_MODEL_DIR", "ml/models"))


@router.post("/ml/train")
async def train_model(
    model_type: str = Query(..., pattern="^(churn|forecast|segmentation)$"),
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    """Train one model from a prepared CSV and persist its production artifact."""
    if auth_enabled():
        require_auth(authorization)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="ML training currently requires a CSV file")
    try:
        data = pd.read_csv(file.file)
        if model_type == "churn":
            model_path, feature_path = train_churn_model(data, MODEL_DIR)
            artifacts = [model_path.name, feature_path.name]
            metrics = None
        elif model_type == "forecast":
            model_path, result_path, metrics = train_forecast_model(data, MODEL_DIR)
            artifacts = [model_path.name, result_path.name]
        else:
            model_path, enriched = train_segmentation_model(data, MODEL_DIR)
            artifacts = [model_path.name]
            metrics = {"customers": int(len(enriched)), "segments": int(enriched["segment"].nunique())}
        return {"model_type": model_type, "artifacts": artifacts, "metrics": metrics}
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model training failed: {exc}") from exc