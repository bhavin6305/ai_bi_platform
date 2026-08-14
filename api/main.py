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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import test_connection
from api.routes import upload, schema, analytics, kpis, chat

logging.basicConfig(
    level  = logging.INFO,
    format = "%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ── Create the FastAPI application ────────────────────────────────────────────
app = FastAPI(
    title       = "AI-Powered BI Platform API",
    description = "Auto schema detection, ETL, KPIs, charts, and AI chat for any business dataset.",
    version     = "1.0.0",
    docs_url    = "/docs",      # Swagger UI at http://localhost:8000/docs
    redoc_url   = "/redoc",     # ReDoc UI at http://localhost:8000/redoc
)

# ── CORS middleware ───────────────────────────────────────────────────────────
# Allows the Streamlit frontend (running on port 8501) to call this API.
# In production, replace "*" with the actual frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Register route modules ────────────────────────────────────────────────────
app.include_router(upload.router,    prefix="/api", tags=["Upload & ETL"])
app.include_router(schema.router,    prefix="/api", tags=["Schema"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(kpis.router,      prefix="/api", tags=["KPIs"])
app.include_router(chat.router,      prefix="/api", tags=["AI Chat"])


# ── Startup event ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Run checks when the server starts."""
    logger.info("Starting AI-Powered BI Platform API...")
    if test_connection():
        logger.info("✓ PostgreSQL connection successful.")
    else:
        logger.error("✗ PostgreSQL connection FAILED. Check your .env file.")


# ── Root health check endpoint ────────────────────────────────────────────────
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
    
