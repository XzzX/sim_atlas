import importlib
from types import SimpleNamespace
from typing import Any

import pytest

from sim_atlas_backend.agent._observability import build_agent_observability
from sim_atlas_backend.models import AgentRequest
from sim_atlas_backend.settings import Settings

observability_module = importlib.import_module("sim_atlas_backend.agent._observability")


def _agent_request() -> AgentRequest:
    return AgentRequest(query="hello", nodes=[], edges=[])


def test_build_agent_observability_is_noop_without_langfuse():
    settings = Settings(jwt_secret_key="x", jwt_algorithm="HS256")
    observability = build_agent_observability(settings)

    trace = observability.start_trace(
        name="agent_stream",
        request=_agent_request(),
        messages=[],
    )

    assert observability.__class__.__name__ == "_NoopObservability"
    assert trace.__class__.__name__ == "_NoopTrace"


def test_build_agent_observability_uses_langfuse_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeTrace:
        def __init__(self, label: str) -> None:
            self.label = label

        def start_observation(
            self,
            *,
            name: str,
            as_type: str = "span",
            model: object = None,
            input: object = None,
            metadata: object = None,
        ) -> "FakeTrace":
            if as_type == "generation":
                captured.setdefault("generations", []).append(
                    (name, model, input, metadata)
                )
            else:
                captured.setdefault("spans", []).append((name, input, metadata))
            return FakeTrace(name)

        def update(self, **kwargs: object) -> None:
            captured.setdefault("updates", []).append(kwargs)

        def end(self, **kwargs: object) -> None:
            captured.setdefault("ends", []).append(kwargs)

        def record_exception(self, exc: BaseException) -> None:
            captured.setdefault("exceptions", []).append(str(exc))

    class FakeLangfuse:
        def __init__(self, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs

        def start_observation(self, *, name: str, **kwargs: object) -> FakeTrace:
            captured["trace_kwargs"] = {"name": name, **kwargs}
            return FakeTrace(name)

        def flush(self) -> None:
            captured["flushed"] = True

    def _fake_import_module(name: str) -> SimpleNamespace:
        return SimpleNamespace(Langfuse=FakeLangfuse)

    monkeypatch.setattr(
        observability_module.importlib,
        "import_module",
        _fake_import_module,
    )

    settings = Settings(
        jwt_secret_key="x",
        jwt_algorithm="HS256",
        langfuse_public_key="pk",
        langfuse_secret_key="sk",
        langfuse_host="http://langfuse.local",
        langfuse_environment="test",
    )

    observability = observability_module.build_agent_observability(settings)
    trace = observability.start_trace(
        name="agent_stream",
        request=_agent_request(),
        messages=[{"role": "user", "content": "hello"}],
        metadata={"request_id": "abc"},
    )
    child = trace.span(name="tool:add_node", input={"label": "node"})
    child.update(output="ok")
    child.end()
    trace.record_exception(RuntimeError("boom"))
    observability.flush()

    assert captured["client_kwargs"] == {
        "public_key": "pk",
        "secret_key": "sk",
        "base_url": "http://langfuse.local",
        "environment": "test",
    }
    assert captured["trace_kwargs"]["name"] == "agent_stream"
    assert captured["flushed"] is True
    assert captured["spans"]
    assert captured["exceptions"] == ["boom"]
