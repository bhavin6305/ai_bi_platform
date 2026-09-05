"""
sql_generator.py
----------------
Converts natural language questions to SQL using Groq + Llama 3.1.

Called by: POST /api/chat
"""

import os
import logging
import re

from groq import Groq
from sqlalchemy import text
from sqlalchemy.engine import Engine

from api.config import retry_with_backoff

logger = logging.getLogger(__name__)

MODEL = "openai/gpt-oss-120b"


def require_groq_api_key() -> str:
    """Raise a clear error when the Groq API key is missing."""
    key = os.environ.get("GROQ_API_KEY")
    if not key or not key.strip():
        raise ValueError("GROQ_API_KEY is not configured. Set it before calling the AI chat pipeline.")
    return key.strip()


def get_groq_client() -> Groq:
    """Build a Groq client lazily so the app can validate env config without crashing during import."""
    return Groq(api_key=require_groq_api_key())


def validate_select_sql(sql: str) -> str:
    """Ensure generated SQL remains read-only and cannot smuggle additional statements."""
    if sql is None:
        raise ValueError("SQL cannot be empty.")

    cleaned = sql.strip()
    if not cleaned:
        raise ValueError("SQL cannot be empty.")

    cleaned = cleaned.rstrip(";")
    if not cleaned.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    if re.search(r";\s*(?:--|/\*|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC|CALL)", cleaned, flags=re.IGNORECASE):
        raise ValueError("Only a single read-only SELECT statement is allowed.")

    if re.search(r"--|/\*\s*|\*/", cleaned, flags=re.IGNORECASE):
        raise ValueError("SQL comments are not allowed.")

    dangerous = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|CALL)\b", re.IGNORECASE)
    if dangerous.search(cleaned):
        raise ValueError("Only SELECT queries are allowed.")

    return cleaned

