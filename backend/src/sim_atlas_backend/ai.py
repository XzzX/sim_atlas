from openai import OpenAI

from sim_atlas_backend.models import NodeMetadata

from .settings import settings


def create_embedding(text: str) -> list[float]:
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_url)

    embedding = (
        client.embeddings.create(
            input=text,
            model=settings.llm_embedding_model,
        )
        .data[0]
        .embedding
    )

    return embedding


def create_ai_docstring(docstring: str, source_code: str) -> str:
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_url)

    docstring = (
        client.chat.completions.create(
            model=settings.llm_chat_model,
            messages=[
                {
                    "role": "user",
                    "content": f"""
Refine the existing docstring based on the source code of the function.
Extract information about the function's purpose, parameters, and return values.
Only return the docstring, nothing else. Do not print the function signature and remove the quotes if present. 
If the docstring is already good, just return it without changes.

docstring:
{docstring}

source code:
```python
{source_code}
```
""",
                }
            ],
        )
        .choices[0]
        .message.content
        or ""
    )
    # Remove thinking part if present (text between <think> tags)
    if "<think>" in docstring and "</think>" in docstring:
        start = docstring.find("<think>")
        end = docstring.find("</think>") + len("</think>")
        docstring = docstring[:start] + docstring[end:]
        docstring = docstring.strip()

    return docstring


def enrich_metadata_with_ai(metadata: NodeMetadata) -> NodeMetadata:
    ai_docstring = create_ai_docstring(metadata.docstring, metadata.source_code)
    embedding = create_embedding(metadata.source_code)
    return metadata.model_copy(
        update={"ai_docstring": ai_docstring, "embedding": embedding}
    )
