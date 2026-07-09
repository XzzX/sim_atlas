from pydantic import BaseModel, ConfigDict, computed_field, field_validator


class ToolkitSettings(BaseModel):
    """Runtime settings for toolkit uploads and optional AI enrichment."""

    model_config = ConfigDict(frozen=True)

    api_url: str
    api_token: str
    llm_url: str | None = None
    llm_key: str | None = None
    llm_model: str | None = None

    @field_validator(
        "api_url", "api_token", "llm_url", "llm_key", "llm_model", mode="before"
    )
    @classmethod
    def _normalize_empty_string(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value

    @computed_field(return_type=bool)
    @property
    def enrichment_enabled(self) -> bool:
        return all((self.llm_url, self.llm_key, self.llm_model))
