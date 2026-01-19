"""
Groq LLM Provider

Supports Llama 3.3, Llama 3.1, and Mixtral models.
FREE TIER: 14,400 requests/day, 300+ tokens/sec (fastest!)

Get API key: https://console.groq.com
"""

import logging
from typing import Optional, AsyncIterator

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GroqProvider(BaseLLMProvider):
    """
    Groq LLM provider - FREE and FASTEST!

    Models:
    - llama-3.3-70b-versatile: Most capable (default)
    - llama-3.1-8b-instant: Fastest
    - mixtral-8x7b-32768: Good for long context
    - gemma2-9b-it: Google's Gemma 2
    """

    MODELS = {
        "default": "llama-3.3-70b-versatile",
        "fast": "llama-3.1-8b-instant",
        "mixtral": "mixtral-8x7b-32768",
        "gemma": "gemma2-9b-it",
    }

    # Groq API base URL (OpenAI compatible)
    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def name(self) -> str:
        return "groq"

    @property
    def default_model(self) -> str:
        return self.MODELS["default"]

    @property
    def client(self):
        """Lazy load the Groq client (uses OpenAI SDK with custom base_url)."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.BASE_URL,
                )
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        return self._client

    def get_model(self, use_accurate: bool = False) -> str:
        """Get model based on accuracy requirement."""
        return self.MODELS["default"] if use_accurate else self.MODELS["fast"]

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: Optional[str] = None,
        use_accurate: bool = False,
    ) -> str:
        """Generate response using Groq API (OpenAI compatible)."""
        model_to_use = model or self.get_model(use_accurate)

        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return response.choices[0].message.content

        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Groq API error ({error_type}): {self._sanitize_error(str(e))}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Generate streaming response using Groq API."""
        model_to_use = model or self.default_model

        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            stream = await self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Groq streaming error ({error_type}): {self._sanitize_error(str(e))}")
            raise

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.1,
    ) -> dict:
        """Generate JSON response using Groq's JSON mode."""
        import json

        model_to_use = self.default_model

        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add explicit JSON instruction for models that don't support json_object mode
            json_prompt = prompt + "\n\nRespond with valid JSON only."
            messages.append({"role": "user", "content": json_prompt})

            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Groq JSON generation error ({error_type}): {self._sanitize_error(str(e))}")
            return {}

    @staticmethod
    def _sanitize_error(error: str) -> str:
        """Remove sensitive info from error messages."""
        import re
        sanitized = re.sub(r"(gsk_|api[_-]?key)[a-zA-Z0-9\-_]{10,}", "[redacted]", error, flags=re.IGNORECASE)
        return sanitized[:200] if len(sanitized) > 200 else sanitized
