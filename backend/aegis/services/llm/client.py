"""LLM client supporting Ollama and OpenAI-compatible endpoints."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from aegis.config import settings

logger = logging.getLogger(__name__)


class LLMConnectionError(Exception):
    pass


def _make_openai_client() -> AsyncOpenAI:
    """Build an AsyncOpenAI client from config, preferring OPENAI_API_BASE over Ollama."""
    if settings.OPENAI_API_BASE:
        return AsyncOpenAI(
            base_url=settings.OPENAI_API_BASE,
            api_key=settings.OPENAI_API_KEY,
        )
    return AsyncOpenAI(
        base_url=f"{settings.OLLAMA_BASE_URL}/v1",
        api_key="ollama",
    )


def _active_model() -> str:
    """Return the model to use for chat completions."""
    if settings.OPENAI_API_BASE and settings.OPENAI_MODEL:
        return settings.OPENAI_MODEL
    return settings.OLLAMA_MODEL


class AegisLLMClient:
    def __init__(self, model: str | None = None):
        self.model = model or _active_model()
        self._client = _make_openai_client()

    async def generate(self, prompt: str, temperature: float = 0.1, max_tokens: int = 4096) -> str:
        """Generate a completion (non-streaming)."""
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMConnectionError(f"LLM generation failed: {exc}") from exc

    async def stream_generate(self, prompt: str, temperature: float = 0.1) -> AsyncIterator[str]:
        """Generate a streaming completion, yielding tokens."""
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=4096,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            raise LLMConnectionError(f"LLM stream failed: {exc}") from exc

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector using the configured embedding provider."""
        provider = settings.EMBEDDING_PROVIDER.lower()

        if provider == "openai":
            # Use the OpenAI-compatible embeddings endpoint
            try:
                resp = await self._client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=text,
                )
                return resp.data[0].embedding
            except Exception as exc:
                raise LLMConnectionError(f"OpenAI embedding failed: {exc}") from exc

        if provider == "huggingface":
            # Use sentence-transformers for local HuggingFace embeddings
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore[import]
            except ImportError as exc:
                raise LLMConnectionError(
                    "sentence-transformers is required for EMBEDDING_PROVIDER=huggingface. "
                    "Run: pip install sentence-transformers"
                ) from exc
            import asyncio
            model = SentenceTransformer(settings.HUGGINGFACE_EMBEDDING_MODEL)
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, lambda: model.encode(text).tolist())
            return embedding

        # Default: Ollama embeddings HTTP API
        import httpx
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text},
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()["embedding"]
