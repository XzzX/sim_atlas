import json
from typing import Any, cast

from openai.types.chat import ChatCompletionToolParam

TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "search_nodes",
            "description": (
                "Search the node catalog using natural language. "
                "Returns a list of nodes with their id, name, port metadata, "
                "and a short description. "
                "Optionally narrow results by port attributes (datatypes, units, quantities), "
                "keywords, or port_type to restrict matching to input or output ports."
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
                        "description": "Maximum number of results to return (default 10).",
                        "default": 10,
                    },
                    "datatypes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Restrict to nodes that have ports with these datatypes (e.g. ['float', 'int']).",
                    },
                    "units": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Restrict to nodes that have ports with these physical units (e.g. ['K', 'eV']).",
                    },
                    "quantities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Restrict to nodes that have ports with these physical quantities (e.g. ['temperature']).",
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Restrict to nodes tagged with these keywords.",
                    },
                    "port_type": {
                        "type": "string",
                        "enum": ["inputs", "outputs", "both"],
                        "description": "Whether port filters apply to input ports, output ports, or both (default both).",
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
                "Find nodes whose ports are compatible with a given port signature "
                "(datatype, unit, quantity). "
                "Use port_type='inputs' (default) to find nodes that can consume a specific output, "
                "or port_type='outputs' to find nodes that produce a specific type of value. "
                "Provide an optional query for semantic ranking on top of the port filter."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional natural language description to rank results semantically in addition to the port filter.",
                    },
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
                    "port_type": {
                        "type": "string",
                        "enum": ["inputs", "outputs", "both"],
                        "description": "Match on input ports (default), output ports, or both.",
                        "default": "inputs",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 10).",
                        "default": 10,
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
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": (
                "Pause the current task and ask the user a clarifying question. "
                "Use this when the request is ambiguous and you cannot make a reasonable "
                "default choice without risking wasted work. "
                "Provide an optional list of suggested answers the user can pick from. "
                "The agent loop will stop after this call; the user's reply will arrive as "
                "the next message in the conversation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The clarifying question to ask the user.",
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of suggested answers to present as clickable choices.",
                    },
                },
                "required": ["question"],
            },
        },
    },
]

_TOOL_SUMMARIES: dict[str, str] = {
    "add_edge": "Connected",
    "remove_edge": "Edge removed",
    "remove_node": "Node removed",
    "ask_clarification": "Awaiting user reply",
}

_SEARCH_TOOL_NAMES = {"search_nodes", "find_compatible_nodes"}
_ADD_NODE_TOOL_NAMES = {"add_function_node", "add_input_node", "add_output_node"}


def tool_summary(tool_name: str, result_json: str) -> str:  # noqa: PLR0911
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
