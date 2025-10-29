# /landing/* endpoints (Day 2) [done]
"""
Landing page endpoints: announcements, consent, onboarding status.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.deps import get_db, get_current_user
from app.db.models import Announcement, ConsentVersion, User

router = APIRouter(prefix="/landing", tags=["landing"])


# ============================================================================
# DTOs
# ============================================================================

class AnnouncementResponse(BaseModel):
    id: int
    title: str
    content: str
    language: str
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConsentResponse(BaseModel):
    version: str
    content: str
    language: str

    class Config:
        from_attributes = True


class UpdateConsentRequest(BaseModel):
    consent_version: str
    consent_given: bool


class UpdatePreferencesRequest(BaseModel):
    preferred_language: Optional[str] = None
    onboarding_completed: Optional[bool] = None


class UserPreferencesResponse(BaseModel):
    preferred_language: str
    consent_version: Optional[str]
    consent_given: bool
    onboarding_completed: bool


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/announcements", response_model=List[AnnouncementResponse])
def get_announcements(
        language: str = "en",
        db: Session = Depends(get_db)
):
    """
    Get active announcements for landing page.
    Filters by language and date range.
    """
    from sqlalchemy import or_
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    announcements = db.query(Announcement).filter(
        Announcement.is_active == True,
        Announcement.language == language,
        or_(Announcement.start_date.is_(None), Announcement.start_date <= now),
        or_(Announcement.end_date.is_(None), Announcement.end_date >= now)
    ).order_by(Announcement.priority.desc(), Announcement.created_at.desc()).all()

    return [AnnouncementResponse(**ann.__dict__) for ann in announcements]


@router.get("/consent/latest", response_model=ConsentResponse)
def get_latest_consent(
        language: str = "en",
        db: Session = Depends(get_db)
):
    """Get the latest active consent document"""
    consent = db.query(ConsentVersion).filter(
        and_(
            ConsentVersion.is_active == True,
            ConsentVersion.language == language
        )
    ).order_by(desc(ConsentVersion.created_at)).first()

    if not consent:
        raise HTTPException(status_code=404, detail="No consent document found")

    return consent


@router.post("/consent/accept")
def accept_consent(
        request: UpdateConsentRequest,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """Mark that user has accepted consent"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.consent_given:
        user.consent_version = request.consent_version
        user.consent_given_at = datetime.utcnow()

    db.commit()

    return {"message": "Consent recorded"}


@router.get("/preferences", response_model=UserPreferencesResponse)
def get_user_preferences(
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """Get user preferences and onboarding status"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserPreferencesResponse(
        preferred_language=user.preferred_language,
        consent_version=user.consent_version,
        consent_given=user.consent_given_at is not None,
        onboarding_completed=user.onboarding_completed
    )


@router.put("/preferences")
def update_user_preferences(
        request: UpdatePreferencesRequest,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """Update user preferences"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.preferred_language:
        user.preferred_language = request.preferred_language

    if request.onboarding_completed is not None:
        user.onboarding_completed = request.onboarding_completed

    db.commit()

    return {"message": "Preferences updated"}