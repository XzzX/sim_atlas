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
    summary: str


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


Event = (
    ReasoningEvent
    | ToolCallEvent
    | ToolResultEvent
    | MessageEvent
    | ClarificationEvent
    | ValidationEvent
    | ErrorEvent
    | GraphUpdateEvent
)


def to_sse(event: Event) -> str:
    """Format an event payload as an SSE data frame."""
    return f"data: {event.model_dump_json()}\n\n"
