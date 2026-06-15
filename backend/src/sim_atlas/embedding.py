import numpy as np
import voyageai  # pyright: ignore[reportMissingTypeStubs]
from fastembed import TextEmbedding
from openai import AsyncOpenAI
from tqdm import tqdm

from .exceptions import AINotConfiguredError
from .settings import load_settings


async def create_embedding(
    documents: list[str], input_type: str = "document"
) -> np.ndarray:
    settings = load_settings()

    match settings.embedding_provider:
        case None:
            raise AINotConfiguredError("embedding_provider is not configured")

        case "voyageai":
            if not settings.embedding_api_key:
                raise AINotConfiguredError(
                    "embedding_api_key is required for the voyageai provider"
                )
            if not settings.embedding_model:
                raise AINotConfiguredError(
                    "embedding_model is required for the voyageai provider"
                )
            vo = voyageai.AsyncClient(api_key=settings.embedding_api_key)  # pyright: ignore[reportPrivateImportUsage]
            embeddings: list[list[float]] = []
            for i in tqdm(
                range(0, len(documents), settings.embedding_batch_size),
                desc="Creating embeddings",
            ):
                result = await vo.embed(
                    documents[i : i + settings.embedding_batch_size],
                    model=settings.embedding_model,
                    input_type=input_type,
                )
                embeddings += result.embeddings  # pyright: ignore[reportAssignmentType]
            return np.array(embeddings, dtype=np.float32)

        case "openai":
            if not settings.embedding_model:
                raise AINotConfiguredError(
                    "embedding_model is required for the openai provider"
                )
            if not settings.embedding_api_key:
                raise AINotConfiguredError(
                    "embedding_api_key is required for the openai provider"
                )
            client = AsyncOpenAI(
                api_key=settings.embedding_api_key, base_url=settings.embedding_base_url
            )
            openai_embeddings: list[list[float]] = []
            for i in tqdm(
                range(0, len(documents), settings.embedding_batch_size),
                desc="Creating embeddings",
            ):
                response = await client.embeddings.create(
                    input=documents[i : i + settings.embedding_batch_size],
                    model=settings.embedding_model,
                )
                openai_embeddings += [e.embedding for e in response.data]
            return np.array(openai_embeddings, dtype=np.float32)

        case "fastembed":
            model_name = settings.embedding_model or "nomic-ai/nomic-embed-text-v1.5"
            ft_model = TextEmbedding(model_name=model_name)
            fastembed_embeddings: list[np.ndarray] = []
            for i in tqdm(
                range(0, len(documents), settings.embedding_batch_size),
                desc="Creating embeddings",
            ):
                response = list(
                    ft_model.embed(
                        documents[i : i + settings.embedding_batch_size],
                        batch_size=settings.embedding_batch_size,
                    )
                )
                fastembed_embeddings += response
            return np.array(fastembed_embeddings, dtype=np.float32)
