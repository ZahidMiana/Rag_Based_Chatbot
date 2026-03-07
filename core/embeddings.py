import torch
from langchain_huggingface import HuggingFaceEmbeddings
from configs.settings import settings
from configs.logger import get_logger

logger = get_logger(__name__)

_embeddings_instance: HuggingFaceEmbeddings | None = None


def get_embedding_function() -> HuggingFaceEmbeddings:
    """
    Returns a singleton HuggingFaceEmbeddings instance.
    Model loads once at startup and is reused across all calls.
    """
    global _embeddings_instance

    if _embeddings_instance is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("loading_embedding_model", model=settings.HF_MODEL_NAME, device=device)

        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=settings.HF_MODEL_NAME,
            model_kwargs={"device": device},
            encode_kwargs={
                "normalize_embeddings": True,  # cosine similarity works correctly
                "batch_size": 64,
            },
        )
        logger.info("embedding_model_loaded", model=settings.HF_MODEL_NAME)

    return _embeddings_instance


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convenience wrapper — embed a list of strings and return vectors."""
    fn = get_embedding_function()
    return fn.embed_documents(texts)


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    fn = get_embedding_function()
    return fn.embed_query(text)
