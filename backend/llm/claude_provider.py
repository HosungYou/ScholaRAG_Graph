"""
Anthropic Claude LLM Provider

Supports Claude 3.5 Haiku, Claude 3.5 Sonnet, and Claude 3 Opus.
"""

import logging
from typing import Optional, AsyncIterator

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseLLMProvider):
    """
    Anthropic Claude LLM provider.

    Models:
    - claude-3-5-haiku-20241022: Fast, cost-effective (default)
    - claude-3-5-sonnet-20241022: Balanced
    - claude-3-opus-20240229: Most capable
    """

    # Model configurations
    MODELS = {
        "haiku": "claude-3-5-haiku-20241022",
        "sonnet": "claude-3-5-sonnet-20241022",
        "opus": "claude-3-opus-20240229",
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return self.MODELS["haiku"]

    @property
    def client(self):
        """Lazy load the Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package required: pip install anthropic")
        return self._client

    def get_model(self, use_accurate: bool = False) -> str:
        """Get model based on accuracy requirement."""
        return self.MODELS["sonnet"] if use_accurate else self.MODELS["haiku"]

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: Optional[str] = None,
        use_accurate: bool = False,
    ) -> str:
        """Generate response using Claude API."""
        model_to_use = model or self.get_model(use_accurate)

        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": model_to_use,
                "max_tokens": max_tokens,
                "messages": messages,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if temperature != 0.7:
                kwargs["temperature"] = temperature

            response = await self.client.messages.create(**kwargs)

            return response.content[0].text

        except Exception as e:
            # Don't log full error which might contain API key info
            error_type = type(e).__name__
            logger.error(f"Claude API error ({error_type}): {self._sanitize_error(str(e))}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Generate streaming response using Claude API."""
        model_to_use = model or self.default_model

        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": model_to_use,
                "max_tokens": max_tokens,
                "messages": messages,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if temperature != 0.7:
                kwargs["temperature"] = temperature

            async with self.client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Claude streaming error ({error_type}): {self._sanitize_error(str(e))}")
            raise

    @staticmethod
    def _sanitize_error(error: str) -> str:
        """Remove sensitive info from error messages."""
        import re
        # Remove potential API keys
        sanitized = re.sub(r"(sk-ant-|api[_-]?key)[a-zA-Z0-9\-_]{10,}", "[redacted]", error, flags=re.IGNORECASE)
        # Truncate long errors
        return sanitized[:200] if len(sanitized) > 200 else sanitized
