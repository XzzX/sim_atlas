from __future__ import annotations

import asyncio
import importlib
from typing import Any, cast

import pytest

from sim_atlas_backend.agent._runner import run_agent_stream
from sim_atlas_backend.models import AgentRequest
from sim_atlas_backend.settings import Settings
from sim_atlas_backend.storage_interface import StorageInterface

runner_module = importlib.import_module("sim_atlas_backend.agent._runner")
settings_module = importlib.import_module("sim_atlas_backend.settings")


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


class _FakeTrace:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        self.events = events

    def span(
        self,
        *,
        name: str,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _FakeTrace:
        self.events.append(
            ("span", {"name": name, "input": input, "metadata": metadata})
        )
        return _FakeTrace(self.events)

    def generation(
        self,
        *,
        name: str,
        model: str | None = None,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _FakeTrace:
        self.events.append(
            (
                "generation",
                {"name": name, "model": model, "input": input, "metadata": metadata},
            )
        )
        return _FakeTrace(self.events)

    def update(self, **kwargs: Any) -> None:
        self.events.append(("update", kwargs))

    def end(self, **kwargs: Any) -> None:
        self.events.append(("end", kwargs))

    def record_exception(self, exc: BaseException) -> None:
        self.events.append(("exception", str(exc)))


class _FakeObservability:
    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []
        self.flushed = False

    def start_trace(
        self,
        *,
        name: str,
        session_id: str,
        request: AgentRequest,
        messages: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> _FakeTrace:
        self.events.append(
            (
                "start_trace",
                {
                    "name": name,
                    "session_id": session_id,
                    "request": request.model_dump(),
                    "messages": messages,
                    "metadata": metadata,
                },
            )
        )
        return _FakeTrace(self.events)

    def flush(self) -> None:
        self.flushed = True


def test_run_agent_stream_records_tracing_without_changing_sse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        jwt_secret_key="x",
        jwt_algorithm="HS256",
        llm_api_key="llm-key",
        llm_api_url="http://llm.local/v1",
        llm_chat_model="test-model",
    )

    monkeypatch.setattr(settings_module, "load_settings", lambda: settings)
    monkeypatch.setattr(runner_module, "load_settings", lambda: settings)
    monkeypatch.setattr(runner_module, "AsyncOpenAI", _FakeAsyncOpenAI)

    def fake_validate_graph(scratch: Any, storage: Any) -> list[str]:
        return []

    monkeypatch.setattr(runner_module, "validate_graph", fake_validate_graph)

    request = AgentRequest(query="Hello", nodes=[], edges=[])
    observability = _FakeObservability()

    async def collect() -> list[str]:
        return [
            chunk
            async for chunk in run_agent_stream(
                request,
                cast(StorageInterface, _FakeStorage()),
                observability=observability,
            )
        ]

    chunks = asyncio.run(collect())

    assert any('"type":"message"' in chunk for chunk in chunks)
    assert any('"type":"graph_update"' in chunk for chunk in chunks)
    assert observability.flushed is True
    assert any(event[0] == "generation" for event in observability.events)
    assert any(event[0] == "update" for event in observability.events)
