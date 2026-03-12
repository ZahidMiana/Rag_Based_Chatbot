from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    GEMINI_API_KEY: str
    HF_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHROMA_DB_PATH: str = "./chroma_db"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "sqlite:///./rag_chatbot.db"
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:8501", "http://localhost:3000"]
    MAX_FILE_SIZE_MB: int = 50

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """Accept both comma-separated string and JSON list from .env."""
        if isinstance(v, str):
            # Handle JSON list: '["http://...", "http://..."]'
            stripped = v.strip()
            if stripped.startswith("["):
                import json
                return json.loads(stripped)
            # Handle comma-separated: 'http://...,http://...'
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return v


settings = Settings()
