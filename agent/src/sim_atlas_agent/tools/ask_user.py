from langchain_core.tools import tool


@tool
def ask_user(question: str) -> str:
    """Ask the user a clarifying question."""
    return f"[No response recorded for: {question}]"
