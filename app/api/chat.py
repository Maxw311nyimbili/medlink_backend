"""
Chat API with real RAG using Weaviate + Ollama
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.core.deps import get_db, get_current_user
from app.db.models import ChatMessage, ChatSource, User
from app.services.rag_service import query_rag_system

router = APIRouter(prefix="/chat", tags=["chat"])


# ============================================================================
# DTOs
# ============================================================================

class SentenceWithConfidence(BaseModel):
    """Single sentence with confidence score and sources"""
    text: str
    confidence: float  # 0.0 to 1.0
    sources: List[dict]  # [{"url": "...", "title": "..."}]


class ChatQueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class ChatQueryResponse(BaseModel):
    answer: str
    sentences: List[SentenceWithConfidence]
    session_id: str


class ChatHistoryResponse(BaseModel):
    id: int
    role: str  # "user" or "assistant"
    content: str
    sentences: Optional[List[dict]]
    session_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/query", response_model=ChatQueryResponse)
def chat_query(
        request: ChatQueryRequest,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """
    Submit a medical query and get AI response with confidence scores.
    Uses Weaviate for retrieval and Ollama for generation.
    """
    # Generate or use existing session_id
    session_id = request.session_id or str(uuid.uuid4())

    # Save user message
    user_message = ChatMessage(
        user_id=user_id,
        role="user",
        content=request.query,
        session_id=session_id
    )
    db.add(user_message)
    db.commit()

    # Query RAG system (Weaviate + Ollama)
    rag_response = query_rag_system(request.query)

    # Save assistant message
    assistant_message = ChatMessage(
        user_id=user_id,
        role="assistant",
        content=rag_response["answer"],
        sentences=rag_response["sentences"],
        session_id=session_id
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    # Save sources for traceability
    for sentence in rag_response["sentences"]:
        for source in sentence.get("sources", []):
            chat_source = ChatSource(
                message_id=assistant_message.id,
                url=source["url"],
                title=source.get("title", ""),
                confidence_score=sentence["confidence"]
            )
            db.add(chat_source)

    db.commit()

    return ChatQueryResponse(
        answer=rag_response["answer"],
        sentences=[
            SentenceWithConfidence(**s) for s in rag_response["sentences"]
        ],
        session_id=session_id
    )


@router.get("/history", response_model=List[ChatHistoryResponse])
def get_chat_history(
        session_id: Optional[str] = None,
        limit: int = 50,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """Get chat history for current user"""
    query = db.query(ChatMessage).filter(ChatMessage.user_id == user_id)

    if session_id:
        query = query.filter(ChatMessage.session_id == session_id)

    messages = query.order_by(ChatMessage.created_at.desc()).limit(limit).all()

    return [ChatHistoryResponse(**msg.__dict__) for msg in reversed(messages)]


@router.delete("/history/{session_id}")
def delete_chat_session(
        session_id: str,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user)
):
    """Delete all messages in a chat session"""
    db.query(ChatMessage).filter(
        ChatMessage.user_id == user_id,
        ChatMessage.session_id == session_id
    ).delete()

    db.commit()

    return {"message": "Chat session deleted"}