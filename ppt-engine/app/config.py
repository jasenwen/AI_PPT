"""PPT Engine configuration — loaded from .env file.

Uses pydantic-settings for type-safe environment variable parsing.
All LiteLLM / MongoDB / path settings are centralized here.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings populated from environment variables / .env."""

    # ------------------------------------------------------------------
    # LiteLLM
    # ------------------------------------------------------------------
    litellm_api_base: str = "https://api.openai.com/v1"
    litellm_api_key: str = ""
    litellm_model: str = "claude-sonnet-4-20250514"

    # SVG generation — separate model / temperature override (optional)
    litellm_svg_model: str = ""
    litellm_svg_temperature: float = 0.0

    # MarkItDown OCR — separate model override (optional)
    litellm_ocr_model: str = ""

    # ------------------------------------------------------------------
    # MongoDB (reuse the LibreChat instance)
    # ------------------------------------------------------------------
    mongo_uri: str = "mongodb://localhost:27017/LibreChat"

    # ------------------------------------------------------------------
    # PPT Engine paths & server
    # ------------------------------------------------------------------
    ppt_engine_host: str = "0.0.0.0"
    ppt_engine_port: int = 8100
    ppt_projects_dir: str = "./data/projects"
    ppt_templates_dir: str = "./data/templates"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    @property
    def svg_model(self) -> str:
        """Model used for SVG page generation."""
        return self.litellm_svg_model or self.litellm_model

    @property
    def ocr_model(self) -> str:
        """Model used by MarkItDown for image OCR."""
        return self.litellm_ocr_model or self.litellm_model

    @property
    def projects_path(self) -> Path:
        p = Path(self.ppt_projects_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def templates_path(self) -> Path:
        p = Path(self.ppt_templates_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


# Singleton — imported everywhere as ``from app.config import settings``
settings = Settings()
