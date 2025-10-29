import firebase_admin
from firebase_admin import credentials, auth
import os
import base64
import json
import tempfile


def initialize_firebase():
    """
    Initialize Firebase Admin SDK.
    Reads from FIREBASE_KEY_BASE64 environment variable or file.
    """
    if firebase_admin._apps:
        return

    try:
        # Try to load from base64 environment variable (Railway)
        firebase_key_base64 = os.getenv("FIREBASE_KEY_BASE64")

        if firebase_key_base64:
            # Decode base64 and load credentials
            firebase_key_json = base64.b64decode(firebase_key_base64).decode('utf-8')
            firebase_key_dict = json.loads(firebase_key_json)
            cred = credentials.Certificate(firebase_key_dict)
            firebase_admin.initialize_app(cred)
            print("✓ Firebase initialized from environment variable")
        else:
            # Fallback to file (local development)
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-key.json")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("✓ Firebase initialized from file")

    except Exception as e:
        print(f"⚠️ Firebase initialization failed: {e}")
        print("Running without Firebase authentication")