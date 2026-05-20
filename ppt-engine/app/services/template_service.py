"""Template service — PPTX import, storage, and CRUD."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.models.template import PPTTemplate, TemplatePage, TemplateAsset

logger = logging.getLogger(__name__)

# Path to the PPT Master scripts bundled with this service
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


class TemplateService:
    """Manage the PPT template library."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._col = db.ppt_templates

    # ------------------------------------------------------------------
    # Import a PPTX file as a new template
    # ------------------------------------------------------------------

    async def import_pptx(
        self,
        pptx_path: Path,
        template_id: str,
        display_name: str,
        category: str = "general",
        created_by: str = "",
    ) -> PPTTemplate:
        """Import a .pptx file into the template library.

        1. Run ``pptx_template_import.py`` to extract manifest + SVG + assets
        2. Parse manifest.json for theme colors, fonts, asset list
        3. Store metadata in MongoDB, files on disk
        """
        output_dir = settings.templates_path / template_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Run pptx_template_import.py
        import_script = _SCRIPTS_DIR / "pptx_template_import.py"
        if not import_script.exists():
            raise FileNotFoundError(f"Import script not found: {import_script}")

        logger.info("Running pptx_template_import: %s → %s", pptx_path, output_dir)
        result = subprocess.run(
            [
                sys.executable,
                str(import_script),
                str(pptx_path),
                "-o", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"pptx_template_import failed: {result.stderr or result.stdout}"
            )
        logger.info("Import stdout: %s", result.stdout.strip())

        # Step 2: Parse manifest.json
        manifest_path = output_dir / "manifest.json"
        manifest: dict[str, Any] = {}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # Extract theme info from manifest
        theme = manifest.get("theme", {})
        primary_color = _extract_primary_color(theme)
        font_stack = _extract_fonts(theme)

        # Step 3: Discover SVG pages
        pages = _discover_pages(output_dir)
        assets = _discover_assets(output_dir)

        # Step 4: Build template record
        template = PPTTemplate(
            template_id=template_id,
            display_name=display_name,
            category=category,
            primary_color=primary_color,
            font_stack=font_stack,
            manifest=manifest,
            pages=pages,
            assets=assets,
            storage_path=str(output_dir),
            created_by=created_by,
        )

        # Step 5: Upsert to MongoDB
        await self._col.replace_one(
            {"template_id": template_id},
            template.model_dump(),
            upsert=True,
        )

        logger.info(
            "Template imported: %s (%d pages, %d assets)",
            template_id, len(pages), len(assets),
        )
        return template

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def list_templates(self) -> list[dict[str, Any]]:
        """Return summaries of all templates."""
        cursor = self._col.find({}, {"_id": 0}).sort("created_at", -1)
        templates = []
        async for doc in cursor:
            t = PPTTemplate(**doc)
            templates.append(t.to_summary())
        return templates

    async def get_template(self, template_id: str) -> PPTTemplate | None:
        """Fetch a single template by ID."""
        doc = await self._col.find_one({"template_id": template_id}, {"_id": 0})
        if doc is None:
            return None
        return PPTTemplate(**doc)

    async def delete_template(self, template_id: str) -> bool:
        """Delete a template from MongoDB and disk."""
        template = await self.get_template(template_id)
        if template is None:
            return False

        # Remove disk files
        storage = Path(template.storage_path)
        if storage.exists():
            shutil.rmtree(storage, ignore_errors=True)

        # Remove MongoDB record
        result = await self._col.delete_one({"template_id": template_id})
        return result.deleted_count > 0

    async def get_page_svg(self, template_id: str, filename: str) -> str | None:
        """Read a template page SVG from disk."""
        template = await self.get_template(template_id)
        if template is None:
            return None
        svg_path = Path(template.storage_path) / "svg-flat" / filename
        if not svg_path.exists():
            svg_path = Path(template.storage_path) / "svg" / filename
        if not svg_path.exists():
            return None
        return svg_path.read_text(encoding="utf-8")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _extract_primary_color(theme: dict) -> str:
    """Extract primary / accent color from manifest theme."""
    colors = theme.get("colors", {})
    for key in ("accent1", "dk1", "dk2"):
        if key in colors and colors[key]:
            return colors[key]
    return "#1A73E8"


def _extract_fonts(theme: dict) -> list[str]:
    """Extract font stack from manifest theme."""
    fonts = theme.get("fonts", {})
    stack = []
    for key in ("majorFont", "minorFont"):
        name = fonts.get(key, "")
        if name and name not in stack:
            stack.append(name)
    return stack or ["Arial", "Microsoft YaHei"]


def _discover_pages(output_dir: Path) -> list[TemplatePage]:
    """Find SVG page files in the import output."""
    pages: list[TemplatePage] = []

    # Prefer svg-flat/ (self-contained), fall back to svg/
    svg_dir = output_dir / "svg-flat"
    if not svg_dir.exists():
        svg_dir = output_dir / "svg"
    if not svg_dir.exists():
        return pages

    for svg_file in sorted(svg_dir.glob("*.svg")):
        page_type = _guess_page_type(svg_file.stem)
        pages.append(TemplatePage(
            filename=svg_file.name,
            page_type=page_type,
            svg_path=str(svg_file.relative_to(output_dir)),
        ))
    return pages


def _discover_assets(output_dir: Path) -> list[TemplateAsset]:
    """Find image assets in the import output."""
    assets_dir = output_dir / "assets"
    if not assets_dir.exists():
        return []
    result: list[TemplateAsset] = []
    for f in sorted(assets_dir.iterdir()):
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"):
            result.append(TemplateAsset(
                filename=f.name,
                path=str(f.relative_to(output_dir)),
            ))
    return result


def _guess_page_type(stem: str) -> str:
    """Guess page type from SVG filename stem."""
    lower = stem.lower()
    if "cover" in lower or lower.startswith("01"):
        return "cover"
    if "chapter" in lower or "divider" in lower:
        return "chapter"
    if "toc" in lower or "contents" in lower:
        return "toc"
    if "ending" in lower or "closing" in lower or "thank" in lower:
        return "ending"
    return "content"
