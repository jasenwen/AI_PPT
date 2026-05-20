"""SVG post-processing service — wraps finalize_svg.py."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


class SVGProcessor:
    """Post-process SVG files before PPTX export.

    Pipeline (from finalize_svg.py):
    1. Icon embedding (expand <use data-icon="..."/>)
    2. Image crop processing
    3. Text flattening (positional tspan → independent text)
    4. Rounded-rect to path conversion
    """

    async def finalize(self, project_path: str | Path) -> None:
        """Run finalize_svg.py on the project's svg_output directory."""
        project = Path(project_path)
        svg_output = project / "svg_output"
        svg_final = project / "svg_final"

        if not svg_output.exists():
            raise FileNotFoundError(f"svg_output not found: {svg_output}")

        svg_final.mkdir(parents=True, exist_ok=True)

        script = _SCRIPTS_DIR / "finalize_svg.py"
        if not script.exists():
            raise FileNotFoundError(f"finalize_svg.py not found: {script}")

        logger.info("Running finalize_svg: %s → %s", svg_output, svg_final)

        result = subprocess.run(
            [
                sys.executable,
                str(script),
                str(project),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"finalize_svg failed: {result.stderr}")

        logger.info("finalize_svg completed: %s", result.stdout.strip())
