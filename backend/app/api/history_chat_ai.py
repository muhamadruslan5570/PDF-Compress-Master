from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.models import ChatAIHistory, User

router = APIRouter(
    prefix="/api/history/chat-ai",
    tags=["Chat AI History"]
)


class ChatAIHistoryCreate(BaseModel):
    user_id: int
    user_message: str
    ai_reply: str
    session_id: Optional[str] = None


@router.post("")
def create_chat_ai_history(
    data: ChatAIHistoryCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == data.user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User tidak ditemukan"
        )

    history = ChatAIHistory(
        user_id=data.user_id,
        session_id=data.session_id,
        user_message=data.user_message,
        ai_reply=data.ai_reply
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    return {
        "success": True,
        "message": "Riwayat Chat AI berhasil disimpan",
        "data": {
            "id": history.id,
            "user_id": history.user_id,
            "session_id": history.session_id,
            "user_message": history.user_message,
            "ai_reply": history.ai_reply,
            "created_at": history.created_at
        }
    }


@router.get("")
def get_chat_ai_history(
    user_id: int,
    db: Session = Depends(get_db)
):
    histories = (
        db.query(ChatAIHistory)
        .filter(ChatAIHistory.user_id == user_id)
        .order_by(ChatAIHistory.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "count": len(histories),
        "data": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "session_id": item.session_id,
                "user_message": item.user_message,
                "ai_reply": item.ai_reply,
                "created_at": item.created_at
            }
            for item in histories
        ]
    }


@router.get("/{session_id}")
def get_chat_ai_session(
    session_id: str,
    user_id: int,
    db: Session = Depends(get_db)
):
    histories = (
        db.query(ChatAIHistory)
        .filter(
            ChatAIHistory.user_id == user_id,
            ChatAIHistory.session_id == session_id
        )
        .order_by(ChatAIHistory.created_at.asc())
        .all()
    )

    return {
        "success": True,
        "session_id": session_id,
        "count": len(histories),
        "data": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "session_id": item.session_id,
                "user_message": item.user_message,
                "ai_reply": item.ai_reply,
                "created_at": item.created_at
            }
            for item in histories
        ]
    }


@router.delete("/{session_id}")
def delete_chat_ai_session(
    session_id: str,
    user_id: int,
    db: Session = Depends(get_db)
):
    histories = (
        db.query(ChatAIHistory)
        .filter(
            ChatAIHistory.user_id == user_id,
            ChatAIHistory.session_id == session_id
        )
        .all()
    )

    if not histories:
        raise HTTPException(
            status_code=404,
            detail="Riwayat Chat AI tidak ditemukan"
        )

    for item in histories:
        db.delete(item)

    db.commit()

    return {
        "success": True,
        "message": "Riwayat Chat AI berhasil dihapus",
        "session_id": session_id,
        "deleted_count": len(histories)
    }
