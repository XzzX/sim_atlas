import numpy as np
import voyageai
from tqdm import tqdm

from .exceptions import AINotConfiguredError
from .settings import settings


def create_embedding(documents: list[str], input_type: str = "document") -> np.ndarray:
    if not settings.voyage_api_key:
        raise AINotConfiguredError("voyage_api_key is not configured")
    vo = voyageai.Client(api_key=settings.voyage_api_key)  # pyright: ignore[reportPrivateImportUsage]
    batch_size = 256
    embeddings: list[list[float]] = []

    for i in tqdm(range(0, len(documents), batch_size), desc="Creating embeddings"):
        embeddings += vo.embed(
            documents[i : i + batch_size], model="voyage-code-3", input_type=input_type
        ).embeddings  # pyright: ignore[reportAssignmentType]

    return np.array(embeddings, dtype=np.float32)
