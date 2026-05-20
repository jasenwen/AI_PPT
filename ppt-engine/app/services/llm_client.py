"""LiteLLM client wrapper — unified LLM gateway for PPT Engine.

Provides two modes:
- ``generate_svg()``:  SVG page generation with temperature=0 for determinism
- ``get_openai_client()``:  OpenAI-compatible client for MarkItDown OCR
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import litellm
from openai import OpenAI

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around LiteLLM for the PPT generation pipeline."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        litellm.suppress_debug_info = True

    def _ensure_prefix(self, model: str) -> str:
        """Ensure model name uses 'openai/' prefix for LiteLLM routing.

        Since we use a custom OpenAI-compatible API base (e.g. DashScope),
        ALL models must be routed through the 'openai/' provider codepath.
        Any existing non-openai prefix (e.g. 'qwen/') is stripped and
        replaced with 'openai/'.
        """
        if model.startswith('openai/'):
            return model
        # Strip any non-openai provider prefix (e.g. 'qwen/qwen3-flash' → 'qwen3-flash')
        if '/' in model:
            model = model.split('/', 1)[1]
        return f'openai/{model}'

    async def generate_svg(self, prompt: str, *, system: str = "") -> str:
        """Generate an SVG page with temperature=0 for determinism."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        model = self._ensure_prefix(self._settings.svg_model)
        logger.info(
            "LLM SVG call — model=%s temp=%s prompt_len=%d",
            model,
            self._settings.litellm_svg_temperature,
            len(prompt),
        )

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=self._settings.litellm_svg_temperature,
            max_tokens=16000,
            api_base=self._settings.litellm_api_base,
            api_key=self._settings.litellm_api_key,
        )

        content = response.choices[0].message.content or ""
        logger.info("LLM SVG response — length=%d", len(content))
        return content

    async def generate_outline(self, prompt: str, *, system: str = "") -> str:
        """Generate outline with slightly higher temperature (0.3)."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        model = self._ensure_prefix(self._settings.litellm_model)
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=8000,
            api_base=self._settings.litellm_api_base,
            api_key=self._settings.litellm_api_key,
        )
        return response.choices[0].message.content or ""

    def get_openai_client(self) -> OpenAI | None:
        """Return OpenAI-compatible client for MarkItDown OCR.

        Returns None if no API key is configured — MarkItDown will
        still work for most file types but skip OCR for images.
        """
        if not self._settings.litellm_api_key:
            logger.warning("No LiteLLM API key configured — OCR disabled")
            return None
        return OpenAI(
            base_url=self._settings.litellm_api_base,
            api_key=self._settings.litellm_api_key,
        )
