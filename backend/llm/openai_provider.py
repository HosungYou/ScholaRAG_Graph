"""
OpenAI GPT LLM Provider

Supports GPT-4, GPT-4 Turbo, and GPT-3.5 Turbo.
"""

import logging
from typing import Optional, AsyncIterator

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI GPT LLM provider.

    Models:
    - gpt-4o-mini: Fast, cost-effective (default)
    - gpt-4o: Balanced
    - gpt-4-turbo: Most capable
    """

    MODELS = {
        "mini": "gpt-4o-mini",
        "standard": "gpt-4o",
        "turbo": "gpt-4-turbo",
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return self.MODELS["mini"]

    @property
    def client(self):
        """Lazy load the OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        return self._client

    def get_model(self, use_accurate: bool = False) -> str:
        """Get model based on accuracy requirement."""
        return self.MODELS["standard"] if use_accurate else self.MODELS["mini"]

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: Optional[str] = None,
        use_accurate: bool = False,
    ) -> str:
        """Generate response using OpenAI API."""
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
            logger.error(f"OpenAI API error ({error_type}): {self._sanitize_error(str(e))}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Generate streaming response using OpenAI API."""
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
            logger.error(f"OpenAI streaming error ({error_type}): {self._sanitize_error(str(e))}")
            raise

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.1,
    ) -> dict:
        """Generate JSON response using OpenAI's JSON mode."""
        import json

        model_to_use = self.default_model

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
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"OpenAI JSON generation error ({error_type}): {self._sanitize_error(str(e))}")
            return {}

    @staticmethod
    def _sanitize_error(error: str) -> str:
        """Remove sensitive info from error messages."""
        import re
        sanitized = re.sub(r"(sk-|api[_-]?key)[a-zA-Z0-9\-_]{10,}", "[redacted]", error, flags=re.IGNORECASE)
        return sanitized[:200] if len(sanitized) > 200 else sanitized
