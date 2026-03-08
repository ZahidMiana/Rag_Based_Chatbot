"""
tests/test_rag.py
Unit tests for Module 4: RAG Core Engine
  - core/rag_chain.py
  - backend/services/rag_service.py
  - backend/schemas/chat.py
"""
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

# ── Schema tests ──────────────────────────────────────────────────────────────

from backend.schemas.chat import ChatRequest, ChatResponse, SourceCitation


def test_chat_request_validation():
    req = ChatRequest(user_id="u1", session_id="s1", question="What is AI?")
    assert req.question == "What is AI?"


def test_chat_request_empty_question():
    with pytest.raises(Exception):
        ChatRequest(user_id="u1", session_id="s1", question="")


def test_chat_response_builds():
    resp = ChatResponse(
        answer="AI is artificial intelligence.",
        sources=[SourceCitation(doc_id="d1", filename="ai.pdf", page=1)],
        session_id="s1",
    )
    assert len(resp.sources) == 1
    assert resp.sources[0].filename == "ai.pdf"


# ── RAGChain unit tests ───────────────────────────────────────────────────────

from core.rag_chain import RAGChain, _extract_sources, get_rag_chain
from langchain.schema import Document


def test_extract_sources_deduplication():
    docs = [
        Document(page_content="a", metadata={"doc_id": "d1", "page": 1, "source_name": "file.pdf"}),
        Document(page_content="b", metadata={"doc_id": "d1", "page": 1, "source_name": "file.pdf"}),
        Document(page_content="c", metadata={"doc_id": "d2", "page": 3, "source_name": "other.pdf"}),
    ]
    sources = _extract_sources(docs)
    assert len(sources) == 2
    assert sources[0]["filename"] == "file.pdf"


def test_extract_sources_empty():
    assert _extract_sources([]) == []


def test_chain_key_format():
    rag = RAGChain.__new__(RAGChain)
    rag._chains = {}
    rag._vsm = MagicMock()
    key = rag._chain_key("user1", "sess1")
    assert key == "user1::sess1"


def test_reset_session_removes_chain():
    rag = RAGChain.__new__(RAGChain)
    rag._chains = {"user1::sess1": MagicMock(), "user2::sess2": MagicMock()}
    rag._vsm = MagicMock()
    rag.reset_session("user1", "sess1")
    assert "user1::sess1" not in rag._chains
    assert "user2::sess2" in rag._chains


def test_reset_all_sessions():
    rag = RAGChain.__new__(RAGChain)
    rag._chains = {
        "u1::s1": MagicMock(),
        "u1::s2": MagicMock(),
        "u2::s1": MagicMock(),
    }
    rag._vsm = MagicMock()
    rag.reset_all_sessions("u1")
    assert "u1::s1" not in rag._chains
    assert "u1::s2" not in rag._chains
    assert "u2::s1" in rag._chains


def test_get_rag_chain_singleton():
    a = get_rag_chain()
    b = get_rag_chain()
    assert a is b


@patch("core.rag_chain.get_vector_store_manager")
@patch("core.rag_chain.get_llm")
def test_query_returns_expected_keys(mock_llm, mock_vsm):
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {
        "answer": "Test answer",
        "source_documents": [
            Document(
                page_content="x",
                metadata={"doc_id": "d1", "page": 2, "source_name": "test.pdf"},
            )
        ],
    }
    mock_store = MagicMock()
    mock_store.as_retriever.return_value = MagicMock()
    mock_vsm.return_value._get_store.return_value = mock_store

    rag = RAGChain()
    rag._chains["u1::s1"] = mock_chain

    result = rag.query("u1", "What is AI?", "s1")
    assert "answer" in result
    assert "sources" in result
    assert "session_id" in result
    assert result["answer"] == "Test answer"


# ── rag_service unit tests ────────────────────────────────────────────────────

from backend.services import rag_service


def test_ask_persists_messages():
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()

    mock_result = {
        "answer": "Hello",
        "sources": [{"doc_id": "d1", "filename": "f.pdf", "page": 1, "file_type": "pdf"}],
        "session_id": "s1",
    }

    with patch.object(rag_service, "get_rag_chain") as mock_get_chain:
        mock_chain = MagicMock()
        mock_chain.query.return_value = mock_result
        mock_get_chain.return_value = mock_chain

        result = rag_service.ask(mock_db, "u1", "What is AI?", "s1")

    assert result["answer"] == "Hello"
    # Two db.add calls: one for user msg, one for assistant msg
    assert mock_db.add.call_count == 2


def test_get_chat_history_calls_db():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    result = rag_service.get_chat_history(mock_db, "u1", "s1")
    assert result == []


def test_get_all_sessions_groups_correctly():
    from datetime import datetime

    mock_messages = []
    for i in range(3):
        m = MagicMock()
        m.session_id = "sess_A"
        m.created_at = datetime(2024, 1, i + 1)
        mock_messages.append(m)
    for i in range(2):
        m = MagicMock()
        m.session_id = "sess_B"
        m.created_at = datetime(2024, 1, i + 1)
        mock_messages.append(m)

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_messages

    sessions = rag_service.get_all_sessions(mock_db, "u1")
    counts = {s["session_id"]: s["message_count"] for s in sessions}
    assert counts["sess_A"] == 3
    assert counts["sess_B"] == 2


def test_clear_history_resets_chain():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.delete.return_value = 4
    mock_db.commit = MagicMock()

    with patch.object(rag_service, "get_rag_chain") as mock_get_chain:
        mock_chain = MagicMock()
        mock_get_chain.return_value = mock_chain
        deleted = rag_service.clear_history(mock_db, "u1", "s1")

    assert deleted == 4
    mock_chain.reset_session.assert_called_once_with("u1", "s1")
