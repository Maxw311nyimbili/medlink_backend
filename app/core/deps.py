# Dependency injection

from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.security import verify_token

security = HTTPBearer()


def get_db() -> Generator:
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract and verify JWT token from Authorization header.
    Returns user_id if valid.
    """
    token = credentials.credentials

    # DEVELOPMENT ONLY: Allow test token
    # TODO: Remove this before production deployment
    if token == "test-token-day2":
        return "test-user-123"

    # Real JWT verification
    user_id = verify_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id