"""Authentication endpoints for account creation and sign-in."""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from api.database import get_engine

router = APIRouter(prefix="/auth")
PASSWORD_ITERATIONS = 310_000
TOKEN_DAYS = 30
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignUpRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=256)


class SignInRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class SettingsUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    email_updates: bool | None = None
    compact_mode: bool | None = None
    show_insights: bool | None = None
    timezone: str | None = Field(default=None, max_length=80)


def _ensure_auth_tables() -> None:
    with get_engine().begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_users (
                user_id SERIAL PRIMARY KEY,
                full_name VARCHAR(120) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("ALTER TABLE app_users ADD COLUMN IF NOT EXISTS email_updates BOOLEAN NOT NULL DEFAULT TRUE"))
        conn.execute(text("ALTER TABLE app_users ADD COLUMN IF NOT EXISTS compact_mode BOOLEAN NOT NULL DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE app_users ADD COLUMN IF NOT EXISTS show_insights BOOLEAN NOT NULL DEFAULT TRUE"))
        conn.execute(text("ALTER TABLE app_users ADD COLUMN IF NOT EXISTS timezone VARCHAR(80) NOT NULL DEFAULT 'UTC'"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                session_id VARCHAR(64) PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    ).hex()


def _issue_token(user_id: int) -> str:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=TOKEN_DAYS)
    with get_engine().begin() as conn:
        conn.execute(
            text("""
                INSERT INTO auth_sessions (session_id, user_id, expires_at)
                VALUES (:session_id, :user_id, :expires_at)
            """),
            {"session_id": token, "user_id": user_id, "expires_at": expires_at},
        )
    return token


def _auth_response(user: dict, token: str) -> dict:
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
        },
    }


@router.post("/signup", status_code=201)
def signup(payload: SignUpRequest):
    email = _normalise_email(payload.email)
    full_name = payload.full_name.strip()
    if not full_name or not EMAIL_PATTERN.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid name and email address.")

    _ensure_auth_tables()
    salt = secrets.token_bytes(16)
    try:
        with get_engine().begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO app_users (full_name, email, password_hash, password_salt)
                    VALUES (:full_name, :email, :password_hash, :password_salt)
                    RETURNING user_id, full_name, email
                """),
                {
                    "full_name": full_name,
                    "email": email,
                    "password_hash": _hash_password(payload.password, salt),
                    "password_salt": salt.hex(),
                },
            )
            user = dict(result.mappings().one())
    except Exception as error:
        if "unique" in str(error).lower() or "duplicate" in str(error).lower():
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        raise

    return _auth_response(user, _issue_token(user["user_id"]))


@router.post("/signin")
def signin(payload: SignInRequest):
    email = _normalise_email(payload.email)
    _ensure_auth_tables()
    with get_engine().connect() as conn:
        user = conn.execute(
            text("""
                SELECT user_id, full_name, email, password_hash, password_salt
                FROM app_users WHERE email = :email
            """),
            {"email": email},
        ).mappings().fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    expected = _hash_password(payload.password, bytes.fromhex(user["password_salt"]))
    if not hmac.compare_digest(expected, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return _auth_response(dict(user), _issue_token(user["user_id"]))


@router.get("/me")
def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    token = authorization[7:].strip()
    _ensure_auth_tables()
    with get_engine().connect() as conn:
        user = conn.execute(
            text("""
                SELECT u.user_id, u.full_name, u.email
                FROM auth_sessions s JOIN app_users u ON u.user_id = s.user_id
                WHERE s.session_id = :token AND s.expires_at > NOW()
            """),
            {"token": token},
        ).mappings().fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return {"user": dict(user)}


def _token_from_header(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    return authorization[7:].strip()


@router.post("/logout", status_code=204)
def logout(authorization: str | None = Header(default=None)):
    token = _token_from_header(authorization)
    _ensure_auth_tables()
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM auth_sessions WHERE session_id = :token"), {"token": token})


@router.get("/settings")
def get_settings(authorization: str | None = Header(default=None)):
    token = _token_from_header(authorization)
    _ensure_auth_tables()
    with get_engine().connect() as conn:
        settings = conn.execute(
            text("""
                  SELECT u.full_name, u.email_updates, u.compact_mode,
                      u.show_insights, u.timezone
                FROM auth_sessions s JOIN app_users u ON u.user_id = s.user_id
                WHERE s.session_id = :token AND s.expires_at > NOW()
            """),
            {"token": token},
        ).mappings().fetchone()
    if not settings:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return {"settings": dict(settings)}


@router.patch("/settings")
def update_settings(payload: SettingsUpdate, authorization: str | None = Header(default=None)):
    token = _token_from_header(authorization)
    _ensure_auth_tables()
    updates = payload.model_dump(exclude_none=True)
    if "full_name" in updates:
        updates["full_name"] = updates["full_name"].strip()
        if not updates["full_name"]:
            raise HTTPException(status_code=400, detail="Display name cannot be empty.")
    if "timezone" in updates:
        try:
            ZoneInfo(updates["timezone"])
        except ZoneInfoNotFoundError:
            raise HTTPException(status_code=400, detail="Invalid timezone.")
    if not updates:
        return get_settings(authorization)

    allowed_columns = {"full_name", "email_updates", "compact_mode", "show_insights", "timezone"}
    assignments = ", ".join(f'"{column}" = :{column}' for column in updates if column in allowed_columns)
    values = {**updates, "token": token}
    with get_engine().begin() as conn:
        result = conn.execute(
            text(f"""
                UPDATE app_users SET {assignments}
                WHERE user_id = (
                    SELECT user_id FROM auth_sessions
                    WHERE session_id = :token AND expires_at > NOW()
                )
            """),
            values,
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return get_settings(authorization)