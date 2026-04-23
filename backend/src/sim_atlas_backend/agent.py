import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any, cast

from openai import AsyncOpenAI, OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionToolParam,
)

from .models import (
    AgentRequest,
    AgentResponse,
    Annotation,
    Filter,
    GraphEdgeContext,
    GraphNodeContext,
)
from .settings import settings
from .storage_interface import StorageInterface

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _slugify(text: str) -> str:
    """Convert a label into a filesystem-safe, LLM-readable id slug."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_") or "node"


class _ScratchGraph:
    def __init__(
        self, nodes: list[GraphNodeContext], edges: list[GraphEdgeContext]
    ) -> None:
        self.nodes: dict[str, GraphNodeContext] = {n.graph_id: n for n in nodes}
        self.edges: list[GraphEdgeContext] = list(edges)

    def new_graph_id(self, label: str) -> str:
        """Return a unique, human-readable id derived from *label*."""
        base = _slugify(label)
        if base not in self.nodes:
            return base
        i = 2
        while f"{base}_{i}" in self.nodes:
            i += 1
        return f"{base}_{i}"


_TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "search_nodes",
            "description": (
                "Search the node catalog using natural language. "
                "Returns a list of nodes with their id, name, port metadata, "
                "and a short description."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description of the node to find.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5).",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_compatible_nodes",
            "description": (
                "Find nodes whose input ports are compatible with a given port "
                "signature (datatype, unit, quantity). Use this to discover nodes "
                "that can consume a specific output."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "datatype": {
                        "type": "string",
                        "description": "Port datatype to match (e.g. 'float', 'int').",
                    },
                    "unit": {
                        "type": "string",
                        "description": "Physical unit to match (e.g. 'K', 'eV').",
                    },
                    "quantity": {
                        "type": "string",
                        "description": "Physical quantity to match (e.g. 'temperature').",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5).",
                        "default": 5,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_node_details",
            "description": (
                "Retrieve the full details of a node from the catalog, including "
                "the complete docstring and all port annotations. Use this when "
                "you need deeper information about a specific node."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "atlas_node_id": {
                        "type": "string",
                        "description": "The Atlas node id (SHA256 hash) to look up.",
                    },
                },
                "required": ["atlas_node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_function_node",
            "description": (
                "Add a function node from the catalog to the graph. "
                "Returns the assigned graph_id and the node's port metadata."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "atlas_node_id": {
                        "type": "string",
                        "description": "The Atlas node id (SHA256 hash) to add.",
                    },
                    "label": {
                        "type": "string",
                        "description": "Display label for the node in the graph.",
                    },
                },
                "required": ["atlas_node_id", "label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_input_node",
            "description": "Add an input port node to the graph. Returns the assigned graph_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "Name of the input parameter.",
                    },
                    "value": {
                        "type": "string",
                        "description": "Default value for the input.",
                        "default": "",
                    },
                },
                "required": ["label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_output_node",
            "description": "Add an output port node to the graph. Returns the assigned graph_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "Name of the output.",
                    },
                },
                "required": ["label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_edge",
            "description": "Connect two nodes in the graph via their ports.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_graph_id": {
                        "type": "string",
                        "description": "graph_id of the source node.",
                    },
                    "source_handle": {
                        "type": "string",
                        "description": "Name of the output port on the source node.",
                    },
                    "target_graph_id": {
                        "type": "string",
                        "description": "graph_id of the target node.",
                    },
                    "target_handle": {
                        "type": "string",
                        "description": "Name of the input port on the target node.",
                    },
                },
                "required": [
                    "source_graph_id",
                    "source_handle",
                    "target_graph_id",
                    "target_handle",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_node",
            "description": (
                "Remove a node from the graph by its graph_id. "
                "Also removes all edges connected to that node."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "graph_id": {
                        "type": "string",
                        "description": "The graph_id of the node to remove.",
                    },
                },
                "required": ["graph_id"],
            },
        },
    },
]


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
    atlas = f" (atlas_id={node.atlas_node_id})" if node.atlas_node_id else ""
    return f"  [{node.graph_id}] {node.name}{atlas}{desc}\n    in: {inputs}\n    out: {outputs}"


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


def _handle_add_node(
    tool_name: str,
    tool_args: dict[str, Any],
    storage: StorageInterface,
    scratch: _ScratchGraph,
) -> str:
    if tool_name == "add_function_node":
        atlas_node_id: str = tool_args["atlas_node_id"]
        label: str = tool_args["label"]
        if not storage.exists(atlas_node_id):
            return json.dumps(
                {"error": f"Node '{atlas_node_id}' not found in catalog."}
            )
        node = storage.read(atlas_node_id)
        graph_id = scratch.new_graph_id(label)
        scratch.nodes[graph_id] = GraphNodeContext(
            graph_id=graph_id,
            atlas_node_id=atlas_node_id,
            name=label,
            short_description=node.ai_docstring.splitlines()[0]
            if node.ai_docstring
            else node.docstring.splitlines()[0]
            if node.docstring
            else None,
            inputs=node.inputs,
            outputs=node.outputs,
        )
        return json.dumps(
            {
                "graph_id": graph_id,
                "inputs": [a.model_dump(exclude_none=True) for a in node.inputs],
                "outputs": [a.model_dump(exclude_none=True) for a in node.outputs],
            }
        )

    if tool_name == "add_input_node":
        label_in: str = tool_args["label"]
        graph_id = scratch.new_graph_id(label_in)
        scratch.nodes[graph_id] = GraphNodeContext(
            graph_id=graph_id,
            atlas_node_id=None,
            name=label_in,
            inputs=[],
            outputs=[Annotation(label=label_in)],
        )
        return json.dumps({"graph_id": graph_id})

    # add_output_node
    label_out: str = tool_args["label"]
    graph_id = scratch.new_graph_id(label_out)
    scratch.nodes[graph_id] = GraphNodeContext(
        graph_id=graph_id,
        atlas_node_id=None,
        name=label_out,
        inputs=[Annotation(label=label_out)],
        outputs=[],
    )
    return json.dumps({"graph_id": graph_id})


def _handle_graph_ops(
    tool_name: str, tool_args: dict[str, Any], scratch: _ScratchGraph
) -> str:
    if tool_name == "add_edge":
        source_graph_id: str = tool_args["source_graph_id"]
        source_handle: str = tool_args["source_handle"]
        target_graph_id: str = tool_args["target_graph_id"]
        target_handle: str = tool_args["target_handle"]
        if source_graph_id not in scratch.nodes:
            return json.dumps(
                {"error": f"Source node '{source_graph_id}' not in graph."}
            )
        if target_graph_id not in scratch.nodes:
            return json.dumps(
                {"error": f"Target node '{target_graph_id}' not in graph."}
            )
        scratch.edges.append(
            GraphEdgeContext(
                source_graph_id=source_graph_id,
                source_handle=source_handle,
                target_graph_id=target_graph_id,
                target_handle=target_handle,
            )
        )
        return json.dumps({"ok": True})

    # remove_node
    graph_id_to_remove: str = tool_args["graph_id"]
    if graph_id_to_remove not in scratch.nodes:
        return json.dumps({"error": f"Node '{graph_id_to_remove}' not in graph."})
    del scratch.nodes[graph_id_to_remove]
    scratch.edges = [
        e
        for e in scratch.edges
        if graph_id_to_remove not in {e.source_graph_id, e.target_graph_id}
    ]
    return json.dumps({"ok": True})


_ADD_NODE_TOOLS = {"add_function_node", "add_input_node", "add_output_node"}


def _execute_graph_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    storage: StorageInterface,
    scratch: _ScratchGraph,
) -> str:
    if tool_name in _ADD_NODE_TOOLS:
        return _handle_add_node(tool_name, tool_args, storage, scratch)
    return _handle_graph_ops(tool_name, tool_args, scratch)


_SEARCH_TOOLS = {"search_nodes", "find_compatible_nodes", "get_node_details"}


def _execute_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    storage: StorageInterface,
    scratch: _ScratchGraph,
) -> str:
    if tool_name in _SEARCH_TOOLS:
        return _execute_search_tool(tool_name, tool_args, storage)
    return _execute_graph_tool(tool_name, tool_args, storage, scratch)


def run_agent(request: AgentRequest, storage: StorageInterface) -> AgentResponse:
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_url)
    scratch = _ScratchGraph(request.nodes, request.edges)

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _build_system_prompt(request)},
        {"role": "user", "content": request.query},
    ]

    final_message = "Done."
    max_iterations = 10
    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model=settings.llm_chat_model,
            messages=messages,
            tools=_TOOLS,
            tool_choice="auto",
        )

        choice = response.choices[0]
        messages.append(
            cast(
                ChatCompletionMessageParam,
                choice.message.model_dump(exclude_unset=True),
            )
        )
        print(
            f"LLM response:\n{json.dumps(choice.message.model_dump(exclude_unset=True), indent=2)}"
        )

        if not choice.message.tool_calls:
            final_message = choice.message.content or "Done."
            break

        for tc in choice.message.tool_calls:
            if not isinstance(tc, ChatCompletionMessageToolCall):
                continue
            args: dict[str, Any] = json.loads(tc.function.arguments)
            logger.debug("Tool call: %s(%s)", tc.function.name, args)
            result = _execute_tool(tc.function.name, args, storage, scratch)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    return AgentResponse(
        nodes=list(scratch.nodes.values()),
        edges=scratch.edges,
        message=final_message,
    )


_TOOL_SUMMARIES: dict[str, str] = {
    "add_edge": "Connected",
    "remove_node": "Removed",
}

_SEARCH_TOOL_NAMES = {"search_nodes", "find_compatible_nodes"}
_ADD_NODE_TOOL_NAMES = {"add_function_node", "add_input_node", "add_output_node"}


def _tool_summary(tool_name: str, result_json: str) -> str:  # noqa: PLR0911
    """Return a short human-readable summary of a tool result."""
    try:
        raw: Any = json.loads(result_json)
    except json.JSONDecodeError:
        return result_json[:120]
    if not isinstance(raw, (dict, list)):
        return "Done"
    if isinstance(raw, dict) and "error" in raw:
        err_raw = cast(dict[str, Any], raw)
        return f"Error: {err_raw.get('error', '?')}"
    if tool_name in _SEARCH_TOOL_NAMES:
        data_list = cast(list[Any], raw) if isinstance(raw, list) else []
        items = [
            f"{cast(dict[str, Any], r).get('score', '?')}: {cast(dict[str, Any], r).get('name', '?')}"
            for r in data_list
            if isinstance(r, dict)
        ]
        return "\n".join(items) if items else "No results"
    if tool_name == "get_node_details" and isinstance(raw, dict):
        data_dict = cast(dict[str, Any], raw)
        return f"Retrieved details for {data_dict.get('name', '?')}"
    if tool_name in _ADD_NODE_TOOL_NAMES and isinstance(raw, dict):
        data_dict = cast(dict[str, Any], raw)
        return f"Added as {data_dict.get('graph_id', '?')}"
    return _TOOL_SUMMARIES.get(tool_name, "Done")


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

    def _sse(event: dict[str, Any]) -> str:
        return f"data: {json.dumps(event)}\n\n"

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
                break

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
