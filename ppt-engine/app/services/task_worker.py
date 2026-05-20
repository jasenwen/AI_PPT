"""Task Worker — deterministic PPT generation pipeline.

After the user confirms an outline and selects a template, the Task Worker
takes over and executes a fixed pipeline with no conversational randomness:

  1. For each page: build prompt from spec_lock + template → LLM(temp=0) → SVG
  2. finalize_svg.py post-processing
  3. svg_to_pptx.py export

The worker runs as a background asyncio task and updates MongoDB as it
progresses, enabling real-time progress polling from the frontend.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.models.task import PPTTask, TaskStatus, PageResult
from app.services.llm_client import LLMClient
from app.services.svg_processor import SVGProcessor
from app.services.pptx_exporter import PPTXExporter

logger = logging.getLogger(__name__)

# Pre-defined system prompt for SVG page generation
_SVG_SYSTEM_PROMPT = """You are an expert SVG designer for presentations.
You generate a single SVG page for a PowerPoint slide.
Output ONLY the SVG code — no explanation, no markdown fences.
The SVG must use viewBox="0 0 1280 720" (16:9) or "0 0 1280 960" (4:3).

Critical rules:
- All styles must be inline (no <style> blocks, no class attributes)
- No <foreignObject>, no CSS animations, no JavaScript
- Text must use <text> elements with explicit x/y coordinates
- Use only web-safe fonts or the fonts specified in the design spec
- All colors must be explicit hex values
- Group related elements with <g id="..."> for animation targeting
"""


class TaskWorker:
    """Execute PPT generation tasks deterministically."""

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        llm: LLMClient,
        svg_processor: SVGProcessor,
        pptx_exporter: PPTXExporter,
    ) -> None:
        self._db = db
        self._col = db.ppt_tasks
        self._llm = llm
        self._svg_processor = svg_processor
        self._pptx_exporter = pptx_exporter

    # Retry / timeout configuration
    MAX_PAGE_RETRIES = 3
    RETRY_BACKOFF_BASE = 2  # seconds
    TASK_TIMEOUT = 1800  # 30 minutes total

    async def execute(self, task_id: str) -> None:
        """Run the full generation pipeline for a confirmed task.

        Features:
        - Per-page retry (up to MAX_PAGE_RETRIES with exponential backoff)
        - Overall task timeout (TASK_TIMEOUT seconds)
        - Individual page error tracking for partial progress
        """
        try:
            task = await self._load_task(task_id)
            if task is None:
                logger.error("Task not found: %s", task_id)
                return

            # Prepare project directory
            project_dir = self._prepare_project(task)

            # Phase 1: Generate SVGs page-by-page
            await self._update(task_id, status=TaskStatus.GENERATING, message="正在生成幻灯片…")

            start_time = asyncio.get_event_loop().time()

            for i in range(task.total_pages):
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self.TASK_TIMEOUT:
                    raise TimeoutError(
                        f"任务超时（已用 {elapsed:.0f}s，限制 {self.TASK_TIMEOUT}s）"
                    )

                page = task.pages[i]
                await self._update_page(task_id, i, status="generating")

                # Retry loop for each page
                svg_content = None
                last_error = None
                for attempt in range(1, self.MAX_PAGE_RETRIES + 1):
                    try:
                        prompt = self._build_page_prompt(task, i)
                        svg_content = await self._llm.generate_svg(
                            prompt, system=_SVG_SYSTEM_PROMPT
                        )
                        svg_content = _extract_svg(svg_content)
                        break  # Success — exit retry loop
                    except Exception as page_err:
                        last_error = page_err
                        if attempt < self.MAX_PAGE_RETRIES:
                            wait = self.RETRY_BACKOFF_BASE ** attempt
                            logger.warning(
                                "Page %d/%d attempt %d failed, retrying in %ds: %s",
                                i + 1, task.total_pages, attempt, wait, page_err,
                            )
                            await self._update_page(
                                task_id, i,
                                error=f"重试 {attempt}/{self.MAX_PAGE_RETRIES}: {page_err}",
                            )
                            await asyncio.sleep(wait)
                        else:
                            logger.error(
                                "Page %d/%d failed after %d attempts: %s",
                                i + 1, task.total_pages, self.MAX_PAGE_RETRIES, page_err,
                            )

                if svg_content is None:
                    # All retries exhausted — mark page as failed, continue to next
                    await self._update_page(
                        task_id, i,
                        status="failed",
                        error=f"生成失败（{self.MAX_PAGE_RETRIES}次重试）: {last_error}",
                    )
                    await self._update(
                        task_id,
                        message=f"第 {i+1} 页生成失败，继续后续页面…",
                    )
                    continue

                # Save SVG to disk
                svg_path = project_dir / "svg_output" / f"p{i+1:02d}.svg"
                svg_path.parent.mkdir(parents=True, exist_ok=True)
                svg_path.write_text(svg_content, encoding="utf-8")

                await self._update_page(
                    task_id, i,
                    status="done",
                    svg_path=str(svg_path.relative_to(project_dir)),
                    error="",
                )
                await self._update(
                    task_id,
                    completed_pages=i + 1,
                    message=f"已完成 {i+1}/{task.total_pages} 页",
                )

            # Check if any pages succeeded
            task = await self._load_task(task_id)
            done_count = sum(1 for p in task.pages if p.status == "done")
            if done_count == 0:
                raise RuntimeError("所有页面生成均失败")

            # Phase 2: SVG post-processing
            await self._update(task_id, status=TaskStatus.FINALIZING, message="正在优化幻灯片…")
            await self._svg_processor.finalize(project_dir)

            # Phase 3: PPTX export
            await self._update(task_id, status=TaskStatus.EXPORTING, message="正在导出 PPTX…")
            pptx_path = await self._pptx_exporter.export(project_dir)

            # Mark complete
            await self._update(
                task_id,
                status=TaskStatus.COMPLETED,
                pptx_path=pptx_path,
                pptx_url=f"/api/ppt/tasks/{task_id}/download",
                message=f"PPT 生成完成！（{done_count}/{task.total_pages} 页成功）",
            )
            logger.info("Task completed: %s → %s (%d/%d pages)", task_id, pptx_path, done_count, task.total_pages)

        except Exception as exc:
            logger.exception("Task failed: %s", task_id)
            await self._update(
                task_id,
                status=TaskStatus.FAILED,
                error=str(exc),
                message=f"生成失败: {exc}",
            )

    # ------------------------------------------------------------------
    # Prompt construction (deterministic — template + spec_lock data)
    # ------------------------------------------------------------------

    def _build_page_prompt(self, task: PPTTask, page_index: int) -> str:
        """Build a deterministic prompt for a single page."""
        page = task.pages[page_index]
        outline_page = {}
        if task.outline and "pages" in task.outline:
            pages_list = task.outline["pages"]
            if page_index < len(pages_list):
                outline_page = pages_list[page_index]

        title = outline_page.get("title", page.title or f"Page {page_index + 1}")
        content_points = outline_page.get("points", [])
        page_type = outline_page.get("type", page.page_type)

        prompt_parts = [
            f"## 任务：生成第 {page_index + 1}/{task.total_pages} 页 SVG",
            f"### 页面类型：{page_type}",
            f"### 页面标题：{title}",
        ]

        if content_points:
            prompt_parts.append("### 内容要点：")
            for j, point in enumerate(content_points, 1):
                prompt_parts.append(f"  {j}. {point}")

        if task.design_spec:
            prompt_parts.append(f"\n### 设计规范（必须严格遵守）：\n{task.design_spec}")

        if task.spec_lock:
            prompt_parts.append(f"\n### 锁定规范：\n{task.spec_lock}")

        return "\n".join(prompt_parts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _prepare_project(self, task: PPTTask) -> Path:
        """Create the project directory structure."""
        project_dir = settings.projects_path / task.task_id
        (project_dir / "svg_output").mkdir(parents=True, exist_ok=True)
        (project_dir / "svg_final").mkdir(parents=True, exist_ok=True)
        return project_dir

    async def _load_task(self, task_id: str) -> PPTTask | None:
        doc = await self._col.find_one({"task_id": task_id}, {"_id": 0})
        return PPTTask(**doc) if doc else None

    async def _update(self, task_id: str, **fields: Any) -> None:
        update: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        if "status" in fields:
            update["status"] = fields.pop("status").value if isinstance(fields["status"], TaskStatus) else fields.pop("status")
        if "message" in fields:
            update["progress_message"] = fields.pop("message")
        update.update(fields)
        await self._col.update_one({"task_id": task_id}, {"$set": update})

    async def _update_page(self, task_id: str, idx: int, **fields: Any) -> None:
        set_ops = {f"pages.{idx}.{k}": v for k, v in fields.items()}
        set_ops["updated_at"] = datetime.now(timezone.utc)
        await self._col.update_one({"task_id": task_id}, {"$set": set_ops})


def _extract_svg(content: str) -> str:
    """Extract SVG from LLM output (strip markdown fences if present)."""
    # Remove ```svg ... ``` or ```xml ... ```
    match = re.search(r"```(?:svg|xml)?\s*\n(.*?)```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    # If it starts with <svg, return as-is
    if "<svg" in content:
        start = content.index("<svg")
        end = content.rfind("</svg>")
        if end > start:
            return content[start:end + 6]
    return content.strip()
