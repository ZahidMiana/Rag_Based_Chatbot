from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Form, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from backend.services import doc_service
from backend.schemas.document import DocumentResponse, DocumentStatusResponse
from backend.middleware.auth_middleware import get_current_user
from backend.middleware.rate_limit import limiter
from backend.models.user import User
from configs.settings import settings

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", status_code=202)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    if not file and not url:
        raise HTTPException(status_code=400, detail="Provide a file or a URL")

    if file:
        file_bytes = await file.read()
        filename = file.filename

        if len(file_bytes) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit",
            )

        file_hash = doc_service._compute_hash(file_bytes)
        duplicate = doc_service.check_duplicate(db, user_id, file_hash)
        if duplicate:
            return {"doc_id": duplicate.id, "status": "already_uploaded", "message": "File already uploaded"}

        doc = doc_service.create_document_record(db, user_id, filename, file_hash)
        background_tasks.add_task(
            doc_service.ingest_document, db, doc.id, user_id, file_bytes, filename
        )

    else:
        import hashlib
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        duplicate = doc_service.check_duplicate(db, user_id, url_hash)
        if duplicate:
            return {"doc_id": duplicate.id, "status": "already_uploaded", "message": "URL already ingested"}

        doc = doc_service.create_document_record(db, user_id, url, url_hash)
        background_tasks.add_task(
            doc_service.ingest_document, db, doc.id, user_id, b"", url
        )

    return {"doc_id": doc.id, "status": "processing"}


@router.get("/list", response_model=List[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return doc_service.get_documents(db, current_user.id)


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
def get_status(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = doc_service.get_document_status(db, current_user.id, doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.delete("/{doc_id}", status_code=200)
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = doc_service.delete_document(db, current_user.id, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted"}
