import asyncio

import numpy as np
import voyageai  # pyright: ignore[reportMissingTypeStubs]
from openai import AsyncOpenAI
from tqdm import tqdm

from .exceptions import AINotConfiguredError
from .settings import load_settings


async def create_embedding(
    documents: list[str], input_type: str = "document"
) -> np.ndarray:
    settings = load_settings()
    provider = settings.embedding_provider
    if provider is None:
        raise AINotConfiguredError("embedding_provider is not configured")

    if provider == "voyageai":
        if not settings.embedding_api_key:
            raise AINotConfiguredError(
                "embedding_api_key is required for the voyageai provider"
            )
        if not settings.embedding_model:
            raise AINotConfiguredError(
                "embedding_model is required for the voyageai provider"
            )
        vo = voyageai.AsyncClient(api_key=settings.embedding_api_key)  # pyright: ignore[reportPrivateImportUsage]
        batch_size = 256
        embeddings: list[list[float]] = []
        for i in tqdm(range(0, len(documents), batch_size), desc="Creating embeddings"):
            result = await vo.embed(
                documents[i : i + batch_size],
                model=settings.embedding_model,
                input_type=input_type,
            )
            embeddings += result.embeddings  # pyright: ignore[reportAssignmentType]
        return np.array(embeddings, dtype=np.float32)

    if provider == "openai":
        if not settings.embedding_model:
            raise AINotConfiguredError(
                "embedding_model is required for the openai provider"
            )
        client = AsyncOpenAI(
            api_key=settings.embedding_api_key, base_url=settings.embedding_base_url
        )
        batch_size = 256
        openai_embeddings: list[list[float]] = []
        for i in tqdm(range(0, len(documents), batch_size), desc="Creating embeddings"):
            response = await client.embeddings.create(
                input=documents[i : i + batch_size],
                model=settings.embedding_model,
            )
            openai_embeddings += [e.embedding for e in response.data]
        return np.array(openai_embeddings, dtype=np.float32)

    if not settings.embedding_model:
        raise AINotConfiguredError(
            "embedding_model is required for the sentence_transformer provider"
        )
    try:
        from sentence_transformers import (  # noqa: PLC0415  # pyright: ignore[reportMissingImports] -- optional dep
            SentenceTransformer,  # pyright: ignore[reportUnknownVariableType]
        )
    except ImportError as e:
        raise AINotConfiguredError(
            "sentence-transformers is not installed — run: pip install 'sim-atlas-backend[local]'"
        ) from e
    model = SentenceTransformer(settings.embedding_model)  # pyright: ignore[reportUnknownVariableType]
    vecs: np.ndarray = await asyncio.to_thread(model.encode, documents)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    return np.array(vecs, dtype=np.float32)
