from __future__ import annotations

import asyncio
import importlib
from typing import Any, cast

import pytest
from pydantic import ValidationError

from sim_atlas.agent._runner import resolve_llm_config, run_agent_stream
from sim_atlas.exceptions import AINotConfiguredError
from sim_atlas.models import AgentRequest
from sim_atlas.storage_interface import StorageInterface

runner_module = importlib.import_module("sim_atlas.agent._runner")


class _FakeFilterOptions:
    datatypes: list[str] = []
    units: list[str] = []
    quantities: list[str] = []
    keywords: list[str] = []


class _FakeStorage:
    def get_filter_options(self) -> _FakeFilterOptions:
        return _FakeFilterOptions()


class _FakeMessage:
    content = "Done."
    tool_calls = None

    def model_dump(self, exclude_unset: bool = False) -> dict[str, str]:
        return {"role": "assistant", "content": self.content}


class _FakeChoice:
    message = _FakeMessage()


class _FakeResponse:
    choices = [_FakeChoice()]
    usage = None


class _FakeCompletions:
    async def create(self, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse()


class _FakeChat:
    completions = _FakeCompletions()


class _FakeAsyncOpenAI:
    def __init__(self, **kwargs: Any) -> None:
        self.chat = _FakeChat()


class _FakeSettings:
    llm_api_key = "test-key"
    llm_base_url = "http://localhost"
    llm_chat_model = "test-model"
    agent_max_iterations = 10
    langfuse_public_key = None
    langfuse_secret_key = None
    langfuse_host = None
    langfuse_environment = None


def test_run_agent_stream_records_tracing_without_changing_sse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)
    monkeypatch.setattr(runner_module, "AsyncOpenAI", _FakeAsyncOpenAI)

    def fake_validate_graph(scratch: Any, storage: Any) -> list[str]:
        return []

    monkeypatch.setattr(runner_module, "validate_graph", fake_validate_graph)

    request = AgentRequest(query="Hello", nodes=[], edges=[])

    async def collect() -> list[str]:
        return [
            chunk
            async for chunk in run_agent_stream(
                request,
                cast(StorageInterface, _FakeStorage()),
                resolve_llm_config(request),
            )
        ]

    chunks = asyncio.run(collect())

    assert any('"type":"message"' in chunk for chunk in chunks)
    assert any('"type":"graph_update"' in chunk for chunk in chunks)


# --- credential resolution ---


class _NoLLMSettings(_FakeSettings):
    llm_api_key = None
    llm_chat_model = None


class _NoBaseUrlSettings(_FakeSettings):
    llm_base_url = None


def test_resolve_llm_config_prefers_request_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    llm = resolve_llm_config(
        AgentRequest(
            query="Hello",
            nodes=[],
            edges=[],
            llm_api_key="user-key",
            llm_chat_model="user-model",
        )
    )

    assert llm.api_key == "user-key"
    assert llm.chat_model == "user-model"
    # The base URL is never caller-supplied.
    assert llm.base_url == "http://localhost"


def test_resolve_llm_config_falls_back_to_server_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    llm = resolve_llm_config(AgentRequest(query="Hello", nodes=[], edges=[]))

    assert llm == ("test-key", "http://localhost", "test-model")


def test_resolve_llm_config_uses_request_credentials_without_server_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _NoLLMSettings)

    llm = resolve_llm_config(
        AgentRequest(
            query="Hello",
            nodes=[],
            edges=[],
            llm_api_key="user-key",
            llm_chat_model="user-model",
        )
    )

    assert llm == ("user-key", "http://localhost", "user-model")


def test_resolve_llm_config_raises_without_any_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _NoLLMSettings)

    with pytest.raises(AINotConfiguredError):
        resolve_llm_config(AgentRequest(query="Hello", nodes=[], edges=[]))


def test_resolve_llm_config_raises_without_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _NoBaseUrlSettings)

    with pytest.raises(AINotConfiguredError):
        resolve_llm_config(
            AgentRequest(
                query="Hello",
                nodes=[],
                edges=[],
                llm_api_key="user-key",
                llm_chat_model="user-model",
            )
        )


@pytest.mark.parametrize(
    ("api_key", "chat_model"),
    [("user-key", None), (None, "user-model")],
)
def test_agent_request_rejects_half_filled_credentials(
    api_key: str | None, chat_model: str | None
) -> None:
    with pytest.raises(ValidationError):
        AgentRequest(
            query="Hello",
            nodes=[],
            edges=[],
            llm_api_key=api_key,
            llm_chat_model=chat_model,
        )
