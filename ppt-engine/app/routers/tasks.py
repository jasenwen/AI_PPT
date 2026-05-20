"""Task lifecycle router — create, poll, and download PPT tasks."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.deps import get_db, get_task_worker
from app.models.task import PPTTask, TaskStatus, PageResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------

class CreateTaskRequest(BaseModel):
    """Request body for creating a new PPT generation task."""
    user_id: str
    conversation_id: str = ""
    source_markdown: str
    source_filename: str = ""
    template_id: str = ""
    outline: dict = Field(default_factory=dict)
    design_spec: str = ""
    spec_lock: str = ""
    total_pages: int = 0
    pages: list[dict] = Field(default_factory=list)


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("")
async def create_task(req: CreateTaskRequest):
    """Create a PPT generation task and start execution.

    Called after the user confirms the outline and selects a template.
    The task is immediately queued for background execution.
    """
    db = get_db()
    task_id = str(uuid.uuid4())[:12]

    # Build page list
    page_results = []
    for i, p in enumerate(req.pages):
        page_results.append(PageResult(
            page_num=i + 1,
            page_type=p.get("type", "content"),
            title=p.get("title", ""),
            status="pending",
        ))
    # Fallback: create pages from total_pages if pages list is empty
    if not page_results and req.total_pages > 0:
        for i in range(req.total_pages):
            page_results.append(PageResult(page_num=i + 1, status="pending"))

    task = PPTTask(
        task_id=task_id,
        user_id=req.user_id,
        conversation_id=req.conversation_id,
        status=TaskStatus.OUTLINE_CONFIRMED,
        source_markdown=req.source_markdown,
        source_filename=req.source_filename,
        template_id=req.template_id,
        outline=req.outline,
        design_spec=req.design_spec,
        spec_lock=req.spec_lock,
        total_pages=len(page_results),
        pages=page_results,
    )

    # Persist to MongoDB
    await db.ppt_tasks.insert_one(task.model_dump())

    # Start background execution
    worker = get_task_worker()
    asyncio.create_task(worker.execute(task_id))

    logger.info("Task created: %s (%d pages)", task_id, len(page_results))
    return {"task_id": task_id, "status": task.status.value, "total_pages": len(page_results)}


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    """Poll task progress."""
    db = get_db()
    doc = await db.ppt_tasks.find_one({"task_id": task_id}, {"_id": 0})
    if doc is None:
        raise HTTPException(404, f"Task not found: {task_id}")

    task = PPTTask(**doc)
    return task.to_progress()


@router.get("/{task_id}/pages/{page_num}/svg")
async def get_page_svg(task_id: str, page_num: int):
    """Get the generated SVG for a specific page."""
    from fastapi.responses import PlainTextResponse
    from app.config import settings

    db = get_db()
    doc = await db.ppt_tasks.find_one({"task_id": task_id}, {"_id": 0})
    if doc is None:
        raise HTTPException(404, "Task not found")

    task = PPTTask(**doc)
    if page_num < 1 or page_num > len(task.pages):
        raise HTTPException(404, "Page not found")

    page = task.pages[page_num - 1]
    if page.status != "done" or not page.svg_path:
        raise HTTPException(404, "Page not yet generated")

    svg_file = settings.projects_path / task.task_id / page.svg_path
    if not svg_file.exists():
        raise HTTPException(404, "SVG file not found on disk")

    return PlainTextResponse(
        svg_file.read_text(encoding="utf-8"),
        media_type="image/svg+xml",
    )


@router.get("/{task_id}/download")
async def download_pptx(task_id: str):
    """Download the generated PPTX file."""
    db = get_db()
    doc = await db.ppt_tasks.find_one({"task_id": task_id}, {"_id": 0})
    if doc is None:
        raise HTTPException(404, "Task not found")

    task = PPTTask(**doc)
    if task.status != TaskStatus.COMPLETED or not task.pptx_path:
        raise HTTPException(400, "PPTX not ready — task status: " + task.status.value)

    pptx_file = Path(task.pptx_path)
    if not pptx_file.exists():
        raise HTTPException(404, "PPTX file not found on disk")

    filename = task.source_filename.rsplit(".", 1)[0] + ".pptx" if task.source_filename else "presentation.pptx"
    return FileResponse(
        str(pptx_file),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )
