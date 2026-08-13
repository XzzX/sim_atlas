import secrets
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from sim_atlas.llm_providers import (
    DEFAULT_LLM_PROVIDERS,
    LLMProvider,
    build_catalog,
)

_CONFIG_FILES = [
    Path("/etc/sim_atlas_config.toml"),  # system (lowest priority)
    Path.home() / ".sim_atlas_config.toml",  # user
    Path(".sim_atlas_config.toml"),  # working directory (highest among files)
]


def _get_config_files() -> list[str]:
    """Get list of config file paths to search for."""
    return [str(p) for p in _CONFIG_FILES]


CONFIG_TEMPLATE = """# Sim Atlas Configuration Template
# Fill in required fields, uncomment and configure optional sections as needed.
# After editing, restart the server.

# === REQUIRED SETTINGS ===

# JWT Secret Key for signing access tokens.
# Generate a strong random key with: python -c "import secrets; print(secrets.token_urlsafe(32))"
# This is used to sign and verify API authentication tokens.
# Minimum recommended length: 32 characters
jwt_secret = "replace-with-strong-secret-key-min-32-chars"

# === OPTIONAL: JWT SETTINGS ===
# JWT Algorithm for token signing (default: HS256)
# Override only if you need a different algorithm.
# Common values: HS256 (HMAC with SHA-256), HS512 (HMAC with SHA-512)
# jwt_algorithm = "HS256"

# === OPTIONAL: LLM / DOCSTRING ENRICHMENT ===
# These three settings power docstring enrichment (POST /enrich) ONLY. They are
# charged to you, the operator, so the endpoint requires an access token.
# The workflow agent does NOT use them: it takes its provider and model from the
# [[llm_providers]] catalog below and its API key from the caller.
# Leave commented out if you don't use docstring enrichment.

# OpenAI-compatible LLM API Key
# Examples: OpenAI (sk-...), LocalAI, Ollama via OpenAI-compatible endpoint
# llm_api_key = "sk-..."

# OpenAI-compatible LLM API Base URL
# Base URL of the OpenAI-compatible API server.
# Examples: https://chat-ai.academiccloud.de/v1/ (GWDG)
#           http://localhost:11434/v1 (Ollama local)
# Must be a valid HTTP(S) URL.
# llm_base_url = "https://chat-ai.academiccloud.de/v1/"

# LLM Chat Model Name
# Name of the model to use for conversational docstring refinement.
# llm_chat_model = "qwen3.6-27b"

# LLM Concurrency
# Maximum number of simultaneous LLM requests.
# Lower values reduce API load; higher values speed up large batches.
# llm_concurrency = 5

# === OPTIONAL: AGENT LLM PROVIDER ALLOWLIST ===
# The endpoints the workflow agent is allowed to relay to. Users pick a provider
# and model in the Web IDE and supply their own API key, so nothing here is
# charged to you.
#
# This is a SECURITY boundary: clients send only the opaque `id`, never a URL, so
# the agent endpoint cannot be turned into an open proxy or an SSRF vector. Only
# add endpoints you are willing to have anonymous callers relay to, and never put
# a credential in a base_url — these values are served by the public
# GET /capabilities.
#
# Defaults (GWDG + OpenAI, shown below) apply when this section is absent.
# Uncommenting it REPLACES the defaults rather than extending them, so re-list
# every provider you want to keep.
#
# `models` entries are either a bare model id or a table. Set
# reasoning_effort = true only for models that accept OpenAI's reasoning_effort
# parameter — most vLLM-hosted open-weight models reject it. Providers rotate
# their line-ups often; GWDG only lists its current set via
# `curl -H "Authorization: Bearer $KEY" https://chat-ai.academiccloud.de/v1/models`.

# [[llm_providers]]
# id = "gwdg"
# label = "GWDG Academic Cloud"
# base_url = "https://chat-ai.academiccloud.de/v1/"
# models = ["qwen3.6-27b"]

# [[llm_providers]]
# id = "openai"
# label = "OpenAI"
# base_url = "https://api.openai.com/v1"
# models = [
#     { name = "gpt-5", label = "GPT-5", reasoning_effort = true },
#     { name = "gpt-5-mini", label = "GPT-5 mini", reasoning_effort = true },
#     "gpt-4.1",
# ]

# A local, unauthenticated endpoint needs requires_api_key = false so users are
# not asked for a key they do not have.
# [[llm_providers]]
# id = "ollama"
# label = "Local Ollama"
# base_url = "http://localhost:11434/v1"
# models = ["llama3.1"]
# requires_api_key = false

# Provider preselected in the Web IDE. Defaults to the first entry above.
# llm_default_provider = "gwdg"

# Maximum tool-calling turns per agent run.
# agent_max_iterations = 10

# === OPTIONAL: EMBEDDINGS ===
# Configure the embedding provider for semantic search.
embedding_provider = "fastembed"                    # fastembed | openai | voyageai
embedding_model = "nomic-ai/nomic-embed-text-v1.5"  # model name
# embedding_api_key = "pa-..."                      # API key (voyageai or openai; omit for fastembed)
# embedding_base_url = "https://..."                # base URL for openai-compatible endpoint (openai provider only)
embedding_batch_size = 8                            # number of documents per embedding batch

# === OPTIONAL: LANGFUSE OBSERVABILITY ===
# Enable this only if you want to export agent traces to Langfuse.
# Tracing is enabled when all of the fields below are set.
# Install the optional dependency with: uv sync --extra langfuse

# Langfuse Public Key
# Used to authenticate trace writes to Langfuse.
# langfuse_public_key = "pk-lf-..."

# Langfuse Secret Key
# Used with the public key to sign trace writes.
# langfuse_secret_key = "sk-lf-..."

# Langfuse Host URL
# Base URL for your Langfuse deployment.
# Examples: https://cloud.langfuse.com, http://localhost:3000
# langfuse_host = "https://cloud.langfuse.com"

# Langfuse Environment
# Optional environment label shown in Langfuse.
# langfuse_environment = "development"
"""


