"""
database.py
-----------
Shared SQLAlchemy engine and session for the FastAPI application.

All route files import get_engine() from here.
The engine is created once at startup and reused across all requests.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


def build_database_url() -> str:
    """Return the DB URL, allowing an explicit override while keeping local defaults."""
    db_url = os.getenv("DB_URL")
    if db_url:
        return db_url

    return (
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', '')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'ai_bi_platform')}"
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Create and return a SQLAlchemy engine.

    @lru_cache ensures this runs only ONCE — the same engine object
    is returned on every subsequent call. This is important because
    creating a new engine per request would be extremely wasteful.

    Pool settings:
        pool_size=5       — keep 5 persistent connections open
        max_overflow=10   — allow up to 10 extra connections under load
        pool_pre_ping=True — test connections before using them
                             (prevents 'connection already closed' errors
                              after PostgreSQL restarts)
    """
    db_url = build_database_url()

    return create_engine(
        db_url,
        pool_size      = 5,
        max_overflow   = 10,
        pool_pre_ping  = True,
    )


def test_connection() -> bool:
    """
    Test if the database connection works.
    Called at app startup — logs a clear error if DB is unreachable.
    """
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        return False