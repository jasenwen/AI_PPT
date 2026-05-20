"""Pure unit tests — no server, no network, no Docker required.

Run:  uv run --with pytest pytest tests/test_unit.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.task import PPTTask, TaskStatus, PageResult
from app.services.task_worker import _extract_svg


# ── _extract_svg helper ──────────────────────────────────────────────

class TestExtractSvg:
    """Test SVG extraction from various LLM output formats."""

    def test_raw_svg(self):
        raw = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect/></svg>'
        assert _extract_svg(raw) == raw

    def test_markdown_fence_svg(self):
        md = '```svg\n<svg viewBox="0 0 1280 720"><rect/></svg>\n```'
        result = _extract_svg(md)
        assert result.startswith("<svg")
        assert result.endswith("</svg>")

    def test_markdown_fence_xml(self):
        md = '```xml\n<svg viewBox="0 0 1280 720"><rect/></svg>\n```'
        result = _extract_svg(md)
        assert "<svg" in result

    def test_svg_with_preamble(self):
        text = 'Here is the SVG:\n<svg viewBox="0 0 1280 720"><rect/></svg>\nDone.'
        result = _extract_svg(text)
        assert result.startswith("<svg")
        assert result.endswith("</svg>")

    def test_plain_text_passthrough(self):
        text = "Sorry, I cannot generate SVG."
        result = _extract_svg(text)
        assert result == text


# ── PPTTask model ────────────────────────────────────────────────────

class TestPPTTaskModel:
    def test_defaults(self):
        task = PPTTask(task_id="t1", user_id="u1")
        assert task.status == TaskStatus.PENDING
        assert task.total_pages == 0
        assert task.pages == []

    def test_to_progress(self):
        pages = [
            PageResult(page_num=1, page_type="cover", title="Cover", status="done"),
            PageResult(page_num=2, page_type="content", title="Body", status="pending"),
        ]
        task = PPTTask(task_id="t2", user_id="u1", total_pages=2, pages=pages,
                       status=TaskStatus.GENERATING, progress_message="1/2")
        prog = task.to_progress()
        assert prog["task_id"] == "t2"
        assert prog["status"] == "generating"
        assert prog["total_pages"] == 2
        assert len(prog["pages"]) == 2
        assert prog["pages"][0]["status"] == "done"


# ── PageResult model ────────────────────────────────────────────────

class TestPageResult:
    def test_defaults(self):
        p = PageResult(page_num=1)
        assert p.page_type == "content"
        assert p.status == "pending"
        assert p.svg_path == ""
        assert p.error == ""


# ── LLMClient._ensure_prefix ────────────────────────────────────────

class TestEnsurePrefix:
    def setup_method(self):
        from app.services.llm_client import LLMClient
        from unittest.mock import MagicMock
        self.client = LLMClient.__new__(LLMClient)
        self.client._settings = MagicMock()

    def test_already_openai(self):
        assert self.client._ensure_prefix("openai/gpt-4o") == "openai/gpt-4o"

    def test_bare_model(self):
        assert self.client._ensure_prefix("gpt-4o") == "openai/gpt-4o"

    def test_other_prefix_stripped(self):
        assert self.client._ensure_prefix("qwen/qwen-turbo") == "openai/qwen-turbo"


# ── TaskWorker._build_page_prompt ────────────────────────────────────

class TestBuildPagePrompt:
    def _make_worker(self):
        from app.services.task_worker import TaskWorker
        from unittest.mock import MagicMock
        return TaskWorker(db=MagicMock(), llm=MagicMock(),
                          svg_processor=MagicMock(), pptx_exporter=MagicMock())

    def test_cover_page(self):
        worker = self._make_worker()
        task = PPTTask(
            task_id="t1", user_id="u1", total_pages=2,
            outline={"pages": [
                {"type": "cover", "title": "Hello", "points": ["2024"]},
                {"type": "content", "title": "Body", "points": ["A", "B"]},
            ]},
            pages=[
                PageResult(page_num=1, page_type="cover", title="Hello"),
                PageResult(page_num=2, page_type="content", title="Body"),
            ],
        )
        prompt = worker._build_page_prompt(task, 0)
        assert "cover" in prompt
        assert "Hello" in prompt
        assert "1/2" in prompt

    def test_with_design_spec(self):
        worker = self._make_worker()
        task = PPTTask(
            task_id="t1", user_id="u1", total_pages=1,
            design_spec="Use blue theme",
            pages=[PageResult(page_num=1)],
            outline={"pages": [{"type": "content", "title": "X", "points": []}]},
        )
        prompt = worker._build_page_prompt(task, 0)
        assert "Use blue theme" in prompt


# ── Config defaults ──────────────────────────────────────────────────

class TestConfig:
    def test_default_port(self):
        from app.config import Settings
        s = Settings(litellm_api_key="test", _env_file=None)
        assert s.ppt_engine_port == 8100

    def test_svg_model_fallback(self):
        from app.config import Settings
        s = Settings(litellm_api_key="test", litellm_model="m1", litellm_svg_model="",
                     _env_file=None)
        assert s.svg_model == "m1"

    def test_svg_model_override(self):
        from app.config import Settings
        s = Settings(litellm_api_key="test", litellm_model="m1",
                     litellm_svg_model="m2", _env_file=None)
        assert s.svg_model == "m2"
