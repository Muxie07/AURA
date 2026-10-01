import io
from abc import ABC, abstractmethod
from typing import Any

import docx
import pypdf
import structlog

logger = structlog.get_logger(__name__)

class DocumentParser(ABC):
    """Base abstraction for all document parsers."""

    @abstractmethod
    def parse(self, content: bytes) -> tuple[str, dict[str, Any]]:
        """Parses document bytes into (extracted_text, metadata)."""
        pass

class TextParser(DocumentParser):
    def parse(self, content: bytes) -> tuple[str, dict[str, Any]]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback for some windows encodings if utf-8 fails
            text = content.decode("windows-1252", errors="ignore")
        return text, {"format": "txt"}

class MarkdownParser(DocumentParser):
    def parse(self, content: bytes) -> tuple[str, dict[str, Any]]:
        # For Phase 3, markdown is treated as text
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("windows-1252", errors="ignore")
        return text, {"format": "markdown"}

class PDFParser(DocumentParser):
    def parse(self, content: bytes) -> tuple[str, dict[str, Any]]:
        try:
            pdf_file = io.BytesIO(content)
            reader = pypdf.PdfReader(pdf_file)

            text_parts = []
            for _i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            full_text = "\n\n".join(text_parts)

            meta: dict[str, Any] = dict(reader.metadata or {})
            metadata = {
                "format": "pdf",
                "pages": len(reader.pages),
                "author": meta.get("/Author", "Unknown"),
                "title": meta.get("/Title", "Unknown")
            }
            return full_text, metadata
        except Exception as e:
            logger.error("pdf_parsing_failed", error=str(e))
            raise ValueError(f"Failed to parse PDF: {e}") from e

class DocxParser(DocumentParser):
    def parse(self, content: bytes) -> tuple[str, dict[str, Any]]:
        try:
            docx_file = io.BytesIO(content)
            doc = docx.Document(docx_file)

            full_text = "\n".join([para.text for para in doc.paragraphs])

            metadata = {
                "format": "docx",
                "paragraphs": len(doc.paragraphs)
            }
            return full_text, metadata
        except Exception as e:
            logger.error("docx_parsing_failed", error=str(e))
            raise ValueError(f"Failed to parse DOCX: {e}") from e

def get_parser(content_type: str, filename: str) -> DocumentParser:
    """Factory to get the right parser based on content_type/filename."""
    content_type = content_type.lower()
    filename = filename.lower()

    if "pdf" in content_type or filename.endswith(".pdf"):
        return PDFParser()
    elif "word" in content_type or "officedocument" in content_type or filename.endswith(".docx"):
        return DocxParser()
    elif "markdown" in content_type or filename.endswith(".md"):
        return MarkdownParser()
    else:
        # Default to text
        return TextParser()
