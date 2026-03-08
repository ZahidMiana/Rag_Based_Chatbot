import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db.database import get_db
from backend.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatMessageResponse,
    SessionInfo,
    SourceCitation,
)
from backend.services import rag_service
from configs.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# ── POST /chat/query ──────────────────────────────────────────────────────────

@router.post("/query", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def query(payload: ChatRequest, db: Session = Depends(get_db)):
    """Run a RAG query and return the answer with source citations."""
    try:
        result = rag_service.ask(
            db=db,
            user_id=payload.user_id,
            question=payload.question,
            session_id=payload.session_id,
        )
        return ChatResponse(
            answer=result["answer"],
            sources=[SourceCitation(**s) for s in result["sources"]],
            session_id=result["session_id"],
        )
    except Exception as e:
        logger.error("chat_query_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer. Please try again.",
        )


# ── POST /chat/stream ─────────────────────────────────────────────────────────

@router.post("/stream")
async def stream_query(payload: ChatRequest):
    """Stream answer tokens via Server-Sent Events."""
    from core.rag_chain import get_rag_chain

    rag = get_rag_chain()

    async def event_generator():
        async for token in rag.stream_query(
            user_id=payload.user_id,
            question=payload.question,
            session_id=payload.session_id,
        ):
            yield f"data: {token}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── GET /chat/history ─────────────────────────────────────────────────────────

@router.get("/history", response_model=ChatHistoryResponse)
def get_history(user_id: str, session_id: str, db: Session = Depends(get_db)):
    """Retrieve all messages for a specific session."""
    messages = rag_service.get_chat_history(db, user_id, session_id)
    response_messages: List[ChatMessageResponse] = []
    for m in messages:
        sources = None
        if m.sources:
            try:
                sources = json.loads(m.sources)
            except json.JSONDecodeError:
                sources = []
        response_messages.append(
            ChatMessageResponse(
                id=m.id,
                user_id=m.user_id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                sources=sources,
                created_at=m.created_at,
            )
        )
    return ChatHistoryResponse(session_id=session_id, messages=response_messages)


# ── GET /chat/sessions ────────────────────────────────────────────────────────

@router.get("/sessions", response_model=List[SessionInfo])
def list_sessions(user_id: str, db: Session = Depends(get_db)):
    """List all chat sessions for a user."""
    sessions = rag_service.get_all_sessions(db, user_id)
    return [SessionInfo(**s) for s in sessions]


# ── DELETE /chat/history ──────────────────────────────────────────────────────

@router.delete("/history", status_code=status.HTTP_200_OK)
def delete_history(user_id: str, session_id: str, db: Session = Depends(get_db)):
    """Delete all messages in a session and reset the chain memory."""
    deleted = rag_service.clear_history(db, user_id, session_id)
    return {"deleted_count": deleted, "session_id": session_id}
