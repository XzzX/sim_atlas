from dataclasses import dataclass
from typing import Any

from openai.types.chat import ChatCompletionToolParam
from pydantic import BaseModel

from ...storage_interface import StorageInterface
from ._errors import ToolError
from ._graph import (
    ADD_EDGE_DESCRIPTION,
    ADD_FUNCTION_NODE_DESCRIPTION,
    ADD_INPUT_NODE_DESCRIPTION,
    ADD_OUTPUT_NODE_DESCRIPTION,
    REMOVE_EDGE_DESCRIPTION,
    REMOVE_NODE_DESCRIPTION,
    AddEdgeInput,
    AddEdgeResult,
    AddFunctionNodeInput,
    AddFunctionNodeResult,
    AddInputNodeInput,
    AddInputNodeResult,
    AddOutputNodeInput,
    AddOutputNodeResult,
    RemoveEdgeInput,
    RemoveEdgeResult,
    RemoveNodeInput,
    RemoveNodeResult,
    ScratchGraph,
    execute_add_edge,
    execute_add_function_node,
    execute_add_input_node,
    execute_add_output_node,
    execute_remove_edge,
    execute_remove_node,
    validate_graph,
)
from ._search import (
    FIND_COMPATIBLE_DESCRIPTION,
    GET_NODE_DETAILS_DESCRIPTION,
    SEARCH_NODES_DESCRIPTION,
    FindCompatibleNodesInput,
    FindCompatibleNodesResult,
    GetNodeDetailsInput,
    GetNodeDetailsResult,
    SearchNodesInput,
    SearchNodesResult,
    execute_find_compatible_nodes,
    execute_get_node_details,
    execute_search_nodes,
)

ExecutorFn = Any


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    prompt_guidance: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    executor: ExecutorFn


TOOL_REGISTRY: list[ToolDef] = [
    ToolDef(
        name="search_nodes",
        description=SEARCH_NODES_DESCRIPTION,
        prompt_guidance="Use search_nodes for intent-based discovery.",
        input_model=SearchNodesInput,
        output_model=SearchNodesResult,
        executor=execute_search_nodes,
    ),
    ToolDef(
        name="find_compatible_nodes",
        description=FIND_COMPATIBLE_DESCRIPTION,
        prompt_guidance=(
            "Use find_compatible_nodes when you know a specific port signature "
            "and want to find what connects to it."
        ),
        input_model=FindCompatibleNodesInput,
        output_model=FindCompatibleNodesResult,
        executor=execute_find_compatible_nodes,
    ),
    ToolDef(
        name="get_node_details",
        description=GET_NODE_DETAILS_DESCRIPTION,
        prompt_guidance=(
            "Use get_node_details when you need more information about a specific "
            "node before deciding."
        ),
        input_model=GetNodeDetailsInput,
        output_model=GetNodeDetailsResult,
        executor=execute_get_node_details,
    ),
    ToolDef(
        name="add_function_node",
        description=ADD_FUNCTION_NODE_DESCRIPTION,
        prompt_guidance=(
            "Use add_function_node to add a node from the catalog; it returns "
            "the assigned graph_id and port metadata — use that graph_id in "
            "subsequent add_edge calls."
        ),
        input_model=AddFunctionNodeInput,
        output_model=AddFunctionNodeResult,
        executor=execute_add_function_node,
    ),
    ToolDef(
        name="add_input_node",
        description=ADD_INPUT_NODE_DESCRIPTION,
        prompt_guidance=(
            "Use add_input_node to expose a parameter or data source. "
            "The single output port is always named 'output'."
        ),
        input_model=AddInputNodeInput,
        output_model=AddInputNodeResult,
        executor=execute_add_input_node,
    ),
    ToolDef(
        name="add_output_node",
        description=ADD_OUTPUT_NODE_DESCRIPTION,
        prompt_guidance=(
            "Use add_output_node to expose a result. "
            "The single input port is always named 'input'."
        ),
        input_model=AddOutputNodeInput,
        output_model=AddOutputNodeResult,
        executor=execute_add_output_node,
    ),
    ToolDef(
        name="add_edge",
        description=ADD_EDGE_DESCRIPTION,
        prompt_guidance=(
            "Use add_edge to connect nodes; verify port names using the port "
            "metadata returned by add_function_node or get_node_details."
        ),
        input_model=AddEdgeInput,
        output_model=AddEdgeResult,
        executor=execute_add_edge,
    ),
    ToolDef(
        name="remove_edge",
        description=REMOVE_EDGE_DESCRIPTION,
        prompt_guidance=(
            "Use remove_edge to disconnect two nodes by specifying all four "
            "endpoint identifiers."
        ),
        input_model=RemoveEdgeInput,
        output_model=RemoveEdgeResult,
        executor=execute_remove_edge,
    ),
    ToolDef(
        name="remove_node",
        description=REMOVE_NODE_DESCRIPTION,
        prompt_guidance=(
            "Use remove_node to delete an existing node and all its connected edges."
        ),
        input_model=RemoveNodeInput,
        output_model=RemoveNodeResult,
        executor=execute_remove_node,
    ),
]

_TOOL_MAP: dict[str, ToolDef] = {tool.name: tool for tool in TOOL_REGISTRY}


def _schema_from_input_model(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    return {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
    }


def _build_tools_list() -> list[ChatCompletionToolParam]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": _schema_from_input_model(tool.input_model),
            },
        }
        for tool in TOOL_REGISTRY
    ]


TOOLS: list[ChatCompletionToolParam] = _build_tools_list()


def get_tool_prompt_guidance_lines() -> list[str]:
    return [tool.prompt_guidance for tool in TOOL_REGISTRY]


async def execute_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    storage: StorageInterface,
    scratch: ScratchGraph,
) -> BaseModel:
    tool = _TOOL_MAP.get(tool_name)
    if tool is None:
        raise ToolError(f"Unknown tool '{tool_name}'.")

    validated_args = tool.input_model.model_validate(tool_args)
    result = await tool.executor(validated_args, storage, scratch)
    return result


__all__ = [
    "TOOL_REGISTRY",
    "TOOLS",
    "ScratchGraph",
    "ToolDef",
    "ToolError",
    "execute_tool",
    "get_tool_prompt_guidance_lines",
    "validate_graph",
]
