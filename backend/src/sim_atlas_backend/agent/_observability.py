from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from ..models import AgentRequest
from ..settings import Settings

logger = logging.getLogger(__name__)


class TraceHandle(Protocol):
    def span(
        self,
        *,
        name: str,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceHandle: ...

    def generation(
        self,
        *,
        name: str,
        model: str | None = None,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceHandle: ...

    def update(self, **kwargs: Any) -> None: ...

    def end(self, **kwargs: Any) -> None: ...

    def record_exception(self, exc: BaseException) -> None: ...


class AgentObservability(Protocol):
    def start_trace(
        self,
        *,
        name: str,
        request: AgentRequest,
        messages: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> TraceHandle: ...

    def flush(self) -> None: ...


@dataclass
class _NoopTrace:
    def span(
        self,
        *,
        name: str,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _NoopTrace:
        return self

    def generation(
        self,
        *,
        name: str,
        model: str | None = None,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _NoopTrace:
        return self

    def update(self, **kwargs: Any) -> None:
        return None

    def end(self, **kwargs: Any) -> None:
        return None

    def record_exception(self, exc: BaseException) -> None:
        return None


class _NoopObservability:
    def start_trace(
        self,
        *,
        name: str,
        request: AgentRequest,
        messages: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> _NoopTrace:
        return _NoopTrace()

    def flush(self) -> None:
        return None


@dataclass
class _LangfuseTrace:
    handle: Any

    def span(
        self,
        *,
        name: str,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _LangfuseTrace:
        child = self.handle.span(name=name, input=input, metadata=metadata)
        return _LangfuseTrace(child)

    def generation(
        self,
        *,
        name: str,
        model: str | None = None,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _LangfuseTrace:
        child = self.handle.generation(
            name=name,
            model=model,
            input=input,
            metadata=metadata,
        )
        return _LangfuseTrace(child)

    def update(self, **kwargs: Any) -> None:
        if hasattr(self.handle, "update"):
            self.handle.update(**kwargs)

    def end(self, **kwargs: Any) -> None:
        if hasattr(self.handle, "end"):
            self.handle.end(**kwargs)

    def record_exception(self, exc: BaseException) -> None:
        if hasattr(self.handle, "record_exception"):
            self.handle.record_exception(exc)
        else:
            self.update(
                metadata={
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                }
            )
        self.end()


class _LangfuseObservability:
    def __init__(self, client: Any) -> None:
        self._client = client

    def start_trace(
        self,
        *,
        name: str,
        request: AgentRequest,
        messages: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> _LangfuseTrace:
        trace = self._client.trace(
            name=name,
            input={"request": request.model_dump(), "messages": messages},
            metadata=metadata,
        )
        return _LangfuseTrace(trace)

    def flush(self) -> None:
        if hasattr(self._client, "flush"):
            self._client.flush()
        elif hasattr(self._client, "shutdown"):
            self._client.shutdown()


def build_agent_observability(settings: Settings) -> AgentObservability:
    if not settings.langfuse_enabled:
        return _NoopObservability()

    client = _get_langfuse_client(
        settings.langfuse_public_key,
        settings.langfuse_secret_key,
        settings.langfuse_host,
        settings.langfuse_environment,
    )
    if client is None:
        return _NoopObservability()
    return _LangfuseObservability(client)


@lru_cache(maxsize=1)
def _get_langfuse_client(
    public_key: str | None,
    secret_key: str | None,
    host: str | None,
    environment: str | None,
) -> Any | None:
    try:
        langfuse_module = importlib.import_module("langfuse")
    except ImportError:
        logger.warning(
            "Langfuse is configured but the SDK is not installed; tracing is disabled."
        )
        return None

    client_class = getattr(langfuse_module, "Langfuse", None)
    if client_class is None:
        logger.warning(
            "Langfuse is configured but the SDK does not expose Langfuse; tracing is disabled."
        )
        return None

    return client_class(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
        environment=environment,
    )