def generate_sql(
    question   : str,
    session_id : str,
    engine     : Engine,
    max_retries: int = 2,
) -> str:
    """
    Convert natural language to SQL with retry on column errors.
    If the generated SQL fails, sends the error back to the LLM
    and asks it to fix the query using only real column names.
    """
    short_id       = session_id.replace("-", "")[:8]
    schema_context = _build_schema_context(short_id, engine)
    last_error     = None
    last_sql       = None

    for attempt in range(max_retries + 1):
        if attempt == 0:
            # First attempt — generate SQL from scratch
            prompt = f"""You are a PostgreSQL expert. Convert the user's question to a SQL SELECT query.

CRITICAL: You MUST only use column names that EXACTLY appear in the schema below.
Do NOT invent, guess, or assume any column names. Only use what is listed.

Available tables and their EXACT columns:
{schema_context}

Rules:
- Write ONLY a SELECT statement
- Use double quotes around ALL table and column names
- LIMIT to 50 rows maximum
- Only use column names from the schema above — never invent columns
- Return ONLY the raw SQL, no explanation, no markdown

Question: {question}

SQL:"""
        else:
            # Retry — tell LLM what went wrong and ask it to fix
            prompt = f"""Your previous SQL query failed with this error:
ERROR: {last_error}

Failed SQL:
{last_sql}

The column names in that query do not exist. You MUST only use the EXACT column names listed below.

Available tables and their EXACT columns:
{schema_context}

Fix the SQL query using ONLY the column names listed above.
Return ONLY the corrected SQL, nothing else.

Original question: {question}

Corrected SQL:"""

        try:
            def call_model():
                client = get_groq_client()
                response = client.chat.completions.create(
                    model      = MODEL,
                    messages   = [
                        {
                            "role"   : "system",
                            "content": (
                                "You are a PostgreSQL expert. You ONLY use column names "
                                "that are explicitly provided to you in the schema. "
                                "You NEVER invent or guess column names. "
                                "If you cannot answer the question with the available columns, "
                                "write a simple COUNT(*) query instead."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens = 300,
                    temperature= 0.0,
                )
                return response

            response = retry_with_backoff(call_model, max_attempts=2, retry_exceptions=(TimeoutError, ConnectionError, OSError))
            raw_sql = response.choices[0].message.content.strip()

            # Clean markdown
            raw_sql = re.sub(r"```sql\s*", "", raw_sql, flags=re.IGNORECASE)
            raw_sql = re.sub(r"```\s*",    "", raw_sql)
            raw_sql = raw_sql.strip()

            raw_sql = validate_select_sql(raw_sql)

            # Try executing — if it fails, retry with the error
            test_result = _try_execute(raw_sql, engine)
            if test_result is not None:
                # Success
                logger.info("SQL generated successfully on attempt %d: %s", attempt + 1, raw_sql[:80])
                return raw_sql
            else:
                last_error = f"Query returned no results or failed silently"
                last_sql   = raw_sql

        except SQLExecutionError as e:
            # SQL ran but had a DB error — retry with the error message
            last_error = str(e)
            last_sql   = e.sql
            logger.warning("SQL attempt %d failed: %s", attempt + 1, last_error[:100])
            continue

        except Exception as e:
            last_error = str(e)
            logger.error("LLM call failed on attempt %d: %s", attempt + 1, e)
            break

    raise ValueError(f"Could not generate valid SQL after {max_retries + 1} attempts. Last error: {last_error}")


class SQLExecutionError(Exception):
    """Raised when SQL executes but hits a DB error."""
    def __init__(self, message: str, sql: str):
        super().__init__(message)
        self.sql = sql


def _try_execute(sql: str, engine: Engine) -> list | None:
    """
    Try to execute SQL. Returns rows on success, raises SQLExecutionError on DB error.
    """
    try:
        with engine.connect() as conn:
            result  = conn.execute(text(sql))
            columns = list(result.keys())
            rows    = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        raise SQLExecutionError(str(e), sql)


def execute_sql(sql: str, engine: Engine) -> list[dict]:
    """Execute a validated SQL query and return results."""
    validated = validate_select_sql(sql)
    try:
        return _try_execute(validated, engine)
    except SQLExecutionError as e:
        raise ValueError(f"Query execution failed: {e}")
def _build_schema_context(short_id: str, engine: Engine) -> str:
    """
    Build explicit schema context showing EXACT column names.
    This is critical — the LLM must see real column names to avoid hallucination.
    """
    context_lines = []
    try:
        with engine.connect() as conn:
            # Get tables for this session
            tables = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name LIKE :prefix "
                "ORDER BY table_name LIMIT 10"
            ), {"prefix": f"{short_id}%"}).fetchall()

            # Get views for this session
            views = conn.execute(text(
                "SELECT viewname FROM pg_views "
                "WHERE schemaname = 'public' "
                "AND (viewname LIKE :p1 OR viewname LIKE :p2) "
                "ORDER BY viewname LIMIT 10"
            ), {"p1": f"{short_id}%", "p2": f"%{short_id}%"}).fetchall()

            all_objects = [r[0] for r in tables] + [r[0] for r in views]

            for obj_name in all_objects[:12]:
                try:
                    cols = conn.execute(text(
                        "SELECT column_name, data_type "
                        "FROM information_schema.columns "
                        "WHERE table_name = :tname AND table_schema = 'public' "
                        "ORDER BY ordinal_position"
                    ), {"tname": obj_name}).fetchall()

                    if cols:
                        # Show EXACT column names — this is what prevents hallucination
                        col_str = "\n".join(
                            f'      - "{c[0]}" ({c[1]})'
                            for c in cols
                        )
                        context_lines.append(f'  Table: "{obj_name}"\n  Columns:\n{col_str}')
                except Exception:
                    pass

    except Exception as e:
        logger.warning("Schema context build failed: %s", e)
        return "(schema unavailable)"

    return "\n\n".join(context_lines) if context_lines else "(no tables found)"