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

logger = logging.getLogger(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL  = "llama-3.1-8b-instant"

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
                temperature= 0.0,   # zero temperature = most deterministic, less hallucination
            )
            raw_sql = response.choices[0].message.content.strip()

            # Clean markdown
            raw_sql = re.sub(r"```sql\s*", "", raw_sql, flags=re.IGNORECASE)
            raw_sql = re.sub(r"```\s*",    "", raw_sql)
            raw_sql = raw_sql.strip()

            # Safety — only SELECT
            if not raw_sql.upper().startswith("SELECT"):
                raise ValueError(f"Not a SELECT statement: {raw_sql[:60]}")

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
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")
    try:
        return _try_execute(sql, engine)
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