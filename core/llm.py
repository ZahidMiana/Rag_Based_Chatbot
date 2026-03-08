import time
from functools import wraps
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted

from configs.settings import settings
from configs.logger import get_logger

logger = get_logger(__name__)

_llm_instance: Optional[ChatGoogleGenerativeAI] = None


def _retry_on_rate_limit(max_retries: int = 3, base_delay: float = 2.0):
    """Decorator: exponential backoff on Gemini 429 / ResourceExhausted."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except ResourceExhausted as e:
                    if attempt == max_retries:
                        logger.error("gemini_rate_limit_exhausted", attempts=max_retries)
                        raise
                    delay = base_delay ** attempt
                    logger.warning(
                        "gemini_rate_limit_retry",
                        attempt=attempt,
                        wait_seconds=delay,
                    )
                    time.sleep(delay)
            return fn(*args, **kwargs)  # final attempt
        return wrapper
    return decorator


def get_llm() -> ChatGoogleGenerativeAI:
    """
    Returns singleton Gemini 1.5 Flash LLM instance.
    Streaming enabled — supports token-by-token output.
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.3,
            max_output_tokens=2048,
            streaming=True,
            convert_system_message_to_human=True,
        )
        logger.info("gemini_llm_initialized", model="gemini-1.5-flash")
    return _llm_instance
