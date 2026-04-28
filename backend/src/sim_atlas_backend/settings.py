from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

_CONFIG_FILES = [
    Path("/etc/sim_atlas/config.toml"),  # system (lowest priority)
    Path.home() / ".sim_atlas" / "config.toml",  # user
    Path(".sim_atlas") / "config.toml",  # working directory (highest among files)
]


class Settings(BaseSettings):
    jwt_secret_key: str
    jwt_algorithm: str
    llm_api_key: str
    llm_api_url: str
    llm_embedding_model: str
    llm_chat_model: str
    voyage_api_key: str

    model_config = SettingsConfigDict(
        toml_file=[str(p) for p in _CONFIG_FILES],
        env_file=".env",
        env_file_encoding="utf-8",
    )

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


settings = Settings.model_validate({})
