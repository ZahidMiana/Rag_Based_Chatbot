from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    HF_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHROMA_DB_PATH: str = "./chroma_db"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "sqlite:///./rag_chatbot.db"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8501"]
    MAX_FILE_SIZE_MB: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
