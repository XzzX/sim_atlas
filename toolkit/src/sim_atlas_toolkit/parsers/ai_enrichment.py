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

    prompt = f"""
You are a technical writer generating Python docstrings. You will receive
Python source code for a single function, method, or class.

Your task: write a docstring for it in NumPy style.

Rules:

1. If the code already contains a docstring, use it as the basis. Keep its
   wording and intent where possible, but verify every statement against the
   actual code. Correct anything that is wrong, outdated, or inconsistent
   with the implementation (e.g., parameters that no longer exist, wrong
   types, wrong default values, described behavior that differs from the code).
2. If there is no docstring, derive one entirely from the code itself. Do
   not invent behavior that cannot be inferred from the implementation or
   signature. If a parameter's purpose is genuinely unclear, describe it
   neutrally based on how it is used.
3. The docstring must contain exactly these sections, in this order:
   - A one-line summary (imperative mood, ends with a period, fits on one
     line, no leading "This function ...").
   - A blank line, then an extended description: one short paragraph
     explaining what the code does, relevant behavior, and side effects.
     Omit this only if the function is trivial and the summary says it all.
   - A "Parameters" section describing every parameter in signature order.
     Use type annotations from the signature if present. Note defaults as
     ", optional" with the default mentioned in the description
     (e.g., "by default 10"). Skip self and cls.
   - A "Returns" section describing the return value(s) with type and
     meaning. If the function returns None, omit this section. For
     generators, use "Yields" instead.
4. Drop everything else. Do not include Raises, Examples, Notes, See Also,
   References, or any other sections, even if the original docstring had
   them.
5. Formatting: NumPy style with underlined section headers, e.g.

   Parameters
   ----------
   x : int
       Description of x.

   Wrap lines at 79 characters. Indent continuation lines of descriptions
   by four spaces relative to the parameter name.
6. Output only the docstring, without the triple quotes, with no
   surrounding code, no markdown fences, and no commentary.

Source code:

<code>
{source_code}
</code>
"""

    response = await client.chat.completions.create(
        model=llm_model,
        messages=[
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content
    return clean_response(content) if content else ""
