# app/core/security.py - JWT token creation and verification (UPDATED)

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a short-lived JWT access token.

    Args:
        data: Payload to encode (typically {"sub": user_id})
        expires_delta: Custom expiration time (defaults to ACCESS_TOKEN_EXPIRE_MINUTES from settings)

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a long-lived JWT refresh token.

    Refresh tokens live much longer than access tokens (e.g., 7 days vs 1 hour).
    When an access token expires, the client uses the refresh token to get a new access token.

    Args:
        data: Payload to encode (typically {"sub": user_id})
        expires_delta: Custom expiration time (defaults to 7 days)

    Returns:
        str: Encoded JWT refresh token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Refresh tokens expire after 7 days
        expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """
    Verify JWT token and extract user ID.

    Args:
        token: JWT token to verify

    Returns:
        str: User ID if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None