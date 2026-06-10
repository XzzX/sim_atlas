from __future__ import annotations

import asyncio
import importlib
from typing import Any, cast

import pytest

from sim_atlas.agent._runner import run_agent_stream
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


class _FakeTrace:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        self.events = events

    def span(
        self,
        *,
        name: str,
        input: Any | None = None,
        level: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _FakeTrace:
        self.events.append(
            (
                "span",
                {"name": name, "input": input, "level": level, "metadata": metadata},
            )
        )
        return _FakeTrace(self.events)

    def generation(
        self,
        *,
        name: str,
        model: str | None = None,
        input: Any | None = None,
        level: str | None = None,
        model_parameters: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _FakeTrace:
        self.events.append(
            (
                "generation",
                {
                    "name": name,
                    "model": model,
                    "input": input,
                    "level": level,
                    "model_parameters": model_parameters,
                    "metadata": metadata,
                },
            )
        )
        return _FakeTrace(self.events)

    def update(self, **kwargs: Any) -> None:
        self.events.append(("update", kwargs))

    def end(self, **kwargs: Any) -> None:
        self.events.append(("end", kwargs))

    def record_exception(self, exc: BaseException) -> None:
        self.events.append(("exception", str(exc)))


def test_run_agent_stream_records_tracing_without_changing_sse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            )
        ]

    chunks = asyncio.run(collect())

    assert any('"type":"message"' in chunk for chunk in chunks)
    assert any('"type":"graph_update"' in chunk for chunk in chunks)
