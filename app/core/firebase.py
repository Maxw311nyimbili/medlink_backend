# app/core/firebase.py - Firebase initialization and token verification

import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings
import json
import os


def initialize_firebase():
    """
    Initialize Firebase Admin SDK.

    This should be called once at app startup.
    The service account JSON is loaded from the path specified in settings.FIREBASE_CREDENTIALS_PATH
    """
    if not firebase_admin._apps:
        # Load credentials from file
        if os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        else:
            # Fallback: try to load from environment variable if file doesn't exist
            raise FileNotFoundError(
                f"Firebase service account JSON not found at {settings.FIREBASE_CREDENTIALS_PATH}. "
                f"Place your firebase-key.json file in the project root or update FIREBASE_CREDENTIALS_PATH in .env"
            )

        firebase_admin.initialize_app(cred)
        print("✓ Firebase Admin SDK initialized successfully")


def verify_firebase_token(id_token: str) -> dict:
    """
    Verify Firebase ID token and return decoded token data.

    This is called when the frontend sends a token from Firebase Auth.
    Firebase handles all the cryptographic verification.

    Args:
        id_token: The Firebase ID token from the frontend

    Returns:
        dict: Decoded token containing:
            - uid: Firebase user ID
            - email: User email
            - name: Display name (if available)
            - picture: Photo URL (if available)
            - email_verified: Whether email is verified
            - iat: Token issued at time
            - exp: Token expiration time

    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        # Firebase Admin SDK verifies the token signature automatically
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except firebase_admin.auth.InvalidIdTokenError as e:
        raise ValueError(f"Invalid Firebase token: {str(e)}")
    except firebase_admin.auth.ExpiredIdTokenError as e:
        raise ValueError(f"Firebase token has expired: {str(e)}")
    except Exception as e:
        raise ValueError(f"Firebase token verification failed: {str(e)}")