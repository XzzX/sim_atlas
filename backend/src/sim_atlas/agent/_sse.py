import asyncio
import contextlib
from collections.abc import AsyncGenerator
from typing import Any, Literal

from pydantic import BaseModel


class ReasoningEvent(BaseModel):
    type: Literal["reasoning"] = "reasoning"
    content: str


class ToolCallEvent(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    name: str
    args: dict[str, Any]


class ToolResultEvent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    name: str
    content: str


class MessageEvent(BaseModel):
    type: Literal["message"] = "message"
    content: str


class ClarificationEvent(BaseModel):
    type: Literal["clarification"] = "clarification"
    question: str
    options: list[str]


class ValidationEvent(BaseModel):
    type: Literal["validation"] = "validation"
    errors: list[str]


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


class GraphUpdateEvent(BaseModel):
    type: Literal["graph_update"] = "graph_update"
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class TruncatedEvent(BaseModel):
    """Emitted when the runaway-check loop exhausts all turns without natural completion."""

    type: Literal["truncated"] = "truncated"


Event = (
    ReasoningEvent
    | ToolCallEvent
    | ToolResultEvent
    | MessageEvent
    | ClarificationEvent
    | ValidationEvent
    | ErrorEvent
    | GraphUpdateEvent
    | TruncatedEvent
)


def to_sse(event: Event) -> str:
    """Format an event payload as an SSE data frame."""
    return f"data: {event.model_dump_json()}\n\n"


KEEPALIVE_INTERVAL_SECONDS = 15.0

# An SSE comment frame: valid per the spec and ignored by conformant clients,
# but real bytes on the wire.
_KEEPALIVE_FRAME = ": keep-alive\n\n"


async def with_keepalive(
    events: AsyncGenerator[str, None],
    interval: float = KEEPALIVE_INTERVAL_SECONDS,
) -> AsyncGenerator[str, None]:
    """Interleave keep-alive frames into `events` whenever it goes quiet.

    The agent runs non-streaming completions, so it emits nothing at all while a
    turn is in flight. A reverse proxy sees only an idle connection and closes it
    once its read timeout expires (nginx defaults to 60s) — and because the
    response headers were flushed before the first event, it cannot report that
    as an error status. It resets the stream instead, which the browser surfaces
    as ERR_HTTP2_PROTOCOL_ERROR.

    Each `anext(events)` runs in its own Task, and a Task copies its context
    from the caller at creation time rather than from whatever the previous Task
    left behind. Left alone, that drops any contextvars `events` sets on itself
    (Langfuse's session/user propagation among them) after the first chunk. So
    the context each Task finishes in is captured and handed to the next one,
    carrying those mutations forward chunk to chunk.
    """
    loop = asyncio.get_running_loop()
    pending = loop.create_task(anext(events))
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=interval)
            if not done:
                yield _KEEPALIVE_FRAME
                continue
            try:
                chunk = pending.result()
            except StopAsyncIteration:
                return
            # Read the result before yielding, so that a throw() or close() at
            # the yield below cannot be mistaken for the inner generator ending.
            ctx = pending.get_context()
            yield chunk
            pending = loop.create_task(anext(events), context=ctx)
    finally:
        pending.cancel()
        # aclose() on a generator with an in-flight asend() raises RuntimeError,
        # so let the cancellation land before closing.
        with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
            await pending
        await events.aclose()
