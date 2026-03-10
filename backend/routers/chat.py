import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db.database import get_db
from backend.schemas.chat import (
    ChatQueryBody,
    ChatResponse,
    ChatHistoryResponse,
    ChatMessageResponse,
    SessionInfo,
    SourceCitation,
)
from backend.services import rag_service
from backend.middleware.auth_middleware import get_current_user
from backend.middleware.rate_limit import limiter
from backend.models.user import User
from configs.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/query", response_model=ChatResponse, status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
def query(
    request: Request,
    payload: ChatQueryBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = rag_service.ask(
            db=db,
            user_id=current_user.id,
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


@router.post("/stream")
async def stream_query(
    payload: ChatQueryBody,
    current_user: User = Depends(get_current_user),
):
    from core.rag_chain import get_rag_chain
    rag = get_rag_chain()

    async def event_generator():
        async for token in rag.stream_query(
            user_id=current_user.id,
            question=payload.question,
            session_id=payload.session_id,
        ):
            yield f"data: {token}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history", response_model=ChatHistoryResponse)
def get_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    messages = rag_service.get_chat_history(db, current_user.id, session_id)
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


@router.get("/sessions", response_model=List[SessionInfo])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = rag_service.get_all_sessions(db, current_user.id)
    return [SessionInfo(**s) for s in sessions]


@router.delete("/history", status_code=status.HTTP_200_OK)
def delete_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = rag_service.clear_history(db, current_user.id, session_id)
    return {"deleted_count": deleted, "session_id": session_id}
