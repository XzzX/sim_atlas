import re

from openai import AsyncOpenAI

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_CODE_FENCE = re.compile(r"\A```[^\n]*\n(.*?)\n```\Z", re.DOTALL)
_QUOTES = ('"""', "'''", '"', "'")


def clean_response(content: str) -> str:
    """Strip reasoning tags, code fences, and wrapping quotes from an LLM reply.

    Args:
        content: The raw message content returned by the LLM.

    Returns:
        The cleaned docstring text.
    """
    # Drop <think>...</think> reasoning blocks emitted by reasoning models.
    content = _THINK_BLOCK.sub("", content)
    # Some reasoning models omit the opening tag; keep only what follows the
    # final closing tag.
    if "</think>" in content:
        content = content.rsplit("</think>", 1)[-1]
    content = content.strip()

    # Unwrap a fenced code block (```python ... ```), if the model added one.
    if match := _CODE_FENCE.match(content):
        content = match.group(1).strip()

    # Unwrap surrounding quotes the model may have wrapped the docstring in.
    for quote in _QUOTES:
        if (
            len(content) >= 2 * len(quote)
            and content.startswith(quote)
            and content.endswith(quote)
        ):
            content = content[len(quote) : -len(quote)].strip()
            break

    return content


async def generate_docstring(
    llm_url: str, llm_key: str, llm_model: str, source_code: str
) -> str:
    """Generate a docstring for the given source code using an LLM.

    Args:
        llm_url: The base URL of the OpenAI-compatible LLM service.
        llm_key: The API key for the LLM service.
        llm_model: The model name to use for generating the docstring.
        source_code: The source code for which to generate the docstring.

    Returns:
        The generated docstring, or an empty string if the LLM returned nothing.
    """
    client = AsyncOpenAI(api_key=llm_key, base_url=llm_url)

    prompt = (
        "Generate a concise docstring for the following Python code. "
        "Return only the docstring text itself, without surrounding quotes, "
        "code fences, or any explanation.\n\n"
        f"{source_code}"
    )

    response = await client.chat.completions.create(
        model=llm_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that writes clear, "
                    "PEP 257-compliant docstrings for Python code."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content
    return clean_response(content) if content else ""
