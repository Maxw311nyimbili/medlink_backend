# Firebase token verification

from sqlalchemy.orm import Session
from app.db.models import User
from app.core.firebase import verify_firebase_token
from app.core.security import create_access_token


def authenticate_with_firebase(id_token: str, db: Session):
    """
    Verify Firebase token and create/update user in database.

    Returns:
        tuple: (access_token, user_dict) or (None, None) if invalid
    """
    # Verify Firebase token
    decoded_token = verify_firebase_token(id_token)
    if not decoded_token:
        return None, None

    # Extract user info
    firebase_uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    display_name = decoded_token.get("name")
    photo_url = decoded_token.get("picture")

    # Get or create user in database
    user = db.query(User).filter(User.id == firebase_uid).first()

    if not user:
        user = User(
            id=firebase_uid,
            email=email,
            display_name=display_name,
            photo_url=photo_url
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update user info if changed
        user.display_name = display_name
        user.photo_url = photo_url
        db.commit()

    # Create JWT token
    access_token = create_access_token(data={"sub": user.id})

    user_dict = {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "photo_url": user.photo_url
    }

    return access_token, user_dict