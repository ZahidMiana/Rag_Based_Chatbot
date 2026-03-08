import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.rag_chain import get_rag_chain
from backend.models.chat import ChatHistory
from configs.logger import get_logger

logger = get_logger(__name__)


# ── Persistence helpers ───────────────────────────────────────────────────────

def _save_message(
    db: Session,
    user_id: str,
    session_id: str,
    role: str,
    content: str,
    sources: Optional[List[Dict[str, Any]]] = None,
) -> ChatHistory:
    record = ChatHistory(
        user_id=user_id,
        session_id=session_id,
        role=role,
        content=content,
        sources=json.dumps(sources) if sources else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── Public service functions ──────────────────────────────────────────────────

def ask(
    db: Session,
    user_id: str,
    question: str,
    session_id: str,
) -> Dict[str, Any]:
    """
    Main RAG query entry point.
    1. Persist the user question.
    2. Run the RAG chain.
    3. Persist the assistant answer + sources.
    4. Return the response dict.
    """
    # Persist user message
    _save_message(db, user_id, session_id, role="user", content=question)

    # Run RAG chain
    rag = get_rag_chain()
    result = rag.query(user_id=user_id, question=question, session_id=session_id)

    # Persist assistant message
    _save_message(
        db,
        user_id,
        session_id,
        role="assistant",
        content=result["answer"],
        sources=result["sources"],
    )

    logger.info("ask_complete", user_id=user_id, session_id=session_id)
    return result


def get_chat_history(
    db: Session,
    user_id: str,
    session_id: str,
    limit: int = 50,
) -> List[ChatHistory]:
    """Return up to `limit` messages for a session, oldest first."""
    return (
        db.query(ChatHistory)
        .filter(
            ChatHistory.user_id == user_id,
            ChatHistory.session_id == session_id,
        )
        .order_by(ChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )


def get_all_sessions(db: Session, user_id: str) -> List[Dict[str, Any]]:
    """Return all unique session IDs for a user with metadata."""
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.created_at.desc())
        .all()
    )

    sessions: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        sid = row.session_id
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "message_count": 0,
                "last_message_at": None,
            }
        sessions[sid]["message_count"] += 1
        if sessions[sid]["last_message_at"] is None:
            sessions[sid]["last_message_at"] = row.created_at

    return list(sessions.values())


def clear_history(db: Session, user_id: str, session_id: str) -> int:
    """Delete all messages for a session and reset the in-memory chain."""
    deleted = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.user_id == user_id,
            ChatHistory.session_id == session_id,
        )
        .delete()
    )
    db.commit()

    # Also reset in-memory chain memory
    get_rag_chain().reset_session(user_id, session_id)

    logger.info("history_cleared", user_id=user_id, session_id=session_id, deleted=deleted)
    return deleted
