"""Operator-controlled catalog of LLM providers the agent may talk to.

This module is a leaf: `settings` imports it, so it must not import `settings`.

The catalog is the security boundary for the agent endpoint. Callers select a
provider by its opaque `id` and the base URL is looked up here, so no
caller-supplied string ever reaches the HTTP client. That removes the whole
class of allowlist bypasses that comparing a caller-supplied URL invites
(trailing slash, case, userinfo, IDN, percent-encoding, ...).
"""

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

#: Values OpenAI accepts for `reasoning_effort`.
LLM_REASONING_EFFORTS: tuple[str, ...] = ("minimal", "low", "medium", "high")

ReasoningEffort = Literal["minimal", "low", "medium", "high"]


class LLMModelSpec(BaseModel):
    """One selectable chat model within a provider."""

    name: str = Field(min_length=1)
    label: str | None = None
    #: Whether this model accepts OpenAI's `reasoning_effort` parameter. Most
    #: vLLM-hosted open-weight models reject it, which would surface as an
    #: opaque upstream 400 mid-stream, so it is opt-in per model.
    reasoning_effort: bool = False

    @model_validator(mode="before")
    @classmethod
    def _accept_bare_name(cls, value: Any) -> Any:
        """Allow `models = ["gpt-4.1"]` as shorthand for `[{name = "gpt-4.1"}]`."""
        if isinstance(value, str):
            return {"name": value}
        return value

    @property
    def display_label(self) -> str:
        return self.label or self.name


class LLMProvider(BaseModel):
    """An OpenAI-compatible endpoint the operator is willing to relay to."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    models: list[LLMModelSpec] = Field(min_length=1)
    default_model: str | None = None
    #: False for a local, unauthenticated endpoint such as Ollama.
    requires_api_key: bool = True

    @model_validator(mode="after")
    def _check_default_model(self) -> Self:
        if (
            self.default_model is not None
            and self.get_model(self.default_model) is None
        ):
            raise ValueError(
                f"default_model {self.default_model!r} is not among the models "
                f"of provider {self.id!r}"
            )
        return self

    def get_model(self, name: str) -> LLMModelSpec | None:
        return next((m for m in self.models if m.name == name), None)

    @property
    def resolved_default_model(self) -> LLMModelSpec:
        if self.default_model is not None:
            model = self.get_model(self.default_model)
            # Guaranteed by _check_default_model.
            assert model is not None
            return model
        return self.models[0]


#: Shipped defaults, so a fresh install offers bring-your-own-key access to both
#: a European academic endpoint and OpenAI without any configuration.
#:
#: These lists are deliberately short. Providers rotate their line-ups faster
#: than this file is released — GWDG only exposes its current set through
#: `GET /v1/models`, which needs a key — so an operator who wants more models
#: adds them via `llm_providers` in the config file.
DEFAULT_LLM_PROVIDERS: list[LLMProvider] = [
    LLMProvider(
        id="gwdg",
        label="GWDG Academic Cloud",
        base_url="https://chat-ai.academiccloud.de/v1/",
        models=[LLMModelSpec(name="qwen3.6-27b", label="Qwen 3.6 27B")],
    ),
    LLMProvider(
        id="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        models=[
            LLMModelSpec(name="gpt-5", label="GPT-5", reasoning_effort=True),
            LLMModelSpec(name="gpt-5-mini", label="GPT-5 mini", reasoning_effort=True),
            LLMModelSpec(name="gpt-5-nano", label="GPT-5 nano", reasoning_effort=True),
            LLMModelSpec(name="gpt-4.1", label="GPT-4.1"),
            LLMModelSpec(name="gpt-4o", label="GPT-4o"),
        ],
    ),
]


def build_catalog(providers: list[LLMProvider]) -> dict[str, LLMProvider]:
    """Index `providers` by id.

    Raises:
        ValueError: When two providers share an id, which would make the
            caller-facing id ambiguous.
    """
    catalog: dict[str, LLMProvider] = {}
    for provider in providers:
        if provider.id in catalog:
            raise ValueError(f"duplicate llm provider id {provider.id!r}")
        catalog[provider.id] = provider
    return catalog
