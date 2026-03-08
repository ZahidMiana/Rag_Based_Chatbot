import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from configs.settings import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import all models so Base sees them before create_all
    import backend.models.document  # noqa: F401
    import backend.models.chat      # noqa: F401
    Base.metadata.create_all(bind=engine)
