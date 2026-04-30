import json

from openai import OpenAI

from .exceptions import AINotConfiguredError
from .settings import settings


def create_embedding(text: str) -> list[float]:
    if (
        not settings.llm_api_key
        or not settings.llm_api_url
        or not settings.llm_embedding_model
    ):
        raise AINotConfiguredError(
            "LLM settings (llm_api_key, llm_api_url, llm_embedding_model) are not configured"
        )
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


def create_ai_descriptions(
    name: str, docstring: str, source_code: str
) -> tuple[str, str]:
    """Generate search-optimized descriptions for a Python function.

    Returns a tuple of (ai_summary, ai_description):
    - ai_summary: one sentence for compact display and keyword search
    - ai_description: 2-5 sentences with rich domain vocabulary for semantic search
    """
    if (
        not settings.llm_api_key
        or not settings.llm_api_url
        or not settings.llm_chat_model
    ):
        raise AINotConfiguredError(
            "LLM settings (llm_api_key, llm_api_url, llm_chat_model) are not configured"
        )
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_url)

    raw = (
        client.chat.completions.create(
            model=settings.llm_chat_model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": f"""You are a search-indexing assistant for a scientific simulation node catalog.
Given a Python function, produce two search-optimized descriptions as a JSON object with exactly these keys:

"summary": One concise sentence (≤20 words) that names what the function does, what it takes as input and what it returns.
  - Use terminology a user would type into a search box.
  - Include the function name or a clear paraphrase of it.

"description": 2-5 sentences that expand on the summary for semantic search embedding.
  - Mention what the inputs represent and what the output represents in physical or conceptual terms (not just type names).
  - Use natural synonyms and alternative phrasings to maximize recall (e.g. both "velocity" and "speed").

Return only the JSON object, no other text.

Here is the function to describe:
```python
{source_code}
```
""",
                }
            ],
        )
        .choices[0]
        .message.content
        or "{}"
    )

    # Remove thinking part if present (text between <think> tags)
    if "<think>" in raw and "</think>" in raw:
        start = raw.find("<think>")
        end = raw.find("</think>") + len("</think>")
        raw = raw[:start] + raw[end:]
        raw = raw.strip()

    parsed = json.loads(raw)
    ai_summary: str = parsed.get("summary", "").strip()
    ai_description: str = parsed.get("description", "").strip()
    return ai_summary, ai_description
