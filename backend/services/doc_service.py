import hashlib
import os
import uuid
import tempfile
from datetime import datetime, timezone
from typing import List, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from backend.models.document import Document
from backend.schemas.document import DocumentResponse, DocumentStatusResponse
from core.document_loader import DocumentLoader
from core.vectorstore import get_vector_store_manager
from configs.logger import get_logger

logger = get_logger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

_loader = DocumentLoader()
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", " ", ""],
)


def _compute_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _get_file_type(filename: str) -> str:
    return os.path.splitext(filename)[-1].lower().lstrip(".")


def check_duplicate(db: Session, user_id: str, file_hash: str) -> Optional[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == user_id, Document.file_hash == file_hash)
        .first()
    )


def get_documents(db: Session, user_id: str) -> List[DocumentResponse]:
    docs = db.query(Document).filter(Document.user_id == user_id).all()
    return [DocumentResponse.model_validate(d) for d in docs]


def get_document_status(db: Session, user_id: str, doc_id: str) -> Optional[DocumentStatusResponse]:
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == user_id)
        .first()
    )
    if not doc:
        return None
    return DocumentStatusResponse(
        doc_id=doc.id,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
    )


def create_document_record(
    db: Session, user_id: str, filename: str, file_hash: str
) -> Document:
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=user_id,
        filename=filename,
        file_type=_get_file_type(filename),
        file_hash=file_hash,
        status="processing",
        chunk_count=0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def ingest_document(
    db: Session,
    doc_id: str,
    user_id: str,
    file_bytes: bytes,
    filename: str,
    vector_store_manager=None,
) -> None:
    """
    Full ingestion pipeline: load → chunk → embed+store → update status.
    Uses the singleton VectorStoreManager if none is explicitly passed.
    """
    if vector_store_manager is None:
        vector_store_manager = get_vector_store_manager()
    tmp_path = None
    try:
        # Save to temp file
        suffix = os.path.splitext(filename)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # Load raw pages
        raw_pages = _loader.load(tmp_path)

        if not raw_pages:
            _update_status(db, doc_id, "failed", error="No text extracted from document")
            return

        # Chunk each page
        all_chunks = []
        for page_data in raw_pages:
            splits = _splitter.split_text(page_data["text"])
            for split_text in splits:
                all_chunks.append({
                    "text": split_text,
                    "metadata": {
                        "user_id": user_id,
                        "doc_id": doc_id,
                        "source_name": filename,
                        "page": page_data["page"],
                        "file_type": _get_file_type(filename),
                        "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                })

        # Store in vector store
        vector_store_manager.add_documents(user_id, all_chunks)

        _update_status(db, doc_id, "ready", chunk_count=len(all_chunks))
        logger.info("ingestion_complete", doc_id=doc_id, chunks=len(all_chunks))

    except Exception as e:
        logger.error("ingestion_failed", doc_id=doc_id, error=str(e))
        _update_status(db, doc_id, "failed", error=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def delete_document(
    db: Session, user_id: str, doc_id: str, vector_store_manager=None
) -> bool:
    if vector_store_manager is None:
        vector_store_manager = get_vector_store_manager()
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == user_id)
        .first()
    )
    if not doc:
        return False

    try:
        vector_store_manager.delete_document(user_id, doc_id)
    except Exception as e:
        logger.error("vectorstore_delete_failed", doc_id=doc_id, error=str(e))

    db.delete(doc)
    db.commit()
    return True


def _update_status(
    db: Session,
    doc_id: str,
    status: str,
    chunk_count: int = 0,
    error: Optional[str] = None,
) -> None:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        doc.status = status
        doc.chunk_count = chunk_count
        doc.error_message = error
        db.commit()
