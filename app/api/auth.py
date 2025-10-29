# /auth/exchange endpoint

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.services.auth_service import authenticate_with_firebase

router = APIRouter(prefix="/auth", tags=["auth"])


class IdTokenExchangeRequest(BaseModel):
    id_token: str


class AuthTokensResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/exchange", response_model=AuthTokensResponse)
def exchange_firebase_token(
        request: IdTokenExchangeRequest,
        db: Session = Depends(get_db)
):
    """
    Exchange Firebase ID token for backend JWT.

    Frontend flow:
    1. User signs in with Google via Firebase
    2. Frontend gets Firebase ID token
    3. Frontend calls this endpoint with ID token
    4. Backend verifies token and returns JWT
    5. Frontend uses JWT for all subsequent requests
    """
    access_token, user = authenticate_with_firebase(request.id_token, db)

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase token"
        )

    return AuthTokensResponse(
        access_token=access_token,
        user=user
    )


@router.get("/me")
def get_current_user_info(
        user_id: str = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Get current user info from JWT.
    Protected endpoint example.
    """
    from app.db.models import User
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "photo_url": user.photo_url
    }