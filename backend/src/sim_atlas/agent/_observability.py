"""Observability shim — real Langfuse when installed, no-ops otherwise."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any


class _NoopSpan:
    def update(self, **_: Any) -> None:
        pass

    def __enter__(self) -> _NoopSpan:
        return self

    def __exit__(self, *_: object) -> None:
        pass


class _NoopLangfuse:
    def __init__(self, **_: Any) -> None:
        pass

    def start_as_current_observation(self, **_: Any) -> _NoopSpan:
        return _NoopSpan()

    def flush(self) -> None:
        pass


@contextmanager
def _noop_propagate_attributes(**_: Any) -> Generator[None, None, None]:
    yield


_NOOP_CLIENT = _NoopLangfuse()


def _noop_get_client() -> _NoopLangfuse:
    return _NOOP_CLIENT


try:
    from langfuse import Langfuse, get_client, propagate_attributes
    from langfuse.openai import AsyncOpenAI
except ImportError:
    Langfuse = _NoopLangfuse
    propagate_attributes = _noop_propagate_attributes
    get_client = _noop_get_client
    from openai import AsyncOpenAI


__all__ = ["AsyncOpenAI", "Langfuse", "get_client", "propagate_attributes"]
