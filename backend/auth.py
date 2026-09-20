"""JWT-based authentication (steps ① and ② of the request flow).

Uses bcrypt directly for password hashing (avoiding known passlib/bcrypt
version-compatibility issues) and PyJWT for signing/verifying access tokens.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

import db

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

_bearer_scheme = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """Raised for signup/login/token failures."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="At least 8 characters")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


def _secret_key() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise AuthError(
            "JWT_SECRET_KEY is not set. Add it to backend/.env (see .env.example).",
            status_code=500,
        )
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _secret_key(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _secret_key(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired. Please log in again.", status_code=401) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid authentication token.", status_code=401) from exc


async def signup(request: SignupRequest) -> TokenResponse:
    existing = await db.get_user_by_email(request.email)
    if existing is not None:
        raise AuthError("An account with this email already exists.", status_code=409)

    password_hash = hash_password(request.password)
    user = await db.create_user(request.email, password_hash)
    token = create_access_token(user["id"], user["email"])
    return TokenResponse(access_token=token, user={"id": user["id"], "email": user["email"]})


async def login(request: LoginRequest) -> TokenResponse:
    user = await db.get_user_by_email(request.email)
    if user is None or not verify_password(request.password, user["password_hash"]):
        raise AuthError("Invalid email or password.", status_code=401)

    token = create_access_token(user["id"], user["email"])
    return TokenResponse(access_token=token, user={"id": user["id"], "email": user["email"]})


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency that validates the JWT and returns {id, email}."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token. Include 'Authorization: Bearer <token>'.",
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except AuthError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error

    return {"id": int(payload["sub"]), "email": payload.get("email")}


async def get_user_from_ws_token(websocket: WebSocket) -> dict[str, Any] | None:
    """Validate the JWT passed as a `?token=` query param on a WebSocket connection.

    Returns None (and does not raise) if the token is missing or invalid so the
    caller can decide how to close the connection.
    """
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except AuthError:
        return None
    return {"id": int(payload["sub"]), "email": payload.get("email")}
