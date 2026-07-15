from pydantic_settings import BaseSettings, SettingsConfigDict


class ToolkitSettings(BaseSettings):
    """Top-level toolkit configuration threaded through the upload pipeline."""

    model_config = SettingsConfigDict(env_prefix="SIM_ATLAS_")

    api_url: str = ""
    """Backend API base URL."""

    api_token: str = ""
    """API token sent as x-api-key to the backend."""

    llm_enabled: bool = False
    """Master switch for LLM-based docstring enrichment; when False the pipeline behaves exactly as before."""

    llm_url: str = ""
    """OpenAI-compatible base URL."""

    llm_key: str = ""
    """API key for the LLM service."""

    llm_model: str = ""
    """Model name to use for generating docstrings."""

    llm_overwrite: bool = False
    """False → only generate when the docstring is empty; True → always (re)generate."""
