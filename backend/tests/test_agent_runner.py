from __future__ import annotations

import asyncio
import importlib
from collections.abc import AsyncGenerator
from typing import Any, cast

import pytest

from sim_atlas.agent._runner import resolve_llm_config, run_agent_stream
from sim_atlas.agent._sse import with_keepalive
from sim_atlas.exceptions import AINotConfiguredError, LLMSelectionError
from sim_atlas.llm_providers import LLMProvider
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


# Built via model_validate so the bare-string model shorthand — the form an
# operator writes in TOML — is exercised here too.
_PLAIN_PROVIDER = LLMProvider.model_validate(
    {
        "id": "plain",
        "label": "Plain",
        "base_url": "http://localhost",
        "models": ["test-model", {"name": "thinker", "reasoning_effort": True}],
    }
)
_OPEN_PROVIDER = LLMProvider.model_validate(
    {
        "id": "open",
        "label": "Open",
        "base_url": "http://ollama",
        "models": ["local-model"],
        "requires_api_key": False,
    }
)


class _FakeSettings:
    # Present but unused by the agent: enrichment-only settings must not leak
    # back into credential resolution.
    llm_api_key = "server-key"
    llm_base_url = "http://enrichment-only"
    llm_chat_model = "enrichment-only-model"
    llm_providers = [_PLAIN_PROVIDER, _OPEN_PROVIDER]
    llm_catalog = {"plain": _PLAIN_PROVIDER, "open": _OPEN_PROVIDER}
    llm_default_provider = None
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

    request = AgentRequest(query="Hello", nodes=[], edges=[], llm_api_key="user-key")

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


# --- SSE keep-alive ---


def test_with_keepalive_fills_silent_gaps() -> None:
    async def slow_events() -> AsyncGenerator[str, None]:
        yield "data: one\n\n"
        await asyncio.sleep(0.25)
        yield "data: two\n\n"

    async def collect() -> list[str]:
        return [chunk async for chunk in with_keepalive(slow_events(), interval=0.05)]

    chunks = asyncio.run(collect())

    assert [c for c in chunks if c.startswith("data: ")] == [
        "data: one\n\n",
        "data: two\n\n",
    ]
    # 0.25s of silence at a 0.05s interval, with slack for a slow test machine.
    min_keepalives = 2
    assert chunks.count(": keep-alive\n\n") >= min_keepalives
    # The filler lands inside the gap, not before the first event or after the last.
    assert chunks[0] == "data: one\n\n"
    assert chunks[-1] == "data: two\n\n"


def test_with_keepalive_stays_silent_while_events_flow() -> None:
    async def fast_events() -> AsyncGenerator[str, None]:
        yield "data: one\n\n"
        yield "data: two\n\n"

    async def collect() -> list[str]:
        return [chunk async for chunk in with_keepalive(fast_events(), interval=30.0)]

    assert asyncio.run(collect()) == ["data: one\n\n", "data: two\n\n"]


def test_with_keepalive_propagates_generator_failures() -> None:
    async def failing_events() -> AsyncGenerator[str, None]:
        yield "data: one\n\n"
        raise RuntimeError("boom")

    async def collect() -> list[str]:
        return [
            chunk async for chunk in with_keepalive(failing_events(), interval=30.0)
        ]

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(collect())


def test_with_keepalive_closes_the_agent_stream_when_the_client_leaves() -> None:
    """A disconnect must not strand the in-flight `anext` on the inner generator."""
    closed = False

    async def slow_events() -> AsyncGenerator[str, None]:
        nonlocal closed
        try:
            yield "data: one\n\n"
            await asyncio.sleep(30)
            yield "data: two\n\n"
        finally:
            closed = True

    async def take_one() -> str:
        stream = with_keepalive(slow_events(), interval=30.0)
        first = ""
        async for chunk in stream:
            first = chunk
            break
        await stream.aclose()
        return first

    assert asyncio.run(take_one()) == "data: one\n\n"
    assert closed


# --- credential resolution ---


class _NoProvidersSettings(_FakeSettings):
    llm_providers: list[LLMProvider] = []
    llm_catalog: dict[str, LLMProvider] = {}


class _DefaultProviderSettings(_FakeSettings):
    llm_default_provider = "open"


def _request(**kwargs: Any) -> AgentRequest:
    return AgentRequest(query="Hello", nodes=[], edges=[], **kwargs)


def test_resolve_llm_config_uses_the_selected_provider_and_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    llm = resolve_llm_config(
        _request(llm_api_key="user-key", llm_provider="plain", llm_chat_model="thinker")
    )

    # The base URL comes from the catalog, never from the request.
    assert llm == ("user-key", "http://localhost", "thinker", None)


def test_resolve_llm_config_defaults_to_the_first_provider_and_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    llm = resolve_llm_config(_request(llm_api_key="user-key"))

    assert llm == ("user-key", "http://localhost", "test-model", None)


def test_resolve_llm_config_honours_the_configured_default_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _DefaultProviderSettings)

    llm = resolve_llm_config(_request(llm_api_key="user-key"))

    assert llm.base_url == "http://ollama"
    assert llm.chat_model == "local-model"


def test_resolve_llm_config_never_falls_back_to_the_server_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The server key is reserved for enrichment; the agent always spends the caller's."""
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    with pytest.raises(LLMSelectionError):
        resolve_llm_config(_request())


def test_resolve_llm_config_allows_a_provider_that_needs_no_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    llm = resolve_llm_config(_request(llm_provider="open"))

    assert llm.base_url == "http://ollama"
    assert llm.api_key


@pytest.mark.parametrize(
    ("kwargs", "rejected"),
    [
        # A URL is just another unknown id: it is looked up, never dialled.
        ({"llm_provider": "http://169.254.169.254/"}, "http://169.254.169.254/"),
        (
            {"llm_provider": "plain", "llm_chat_model": "not-allowlisted"},
            "not-allowlisted",
        ),
    ],
)
def test_resolve_llm_config_rejects_selections_outside_the_allowlist(
    kwargs: dict[str, str], rejected: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    with pytest.raises(LLMSelectionError) as excinfo:
        resolve_llm_config(_request(llm_api_key="user-key", **kwargs))

    # The message enumerates the allowlist and never reflects the rejected value.
    assert rejected not in str(excinfo.value)


def test_resolve_llm_config_raises_without_any_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _NoProvidersSettings)

    with pytest.raises(AINotConfiguredError):
        resolve_llm_config(_request(llm_api_key="user-key"))


def test_resolve_llm_config_keeps_reasoning_effort_for_a_supporting_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    llm = resolve_llm_config(
        _request(
            llm_api_key="user-key",
            llm_chat_model="thinker",
            llm_reasoning_effort="high",
        )
    )

    assert llm.reasoning_effort == "high"


def test_resolve_llm_config_drops_reasoning_effort_for_other_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale browser selection must not break a run on a non-reasoning model."""
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    llm = resolve_llm_config(
        _request(
            llm_api_key="user-key",
            llm_chat_model="test-model",
            llm_reasoning_effort="high",
        )
    )

    assert llm.reasoning_effort is None
