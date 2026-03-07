"""
Module 3 — VectorStoreManager tests.

These tests use a temporary ChromaDB path so they never pollute the real DB.
They DO run real embeddings (all-MiniLM-L6-v2) because that's the correct
way to validate the vector store integration end-to-end.
Set env var SKIP_EMBED_TESTS=1 to skip if running in a CI environment
without the model downloaded.
"""

import os
import uuid
import shutil
import tempfile
import pytest

SKIP_EMBED = os.getenv("SKIP_EMBED_TESTS", "0") == "1"
skip_reason = "SKIP_EMBED_TESTS=1 — skipping embedding-heavy tests"


@pytest.fixture(scope="module")
def tmp_chroma_path():
    """Temporary ChromaDB dir, cleaned up after the module test session."""
    path = tempfile.mkdtemp(prefix="test_chroma_")
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="module")
def vsm(tmp_chroma_path):
    """Create a VectorStoreManager pointed at the temp path."""
    # Override settings path before importing
    import configs.settings as s
    original = s.settings.CHROMA_DB_PATH
    s.settings.CHROMA_DB_PATH = tmp_chroma_path

    from core.vectorstore import VectorStoreManager
    manager = VectorStoreManager()
    yield manager

    s.settings.CHROMA_DB_PATH = original


def make_chunks(doc_id: str, user_id: str, texts: list[str]) -> list[dict]:
    return [
        {
            "text": text,
            "metadata": {
                "user_id": user_id,
                "doc_id": doc_id,
                "source_name": "test_doc.pdf",
                "page": i + 1,
                "file_type": "pdf",
                "upload_timestamp": "2026-03-07T00:00:00",
            },
        }
        for i, text in enumerate(texts)
    ]


# ── add_documents ────────────────────────────────────────────────────────────

@pytest.mark.skipif(SKIP_EMBED, reason=skip_reason)
class TestAddDocuments:

    def test_add_returns_correct_count(self, vsm):
        user_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        chunks = make_chunks(doc_id, user_id, ["Alpha text.", "Beta text.", "Gamma text."])
        count = vsm.add_documents(user_id, chunks)
        assert count == 3

    def test_add_empty_returns_zero(self, vsm):
        user_id = str(uuid.uuid4())
        count = vsm.add_documents(user_id, [])
        assert count == 0

    def test_collection_count_increases(self, vsm):
        user_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        chunks = make_chunks(doc_id, user_id, [f"Chunk number {i}" for i in range(10)])
        vsm.add_documents(user_id, chunks)
        assert vsm.get_collection_count(user_id) == 10


# ── similarity_search ────────────────────────────────────────────────────────

@pytest.mark.skipif(SKIP_EMBED, reason=skip_reason)
class TestSimilaritySearch:

    def test_search_returns_results(self, vsm):
        user_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        texts = [
            "Machine learning is a subset of artificial intelligence.",
            "Python is a popular programming language.",
            "Neural networks are inspired by the human brain.",
            "Deep learning uses multiple layers of neurons.",
            "Natural language processing deals with text data.",
        ]
        vsm.add_documents(user_id, make_chunks(doc_id, user_id, texts))
        results = vsm.similarity_search(user_id, "What is deep learning?", k=3)
        assert len(results) <= 3
        assert len(results) > 0

    def test_search_empty_collection_returns_empty(self, vsm):
        user_id = str(uuid.uuid4())  # Fresh user, no documents
        results = vsm.similarity_search(user_id, "anything", k=5)
        assert results == []

    def test_user_isolation(self, vsm):
        """user_B should get 0 results from a query that matches user_A's docs."""
        user_a = str(uuid.uuid4())
        user_b = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())

        vsm.add_documents(
            user_a,
            make_chunks(doc_id, user_a, [
                "The Eiffel Tower is located in Paris, France.",
                "Paris is the capital city of France.",
                "The tower was built in 1889 by Gustave Eiffel.",
            ]),
        )

        # user_B has no documents — must return empty
        results_b = vsm.similarity_search(user_b, "Where is the Eiffel Tower?", k=5)
        assert results_b == [], f"Expected 0 results for user_B, got {len(results_b)}"

        # user_A must get results
        results_a = vsm.similarity_search(user_a, "Where is the Eiffel Tower?", k=3)
        assert len(results_a) > 0


# ── delete_document ──────────────────────────────────────────────────────────

@pytest.mark.skipif(SKIP_EMBED, reason=skip_reason)
class TestDeleteDocument:

    def test_delete_removes_chunks(self, vsm):
        user_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        chunks = make_chunks(doc_id, user_id, ["Delete me A.", "Delete me B.", "Delete me C."])
        vsm.add_documents(user_id, chunks)

        assert vsm.get_collection_count(user_id) == 3
        deleted = vsm.delete_document(user_id, doc_id)
        assert deleted == 3
        assert vsm.get_collection_count(user_id) == 0

    def test_delete_only_removes_target_doc(self, vsm):
        user_id = str(uuid.uuid4())
        doc_a = str(uuid.uuid4())
        doc_b = str(uuid.uuid4())

        vsm.add_documents(user_id, make_chunks(doc_a, user_id, ["Doc A chunk 1.", "Doc A chunk 2."]))
        vsm.add_documents(user_id, make_chunks(doc_b, user_id, ["Doc B chunk 1.", "Doc B chunk 2."]))

        assert vsm.get_collection_count(user_id) == 4
        vsm.delete_document(user_id, doc_a)
        assert vsm.get_collection_count(user_id) == 2  # only doc_b remains

    def test_delete_nonexistent_doc_returns_zero(self, vsm):
        user_id = str(uuid.uuid4())
        result = vsm.delete_document(user_id, "nonexistent_doc_id")
        assert result == 0


# ── get_document_ids ─────────────────────────────────────────────────────────

@pytest.mark.skipif(SKIP_EMBED, reason=skip_reason)
class TestGetDocumentIds:

    def test_returns_correct_doc_ids(self, vsm):
        user_id = str(uuid.uuid4())
        doc_a = str(uuid.uuid4())
        doc_b = str(uuid.uuid4())

        vsm.add_documents(user_id, make_chunks(doc_a, user_id, ["Chunk 1", "Chunk 2"]))
        vsm.add_documents(user_id, make_chunks(doc_b, user_id, ["Chunk 3", "Chunk 4"]))

        ids = vsm.get_document_ids(user_id)
        assert set(ids) == {doc_a, doc_b}

    def test_empty_user_returns_empty_list(self, vsm):
        user_id = str(uuid.uuid4())
        ids = vsm.get_document_ids(user_id)
        assert ids == []


# ── delete_collection ─────────────────────────────────────────────────────────

@pytest.mark.skipif(SKIP_EMBED, reason=skip_reason)
class TestDeleteCollection:

    def test_delete_collection_removes_all(self, vsm):
        user_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        vsm.add_documents(user_id, make_chunks(doc_id, user_id, ["A", "B", "C", "D", "E"]))
        assert vsm.get_collection_count(user_id) == 5
        vsm.delete_collection(user_id)
        assert vsm.get_collection_count(user_id) == 0


# ── get_collection_count ──────────────────────────────────────────────────────

class TestGetCollectionCount:

    def test_nonexistent_user_returns_zero(self, vsm):
        assert vsm.get_collection_count("totally_new_user_xyz") == 0
