"""
Google Gemini LLM Provider

Supports Gemini 1.5 Pro and Gemini 1.5 Flash.
"""

import logging
from typing import Optional, AsyncIterator

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini LLM provider.

    Models:
    - gemini-1.5-flash: Fast, cost-effective (default)
    - gemini-1.5-pro: Most capable
    """

    MODELS = {
        "flash": "gemini-1.5-flash",
        "pro": "gemini-1.5-pro",
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._model = None

    @property
    def name(self) -> str:
        return "google"

    @property
    def default_model(self) -> str:
        return self.MODELS["flash"]

    def _get_model(self, model_name: str):
        """Get Gemini model instance."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            return genai.GenerativeModel(model_name)
        except ImportError:
            raise ImportError(
                "google-generativeai package required: pip install google-generativeai"
            )

    def get_model(self, use_accurate: bool = False) -> str:
        """Get model based on accuracy requirement."""
        return self.MODELS["pro"] if use_accurate else self.MODELS["flash"]

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: Optional[str] = None,
        use_accurate: bool = False,
    ) -> str:
        """Generate response using Gemini API."""
        model_name = model or self.get_model(use_accurate)

        try:
            genai_model = self._get_model(model_name)

            # Combine system prompt with user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }

            response = await genai_model.generate_content_async(
                full_prompt,
                generation_config=generation_config,
            )

            return response.text

        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Gemini API error ({error_type}): {self._sanitize_error(str(e))}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Generate streaming response using Gemini API."""
        model_name = model or self.default_model

        try:
            genai_model = self._get_model(model_name)

            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }

            response = await genai_model.generate_content_async(
                full_prompt,
                generation_config=generation_config,
                stream=True,
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Gemini streaming error ({error_type}): {self._sanitize_error(str(e))}")
            raise

    @staticmethod
    def _sanitize_error(error: str) -> str:
        """Remove sensitive info from error messages."""
        import re
        sanitized = re.sub(r"(AIza|api[_-]?key)[a-zA-Z0-9\-_]{10,}", "[redacted]", error, flags=re.IGNORECASE)
        return sanitized[:200] if len(sanitized) > 200 else sanitized
