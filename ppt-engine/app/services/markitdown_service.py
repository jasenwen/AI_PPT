"""MarkItDown service — document-to-Markdown preprocessing.

Wraps microsoft/markitdown with LiteLLM-backed OCR for images.
Supports: PDF, DOCX, XLSX, PPTX, HTML, CSV, JSON, XML, Images, Audio, ZIP.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from markitdown import MarkItDown

from app.services.llm_client import LLMClient
from app.config import Settings

logger = logging.getLogger(__name__)


class MarkItDownService:
    """Convert uploaded files to structured Markdown."""

    def __init__(self, llm_client: LLMClient, settings: Settings) -> None:
        self._llm_client = llm_client
        self._settings = settings
        self._md = MarkItDown(
            enable_plugins=True,
            llm_client=llm_client.get_openai_client(),
            llm_model=settings.ocr_model,
        )

    def convert_file(self, file_path: str | Path) -> str:
        """Convert a local file to Markdown.

        Args:
            file_path: Absolute or relative path to the source file.

        Returns:
            Markdown text content.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")

        logger.info("MarkItDown converting: %s (%d bytes)", path.name, path.stat().st_size)
        result = self._md.convert(str(path))
        md_text = result.text_content or ""
        logger.info("MarkItDown result: %d chars", len(md_text))
        return md_text

    def convert_bytes(self, data: bytes, filename: str) -> str:
        """Convert in-memory file bytes to Markdown.

        Writes to a temp file then converts — MarkItDown requires
        a file path for most converters.
        """
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            return self.convert_file(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def convert_url(self, url: str) -> str:
        """Convert a URL to Markdown (HTML pages, YouTube, etc.)."""
        logger.info("MarkItDown converting URL: %s", url)
        result = self._md.convert(url)
        md_text = result.text_content or ""
        logger.info("MarkItDown URL result: %d chars", len(md_text))
        return md_text
