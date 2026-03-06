import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from core.document_loader import DocumentLoader
from backend.services.doc_service import _compute_hash, _get_file_type


loader = DocumentLoader()


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_txt_file(content: str) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
    tmp.write(content)
    tmp.close()
    return tmp.name


def make_csv_file() -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8")
    tmp.write("name,age,city\nAlice,30,Lahore\nBob,25,Karachi\n")
    tmp.close()
    return tmp.name


# ── DocumentLoader Tests ──────────────────────────────────────────────────────

class TestDocumentLoader:

    def test_load_txt(self):
        path = make_txt_file("Hello RAG world. This is a test document.")
        try:
            result = loader.load_txt(path)
            assert len(result) == 1
            assert "Hello RAG world" in result[0]["text"]
            assert result[0]["page"] == 1
            assert result[0]["source"] == path
        finally:
            os.remove(path)

    def test_load_markdown(self):
        path = make_txt_file("# Heading\n\nThis is **bold** text and `code` block.\n\nAnother paragraph.")
        os.rename(path, path.replace(".txt", ".md"))
        md_path = path.replace(".txt", ".md")
        try:
            result = loader.load_markdown(md_path)
            assert len(result) == 1
            assert "Heading" in result[0]["text"]
            assert "**" not in result[0]["text"]
        finally:
            os.remove(md_path)

    def test_load_csv(self):
        path = make_csv_file()
        try:
            result = loader.load_csv(path)
            assert len(result) == 2
            assert "name: Alice" in result[0]["text"]
            assert "age: 25" in result[1]["text"]
        finally:
            os.remove(path)

    def test_auto_route_txt(self):
        path = make_txt_file("Routing test content for auto-detection.")
        try:
            result = loader.load(path)
            assert len(result) > 0
        finally:
            os.remove(path)

    def test_auto_route_csv(self):
        path = make_csv_file()
        try:
            result = loader.load(path)
            assert len(result) == 2
        finally:
            os.remove(path)

    def test_unsupported_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            loader.load("/fake/file.xyz")

    def test_empty_txt_returns_empty(self):
        path = make_txt_file("   ")
        try:
            result = loader.load_txt(path)
            assert result == []
        finally:
            os.remove(path)


# ── Hash & File Type Utilities ────────────────────────────────────────────────

class TestUtils:

    def test_compute_hash_consistent(self):
        data = b"some file content"
        assert _compute_hash(data) == _compute_hash(data)

    def test_compute_hash_different_inputs(self):
        assert _compute_hash(b"abc") != _compute_hash(b"xyz")

    def test_get_file_type_pdf(self):
        assert _get_file_type("report.pdf") == "pdf"

    def test_get_file_type_docx(self):
        assert _get_file_type("notes.DOCX") == "docx"

    def test_get_file_type_no_extension(self):
        assert _get_file_type("noextension") == ""


# ── doc_service deduplication ────────────────────────────────────────────────

class TestDocServiceDedup:

    def test_check_duplicate_returns_existing(self):
        from backend.services.doc_service import check_duplicate
        mock_db = MagicMock()
        existing_doc = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_doc

        result = check_duplicate(mock_db, "user_123", "somehash")
        assert result == existing_doc

    def test_check_duplicate_returns_none_when_new(self):
        from backend.services.doc_service import check_duplicate
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = check_duplicate(mock_db, "user_123", "newhash")
        assert result is None
