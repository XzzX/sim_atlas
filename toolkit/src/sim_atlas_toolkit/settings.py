from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ToolkitSettings(BaseSettings):
    """Top-level toolkit configuration threaded through the upload pipeline."""

    model_config = SettingsConfigDict(env_prefix="SIM_ATLAS_")

    api_url: str = ""
    """Backend API base URL."""

    api_token: str = ""
    """API token sent as x-api-key to the backend."""

    llm_docstrings: Literal["no", "missing", "overwrite"] = "no"
    """Docstring enrichment strategy: ``no`` disables the LLM entirely, ``missing`` generates only when the docstring is empty, ``overwrite`` always regenerates."""

    llm_url: str = ""
    """OpenAI-compatible base URL."""

    llm_key: str = ""
    """API key for the LLM service."""

    llm_model: str = ""
    """Model name to use for generating docstrings."""

    embed_enabled: bool = True
    """Master switch for triggering backend embedding after upload; on by default."""
