import os
import re
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
import pandas as pd

from configs.logger import get_logger

logger = get_logger(__name__)


class DocumentLoader:
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx", ".xls"}

    def load(self, source: str) -> List[Dict[str, Any]]:
        """Route to correct loader based on source type (file path or URL)."""
        if source.startswith("http://") or source.startswith("https://"):
            return self.load_url(source)

        ext = Path(source).suffix.lower()
        loaders = {
            ".pdf": self.load_pdf,
            ".docx": self.load_docx,
            ".txt": self.load_txt,
            ".md": self.load_markdown,
            ".csv": self.load_csv,
            ".xlsx": self.load_excel,
            ".xls": self.load_excel,
        }

        if ext not in loaders:
            raise ValueError(f"Unsupported file type: {ext}")

        return loaders[ext](source)

    def load_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        pages = []
        try:
            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                if text:
                    pages.append({
                        "text": text,
                        "page": page_num,
                        "source": file_path,
                    })
            doc.close()
        except Exception as e:
            logger.error("pdf_load_failed", path=file_path, error=str(e))
            raise
        return pages

    def load_docx(self, file_path: str) -> List[Dict[str, Any]]:
        pages = []
        try:
            doc = DocxDocument(file_path)
            full_text = "\n".join(
                para.text.strip()
                for para in doc.paragraphs
                if para.text.strip()
            )
            if full_text:
                pages.append({"text": full_text, "page": 1, "source": file_path})
        except Exception as e:
            logger.error("docx_load_failed", path=file_path, error=str(e))
            raise
        return pages

    def load_txt(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read().strip()
            if text:
                return [{"text": text, "page": 1, "source": file_path}]
        except Exception as e:
            logger.error("txt_load_failed", path=file_path, error=str(e))
            raise
        return []

    def load_markdown(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            # Strip common markdown symbols
            text = re.sub(r"#{1,6}\s", "", raw)
            text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
            text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text, flags=re.DOTALL)
            text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
            text = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", text)
            text = text.strip()
            if text:
                return [{"text": text, "page": 1, "source": file_path}]
        except Exception as e:
            logger.error("md_load_failed", path=file_path, error=str(e))
            raise
        return []

    def load_url(self, url: str) -> List[Dict[str, Any]]:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script/style noise
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
            text = "\n\n".join(p for p in paragraphs if len(p) > 40)

            if text:
                return [{"text": text, "page": 1, "source": url}]
        except Exception as e:
            logger.error("url_load_failed", url=url, error=str(e))
            raise
        return []

    def load_csv(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            df = pd.read_csv(file_path)
            rows = []
            for i, row in df.iterrows():
                row_text = ", ".join(f"{col}: {val}" for col, val in row.items() if pd.notna(val))
                if row_text:
                    rows.append({"text": row_text, "page": i + 1, "source": file_path})
            return rows
        except Exception as e:
            logger.error("csv_load_failed", path=file_path, error=str(e))
            raise

    def load_excel(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            df = pd.read_excel(file_path)
            rows = []
            for i, row in df.iterrows():
                row_text = ", ".join(f"{col}: {val}" for col, val in row.items() if pd.notna(val))
                if row_text:
                    rows.append({"text": row_text, "page": i + 1, "source": file_path})
            return rows
        except Exception as e:
            logger.error("excel_load_failed", path=file_path, error=str(e))
            raise
