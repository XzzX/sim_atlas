import json

from langfuse.openai import AsyncOpenAI  # pyright: ignore[reportPrivateImportUsage]
from pydantic import BaseModel

from .exceptions import AINotConfiguredError
from .settings import load_settings


class _AIDescriptionResponse(BaseModel):
    summary: str
    description: str
    args: dict[str, str] = {}


async def create_ai_descriptions(
    name: str, docstring: str, source_code: str, output_labels: list[str] | None = None
) -> tuple[str, str, dict[str, str]]:
    """Generate search-optimized descriptions for a Python function.

    Returns a tuple of (ai_summary, ai_description, args_descriptions):
    - ai_summary: one sentence for compact display and keyword search
    - ai_description: 2-5 sentences with rich domain vocabulary for semantic search
    - args_descriptions: mapping of parameter name to one-sentence description
    """
    settings = load_settings()
    if (
        not settings.llm_api_key
        or not settings.llm_api_url
        or not settings.llm_chat_model
    ):
        raise AINotConfiguredError(
            "LLM settings (llm_api_key, llm_api_url, llm_chat_model) are not configured"
        )
    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_url)

    response = await client.chat.completions.create(
        model=settings.llm_chat_model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": f"""You are a search-indexing assistant for a scientific simulation node catalog.
Given a Python function, produce search-optimized descriptions as a JSON object with exactly these keys:

"summary": One concise sentence (≤20 words) that names what the function does, what it takes as input and what it returns.
  - Use terminology a user would type into a search box.
  - Include the function name or a clear paraphrase of it.

"description": 2-5 sentences that expand on the summary for semantic search embedding.
  - Mention what the inputs represent and what the output represents in physical or conceptual terms (not just type names).
  - Use natural synonyms and alternative phrasings to maximize recall (e.g. both "velocity" and "speed").

"args": An object mapping each parameter name and return value name to a one-sentence description of its physical or conceptual meaning.
  - Use the exact parameter name as the key (e.g. "temperature", "return").
  - Describe what the value represents in domain terms, not just its type (e.g. "initial temperature of the simulation box in Kelvin").
  - Include all inputs and outputs; use "return" for a single return value or the tuple element name for multiple.

Return only the JSON object, no other text.

Here is the function to describe:
```python
{source_code}
```
{f"The parsed output port names are (use these exact strings as keys for outputs in the args object): {', '.join(output_labels)}" if output_labels else ""}
""",
            }
        ],
    )
    raw = response.choices[0].message.content or "{}"

    # Remove thinking part if present (text between <think> tags)
    if "<think>" in raw and "</think>" in raw:
        start = raw.find("<think>")
        end = raw.find("</think>") + len("</think>")
        raw = raw[:start] + raw[end:]
        raw = raw.strip()

    result = _AIDescriptionResponse.model_validate(json.loads(raw))
    return result.summary, result.description, result.args
