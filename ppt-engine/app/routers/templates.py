"""Template management router — CRUD for PPT template library."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import PlainTextResponse

from app.deps import get_template_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
async def list_templates():
    """List all templates in the library."""
    svc = get_template_service()
    return await svc.list_templates()


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get full details of a template."""
    svc = get_template_service()
    template = await svc.get_template(template_id)
    if template is None:
        raise HTTPException(404, f"Template not found: {template_id}")
    return template.model_dump()


@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    template_id: str = Form(...),
    display_name: str = Form(...),
    category: str = Form("general"),
    user_id: str = Form(""),
):
    """Upload a PPTX file and import it as a template.

    The file is processed by ``pptx_template_import.py`` to extract
    theme colors, fonts, SVG page skeletons, and brand assets.
    """
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(400, "Only .pptx files are accepted")

    # Write upload to temp file
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        svc = get_template_service()
        template = await svc.import_pptx(
            pptx_path=tmp_path,
            template_id=template_id,
            display_name=display_name,
            category=category,
            created_by=user_id,
        )
        return template.to_summary()
    except Exception as exc:
        logger.exception("Template import failed")
        raise HTTPException(500, f"Import failed: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    """Delete a template from the library."""
    svc = get_template_service()
    deleted = await svc.delete_template(template_id)
    if not deleted:
        raise HTTPException(404, f"Template not found: {template_id}")
    return {"deleted": True, "template_id": template_id}


@router.get("/{template_id}/pages/{filename}")
async def get_template_page_svg(template_id: str, filename: str):
    """Get a template page SVG content."""
    svc = get_template_service()
    svg = await svc.get_page_svg(template_id, filename)
    if svg is None:
        raise HTTPException(404, "Page not found")
    return PlainTextResponse(svg, media_type="image/svg+xml")
