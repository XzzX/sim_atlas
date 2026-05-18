import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, cast

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
)
from pydantic import ValidationError

from ..models import AgentRequest
from ..settings import load_settings
from ..storage_interface import StorageInterface
from ._observability import AgentObservability, build_agent_observability
from ._prompt import build_system_prompt
from ._sse import (
    ErrorEvent,
    GraphUpdateEvent,
    MessageEvent,
    ReasoningEvent,
    ToolCallEvent,
    ToolResultEvent,
    ValidationEvent,
    to_sse,
)
from .tools import TOOLS, ScratchGraph, ToolError, execute_tool, validate_graph

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _graph_update_event(scratch: ScratchGraph) -> GraphUpdateEvent:
    return GraphUpdateEvent(
        nodes=[n.model_dump(exclude_none=True) for n in scratch.nodes.values()],
        edges=[e.model_dump() for e in scratch.edges],
    )


def _snapshot_messages(
    messages: list[ChatCompletionMessageParam],
) -> list[dict[str, Any]]:
    return [cast(dict[str, Any], message) for message in messages]


async def run_agent_stream(
    request: AgentRequest,
    storage: StorageInterface,
    observability: AgentObservability | None = None,
) -> AsyncGenerator[str, None]:
    """Async generator that streams SSE events while running the agent loop."""
    settings = load_settings()
    assert settings.llm_api_key and settings.llm_api_url and settings.llm_chat_model
    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_url)
    observability = observability or build_agent_observability(settings)
    scratch = ScratchGraph(request.nodes, request.edges)

    history_messages: list[ChatCompletionMessageParam] = [
        cast(ChatCompletionMessageParam, {"role": m.role, "content": m.content})
        for m in request.history
    ]
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": build_system_prompt(request, storage)},
        *history_messages,
        {"role": "user", "content": request.query},
    ]

    trace = observability.start_trace(
        name="agent_stream",
        request=request,
        messages=_snapshot_messages(messages),
        metadata={
            "model": settings.llm_chat_model,
            "node_count": len(request.nodes),
            "edge_count": len(request.edges),
        },
    )

    final_message = "Done."
    max_iterations = 10
    try:
        for _ in range(max_iterations):
            generation = trace.generation(
                name="llm_completion",
                model=settings.llm_chat_model,
                input={"messages": _snapshot_messages(messages), "tools": TOOLS},
            )
            response = await client.chat.completions.create(
                model=settings.llm_chat_model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            choice = response.choices[0]
            logger.debug(
                "LLM response message: %s",
                json.dumps(choice.message.model_dump(exclude_unset=True), indent=2),
            )
            generation.update(output=choice.message.model_dump(exclude_unset=True))
            generation.end()
            messages.append(
                cast(
                    ChatCompletionMessageParam,
                    choice.message.model_dump(exclude_unset=True),
                )
            )

            if not choice.message.tool_calls:
                final_message = choice.message.content or "Done."
                validation_span = trace.span(
                    name="graph_validation",
                    input=_graph_update_event(scratch).model_dump(),
                )
                validation_errors = validate_graph(scratch, storage)
                validation_span.update(output={"errors": validation_errors})
                validation_span.end()
                if not validation_errors:
                    break
                # Emit a validation event so the UI can show a correction round.
                yield to_sse(ValidationEvent(errors=validation_errors))
                error_text = "\n".join(f"- {e}" for e in validation_errors)
                logger.debug(
                    "Graph validation errors (stream); asking agent to correct:\n%s",
                    error_text,
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The current graph has validation errors. "
                            "Please fix them using the available tools:\n" + error_text
                        ),
                    }
                )
                continue

            reasoning = (
                getattr(choice.message, "reasoning", None)
                or choice.message.content
                or None
            )
            if reasoning:
                yield to_sse(ReasoningEvent(content=reasoning))
            for tc in choice.message.tool_calls:
                if not isinstance(tc, ChatCompletionMessageToolCall):
                    continue
                args: dict[str, Any] = json.loads(tc.function.arguments)
                tool_span = trace.span(
                    name=f"tool:{tc.function.name}",
                    input=args,
                    metadata={"tool_call_id": tc.id},
                )
                yield to_sse(ToolCallEvent(name=tc.function.name, args=args))

                try:
                    result = await execute_tool(tc.function.name, args, storage, scratch)
                    content = result.model_dump_json()
                except ValidationError as exc:
                    content = json.dumps(
                        {"error": f"Invalid arguments for '{tc.function.name}': {exc}"}
                    )
                except ToolError as exc:
                    content = json.dumps({"error": str(exc)})

                yield to_sse(ToolResultEvent(name=tc.function.name, content=content))
                tool_span.update(output=content)
                tool_span.end()
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content,
                    }
                )
                trace.update(input={"request": request.model_dump(), "messages": _snapshot_messages(messages)})

            yield to_sse(_graph_update_event(scratch))

        trace.update(
            output={
                "message": final_message,
                "graph": _graph_update_event(scratch).model_dump(),
            }
        )
        trace.end()
        yield to_sse(MessageEvent(content=final_message))
        yield to_sse(_graph_update_event(scratch))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent stream error")
        trace.record_exception(exc)
        yield to_sse(ErrorEvent(message=str(exc)))
    finally:
        observability.flush()
