"""Shared fixtures for PPT Engine tests."""

import sys
from pathlib import Path

import pytest

# Ensure app package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = "http://localhost:8100"


@pytest.fixture
def base_url():
    return BASE_URL


# --------------- Test SVG content ---------------

TEST_SVG_COVER = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#1a1a2e"/>
  <text x="640" y="300" text-anchor="middle" fill="#e94560"
        font-size="56" font-family="Arial">AI Enterprise</text>
  <text x="640" y="400" text-anchor="middle" fill="#ffffff"
        font-size="28" font-family="Arial">2024 Report</text>
</svg>"""

TEST_SVG_CONTENT = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#16213e"/>
  <text x="100" y="80" fill="#e94560" font-size="36" font-family="Arial">Core Tech</text>
  <g id="group1">
    <circle cx="300" cy="360" r="80" fill="#0f3460"/>
    <text x="300" y="365" text-anchor="middle" fill="white" font-size="18">LLM</text>
  </g>
  <g id="group2">
    <rect x="560" y="280" width="160" height="160" rx="12" fill="#0f3460"/>
    <text x="640" y="365" text-anchor="middle" fill="white" font-size="18">KG</text>
  </g>
</svg>"""

TEST_SVG_ENDING = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#1a1a2e"/>
  <text x="640" y="340" text-anchor="middle" fill="#e94560"
        font-size="72" font-family="Arial">Thanks</text>
  <text x="640" y="420" text-anchor="middle" fill="#ffffff"
        font-size="32" font-family="Arial">Q&amp;A</text>
</svg>"""


@pytest.fixture
def test_project(tmp_path):
    """Create a temporary project directory with test SVG files."""
    svg_output = tmp_path / "svg_output"
    svg_output.mkdir()
    (svg_output / "p01.svg").write_text(TEST_SVG_COVER, encoding="utf-8")
    (svg_output / "p02.svg").write_text(TEST_SVG_CONTENT, encoding="utf-8")
    (svg_output / "p03.svg").write_text(TEST_SVG_ENDING, encoding="utf-8")
    return tmp_path
