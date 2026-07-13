from openai import AsyncOpenAI


async def generate_docstring(
    llm_url: str, llm_key: str, llm_model: str, source_code: str
) -> str:
    """
    Generate a docstring for the given source code using an LLM.

    Args:
        llm_url (str): The URL of the LLM service.
        llm_key (str): The API key for the LLM service.
        llm_model (str): The model name to use for generating the docstring.
        source_code (str): The source code for which to generate the docstring.

    Returns:
        str: The generated docstring.
    """

    client = AsyncOpenAI(api_key=llm_key, base_url=llm_url)

    prompt = f"Generate a docstring for the following Python function:\n\n{source_code}\n\nDocstring:"

    response = await client.chat.completions.create(
        model=llm_model,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that generates docstrings for Python functions.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    # Extract the generated docstring from the response
    content = response.choices[0].message.content

    return content.strip() if content else ""
