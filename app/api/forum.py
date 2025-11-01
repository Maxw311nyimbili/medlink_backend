"""
Forum API endpoints for posts and comments with offline sync support.
FIXED: All endpoints now have author_name fallback to email or "Unknown"
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.deps import get_db, get_current_user
from app.db.models import ForumPost, ForumComment, User, SyncQueue
from app.services.sync_service import process_sync_batch

router = APIRouter(prefix="/forum", tags=["forum"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_author_name(user: Optional[User]) -> str:
    """
    Get author name with fallback chain.
    display_name → email → "Unknown"
    """
    if not user:
        return "Unknown"
    return user.display_name or user.email or "Unknown"


# ============================================================================
# DTOs (Request/Response Models)
# ============================================================================

class CreatePostRequest(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    tags: Optional[List[str]] = []
    client_id: Optional[str] = None  # For offline sync


class UpdatePostRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class CreateCommentRequest(BaseModel):
    content: str
    parent_comment_id: Optional[int] = None
    client_id: Optional[str] = None  # For offline sync


class PostResponse(BaseModel):
    id: int
    client_id: Optional[str]
    title: str
    content: str
    category: Optional[str]
    tags: List[str]
    user_id: str
    author_name: Optional[str]
    is_deleted: bool
    version: int
    created_at: datetime
    updated_at: Optional[datetime]
    comment_count: int = 0

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    id: int
    client_id: Optional[str]
    content: str
    post_id: int
    user_id: str
    author_name: Optional[str]
    parent_comment_id: Optional[int]
    is_deleted: bool
    version: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SyncBatchRequest(BaseModel):
    """Batch sync request from offline client"""
    operations: List[dict]  # [{"type": "create_post", "data": {...}, "client_id": "..."}]


class SyncBatchResponse(BaseModel):
    """Returns mapping of client_id → server_id"""
    synced: dict  # {"client-uuid-1": 123, "client-uuid-2": 124}
    conflicts: List[dict]
    errors: List[dict]


# ============================================================================
# FORUM POSTS ENDPOINTS
# ============================================================================

@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
        request: CreatePostRequest,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """
    Create a new forum post.

    Supports offline sync via client_id.

    FIXED: Always returns author_name (with fallback to email or "Unknown")
    """
    # Check if client_id already exists (duplicate sync)
    if request.client_id:
        existing = db.query(ForumPost).filter(
            ForumPost.client_id == request.client_id
        ).first()
        if existing:
            # Already synced, return existing
            author = db.query(User).filter(User.id == existing.user_id).first()
            author_name = get_author_name(author)
            return PostResponse(
                **existing.__dict__,
                author_name=author_name,
                comment_count=len(existing.comments)
            )

    # Create new post
    post = ForumPost(
        title=request.title,
        content=request.content,
        category=request.category,
        tags=request.tags or [],
        user_id=user_id,
        client_id=request.client_id,
        version=1
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    author = db.query(User).filter(User.id == user_id).first()
    author_name = get_author_name(author)

    return PostResponse(
        **post.__dict__,
        author_name=author_name,
        comment_count=0
    )


@router.get("/posts", response_model=List[PostResponse])
def get_posts(
        category: Optional[str] = None,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db)
):
    """
    Get forum posts with optional category filter.
    Returns posts sorted by most recent first.

    FIXED: All posts include author_name with fallback
    """
    query = db.query(ForumPost).filter(ForumPost.is_deleted == False)

    if category:
        query = query.filter(ForumPost.category == category)

    posts = query.order_by(desc(ForumPost.created_at)).offset(offset).limit(limit).all()

    # Get authors
    user_ids = [p.user_id for p in posts]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: get_author_name(u) for u in users}

    return [
        PostResponse(
            **post.__dict__,
            author_name=user_map.get(post.user_id, "Unknown"),
            comment_count=len([c for c in post.comments if not c.is_deleted])
        )
        for post in posts
    ]


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(
        post_id: int,
        db: Session = Depends(get_db)
):
    """
    Get a single post by ID

    FIXED: Always returns author_name with fallback
    """
    post = db.query(ForumPost).filter(
        and_(ForumPost.id == post_id, ForumPost.is_deleted == False)
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    author = db.query(User).filter(User.id == post.user_id).first()
    author_name = get_author_name(author)

    return PostResponse(
        **post.__dict__,
        author_name=author_name,
        comment_count=len([c for c in post.comments if not c.is_deleted])
    )


@router.put("/posts/{post_id}", response_model=PostResponse)
def update_post(
        post_id: int,
        request: UpdatePostRequest,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """
    Update a post (only by author)

    FIXED: Always returns author_name with fallback
    """
    post = db.query(ForumPost).filter(ForumPost.id == post_id).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this post")

    # Update fields
    if request.title is not None:
        post.title = request.title
    if request.content is not None:
        post.content = request.content
    if request.category is not None:
        post.category = request.category
    if request.tags is not None:
        post.tags = request.tags

    post.version += 1  # Increment version for conflict detection

    db.commit()
    db.refresh(post)

    author = db.query(User).filter(User.id == user_id).first()
    author_name = get_author_name(author)

    return PostResponse(
        **post.__dict__,
        author_name=author_name,
        comment_count=len(post.comments)
    )


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
        post_id: int,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """Soft delete a post (only by author)"""
    post = db.query(ForumPost).filter(ForumPost.id == post_id).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    post.is_deleted = True
    post.version += 1

    db.commit()

    return None


# ============================================================================
# FORUM COMMENTS ENDPOINTS
# ============================================================================

@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
        post_id: int,
        request: CreateCommentRequest,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """
    Add a comment to a post

    FIXED: Always returns author_name with fallback
    """
    # Verify post exists
    post = db.query(ForumPost).filter(
        and_(ForumPost.id == post_id, ForumPost.is_deleted == False)
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check for duplicate client_id
    if request.client_id:
        existing = db.query(ForumComment).filter(
            ForumComment.client_id == request.client_id
        ).first()
        if existing:
            author = db.query(User).filter(User.id == existing.user_id).first()
            author_name = get_author_name(author)
            return CommentResponse(
                **existing.__dict__,
                author_name=author_name
            )

    comment = ForumComment(
        content=request.content,
        post_id=post_id,
        user_id=user_id,
        parent_comment_id=request.parent_comment_id,
        client_id=request.client_id,
        version=1
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    author = db.query(User).filter(User.id == user_id).first()
    author_name = get_author_name(author)

    return CommentResponse(
        **comment.__dict__,
        author_name=author_name
    )


@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
def get_comments(
        post_id: int,
        db: Session = Depends(get_db)
):
    """
    Get all comments for a post

    FIXED: All comments include author_name with fallback
    """
    comments = db.query(ForumComment).filter(
        and_(
            ForumComment.post_id == post_id,
            ForumComment.is_deleted == False
        )
    ).order_by(ForumComment.created_at).all()

    # Get authors
    user_ids = [c.user_id for c in comments]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: get_author_name(u) for u in users}

    return [
        CommentResponse(
            **comment.__dict__,
            author_name=user_map.get(comment.user_id, "Unknown")
        )
        for comment in comments
    ]


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
        comment_id: int,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """Soft delete a comment (only by author)"""
    comment = db.query(ForumComment).filter(ForumComment.id == comment_id).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    comment.is_deleted = True
    comment.version += 1

    db.commit()

    return None


# ============================================================================
# OFFLINE SYNC ENDPOINT
# ============================================================================

@router.post("/sync", response_model=SyncBatchResponse)
def sync_offline_changes(
        request: SyncBatchRequest,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """
    Batch sync offline changes.

    Frontend sends all pending operations (creates, updates, deletes).
    Backend processes them and returns client_id → server_id mapping.

    Conflict resolution: Last-write-wins based on version numbers.
    """
    result = process_sync_batch(request.operations, user_id, db)
    return SyncBatchResponse(**result)