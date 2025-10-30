# Firebase Admin init

import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings


def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)


def verify_firebase_token(id_token: str):
    """
    Verify Firebase ID token and return decoded token.

    Returns:
        dict: Decoded token with user info (uid, email, etc.)
        None: If token is invalid
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Firebase token verification failed: {e}")
        return None