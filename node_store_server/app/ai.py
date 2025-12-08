from bson.binary import Binary, BinaryVectorDtype
from dotenv import dotenv_values

config = dotenv_values(".env")


def create_embedding(text: str) -> Binary:
    from openai import OpenAI

    # API configuration
    api_key = config["LLM_API_KEY"] or ""
    base_url = config["LLM_API_URL"] or ""
    model = config["LLM_EMBEDDING_MODEL"] or ""

    # Start OpenAI client
    client = OpenAI(api_key=api_key, base_url=base_url)

    # Get response
    embedding = (
        client.embeddings.create(
            input=text,
            model=model,
        )
        .data[0]
        .embedding
    )

    # Define a function to generate BSON vectors
    def generate_bson_vector(vector, vector_dtype):
        return Binary.from_vector(vector, vector_dtype)

    # Generate BSON vector from the sample float32 embedding
    bson_float32_embedding = generate_bson_vector(embedding, BinaryVectorDtype.FLOAT32)
    return bson_float32_embedding


def create_ai_docstring(docstring: str, source_code: str) -> str:
    from openai import OpenAI

    # API configuration
    api_key = config["LLM_API_KEY"] or ""
    base_url = config["LLM_API_URL"] or ""
    model = config["LLM_CHAT_MODEL"] or ""

    # Start OpenAI client
    client = OpenAI(api_key=api_key, base_url=base_url)

    # Get response
    docstring = (
        client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f"""
Refine the existing docstring based on the source code of the function.
Extract information about the function's purpose, parameters, and return values.
Only return the docstring, nothing else.

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
