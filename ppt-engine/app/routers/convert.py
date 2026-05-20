"""Document conversion router — MarkItDown preprocessing."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.deps import get_markitdown

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/convert", tags=["convert"])


@router.post("")
async def convert_document(
    file: UploadFile | None = File(None),
    url: str = Form(""),
    text: str = Form(""),
):
    """Convert an uploaded file, URL, or raw text to Markdown.

    Accepts one of:
    - ``file``: uploaded document (PDF, DOCX, XLSX, PPTX, HTML, etc.)
    - ``url``: URL to convert (web page, YouTube, etc.)
    - ``text``: raw text (returned as-is)
    """
    md_service = get_markitdown()

    if file is not None:
        content = await file.read()
        if not content:
            raise HTTPException(400, "Empty file uploaded")
        try:
            md_text = md_service.convert_bytes(content, file.filename or "document")
        except Exception as exc:
            logger.exception("Conversion failed: %s", file.filename)
            raise HTTPException(500, f"Conversion failed: {exc}") from exc
        return {
            "markdown": md_text,
            "source": file.filename,
            "source_type": "file",
            "char_count": len(md_text),
        }

    if url:
        try:
            md_text = md_service.convert_url(url)
        except Exception as exc:
            logger.exception("URL conversion failed: %s", url)
            raise HTTPException(500, f"URL conversion failed: {exc}") from exc
        return {
            "markdown": md_text,
            "source": url,
            "source_type": "url",
            "char_count": len(md_text),
        }

    if text:
        return {
            "markdown": text,
            "source": "raw_text",
            "source_type": "text",
            "char_count": len(text),
        }

    raise HTTPException(400, "Provide a file, URL, or text")
