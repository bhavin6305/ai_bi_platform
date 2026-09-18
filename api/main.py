"""
main.py
-------
FastAPI application entry point.

Run the server with:
    uvicorn api.main:app --reload --port 8000

The --reload flag restarts the server automatically when you
save any Python file. Only use this during development.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import get_allowed_cors_origins, get_app_environment
from api.database import test_connection
from api.metrics import MetricsMiddleware, metrics_response
from api.observability import RequestLoggingMiddleware
from api.rate_limit import RateLimitMiddleware
from api.routes import upload, schema, analytics, kpis, chat, auth, notifications, reports, comparisons, ml

logging.basicConfig(
    level  = logging.INFO,
    format = "%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Run dependency checks when the application starts and stops."""
    logger.info("Starting AI-Powered BI Platform API in %s mode...", get_app_environment())
    if test_connection():
        logger.info("PostgreSQL connection successful.")
    else:
        logger.error("PostgreSQL connection FAILED. Check your .env file.")
    yield


app = FastAPI(
    title       = "AI-Powered BI Platform API",
    description = "Auto schema detection, ETL, KPIs, charts, and AI chat for any business dataset.",
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    lifespan    = lifespan,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins     = get_allowed_cors_origins(),
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(upload.router,    prefix="/api", tags=["Upload & ETL"])
app.include_router(schema.router,    prefix="/api", tags=["Schema"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(kpis.router,      prefix="/api", tags=["KPIs"])
app.include_router(comparisons.router, prefix="/api", tags=["KPI Comparisons"])
app.include_router(chat.router,      prefix="/api", tags=["AI Chat"])
app.include_router(auth.router,     prefix="/api", tags=["Authentication"])
app.include_router(notifications.router, prefix="/api", tags=["Notifications"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(ml.router, prefix="/api", tags=["Machine Learning"])


@app.get("/", tags=["Health"])
def root():
    """Health check — confirms the API is running."""
    return {
        "status" : "running",
        "message": "AI-Powered BI Platform API is up.",
        "docs"   : "http://localhost:8000/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    """Detailed health check including DB status."""
    db_ok = test_connection()
    return {
        "api"     : "ok",
        "database": "ok" if db_ok else "error",
    }


@app.get("/ready", tags=["Health"])
def readiness():
    """Return 503 until the API can reach its database dependency."""
    db_ok = test_connection()
    payload = {
        "ready": db_ok,
        "database": "ok" if db_ok else "error",
    }
    return JSONResponse(status_code=200 if db_ok else 503, content=payload)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_response()
