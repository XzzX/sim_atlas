import importlib
from types import SimpleNamespace

from sim_atlas_backend.agent._observability import build_agent_observability
from sim_atlas_backend.models import AgentRequest
from sim_atlas_backend.settings import Settings

observability_module = importlib.import_module(
    "sim_atlas_backend.agent._observability"
)


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


def test_build_agent_observability_uses_langfuse_client(monkeypatch):
    captured: dict[str, object] = {}

    class FakeTrace:
        def __init__(self, label: str) -> None:
            self.label = label

        def span(self, *, name: str, input=None, metadata=None):
            captured.setdefault("spans", []).append((name, input, metadata))
            return FakeTrace(name)

        def generation(self, *, name: str, model=None, input=None, metadata=None):
            captured.setdefault("generations", []).append(
                (name, model, input, metadata)
            )
            return FakeTrace(name)

        def update(self, **kwargs):
            captured.setdefault("updates", []).append(kwargs)

        def end(self, **kwargs):
            captured.setdefault("ends", []).append(kwargs)

        def record_exception(self, exc):
            captured.setdefault("exceptions", []).append(str(exc))

    class FakeLangfuse:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        def trace(self, **kwargs):
            captured["trace_kwargs"] = kwargs
            return FakeTrace(kwargs["name"])

        def flush(self):
            captured["flushed"] = True

    monkeypatch.setattr(
        observability_module.importlib,
        "import_module",
        lambda name: SimpleNamespace(Langfuse=FakeLangfuse),
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
        "host": "http://langfuse.local",
        "environment": "test",
    }
    assert captured["trace_kwargs"]["name"] == "agent_stream"
    assert captured["flushed"] is True
    assert captured["spans"]
    assert captured["exceptions"] == ["boom"]