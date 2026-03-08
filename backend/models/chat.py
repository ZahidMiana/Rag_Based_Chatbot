import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from db.database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)       # "user" or "assistant"
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)       # JSON-encoded list of source dicts
    created_at = Column(DateTime, default=datetime.utcnow)
