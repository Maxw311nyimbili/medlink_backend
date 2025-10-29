# /media/upload endpoint
"""
Media/MedScanner API for image upload and processing
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import uuid
from datetime import datetime

from app.core.deps import get_db, get_current_user
from app.db.models import MediaUpload

router = APIRouter(prefix="/media", tags=["media"])

# Upload directory
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================================
# DTOs
# ============================================================================

class UploadResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    scan_type: str
    processing_status: str
    extracted_data: Optional[dict]

    class Config:
        from_attributes = True


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_image(
        file: UploadFile = File(...),
        scan_type: str = Form(...),  # "barcode", "text_ocr", "label_ocr"
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """
    Upload an image from MedScanner.

    Supports:
    - Barcode scanning
    - Text OCR (prescription, labels)
    - Future: AI analysis
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Create database record
    media_upload = MediaUpload(
        user_id=user_id,
        file_name=file.filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
        scan_type=scan_type,
        processing_status="pending"
    )

    db.add(media_upload)
    db.commit()
    db.refresh(media_upload)  # First refresh

    # Process image (placeholder for now)
    media_upload.processing_status = "completed"
    media_upload.extracted_data = {
        "message": "Image uploaded successfully. OCR processing will be implemented in production.",
        "filename": file.filename
    }
    media_upload.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(media_upload)  # Second refresh ← THIS WAS MISSING

    return UploadResponse(**media_upload.__dict__)