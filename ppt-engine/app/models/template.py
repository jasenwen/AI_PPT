"""PPT Template data model — stored in MongoDB ``ppt_templates`` collection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TemplatePage(BaseModel):
    """A single page/layout within a template."""
    filename: str              # e.g. "01_cover.svg"
    page_type: str             # cover / chapter / content / ending / toc
    svg_path: str              # relative path in template storage
    thumbnail: str = ""        # base64 or URL of thumbnail


class TemplateAsset(BaseModel):
    """A brand asset bundled with the template."""
    filename: str              # e.g. "logo.png"
    path: str                  # relative path in template storage
    usage: str = ""            # description of usage


class PPTTemplate(BaseModel):
    """Full template record persisted in MongoDB."""
    template_id: str                        # unique slug e.g. "acme_brand_2024"
    display_name: str                       # "ACME 企业模板"
    category: str = "general"               # brand / general / scenario / government
    canvas_format: str = "ppt169"           # ppt169 / ppt43 / ...
    primary_color: str = "#1A73E8"
    font_stack: list[str] = Field(default_factory=lambda: ["Arial", "Microsoft YaHei"])
    design_spec_md: str = ""                # full design_spec.md content
    manifest: dict[str, Any] = Field(default_factory=dict)  # pptx_template_import output
    pages: list[TemplatePage] = Field(default_factory=list)
    assets: list[TemplateAsset] = Field(default_factory=list)
    storage_path: str = ""                  # absolute path on disk
    created_by: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_summary(self) -> dict[str, Any]:
        """Lightweight summary for list endpoints."""
        return {
            "template_id": self.template_id,
            "display_name": self.display_name,
            "category": self.category,
            "canvas_format": self.canvas_format,
            "primary_color": self.primary_color,
            "page_count": len(self.pages),
            "created_at": self.created_at.isoformat(),
        }
