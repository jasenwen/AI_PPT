"""PPTX export service — wraps svg_to_pptx conversion."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


class PPTXExporter:
    """Convert finalized SVGs to a native editable PPTX file."""

    async def export(
        self,
        project_path: str | Path,
        *,
        canvas_format: str = "ppt169",
        transition: str = "fade",
        use_native_shapes: bool = True,
    ) -> str:
        """Run svg_to_pptx to produce the final .pptx file.

        Returns the absolute path to the generated PPTX file.
        """
        project = Path(project_path)
        svg_final = project / "svg_final"
        if not svg_final.exists():
            svg_final = project / "svg_output"
        if not svg_final.exists():
            raise FileNotFoundError(f"No SVG directory found in: {project}")

        output_pptx = project / "output.pptx"

        script = _SCRIPTS_DIR / "svg_to_pptx.py"
        if not script.exists():
            raise FileNotFoundError(f"svg_to_pptx.py not found: {script}")

        cmd = [
            sys.executable,
            str(script),
            str(project),
            "-o", str(output_pptx),
        ]
        if use_native_shapes:
            cmd.extend(["--only", "native"])

        logger.info("Running svg_to_pptx: %s → %s", project, output_pptx)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            raise RuntimeError(f"svg_to_pptx failed: {result.stderr}")

        logger.info("PPTX export completed: %s", output_pptx)
        return str(output_pptx)
