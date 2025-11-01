# app/api/auth.py - Authentication API endpoints (UPDATED)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


# ============ Request/Response Models ============

class IdTokenExchangeRequest(BaseModel):
    """Request body for exchanging Firebase ID token."""
    id_token: str = Field(
        ...,
        description="Firebase ID token from frontend Firebase Auth"
    )


class AuthTokensResponse(BaseModel):
    """Response containing access and refresh tokens."""
    access_token: str = Field(..., description="JWT access token (short-lived)")
    refresh_token: str = Field(..., description="JWT refresh token (long-lived)")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    user: dict = Field(..., description="Authenticated user info")


class RefreshTokenRequest(BaseModel):
    """Request body for refreshing access token."""
    refresh_token: str = Field(..., description="JWT refresh token")


class UserResponse(BaseModel):
    """Response containing user information."""
    id: str
    email: str
    display_name: str = None
    photo_url: str = None


# ============ Endpoints ============

@router.post("/exchange", response_model=AuthTokensResponse)
def exchange_firebase_token(
        request: IdTokenExchangeRequest,
        db: Session = Depends(get_db)
):
    """
    Exchange Firebase ID token for backend JWT tokens.

    This is the main authentication endpoint.

    Flow:
    1. User signs in with Google in Flutter app using Firebase Auth
    2. Firebase returns an ID token to the Flutter app
    3. Flutter app sends ID token to this endpoint
    4. Backend verifies ID token with Firebase Admin SDK
    5. Backend creates/updates user in database
    6. Backend returns access token + refresh token
    7. Flutter app stores tokens securely and uses them for API requests

    Args:
        request: Contains Firebase ID token
        db: Database session

    Returns:
        AuthTokensResponse: Access token, refresh token, and user info

    Raises:
        HTTPException 401: If Firebase token is invalid
    """
    try:
        access_token, refresh_token, user = AuthService.authenticate_with_firebase(
            request.id_token, db
        )

        # Access tokens typically expire in 1 hour (3600 seconds)
        expires_in = 3600

        return AuthTokensResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            user=user,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh")
def refresh_access_token(
        request: RefreshTokenRequest,
        db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    When the access token expires, the Flutter app calls this endpoint
    with the stored refresh token to get a new access token.

    Args:
        request: Contains refresh token
        db: Database session

    Returns:
        dict: New access token and expiration time

    Raises:
        HTTPException 401: If refresh token is invalid
    """
    from app.core.security import verify_token

    # Verify the refresh token
    user_id = verify_token(request.refresh_token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Generate new access token
    new_access_token = AuthService.refresh_access_token(user_id)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 3600,
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
        user_id: str = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Get current authenticated user information.

    This is a protected endpoint - requires valid access token.
    Used by Flutter app to verify authentication and get user details.

    Args:
        user_id: Extracted from JWT access token by get_current_user dependency
        db: Database session

    Returns:
        UserResponse: User information

    Raises:
        HTTPException 404: If user not found
    """
    user = AuthService.get_user_info(user_id, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.post("/logout")
def logout(user_id: str = Depends(get_current_user)):
    """
    Logout endpoint (optional).

    The Flutter app can call this to notify the backend of logout.
    In practice, logout happens on the Flutter side (clear tokens).
    This endpoint could be used for logging/cleanup.

    Args:
        user_id: Extracted from JWT access token

    Returns:
        dict: Success message
    """
    # Log the logout
    print(f"User {user_id} logged out")

    return {"message": "Successfully logged out"}