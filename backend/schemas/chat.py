from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user asking the question")
    session_id: str = Field(..., description="Conversation session identifier")
    question: str = Field(..., min_length=1, max_length=4000)


class SourceCitation(BaseModel):
    doc_id: str
    filename: str
    page: int
    file_type: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    session_id: str


class ChatMessageResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    role: str                         # "user" or "assistant"
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessageResponse]


class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    last_message_at: Optional[datetime] = None
