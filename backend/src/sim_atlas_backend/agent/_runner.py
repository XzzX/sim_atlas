import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, cast

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
)

from ..models import AgentRequest, Filter, GraphNodeContext
from ..settings import settings
from ..storage_interface import StorageInterface
from ._graph import _ScratchGraph, _execute_graph_tool, _validate_graph
from ._tools import _TOOLS, _tool_summary

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_SEARCH_TOOLS = {"search_nodes", "find_compatible_nodes", "get_node_details"}


def _node_to_context(node: GraphNodeContext) -> str:
    inputs = ", ".join(
        f"{a.label}:{a.datatype or '?'}"
        + (f"[{a.unit}]" if a.unit else "")
        + (f"({a.quantity})" if a.quantity else "")
        for a in node.inputs
    )
    outputs = ", ".join(
        f"{a.label}:{a.datatype or '?'}"
        + (f"[{a.unit}]" if a.unit else "")
        + (f"({a.quantity})" if a.quantity else "")
        for a in node.outputs
    )
    desc = f" — {node.short_description}" if node.short_description else ""
    atlas = f" (atlas_id={node.atlas_node_id})" if node.node_kind == "function" else ""
    return f"  [{node.node_kind}:{node.graph_id}] {node.name}{atlas}{desc}\n    in: {inputs}\n    out: {outputs}"


def _build_system_prompt(request: AgentRequest) -> str:
    node_lines = "\n".join(_node_to_context(n) for n in request.nodes)
    edge_lines = "\n".join(
        f"  {e.source_graph_id}/{e.source_handle} → {e.target_graph_id}/{e.target_handle}"
        for e in request.edges
    )
    return f"""You are an expert workflow builder for scientific simulation pipelines.
You have access to a catalog of simulation nodes (functions) that can be searched and connected.

## Current graph

### Nodes
{node_lines or "  (empty)"}

### Edges
{edge_lines or "  (none)"}

## Your role
You are an editor of an existing workflow graph.
Treat the current graph as intentional work that should be preserved unless change is necessary.
Make the minimum changes needed to satisfy the user's request.
Prefer adding new nodes and edges over modifying or removing existing ones.
Only remove or rewire existing nodes when the user explicitly asks, or when it is genuinely necessary to produce a correct result.

## Tools
- Use search_nodes for intent-based discovery.
- Use find_compatible_nodes when you know a specific port signature and want to find what connects to it.
- Use get_node_details when you need more information about a specific node before deciding.
- Use add_function_node to add a node from the catalog; it returns the assigned graph_id and port metadata — use that graph_id in subsequent add_edge calls.
- Use add_input_node to expose a parameter or data source. Provide a default value when appropriate. The single output port is always named 'output'. There are no input ports.
- Use add_output_node to expose a result. The single input port is always named 'input'. There are no output ports.
- Use add_edge to connect nodes; verify port names using the port metadata returned by add_function_node or get_node_details.
- Use remove_edge to disconnect two nodes by specifying all four endpoint identifiers (source_graph_id, source_handle, target_graph_id, target_handle).
- Use remove_node to delete an existing node (also removes its connected edges).
- When you are finished, respond with a concise summary of only the changes you made.
"""


