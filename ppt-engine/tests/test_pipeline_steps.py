"""Step-by-step integration tests — run each step independently.

Prerequisites:
  - MongoDB running on localhost:27017
  - PPT Engine running on localhost:8100

Run ALL steps:
  uv run --with pytest pytest tests/test_pipeline_steps.py -v

Run a SINGLE step (avoids timeout):
  uv run --with pytest pytest tests/test_pipeline_steps.py -v -k step1
  uv run --with pytest pytest tests/test_pipeline_steps.py -v -k step2
  uv run --with pytest pytest tests/test_pipeline_steps.py -v -k step3
  uv run --with pytest pytest tests/test_pipeline_steps.py -v -k step4
  uv run --with pytest pytest tests/test_pipeline_steps.py -v -k step5
  uv run --with pytest pytest tests/test_pipeline_steps.py -v -k step6
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://localhost:8100"
# Shared file to pass task_id between steps (optional)
_STATE_FILE = Path(__file__).parent / ".test_state.json"


def _save_state(data: dict):
    existing = _load_state()
    existing.update(data)
    _STATE_FILE.write_text(json.dumps(existing), encoding="utf-8")


def _load_state() -> dict:
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    return {}


def _server_available() -> bool:
    try:
        r = requests.get(f"{BASE}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


# Skip all tests in this file if server is not available
pytestmark = pytest.mark.skipif(
    not _server_available(),
    reason="PPT Engine not running on localhost:8100",
)


# ═══════════════════════════════════════════════════════════════════
# STEP 1 — Health & MongoDB connectivity
# ═══════════════════════════════════════════════════════════════════

class TestStep1Health:
    """step1: Verify server health and MongoDB connection."""

    def test_step1_health_endpoint(self):
        r = requests.get(f"{BASE}/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["service"] == "ppt-engine"
        print(f"  ✓ Health OK: {data}")

    def test_step1_openapi_docs(self):
        r = requests.get(f"{BASE}/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        assert "PPT Engine" in spec["info"]["title"]
        paths = list(spec["paths"].keys())
        print(f"  ✓ API paths: {paths}")


# ═══════════════════════════════════════════════════════════════════
# STEP 2 — Task CRUD (create + query, no LLM execution)
# ═══════════════════════════════════════════════════════════════════

class TestStep2TaskCRUD:
    """step2: Create and query a PPT task (worker will run in background)."""

    TASK_DATA = {
        "user_id": "unit-test",
        "conversation_id": "unit-conv",
        "source_markdown": "# Test\n\n- Point 1\n- Point 2",
        "outline": {
            "title": "Test",
            "pages": [
                {"type": "cover", "title": "Test Cover", "points": ["2024"]},
            ],
        },
        "pages": [
            {"type": "cover", "title": "Test Cover"},
        ],
    }

    def test_step2_create_task(self):
        r = requests.post(f"{BASE}/api/tasks", json=self.TASK_DATA)
        assert r.status_code == 200, f"Create failed: {r.text}"
        data = r.json()
        assert "task_id" in data
        assert data["total_pages"] == 1
        _save_state({"task_id": data["task_id"]})
        print(f"  ✓ Task created: {data['task_id']} ({data['total_pages']} pages)")

    def test_step2_poll_task(self):
        state = _load_state()
        task_id = state.get("task_id")
        if not task_id:
            pytest.skip("No task_id from previous step — run step2_create first")

        r = requests.get(f"{BASE}/api/tasks/{task_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["task_id"] == task_id
        assert "status" in data
        print(f"  ✓ Task status: {data['status']} — {data.get('progress_message', '')}")

    def test_step2_task_not_found(self):
        r = requests.get(f"{BASE}/api/tasks/nonexistent-id")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# STEP 3 — LLM SVG generation (direct call, single page)
# ═══════════════════════════════════════════════════════════════════

class TestStep3LLM:
    """step3: Test LLM SVG generation directly (bypasses task worker).

    This isolates the LLM call from the rest of the pipeline.
    Requires LITELLM_API_KEY in .env to be valid.
    """

    def test_step3_llm_generate_single_svg(self):
        import asyncio
        from app.config import Settings
        from app.services.llm_client import LLMClient

        settings = Settings()
        if not settings.litellm_api_key:
            pytest.skip("LITELLM_API_KEY not configured")

        llm = LLMClient(settings)

        prompt = (
            "## 任务：生成第 1/1 页 SVG\n"
            "### 页面类型：cover\n"
            "### 页面标题：AI技术概览\n"
            "### 内容要点：\n"
            "  1. 人工智能\n"
            "  2. 大语言模型\n"
        )
        system = (
            "You are an SVG designer. Output ONLY SVG code.\n"
            'Use viewBox="0 0 1280 720". All styles must be inline.\n'
            "No <style>, no <foreignObject>, no JavaScript."
        )

        print("  ⏳ Calling LLM (this may take 10-30s)...")
        svg = asyncio.run(llm.generate_svg(prompt, system=system))

        assert "<svg" in svg, f"No <svg> tag in response (len={len(svg)})"
        assert "</svg>" in svg, f"No </svg> tag in response"

        # Extract clean SVG
        from app.services.task_worker import _extract_svg
        clean = _extract_svg(svg)
        assert clean.startswith("<svg")
        print(f"  ✓ SVG generated: {len(clean)} chars")

        # Save for step4/step5 to reuse
        _save_state({"llm_svg": clean})


# ═══════════════════════════════════════════════════════════════════
# STEP 4 — SVG post-processing (finalize_svg.py)
# ═══════════════════════════════════════════════════════════════════

class TestStep4Finalize:
    """step4: Test SVG finalization using pre-made test SVGs.

    Does NOT require LLM — uses conftest fixtures.
    """

    def test_step4_finalize_svg(self, test_project):
        """Run finalize_svg.py on test SVG files."""
        scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
        script = scripts_dir / "finalize_svg.py"
        if not script.exists():
            pytest.skip(f"finalize_svg.py not found: {script}")

        print(f"  ⏳ Running finalize_svg on {test_project}...")
        result = subprocess.run(
            [sys.executable, str(script), str(test_project)],
            capture_output=True, text=True, timeout=60,
        )

        print(f"  stdout: {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"  stderr: {result.stderr.strip()}")
        assert result.returncode == 0, f"finalize_svg failed: {result.stderr}"

        svg_final = test_project / "svg_final"
        assert svg_final.exists(), "svg_final/ not created"
        final_files = list(svg_final.glob("*.svg"))
        assert len(final_files) == 3, f"Expected 3 SVGs, got {len(final_files)}"
        print(f"  ✓ Finalized {len(final_files)} SVG files")

    def test_step4_finalize_with_llm_svg(self, tmp_path):
        """Run finalize on LLM-generated SVG if available from step3."""
        state = _load_state()
        llm_svg = state.get("llm_svg")
        if not llm_svg:
            pytest.skip("No LLM SVG from step3 — run step3 first")

        svg_output = tmp_path / "svg_output"
        svg_output.mkdir()
        (svg_output / "p01.svg").write_text(llm_svg, encoding="utf-8")

        scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
        script = scripts_dir / "finalize_svg.py"
        result = subprocess.run(
            [sys.executable, str(script), str(tmp_path)],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"finalize failed: {result.stderr}"
        assert (tmp_path / "svg_final" / "p01.svg").exists()
        print("  ✓ LLM SVG finalized successfully")


# ═══════════════════════════════════════════════════════════════════
# STEP 5 — PPTX export (svg_to_pptx.py)
# ═══════════════════════════════════════════════════════════════════

class TestStep5Export:
    """step5: Test PPTX export from pre-made SVG files.

    Does NOT require LLM — uses conftest fixtures.
    """

    def test_step5_export_pptx_native(self, test_project):
        """Export test SVGs to PPTX (native shapes mode)."""
        scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
        script = scripts_dir / "svg_to_pptx.py"
        if not script.exists():
            pytest.skip(f"svg_to_pptx.py not found: {script}")

        output = test_project / "output.pptx"
        print(f"  ⏳ Running svg_to_pptx on {test_project}...")
        result = subprocess.run(
            [sys.executable, str(script), str(test_project),
             "-o", str(output), "--only", "native"],
            capture_output=True, text=True, timeout=120,
        )

        print(f"  stdout: {result.stdout[:500]}")
        if result.returncode != 0:
            print(f"  stderr: {result.stderr[:500]}")
        assert result.returncode == 0, f"svg_to_pptx failed: {result.stderr}"
        assert output.exists(), "output.pptx not created"
        size_kb = output.stat().st_size / 1024
        print(f"  ✓ PPTX created: {output.name} ({size_kb:.1f} KB)")

    def test_step5_export_after_finalize(self, test_project):
        """Export after finalization (finalize → export pipeline)."""
        scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
        finalize = scripts_dir / "finalize_svg.py"
        export = scripts_dir / "svg_to_pptx.py"
        if not finalize.exists() or not export.exists():
            pytest.skip("Scripts not found")

        # Step A: finalize
        r1 = subprocess.run(
            [sys.executable, str(finalize), str(test_project)],
            capture_output=True, text=True, timeout=60,
        )
        assert r1.returncode == 0, f"finalize failed: {r1.stderr}"

        # Step B: export
        output = test_project / "output.pptx"
        r2 = subprocess.run(
            [sys.executable, str(export), str(test_project),
             "-o", str(output), "--only", "native"],
            capture_output=True, text=True, timeout=120,
        )
        assert r2.returncode == 0, f"export failed: {r2.stderr}"
        assert output.exists()
        size_kb = output.stat().st_size / 1024
        print(f"  ✓ Pipeline finalize→export OK: {size_kb:.1f} KB")


# ═══════════════════════════════════════════════════════════════════
# STEP 6 — Full single-page task via API (LLM + finalize + export)
# ═══════════════════════════════════════════════════════════════════

class TestStep6FullTask:
    """step6: End-to-end single-page task via API.

    Creates a 1-page task, polls until completion or failure (max 120s).
    Requires: running server + valid LLM API key.
    """

    def test_step6_single_page_task(self):
        task_data = {
            "user_id": "e2e-step6",
            "conversation_id": "e2e-step6",
            "source_markdown": "# Quick Test\n- AI\n- LLM",
            "outline": {
                "title": "Quick Test",
                "pages": [
                    {"type": "cover", "title": "Quick Test", "points": ["AI", "LLM"]},
                ],
            },
            "pages": [{"type": "cover", "title": "Quick Test"}],
        }

        # Create task
        r = requests.post(f"{BASE}/api/tasks", json=task_data)
        assert r.status_code == 200, f"Create failed: {r.text}"
        task_id = r.json()["task_id"]
        print(f"  ✓ Task created: {task_id}")

        # Poll (max 120s)
        max_wait = 120
        elapsed = 0
        final_status = None

        while elapsed < max_wait:
            time.sleep(5)
            elapsed += 5
            sr = requests.get(f"{BASE}/api/tasks/{task_id}")
            data = sr.json()
            status = data["status"]
            msg = data.get("progress_message", "")
            print(f"    [{elapsed:3d}s] {status} — {msg}")

            if status in ("completed", "failed"):
                final_status = data
                break

        assert final_status is not None, f"Task timed out after {max_wait}s"

        if final_status["status"] == "completed":
            print(f"  ✓ Task completed! PPTX: {final_status.get('pptx_url', 'N/A')}")
            # Try download
            dl = requests.get(f"{BASE}/api/tasks/{task_id}/download")
            assert dl.status_code == 200, f"Download failed: {dl.status_code}"
            print(f"  ✓ Download OK: {len(dl.content)} bytes")
        else:
            error = final_status.get("error", "unknown")
            # Print page-level errors
            for p in final_status.get("pages", []):
                if p.get("error"):
                    print(f"    Page {p['page_num']}: {p['error']}")
            pytest.fail(f"Task failed: {error}")
