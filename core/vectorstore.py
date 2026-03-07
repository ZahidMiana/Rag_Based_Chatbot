import os
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain.schema import Document

from core.embeddings import get_embedding_function
from configs.settings import settings
from configs.logger import get_logger

logger = get_logger(__name__)

# MMR retrieval config
MMR_FETCH_K = 20
MMR_LAMBDA_MULT = 0.5
DEFAULT_TOP_K = 5
SCORE_THRESHOLD = 0.4


class VectorStoreManager:
    """
    Manages per-user ChromaDB collections.
    Each user gets an isolated collection: collection name = f"user_{user_id}"
    No user can ever read or write to another user's collection.
    """

    def __init__(self):
        os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._embedding_fn = get_embedding_function()
        self._stores: Dict[str, Chroma] = {}  # cache per user_id
        logger.info("vectorstore_initialized", path=settings.CHROMA_DB_PATH)

    def _collection_name(self, user_id: str) -> str:
        # ChromaDB collection names must be alphanumeric + underscores/hyphens
        safe_id = user_id.replace("-", "_")
        return f"user_{safe_id}"

    def _get_store(self, user_id: str) -> Chroma:
        """Get or create a LangChain Chroma store for the given user."""
        if user_id not in self._stores:
            self._stores[user_id] = Chroma(
                client=self._client,
                collection_name=self._collection_name(user_id),
                embedding_function=self._embedding_fn,
                collection_metadata={"hnsw:space": "cosine"},
            )
        return self._stores[user_id]

    def add_documents(self, user_id: str, chunks: List[Dict[str, Any]]) -> int:
        """
        Embed and upsert chunks into the user's collection.
        Each chunk: {"text": str, "metadata": dict}
        Returns number of chunks stored.
        """
        if not chunks:
            return 0

        store = self._get_store(user_id)
        documents = [
            Document(page_content=chunk["text"], metadata=chunk["metadata"])
            for chunk in chunks
        ]

        # Build deterministic IDs so re-ingestion won't duplicate
        ids = [
            f"{chunk['metadata']['doc_id']}_chunk_{i}"
            for i, chunk in enumerate(chunks)
        ]

        store.add_documents(documents=documents, ids=ids)
        logger.info("chunks_added", user_id=user_id, count=len(documents))
        return len(documents)

    def similarity_search(
        self,
        user_id: str,
        query: str,
        k: int = DEFAULT_TOP_K,
    ) -> List[Document]:
        """
        MMR search inside the user's collection.
        Fetches MMR_FETCH_K candidates, re-ranks with MMR, returns top k.
        Filters out chunks below SCORE_THRESHOLD.
        Returns empty list if no relevant results found.
        """
        store = self._get_store(user_id)

        try:
            # Check collection has any docs at all
            collection = self._client.get_collection(self._collection_name(user_id))
            if collection.count() == 0:
                return []
        except Exception:
            return []

        results = store.max_marginal_relevance_search(
            query=query,
            k=k,
            fetch_k=MMR_FETCH_K,
            lambda_mult=MMR_LAMBDA_MULT,
        )

        # Score threshold filter: re-rank with similarity scores
        if results:
            scored = store.similarity_search_with_score(query=query, k=MMR_FETCH_K)
            # Build a map of content → score
            score_map: Dict[str, float] = {doc.page_content: score for doc, score in scored}
            # Filter MMR results by threshold (cosine: lower = more similar in ChromaDB)
            filtered = [
                doc for doc in results
                if score_map.get(doc.page_content, 1.0) <= (1.0 - SCORE_THRESHOLD)
            ]
            if filtered:
                return filtered[:k]

        return results[:k] if results else []

    def delete_document(self, user_id: str, doc_id: str) -> int:
        """
        Delete all chunks belonging to a specific doc_id from the user's collection.
        Returns number of chunks deleted.
        """
        store = self._get_store(user_id)
        try:
            collection = self._client.get_collection(self._collection_name(user_id))
            # Get all chunk IDs for this doc
            results = collection.get(where={"doc_id": doc_id})
            ids_to_delete = results.get("ids", [])
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                # Invalidate cached store so next access is fresh
                if user_id in self._stores:
                    del self._stores[user_id]
                logger.info("doc_chunks_deleted", user_id=user_id, doc_id=doc_id, count=len(ids_to_delete))
            return len(ids_to_delete)
        except Exception as e:
            logger.error("delete_document_failed", user_id=user_id, doc_id=doc_id, error=str(e))
            return 0

    def get_document_ids(self, user_id: str) -> List[str]:
        """Return a list of unique doc_ids stored in the user's collection."""
        try:
            collection = self._client.get_collection(self._collection_name(user_id))
            results = collection.get(include=["metadatas"])
            ids = list({
                meta.get("doc_id")
                for meta in results.get("metadatas", [])
                if meta and meta.get("doc_id")
            })
            return ids
        except Exception:
            return []

    def delete_collection(self, user_id: str) -> None:
        """Nuke the entire user collection — used when deleting a user account."""
        try:
            self._client.delete_collection(self._collection_name(user_id))
            if user_id in self._stores:
                del self._stores[user_id]
            logger.info("collection_deleted", user_id=user_id)
        except Exception as e:
            logger.error("collection_delete_failed", user_id=user_id, error=str(e))

    def get_collection_count(self, user_id: str) -> int:
        """Return total number of chunks stored for a user."""
        try:
            collection = self._client.get_collection(self._collection_name(user_id))
            return collection.count()
        except Exception:
            return 0


# ── Module-level singleton ────────────────────────────────────────────────────
_vsm_instance: Optional[VectorStoreManager] = None


def get_vector_store_manager() -> VectorStoreManager:
    """Return the singleton VectorStoreManager. Safe to call multiple times."""
    global _vsm_instance
    if _vsm_instance is None:
        _vsm_instance = VectorStoreManager()
    return _vsm_instance
