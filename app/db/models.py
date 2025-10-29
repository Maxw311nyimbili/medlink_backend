# All SQLAlchemy models

"""
All SQLAlchemy models for MedLink backend.
Complete schema for all 4 days - structure will NOT change.
"""

from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Text,
    ForeignKey, Float, JSON, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


# ============================================================================
# USER MODEL (Day 1)
# ============================================================================

class User(Base):
    """
    User model synced with Firebase Auth.
    Primary key is Firebase UID.
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)  # Firebase UID
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)

    # Preferences
    preferred_language = Column(String, default="en", nullable=False)
    consent_version = Column(String, nullable=True)  # e.g., "1.0"
    consent_given_at = Column(DateTime(timezone=True), nullable=True)
    onboarding_completed = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    forum_posts = relationship("ForumPost", back_populates="author", cascade="all, delete-orphan")
    forum_comments = relationship("ForumComment", back_populates="author", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    media_uploads = relationship("MediaUpload", back_populates="user", cascade="all, delete-orphan")


# ============================================================================
# FORUM MODELS (Day 2)
# ============================================================================

class ForumPost(Base):
    """
    Forum posts with offline sync support.
    """
    __tablename__ = "forum_posts"

    # Primary key (server-assigned)
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Offline sync tracking
    client_id = Column(String, nullable=True, index=True)  # UUID from mobile app

    # Content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)  # e.g., "pregnancy", "pediatrics"
    tags = Column(JSON, default=list)  # ["tag1", "tag2"]

    # Author
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_flagged = Column(Boolean, default=False, nullable=False)

    # Sync metadata
    version = Column(Integer, default=1, nullable=False)  # For conflict resolution
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    author = relationship("User", back_populates="forum_posts")
    comments = relationship("ForumComment", back_populates="post", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('idx_forum_posts_user_created', 'user_id', 'created_at'),
        Index('idx_forum_posts_category', 'category'),
        Index('idx_forum_posts_client_id', 'client_id'),
    )


class ForumComment(Base):
    """
    Comments on forum posts with offline sync.
    """
    __tablename__ = "forum_comments"

    # Primary key (server-assigned)
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Offline sync tracking
    client_id = Column(String, nullable=True, index=True)  # UUID from mobile app

    # Content
    content = Column(Text, nullable=False)

    # References
    post_id = Column(Integer, ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_comment_id = Column(Integer, ForeignKey("forum_comments.id", ondelete="CASCADE"),
                               nullable=True)  # For nested replies

    # Status
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_flagged = Column(Boolean, default=False, nullable=False)

    # Sync metadata
    version = Column(Integer, default=1, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    post = relationship("ForumPost", back_populates="comments")
    author = relationship("User", back_populates="forum_comments")
    replies = relationship("ForumComment", backref="parent", remote_side=[id])

    __table_args__ = (
        Index('idx_forum_comments_post_created', 'post_id', 'created_at'),
    )


class SyncQueue(Base):
    """
    Tracks pending operations from offline clients.
    Used for conflict resolution and audit trail.
    """
    __tablename__ = "sync_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Operation details
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)  # "post" or "comment"
    entity_id = Column(String, nullable=False)  # client_id or server id
    operation = Column(String(20), nullable=False)  # "create", "update", "delete"

    # Payload
    payload = Column(JSON, nullable=False)  # The actual data

    # Status
    status = Column(String(20), default="pending", nullable=False)  # pending, processed, failed
    conflict_resolution = Column(String(50), nullable=True)  # "server_wins", "client_wins", "merged"
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_sync_queue_status', 'status', 'created_at'),
        Index('idx_sync_queue_user', 'user_id', 'created_at'),
    )


# ============================================================================
# CHAT MODELS (Day 2-3)
# ============================================================================

class ChatMessage(Base):
    """
    Stores chat messages with confidence scores and sources.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Message content
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)

    # For assistant messages: structured response with confidence
    sentences = Column(JSON, nullable=True)  # [{"text": "...", "confidence": 0.9, "sources": [...]}]

    # Session tracking
    session_id = Column(String, nullable=True, index=True)  # Group messages in same conversation

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="chat_messages")

    __table_args__ = (
        Index('idx_chat_messages_user_session', 'user_id', 'session_id', 'created_at'),
    )


class ChatSource(Base):
    """
    Stores sources used in chat responses for traceability.
    """
    __tablename__ = "chat_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)

    message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)

    # Source details
    url = Column(String, nullable=False)
    title = Column(String(500), nullable=True)
    snippet = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=False)  # Weaviate certainty score

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ============================================================================
# MEDIA MODELS (Day 3)
# ============================================================================

class MediaUpload(Base):
    """
    Tracks uploaded images from MedScanner.
    """
    __tablename__ = "media_uploads"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # File details
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Local path or S3 URL
    file_size = Column(Integer, nullable=True)  # bytes
    mime_type = Column(String(100), nullable=False)

    # Processing results
    scan_type = Column(String(50), nullable=False)  # "barcode", "text_ocr", "label_ocr"
    extracted_data = Column(JSON, nullable=True)  # {"barcode": "...", "text": "..."}
    processing_status = Column(String(20), default="pending", nullable=False)  # pending, completed, failed
    error_message = Column(Text, nullable=True)

    # Metadata
    device_info = Column(JSON, nullable=True)  # Device model, OS version

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="media_uploads")

    __table_args__ = (
        Index('idx_media_uploads_user_created', 'user_id', 'created_at'),
        Index('idx_media_uploads_status', 'processing_status'),
    )


# ============================================================================
# LANDING PAGE MODELS (Day 2)
# ============================================================================

class Announcement(Base):
    """
    System announcements shown on landing page.
    """
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)

    # Targeting
    language = Column(String(10), default="en", nullable=False)  # "en", "es", etc.
    priority = Column(Integer, default=0, nullable=False)  # Higher = shown first

    # Visibility
    is_active = Column(Boolean, default=True, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_announcements_active_priority', 'is_active', 'priority', 'language'),
    )


class ConsentVersion(Base):
    """
    Tracks consent document versions for compliance.
    """
    __tablename__ = "consent_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    version = Column(String(20), unique=True, nullable=False)  # e.g., "1.0", "1.1"
    content = Column(Text, nullable=False)
    language = Column(String(10), default="en", nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_consent_versions_active', 'is_active', 'version'),
    )


# ============================================================================
# KNOWLEDGE BASE METADATA (Day 3)
# ============================================================================

class KnowledgeSource(Base):
    """
    Tracks sources ingested into Weaviate for RAG.
    Links Weaviate vector IDs to source metadata.
    """
    __tablename__ = "knowledge_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Source details
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String(1000), nullable=True)
    domain = Column(String(255), nullable=True)  # e.g., "mayoclinic.org"

    # Content metadata
    content_hash = Column(String(64), nullable=False)  # SHA-256 of content
    word_count = Column(Integer, nullable=True)
    language = Column(String(10), default="en", nullable=False)

    # Weaviate integration
    weaviate_id = Column(String, nullable=True, index=True)  # UUID in Weaviate
    ingestion_status = Column(String(20), default="pending", nullable=False)  # pending, completed, failed

    # Quality scores
    credibility_score = Column(Float, nullable=True)  # 0-1, based on domain reputation
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_knowledge_sources_status', 'ingestion_status'),
        Index('idx_knowledge_sources_domain', 'domain'),
    )