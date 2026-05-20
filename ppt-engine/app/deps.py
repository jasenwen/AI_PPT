"""Dependency injection — service singletons for the application.

All services are lazily initialised and cached. Router modules import
the ``get_*`` helpers to access shared instances.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from motor.motor_asyncio import AsyncIOMotorDatabase

if TYPE_CHECKING:
    from app.services.llm_client import LLMClient
    from app.services.markitdown_service import MarkItDownService
    from app.services.template_service import TemplateService
    from app.services.task_worker import TaskWorker

_db: AsyncIOMotorDatabase | None = None
_llm: LLMClient | None = None
_markitdown: MarkItDownService | None = None
_template_service: TemplateService | None = None
_task_worker: TaskWorker | None = None


def init_services(db: AsyncIOMotorDatabase) -> None:
    """Initialise all service singletons (called once at startup)."""
    global _db, _llm, _markitdown, _template_service, _task_worker

    from app.config import settings
    from app.services.llm_client import LLMClient
    from app.services.markitdown_service import MarkItDownService
    from app.services.template_service import TemplateService
    from app.services.svg_processor import SVGProcessor
    from app.services.pptx_exporter import PPTXExporter
    from app.services.task_worker import TaskWorker

    _db = db
    _llm = LLMClient(settings)
    _markitdown = MarkItDownService(_llm, settings)
    _template_service = TemplateService(db)
    _task_worker = TaskWorker(
        db=db,
        llm=_llm,
        svg_processor=SVGProcessor(),
        pptx_exporter=PPTXExporter(),
    )


def get_db() -> AsyncIOMotorDatabase:
    assert _db is not None, "Services not initialised"
    return _db


def get_llm() -> LLMClient:
    assert _llm is not None, "Services not initialised"
    return _llm


def get_markitdown() -> MarkItDownService:
    assert _markitdown is not None, "Services not initialised"
    return _markitdown


def get_template_service() -> TemplateService:
    assert _template_service is not None, "Services not initialised"
    return _template_service


def get_task_worker() -> TaskWorker:
    assert _task_worker is not None, "Services not initialised"
    return _task_worker
