from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnrichmentSettings(BaseSettings):
    """LLM-based docstring enrichment configuration."""

    model_config = SettingsConfigDict(env_prefix="SIM_ATLAS_LLM_")

    enabled: bool = False
    """Master switch; when False the pipeline behaves exactly as before."""

    url: str = ""
    """OpenAI-compatible base URL."""

    key: str = ""
    """API key for the LLM service."""

    model: str = ""
    """Model name to use for generating docstrings."""

    overwrite: bool = False
    """False → only generate when the docstring is empty; True → always (re)generate."""


class ToolkitSettings(BaseSettings):
    """Top-level toolkit configuration threaded through the upload pipeline."""

    model_config = SettingsConfigDict(env_prefix="SIM_ATLAS_")

    enrichment: EnrichmentSettings = Field(default_factory=EnrichmentSettings)
    """LLM docstring enrichment configuration."""
