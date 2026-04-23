import json
from typing import Any, cast

from openai.types.chat import ChatCompletionToolParam

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
    {
        "type": "function",
        "function": {
            "name": "remove_edge",
            "description": "Remove an edge from the graph by matching all four of its endpoint identifiers.",
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
]

_TOOL_SUMMARIES: dict[str, str] = {
    "add_edge": "Connected",
    "remove_edge": "Edge removed",
    "remove_node": "Node removed",
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
