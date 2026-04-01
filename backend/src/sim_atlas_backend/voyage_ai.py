import numpy as np
import voyageai
from dotenv import load_dotenv

load_dotenv()


def create_embedding(documents: list[str], input_type: str = "document") -> np.ndarray:
    vo = voyageai.Client()  # pyright: ignore[reportPrivateImportUsage]
    # This will automatically use the environment variable VOYAGE_API_KEY.
    # Alternatively, you can use vo = voyageai.Client(api_key="<your secret key>")

    batch_size = 256
    embeddings: list[list[float]] = []

    for i in range(0, len(documents), batch_size):
        embeddings += vo.embed(
            documents[i : i + batch_size], model="voyage-code-3", input_type="document"
        ).embeddings

    return np.array(embeddings, dtype=np.float32)  # pyright: ignore[reportReturnType]
