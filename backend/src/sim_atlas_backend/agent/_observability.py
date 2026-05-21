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
        level: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceHandle: ...

    def generation(
        self,
        *,
        name: str,
        model: str | None = None,
        input: Any | None = None,
        level: str | None = None,
        model_parameters: dict[str, Any] | None = None,
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
        session_id: str,
        request: AgentRequest,
        messages: list[dict[str, Any]],
        user_id: str | None = None,
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
        level: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _NoopTrace:
        return self

    def generation(
        self,
        *,
        name: str,
        model: str | None = None,
        input: Any | None = None,
        level: str | None = None,
        model_parameters: dict[str, Any] | None = None,
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
        session_id: str,
        request: AgentRequest,
        messages: list[dict[str, Any]],
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _NoopTrace:
        return _NoopTrace()

    def flush(self) -> None:
        return None


class _LangfuseTrace:
    def __init__(self, handle: Any, propagate_ctx: Any | None = None) -> None:
        self._handle = handle
        self._propagate_ctx = propagate_ctx

    def span(
        self,
        *,
        name: str,
        input: Any | None = None,
        level: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _LangfuseTrace:
        child = self._handle.start_observation(
            name=name,
            as_type="span",
            input=input,
            metadata=metadata,
            **({} if level is None else {"level": level}),
        )
        return _LangfuseTrace(child)

    def generation(
        self,
        *,
        name: str,
        model: str | None = None,
        input: Any | None = None,
        level: str | None = None,
        model_parameters: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _LangfuseTrace:
        child = self._handle.start_observation(
            name=name,
            as_type="generation",
            model=model,
            input=input,
            metadata=metadata,
            **({} if level is None else {"level": level}),
            **(
                {}
                if model_parameters is None
                else {"model_parameters": model_parameters}
            ),
        )
        return _LangfuseTrace(child)

    def update(self, **kwargs: Any) -> None:
        self._handle.update(**kwargs)

    def end(self, **kwargs: Any) -> None:
        self._handle.end(**kwargs)
        if self._propagate_ctx is not None:
            self._propagate_ctx.__exit__(None, None, None)
            self._propagate_ctx = None

    def record_exception(self, exc: BaseException) -> None:
        self._handle.update(level="ERROR", status_message=str(exc))
        self.end()


class _LangfuseObservability:
    def __init__(self, client: Any, propagate_attributes: Any) -> None:
        self._client = client
        self._propagate_attributes = propagate_attributes

    def start_trace(
        self,
        *,
        name: str,
        session_id: str,
        request: AgentRequest,
        messages: list[dict[str, Any]],
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _LangfuseTrace:
        ctx = self._propagate_attributes(
            session_id=session_id,
            **({} if user_id is None else {"user_id": user_id}),
        )
        ctx.__enter__()
        obs = self._client.start_observation(
            name=name,
            input={"request": request.model_dump(), "messages": messages},
            metadata=metadata or {},
        )
        return _LangfuseTrace(obs, ctx)

    def flush(self) -> None:
        self._client.flush()


def build_agent_observability(settings: Settings) -> AgentObservability:
    if not settings.langfuse_enabled:
        return _NoopObservability()

    result = _get_langfuse_client(
        settings.langfuse_public_key,
        settings.langfuse_secret_key,
        settings.langfuse_host,
        settings.langfuse_environment,
    )
    if result is None:
        return _NoopObservability()
    client, propagate_attributes = result
    return _LangfuseObservability(client, propagate_attributes)


@lru_cache(maxsize=1)
def _get_langfuse_client(
    public_key: str | None,
    secret_key: str | None,
    base_url: str | None,
    environment: str | None,
) -> tuple[Any, Any] | None:
    try:
        langfuse_module = importlib.import_module("langfuse")
    except ImportError:
        logger.warning(
            "Langfuse is configured but the SDK is not installed; tracing is disabled."
        )
        return None

    client_class = getattr(langfuse_module, "Langfuse", None)
    if client_class is None:
        logger.warning("Langfuse SDK does not expose Langfuse; tracing is disabled.")
        return None

    propagate_attributes = getattr(langfuse_module, "propagate_attributes", None)
    if propagate_attributes is None:
        logger.warning(
            "Langfuse SDK does not expose propagate_attributes; tracing is disabled."
        )
        return None

    client = client_class(
        public_key=public_key,
        secret_key=secret_key,
        base_url=base_url,
        environment=environment,
    )
    return client, propagate_attributes
