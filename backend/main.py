from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from backend.middleware.logging_middleware import LoggingMiddleware
from backend.middleware.rate_limit import limiter
from backend.routers import auth, documents, chat, admin
from configs.settings import settings
from configs.logger import get_logger
from db.database import init_db, SessionLocal

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup_begin")
    init_db()
    from core.embeddings import get_embedding_function
    get_embedding_function()  # warmup — downloads model once
    from core.vectorstore import get_vector_store_manager
    get_vector_store_manager()  # open ChromaDB connection
    logger.info("startup_complete")
    yield
    logger.info("shutdown")


app = FastAPI(
    title="DocuMind AI",
    version="1.0.0",
    description="RAG-based document chat API. Upload docs, ask questions, get cited answers.",
    lifespan=lifespan,
)

# ── Rate limiter ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware (order matters: last added = outermost) ────────────────────────
app.add_middleware(LoggingMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(admin.router)


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_status = "error"

    chroma_status = "ok"
    try:
        from core.vectorstore import get_vector_store_manager
        get_vector_store_manager()
    except Exception:
        chroma_status = "error"

    return {
        "status": "ok",
        "db": db_status,
        "chroma": chroma_status,
        "version": "1.0.0",
    }