def _execute_search_tool(
    tool_name: str, tool_args: dict[str, Any], storage: StorageInterface
) -> str:
    if tool_name == "search_nodes":
        query: str = tool_args["query"]
        limit: int = tool_args.get("limit", 5)
        response = storage.search_semantic(query, limit=limit)
        results = [
            {
                "atlas_node_id": item.node.id,
                "name": item.node.name,
                "short_description": item.node.ai_docstring.splitlines()[0]
                if item.node.ai_docstring
                else item.node.docstring.splitlines()[0]
                if item.node.docstring
                else None,
                "inputs": [a.model_dump(exclude_none=True) for a in item.node.inputs],
                "outputs": [a.model_dump(exclude_none=True) for a in item.node.outputs],
                "score": round(item.score, 4),
            }
            for item in response.results.data
        ]
        return json.dumps(results)

    if tool_name == "find_compatible_nodes":
        datatype: str | None = tool_args.get("datatype")
        unit: str | None = tool_args.get("unit")
        quantity: str | None = tool_args.get("quantity")
        limit: int = tool_args.get("limit", 5)
        f = Filter(
            datatypes=[datatype] if datatype else None,
            units=[unit] if unit else None,
            quantities=[quantity] if quantity else None,
        )
        response = storage.search(query=None, filter=f, limit=limit)
        results = [
            {
                "atlas_node_id": item.node.id,
                "name": item.node.name,
                "short_description": item.node.ai_docstring.splitlines()[0]
                if item.node.ai_docstring
                else item.node.docstring.splitlines()[0]
                if item.node.docstring
                else None,
                "inputs": [a.model_dump(exclude_none=True) for a in item.node.inputs],
                "outputs": [a.model_dump(exclude_none=True) for a in item.node.outputs],
            }
            for item in response.results.data
        ]
        return json.dumps(results)

    # get_node_details
    atlas_node_id: str = tool_args["atlas_node_id"]
    try:
        node = storage.read(atlas_node_id)
    except KeyError:
        return json.dumps({"error": f"Node '{atlas_node_id}' not found."})
    return json.dumps(
        {
            "atlas_node_id": node.id,
            "name": node.name,
            "docstring": node.ai_docstring or node.docstring,
            "inputs": [a.model_dump(exclude_none=True) for a in node.inputs],
            "outputs": [a.model_dump(exclude_none=True) for a in node.outputs],
        }
    )


def _execute_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    storage: StorageInterface,
    scratch: _ScratchGraph,
) -> str:
    if tool_name in _SEARCH_TOOLS:
        return _execute_search_tool(tool_name, tool_args, storage)
    return _execute_graph_tool(tool_name, tool_args, storage, scratch)


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def run_agent_stream(
    request: AgentRequest, storage: StorageInterface
) -> AsyncGenerator[str, None]:
    """Async generator that streams SSE events while running the agent loop."""
    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_url)
    scratch = _ScratchGraph(request.nodes, request.edges)

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _build_system_prompt(request)},
        {"role": "user", "content": request.query},
    ]

    final_message = "Done."
    max_iterations = 10
    try:
        for _ in range(max_iterations):
            response = await client.chat.completions.create(
                model=settings.llm_chat_model,
                messages=messages,
                tools=_TOOLS,
                tool_choice="auto",
            )
            choice = response.choices[0]
            print(
                f"response:\n{json.dumps(choice.message.model_dump(exclude_unset=True), indent=2)}"
            )
            messages.append(
                cast(
                    ChatCompletionMessageParam,
                    choice.message.model_dump(exclude_unset=True),
                )
            )

            if not choice.message.tool_calls:
                final_message = choice.message.content or "Done."
                validation_errors = _validate_graph(scratch, storage)
                if not validation_errors:
                    break
                # Emit a validation event so the UI can show a correction round.
                yield _sse({"type": "validation", "errors": validation_errors})
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
                yield _sse({"type": "reasoning", "content": reasoning})
            for tc in choice.message.tool_calls:
                if not isinstance(tc, ChatCompletionMessageToolCall):
                    continue
                args: dict[str, Any] = json.loads(tc.function.arguments)
                yield _sse(
                    {"type": "tool_call", "name": tc.function.name, "args": args}
                )
                result = _execute_tool(tc.function.name, args, storage, scratch)
                summary = _tool_summary(tc.function.name, result)
                yield _sse(
                    {
                        "type": "tool_result",
                        "name": tc.function.name,
                        "summary": summary,
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        yield _sse({"type": "message", "content": final_message})
        yield _sse(
            {
                "type": "done",
                "nodes": [
                    n.model_dump(exclude_none=True) for n in scratch.nodes.values()
                ],
                "edges": [e.model_dump() for e in scratch.edges],
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent stream error")
        yield _sse({"type": "error", "message": str(exc)})
