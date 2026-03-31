import voyageai
from dotenv import load_dotenv

load_dotenv()


def create_embedding(
    text: list[str], input_type: str = "document"
) -> list[list[float]]:
    vo = voyageai.Client()  # pyright: ignore[reportPrivateImportUsage]
    # This will automatically use the environment variable VOYAGE_API_KEY.
    # Alternatively, you can use vo = voyageai.Client(api_key="<your secret key>")

    result = vo.embed(text, model="voyage-code-3", input_type=input_type)
    return result.embeddings  # pyright: ignore[reportReturnType]
