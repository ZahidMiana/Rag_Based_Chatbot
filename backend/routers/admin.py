from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from db.database import get_db
from backend.models.user import User
from backend.models.document import Document
from backend.models.chat import ChatHistory
from backend.middleware.auth_middleware import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


class UserAdminResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    doc_count: int = 0

    model_config = {"from_attributes": True}


@router.get("/users", response_model=List[UserAdminResponse])
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    result = []
    for u in users:
        count = db.query(Document).filter(Document.user_id == u.id).count()
        result.append(
            UserAdminResponse(
                id=u.id,
                username=u.username,
                email=u.email,
                role=u.role,
                is_active=u.is_active,
                doc_count=count,
            )
        )
    return result


@router.delete("/users/{user_id}", status_code=200)
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    return {"message": f"User {user.username} deactivated"}


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total_users = db.query(User).count()
    total_docs = db.query(Document).count()
    queries_today = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.role == "user",
            ChatHistory.created_at >= today_start.isoformat(),
        )
        .count()
    )
    return {
        "total_users": total_users,
        "total_documents": total_docs,
        "queries_today": queries_today,
    }
