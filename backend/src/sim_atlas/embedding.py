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
from typing import Literal

import numpy as np
from tqdm import tqdm

from sim_atlas.exceptions import AINotConfiguredError

type Provider = Literal["fastembed", "openai", "voyageai"]
type Embedder = Callable[[list[str], str], Awaitable[np.ndarray]]

_DEFAULT_FASTEMBED_MODEL = "nomic-ai/nomic-embed-text-v1.5"


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: Provider
    model: str | None = None  # fastembed falls back to nomic-embed-text-v1.5
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = None  # openai-compatible endpoints only
    batch_size: int = 8


def load_embedder(config: EmbeddingConfig) -> None:
    """Import the provider and build its model/client now instead of on first use.

    Raises `AINotConfiguredError` if the config is incomplete or the provider's
    extra is missing or cannot be imported.
    """
    _embedder(config)


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
    match config.provider:
        case "fastembed":
            return _fastembed_embedder(
                config.model or _DEFAULT_FASTEMBED_MODEL, config.batch_size
            )
        case "openai":
            return _openai_embedder(
                _required(config.model, "embedding_model", config.provider),
                _required(config.api_key, "embedding_api_key", config.provider),
                config.base_url,
                config.batch_size,
            )
        case "voyageai":
            return _voyageai_embedder(
                _required(config.model, "embedding_model", config.provider),
                _required(config.api_key, "embedding_api_key", config.provider),
                config.batch_size,
            )


def _required(value: str | None, name: str, provider: Provider) -> str:
    if not value:
        raise AINotConfiguredError(f"{name} is required for the {provider} provider")
    return value


def _missing_extra(provider: Provider) -> AINotConfiguredError:
    return AINotConfiguredError(
        f"embedding provider '{provider}' requires: pip install 'sim-atlas[{provider}]'"
    )


def _batches(documents: list[str], size: int) -> Iterator[list[str]]:
    for i in tqdm(range(0, len(documents), size), desc="Creating embeddings"):
        yield documents[i : i + size]


def _fastembed_embedder(model_name: str, batch_size: int) -> Embedder:
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
    model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    async def embed(documents: list[str], input_type: str) -> np.ndarray:
        embeddings: list[np.ndarray] = []
        for batch in _batches(documents, batch_size):
            embeddings += model.embed(batch, batch_size=batch_size)
        return np.array(embeddings, dtype=np.float32)

    return embed


def _openai_embedder(
    model: str, api_key: str, base_url: str | None, batch_size: int
) -> Embedder:
    try:
        from openai import AsyncOpenAI  # noqa: PLC0415
    except ImportError as e:
        raise _missing_extra("openai") from e

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def embed(documents: list[str], input_type: str) -> np.ndarray:
        embeddings: list[list[float]] = []
        for batch in _batches(documents, batch_size):
            response = await client.embeddings.create(input=batch, model=model)
            embeddings += [e.embedding for e in response.data]
        return np.array(embeddings, dtype=np.float32)

    return embed


def _voyageai_embedder(model: str, api_key: str, batch_size: int) -> Embedder:
    try:
        import voyageai  # noqa: PLC0415  # pyright: ignore[reportMissingTypeStubs]
    except ImportError as e:
        raise _missing_extra("voyageai") from e

    client = voyageai.AsyncClient(api_key=api_key)  # pyright: ignore[reportPrivateImportUsage]

    async def embed(documents: list[str], input_type: str) -> np.ndarray:
        embeddings: list[list[float]] = []
        for batch in _batches(documents, batch_size):
            result = await client.embed(batch, model=model, input_type=input_type)
            embeddings += result.embeddings  # pyright: ignore[reportAssignmentType]
        return np.array(embeddings, dtype=np.float32)

    return embed
