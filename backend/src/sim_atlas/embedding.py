"""Text embeddings for semantic search.

Standalone: everything is passed in via `EmbeddingConfig`; this module never
reads settings or touches a config file. Each provider's package is an optional
extra (`sim-atlas[fastembed]`, `[openai]`, `[voyageai]`) imported lazily on
first use.
"""

import os
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from importlib.util import find_spec
from typing import Literal

import numpy as np
from tqdm import tqdm

from sim_atlas.exceptions import AINotConfiguredError

type Provider = Literal["fastembed", "openai", "voyageai"]
type Embedder = Callable[[list[str], str], Awaitable[np.ndarray]]

_DEFAULT_FASTEMBED_MODEL = "nomic-ai/nomic-embed-text-v1.5"


def provider_installed(provider: Provider) -> bool:
    """Whether the optional package for *provider* is importable."""
    return find_spec(provider) is not None


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: Provider
    model: str | None = None  # fastembed falls back to nomic-embed-text-v1.5
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = None  # openai-compatible endpoints only
    batch_size: int = 8

    @property
    def problem(self) -> str | None:
        """Why this config cannot embed, or None if it can."""
        if not provider_installed(self.provider):
            return str(_missing_extra(self.provider))
        if self.provider in ("openai", "voyageai"):
            if not self.api_key:
                return f"embedding_api_key is required for the {self.provider} provider"
            if not self.model:
                return f"embedding_model is required for the {self.provider} provider"
        return None

    @property
    def ready(self) -> bool:
        return self.problem is None


async def create_embedding(
    config: EmbeddingConfig, documents: list[str], input_type: str = "document"
) -> np.ndarray:
    """Embed *documents*; returns a float32 array of shape (len(documents), dim)."""
    return await _embedder(config)(documents, input_type)


# The model/client is built once and reused. Constructing them per call is very
# expensive: a TextEmbedding rebuilds the ONNX session and tokenizer (seconds),
# and a fresh HTTP client discards the connection pool, so every request pays a
# new TCP+TLS handshake to the provider.
@lru_cache(maxsize=1)
def _embedder(config: EmbeddingConfig) -> Embedder:
    if (problem := config.problem) is not None:
        raise AINotConfiguredError(problem)
    match config.provider:
        case "fastembed":
            return _fastembed_embedder(config)
        case "openai":
            return _openai_embedder(config)
        case "voyageai":
            return _voyageai_embedder(config)


def _missing_extra(provider: Provider) -> AINotConfiguredError:
    return AINotConfiguredError(
        f"embedding provider '{provider}' requires: pip install 'sim-atlas[{provider}]'"
    )


def _batches(documents: list[str], size: int) -> Iterator[list[str]]:
    for i in tqdm(range(0, len(documents), size), desc="Creating embeddings"):
        yield documents[i : i + size]


def _fastembed_embedder(config: EmbeddingConfig) -> Embedder:
    try:
        from fastembed import TextEmbedding  # noqa: PLC0415
        from huggingface_hub.constants import HF_HUB_CACHE  # noqa: PLC0415
    except ImportError as e:
        raise _missing_extra("fastembed") from e

    # fastembed defaults to <tmp>/fastembed_cache, which is wiped on reboot or
    # container rebuild and forces a re-download. Use the standard Hugging Face
    # hub cache (honours HF_HOME / HF_HUB_CACHE) so models persist and are shared
    # with other HF-based tools. FASTEMBED_CACHE_PATH still takes precedence.
    cache_dir = os.getenv("FASTEMBED_CACHE_PATH") or HF_HUB_CACHE
    model = TextEmbedding(
        model_name=config.model or _DEFAULT_FASTEMBED_MODEL, cache_dir=cache_dir
    )

    async def embed(documents: list[str], input_type: str) -> np.ndarray:
        embeddings: list[np.ndarray] = []
        for batch in _batches(documents, config.batch_size):
            embeddings += model.embed(batch, batch_size=config.batch_size)
        return np.array(embeddings, dtype=np.float32)

    return embed


def _openai_embedder(config: EmbeddingConfig) -> Embedder:
    try:
        from openai import AsyncOpenAI  # noqa: PLC0415
    except ImportError as e:
        raise _missing_extra("openai") from e

    model = config.model
    if model is None:  # unreachable after EmbeddingConfig.problem; narrows the type
        raise AINotConfiguredError(
            "embedding_model is required for the openai provider"
        )
    client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)

    async def embed(documents: list[str], input_type: str) -> np.ndarray:
        embeddings: list[list[float]] = []
        for batch in _batches(documents, config.batch_size):
            response = await client.embeddings.create(input=batch, model=model)
            embeddings += [e.embedding for e in response.data]
        return np.array(embeddings, dtype=np.float32)

    return embed


def _voyageai_embedder(config: EmbeddingConfig) -> Embedder:
    try:
        import voyageai  # noqa: PLC0415  # pyright: ignore[reportMissingTypeStubs]
    except ImportError as e:
        raise _missing_extra("voyageai") from e

    client = voyageai.AsyncClient(api_key=config.api_key)  # pyright: ignore[reportPrivateImportUsage]

    async def embed(documents: list[str], input_type: str) -> np.ndarray:
        embeddings: list[list[float]] = []
        for batch in _batches(documents, config.batch_size):
            result = await client.embed(
                batch, model=config.model, input_type=input_type
            )
            embeddings += result.embeddings  # pyright: ignore[reportAssignmentType]
        return np.array(embeddings, dtype=np.float32)

    return embed
