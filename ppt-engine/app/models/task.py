"""PPT Task data model — stored in MongoDB ``ppt_tasks`` collection.

Implements the deterministic task state machine:
  PENDING → PREPROCESSING → OUTLINE_READY → OUTLINE_CONFIRMED
  → GENERATING → FINALIZING → EXPORTING → COMPLETED
  (any state) → FAILED
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    OUTLINE_READY = "outline_ready"
    OUTLINE_CONFIRMED = "outline_confirmed"
    GENERATING = "generating"
    FINALIZING = "finalizing"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class PageResult(BaseModel):
    """Result for a single generated slide."""
    page_num: int
    page_type: str = "content"       # cover / chapter / content / ending
    title: str = ""
    svg_path: str = ""               # relative path to SVG file
    status: str = "pending"          # pending / generating / done / error
    error: str = ""


class PPTTask(BaseModel):
    """Full task record persisted in MongoDB."""
    task_id: str
    user_id: str
    conversation_id: str = ""

    status: TaskStatus = TaskStatus.PENDING
    progress_message: str = ""

    # ---- Input ----
    source_markdown: str = ""
    source_filename: str = ""
    research_data: str = ""
    template_id: str = ""            # selected template

    # ---- Strategist phase output (locked after confirmation) ----
    outline: dict[str, Any] = Field(default_factory=dict)
    design_spec: str = ""
    spec_lock: str = ""

    # ---- Executor phase progress ----
    total_pages: int = 0
    completed_pages: int = 0
    pages: list[PageResult] = Field(default_factory=list)
    project_path: str = ""           # disk path for SVG files

    # ---- Output ----
    pptx_url: str = ""
    pptx_path: str = ""

    # ---- Error ----
    error: str = ""

    # ---- Timestamps ----
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_progress(self) -> dict[str, Any]:
        """Lightweight progress snapshot for polling."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "progress_message": self.progress_message,
            "total_pages": self.total_pages,
            "completed_pages": self.completed_pages,
            "pages": [p.model_dump() for p in self.pages],
            "pptx_url": self.pptx_url,
            "error": self.error,
            "updated_at": self.updated_at.isoformat(),
        }
