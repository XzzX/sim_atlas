import numpy as np
import voyageai
from tqdm import tqdm

from .exceptions import AINotConfiguredError
from .settings import load_settings


async def create_embedding(
    documents: list[str], input_type: str = "document"
) -> np.ndarray:
    settings = load_settings()
    if not settings.voyage_api_key:
        raise AINotConfiguredError("voyage_api_key is not configured")
    vo = voyageai.AsyncClient(api_key=settings.voyage_api_key)  # pyright: ignore[reportPrivateImportUsage]
    batch_size = 256
    embeddings: list[list[float]] = []

    for i in tqdm(range(0, len(documents), batch_size), desc="Creating embeddings"):
        result = await vo.embed(
            documents[i : i + batch_size], model="voyage-3", input_type=input_type
        )
        embeddings += result.embeddings  # pyright: ignore[reportAssignmentType]

    return np.array(embeddings, dtype=np.float32)