class Settings(BaseSettings):
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    # These three drive docstring enrichment (`POST /enrich`) only. The agent
    # gets its provider and model from `llm_providers` and its key from the
    # caller; see ADR-0019. Do not reintroduce them into the agent path.
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_chat_model: str | None = None
    llm_concurrency: int = 5
    # Providers the agent may relay to. Setting this in a config file *replaces*
    # the built-in list rather than extending it.
    llm_providers: list[LLMProvider] = Field(
        default_factory=lambda: list(DEFAULT_LLM_PROVIDERS)
    )
    llm_default_provider: str | None = None
    agent_max_iterations: int = Field(default=10, ge=1)
    embedding_provider: Literal["fastembed", "openai", "voyageai"] | None = None
    embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_batch_size: int = 8
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None
    langfuse_environment: str | None = None

    model_config = SettingsConfigDict(
        toml_file=_get_config_files(),
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SIM_ATLAS_",
    )

    @model_validator(mode="after")
    def _check_llm_providers(self) -> "Settings":
        # Surfaces a misconfigured catalog at startup rather than as a 400 on the
        # first agent request.
        catalog = build_catalog(self.llm_providers)
        if self.llm_default_provider is not None and (
            self.llm_default_provider not in catalog
        ):
            raise ValueError(
                f"llm_default_provider {self.llm_default_provider!r} is not among "
                f"the configured llm_providers ({', '.join(catalog) or 'none'})"
            )
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
        )

    @property
    def config_dir(self) -> Path:
        """Directory of the highest-priority config file that exists, or cwd."""
        for path in reversed(_CONFIG_FILES):  # highest priority first
            if path.exists():
                return path.parent
        return Path(".")

    @property
    def langfuse_enabled(self) -> bool:
        return bool(
            self.langfuse_public_key and self.langfuse_secret_key and self.langfuse_host
        )

    @property
    def llm_catalog(self) -> dict[str, LLMProvider]:
        """Configured providers indexed by id; validated at construction."""
        return build_catalog(self.llm_providers)

    @property
    def enrichment_enabled(self) -> bool:
        """Whether `POST /enrich` can run on the server's own credentials."""
        return bool(self.llm_api_key and self.llm_base_url and self.llm_chat_model)

    @property
    def embeddings_enabled(self) -> bool:
        match self.embedding_provider:
            case "fastembed":
                return True
            case "openai" | "voyageai":
                return bool(self.embedding_api_key and self.embedding_model)
            case _:
                return False


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """
    Load settings from environment, .env file, or TOML config files.

    On the first startup, if no config file exists and required settings are
    missing, generates a strong JWT secret, writes a config file, and continues
    loading without requiring a restart.

    Returns:
        Settings: Validated settings instance

    Raises:
        ValidationError: When config file exists but contains invalid values
    """
    try:
        return Settings.model_validate({})
    except ValidationError as e:
        # Check if any config file exists
        config_exists = any(path.exists() for path in _CONFIG_FILES)

        if not config_exists:
            # Check if any required fields are actually missing
            # by examining the error details
            missing_required = any(
                error.get("type") == "missing" for error in e.errors()
            )

            if missing_required:
                # Generate a strong JWT secret so the server can start immediately
                jwt_secret = secrets.token_urlsafe(32)
                config_content = CONFIG_TEMPLATE.replace(
                    'jwt_secret = "replace-with-strong-secret-key-min-32-chars"',
                    f'jwt_secret = "{jwt_secret}"',
                )

                # Write config to working directory
                config_path = _CONFIG_FILES[2]  # .sim_atlas_config.toml
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text(config_content)

                # Inform the user
                print(
                    f"\n{'=' * 70}",
                    "New configuration file created:",
                    f"{config_path.absolute()}",
                    f"{'=' * 70}",
                    "\nA strong JWT secret has been generated and saved automatically.",
                    "You can check the configuration and restart the server if you want.",
                    f"{'=' * 70}\n",
                    sep="\n",
                    file=sys.stderr,
                )

                # Clear the lru_cache so the newly written file is picked up
                load_settings.cache_clear()
                return Settings.model_validate({})

        # If config exists or error is not about missing fields, re-raise
        raise


# Load settings on import
settings = load_settings()
