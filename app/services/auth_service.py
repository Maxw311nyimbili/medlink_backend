# app/services/auth_service.py - Authentication service handling Firebase and JWT

from sqlalchemy.orm import Session
from app.db.models import User
from app.core.firebase import verify_firebase_token
from app.core.security import create_access_token, create_refresh_token
from datetime import datetime, timedelta


class AuthService:
    """Service for handling authentication flows."""

    @staticmethod
    def authenticate_with_firebase(id_token: str, db: Session):
        """
        Complete Firebase authentication flow:
        1. Verify Firebase ID token
        2. Create/update user in database
        3. Generate JWT access token

        Args:
            id_token: Firebase ID token from frontend
            db: Database session

        Returns:
            tuple: (access_token, refresh_token, user_dict)
                - access_token: JWT for API requests (short-lived)
                - refresh_token: JWT for refreshing access token (long-lived)
                - user_dict: User information

        Raises:
            ValueError: If Firebase token is invalid
        """
        # Step 1: Verify Firebase token
        try:
            decoded_token = verify_firebase_token(id_token)
        except ValueError as e:
            raise ValueError(f"Firebase verification failed: {str(e)}")

        # Step 2: Extract user information from token
        firebase_uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        display_name = decoded_token.get("name")
        photo_url = decoded_token.get("picture")

        if not firebase_uid or not email:
            raise ValueError("Firebase token missing required fields (uid, email)")

        # Step 3: Get or create user in database
        user = db.query(User).filter(User.id == firebase_uid).first()

        if not user:
            # Create new user
            user = User(
                id=firebase_uid,
                email=email,
                display_name=display_name,
                photo_url=photo_url,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✓ New user created: {email} (Firebase UID: {firebase_uid})")
        else:
            # Update existing user info if changed
            user.display_name = display_name
            user.photo_url = photo_url
            user.updated_at = datetime.utcnow()
            db.commit()
            print(f"✓ User updated: {email}")

        # Step 4: Generate JWT tokens
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = create_refresh_token(data={"sub": user.id})

        # Step 5: Return tokens and user info
        user_dict = {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "photo_url": user.photo_url,
        }

        return access_token, refresh_token, user_dict

    @staticmethod
    def refresh_access_token(user_id: str):
        """
        Generate a new access token for an authenticated user.
        Called when access token expires.

        Args:
            user_id: User ID (from JWT refresh token)

        Returns:
            str: New access token
        """
        return create_access_token(data={"sub": user_id})

    @staticmethod
    def get_user_info(user_id: str, db: Session):
        """
        Get user information by ID.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            dict: User information or None if not found
        """
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return None

        return {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "photo_url": user.photo_url,
        }