"""Azure-managed PostgreSQL persistence for users and analysis history
(steps 4 and 6 of the request flow).

The API is designed to degrade gracefully: if ``DATABASE_URL`` is not set,
``init_db`` simply skips connecting and every read/write helper becomes a
no-op (or raises ``DatabaseError`` for endpoints that require history), so
the rest of the app keeps working without a database configured.
"""

from __future__ import annotations

import json
import os
from typing import Any
from uuid import UUID

import asyncpg

_pool: asyncpg.Pool | None = None

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

CREATE_ANALYSES_TABLE = """
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY,
    user_id INTEGER,
    resource_group TEXT NOT NULL,
    resources_scanned INTEGER NOT NULL DEFAULT 0,
    issues_found INTEGER NOT NULL DEFAULT 0,
    estimated_savings TEXT,
    analysis_result JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


class DatabaseError(Exception):
    """Raised when a database operation cannot be completed."""

    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def init_db() -> None:
    """Create the connection pool and ensure tables exist.

    Safe to call once at application startup. If ``DATABASE_URL`` is not
    configured, the app continues to run without persistence.
    """
    global _pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        _pool = None
        return

    try:
        _pool = await asyncpg.create_pool(dsn=database_url, min_size=1, max_size=5)
        async with _pool.acquire() as conn:
            await conn.execute(CREATE_USERS_TABLE)
            await conn.execute(CREATE_ANALYSES_TABLE)
    except Exception as exc:
        _pool = None
        raise DatabaseError(
            f"Failed to connect to PostgreSQL using DATABASE_URL: {exc}"
        ) from exc


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def is_configured() -> bool:
    return _pool is not None


async def create_user(email: str, password_hash: str) -> dict[str, Any]:
    """Insert a new user and return its row. Raises DatabaseError on duplicate email."""
    if _pool is None:
        raise DatabaseError(
            "Database not configured. Set DATABASE_URL in backend/.env to enable accounts.",
            status_code=503,
        )
    try:
        async with _pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, password_hash)
                VALUES ($1, $2)
                RETURNING id, email, created_at
                """,
                email,
                password_hash,
            )
    except asyncpg.UniqueViolationError as exc:
        raise DatabaseError("An account with this email already exists.", status_code=409) from exc
    return dict(row)


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    if _pool is None:
        raise DatabaseError(
            "Database not configured. Set DATABASE_URL in backend/.env to enable accounts.",
            status_code=503,
        )
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = $1",
            email,
        )
    return dict(row) if row else None


async def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    if _pool is None:
        return None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, created_at FROM users WHERE id = $1",
            user_id,
        )
    return dict(row) if row else None


async def create_analysis(analysis_id: UUID, user_id: int | None, resource_group: str) -> None:
    """Insert a placeholder 'in_progress' row for a new analysis. No-op without a DB."""
    if _pool is None:
        return
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO analyses (id, user_id, resource_group, status)
            VALUES ($1, $2, $3, 'in_progress')
            """,
            analysis_id,
            user_id,
            resource_group,
        )


async def complete_analysis(
    analysis_id: UUID,
    resources_scanned: int,
    issues_found: int,
    estimated_savings: str,
    analysis_result: dict[str, Any],
) -> None:
    """Persist the final analysis result. No-op without a DB."""
    if _pool is None:
        return
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE analyses
            SET resources_scanned = $2,
                issues_found = $3,
                estimated_savings = $4,
                analysis_result = $5::jsonb,
                status = 'completed'
            WHERE id = $1
            """,
            analysis_id,
            resources_scanned,
            issues_found,
            estimated_savings,
            json.dumps(analysis_result, default=str),
        )


async def fail_analysis(analysis_id: UUID, error_message: str) -> None:
    """Mark an analysis row as failed. No-op without a DB."""
    if _pool is None:
        return
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE analyses
            SET status = 'failed', analysis_result = $2::jsonb
            WHERE id = $1
            """,
            analysis_id,
            json.dumps({"error": error_message}),
        )


async def get_history(user_id: int | None) -> list[dict[str, Any]]:
    """Return past analyses for the given user (or anonymous ones if None)."""
    if _pool is None:
        raise DatabaseError(
            "Database not configured. Set DATABASE_URL in backend/.env to enable history.",
            status_code=503,
        )

    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, resource_group, resources_scanned, issues_found,
                   estimated_savings, analysis_result, status, created_at
            FROM analyses
            WHERE user_id IS NOT DISTINCT FROM $1
            ORDER BY created_at DESC
            """,
            user_id,
        )

    history = []
    for row in rows:
        record = dict(row)
        record["id"] = str(record["id"])
        result = record.get("analysis_result")
        record["analysis_result"] = json.loads(result) if isinstance(result, str) else result
        history.append(record)
    return history
