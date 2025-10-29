# Forum sync logic (Day 2)
"""
Offline sync service for forum posts and comments.
Handles conflict resolution and batch operations.
"""
from sqlalchemy.orm import Session
from app.db.models import ForumPost, ForumComment, SyncQueue
from datetime import datetime


def process_sync_batch(operations: list, user_id: str, db: Session) -> dict:
    """
    Process a batch of sync operations from offline client.

    Returns:
        {
            "synced": {"client-id-1": server_id_1, ...},
            "conflicts": [{...}],
            "errors": [{...}]
        }
    """
    synced = {}
    conflicts = []
    errors = []

    for op in operations:
        try:
            op_type = op.get("type")
            data = op.get("data", {})
            client_id = op.get("client_id")

            if op_type == "create_post":
                result = _sync_create_post(data, client_id, user_id, db)
                if result:
                    synced[client_id] = result

            elif op_type == "create_comment":
                result = _sync_create_comment(data, client_id, user_id, db)
                if result:
                    synced[client_id] = result

            elif op_type == "update_post":
                result = _sync_update_post(data, user_id, db)
                if result.get("conflict"):
                    conflicts.append(result)

            elif op_type == "delete_post":
                _sync_delete_post(data, user_id, db)

            else:
                errors.append({"client_id": client_id, "error": f"Unknown operation: {op_type}"})

        except Exception as e:
            errors.append({"client_id": client_id, "error": str(e)})

    db.commit()

    return {
        "synced": synced,
        "conflicts": conflicts,
        "errors": errors
    }


def _sync_create_post(data: dict, client_id: str, user_id: str, db: Session) -> int:
    """Create or retrieve existing post by client_id"""
    # Check if already synced
    existing = db.query(ForumPost).filter(ForumPost.client_id == client_id).first()
    if existing:
        return existing.id

    # Create new
    post = ForumPost(
        title=data["title"],
        content=data["content"],
        category=data.get("category"),
        tags=data.get("tags", []),
        user_id=user_id,
        client_id=client_id,
        version=1
    )
    db.add(post)
    db.flush()  # Get ID without committing

    return post.id


def _sync_create_comment(data: dict, client_id: str, user_id: str, db: Session) -> int:
    """Create or retrieve existing comment by client_id"""
    existing = db.query(ForumComment).filter(ForumComment.client_id == client_id).first()
    if existing:
        return existing.id

    comment = ForumComment(
        content=data["content"],
        post_id=data["post_id"],
        user_id=user_id,
        parent_comment_id=data.get("parent_comment_id"),
        client_id=client_id,
        version=1
    )
    db.add(comment)
    db.flush()

    return comment.id


def _sync_update_post(data: dict, user_id: str, db: Session) -> dict:
    """
    Update post with conflict detection.
    Uses optimistic locking (version numbers).
    """
    post_id = data.get("id")
    client_version = data.get("version", 1)

    post = db.query(ForumPost).filter(ForumPost.id == post_id).first()

    if not post:
        return {"conflict": True, "reason": "Post not found"}

    if post.user_id != user_id:
        return {"conflict": True, "reason": "Not authorized"}

    # Conflict detection: server version ahead of client
    if post.version > client_version:
        return {
            "conflict": True,
            "reason": "Version conflict",
            "server_version": post.version,
            "client_version": client_version
        }

    # Apply update
    if "title" in data:
        post.title = data["title"]
    if "content" in data:
        post.content = data["content"]
    if "category" in data:
        post.category = data["category"]
    if "tags" in data:
        post.tags = data["tags"]

    post.version += 1
    db.flush()

    return {"success": True}


def _sync_delete_post(data: dict, user_id: str, db: Session):
    """Soft delete post"""
    post_id = data.get("id")
    post = db.query(ForumPost).filter(ForumPost.id == post_id).first()

    if post and post.user_id == user_id:
        post.is_deleted = True
        post.version += 1
        db.flush()