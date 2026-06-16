from typing import Any, Literal

from pydantic import BaseModel, Field

from sim_atlas.agent.tools._errors import ToolError
from sim_atlas.models import ArtifactType, Filter, FunctionMetadata
from sim_atlas.storage_interface import StorageInterface

_SEARCH_NODES_DESCRIPTION_PARTS = (
    "Search the node catalog using natural language. ",
    "Returns a formatted list of matching nodes with their atlas_node_id, ",
    "port signatures, and a brief description.",
)
SEARCH_NODES_DESCRIPTION = "".join(_SEARCH_NODES_DESCRIPTION_PARTS)

_FIND_COMPATIBLE_DESCRIPTION_PARTS = (
    "Find nodes whose ports are compatible with a given port signature ",
    "(datatype, unit, quantity). ",
    "Use port_type='inputs' (default) to find nodes that can consume a specific output, ",
    "or port_type='outputs' to find nodes that produce a specific type of value. ",
    "Provide an optional query for semantic ranking on top of the port filter.",
)
FIND_COMPATIBLE_DESCRIPTION = "".join(_FIND_COMPATIBLE_DESCRIPTION_PARTS)

_GET_NODE_DETAILS_DESCRIPTION_PARTS = (
    "Retrieve the full details of a node from the catalog, including ",
    "the complete docstring and all port annotations. Use this when ",
    "you need deeper information about a specific node.",
)
GET_NODE_DETAILS_DESCRIPTION = "".join(_GET_NODE_DETAILS_DESCRIPTION_PARTS)


class PortMetadata(BaseModel):
    has_default_value: bool = False
    label: str | None = None
    datatype: str | None = None
    unit: str | None = None
    quantity: str | None = None
    description: str | None = None


class SearchNodeItem(BaseModel):
    atlas_node_id: str
    name: str
    short_description: str | None = None
    inputs: list[PortMetadata]
    outputs: list[PortMetadata]
    score: float | None = None


class SearchNodesInput(BaseModel):
    query: str = Field(
        description=(
            "Descriptive sentence or phrase explaining what the node should do, "
            "its scientific purpose, or the kind of data it processes. "
            "Use full words and domain terminology — for example "
            "'compute the gradient of a temperature field' or "
            "'load atomic structure from a file' rather than "
            "'get temperature' or 'structure loader'. "
            "Richer queries produce better results."
        )
    )


class SearchNodesResult(BaseModel):
    results: list[SearchNodeItem]


class FindCompatibleNodesInput(BaseModel):
    query: str | None = Field(
        default=None,
        description=(
            "Optional descriptive sentence explaining the scientific purpose "
            "or domain context to rank results semantically in addition to the port filter. "
            "Use full words and domain terminology rather than short keywords."
        ),
    )
    datatype: str | None = Field(
        default=None,
        description="Port datatype to match (e.g. 'float', 'int').",
    )
    unit: str | None = Field(
        default=None,
        description="Physical unit to match (e.g. 'K', 'eV').",
    )
    quantity: str | None = Field(
        default=None,
        description="Physical quantity to match (e.g. 'temperature').",
    )
    port_type: Literal["inputs", "outputs", "both"] = Field(
        default="inputs",
        description="Match on input ports (default), output ports, or both.",
    )


class FindCompatibleNodesResult(BaseModel):
    results: list[SearchNodeItem]


class GetNodeDetailsInput(BaseModel):
    atlas_node_id: str = Field(description="The Atlas node id (UUID) to look up.")


class GetNodeDetailsResult(BaseModel):
    atlas_node_id: str
    name: str
    docstring: str
    inputs: list[PortMetadata]
    outputs: list[PortMetadata]


def _to_short_description(brief_description: str | None, docstring: str) -> str | None:
    if brief_description:
        return brief_description
    lines = docstring.splitlines()
    return lines[0] if lines else None


def format_port(port: PortMetadata) -> str:
    line = port.label or "?"
    if port.datatype:
        line += f": {port.datatype}"
    annots = [x for x in [port.unit, port.quantity] if x]
    if annots:
        line += f" [{', '.join(annots)}]"
    if port.has_default_value:
        line += " (optional)"
    if port.description:
        line += f" — {port.description}"
    return line


def _format_item(
    index: int,
    atlas_node_id: str,
    name: str,
    description: str | None,
    inputs: list[PortMetadata],
    outputs: list[PortMetadata],
) -> str:
    header = f"[{index}] {name}\natlas_node_id: {atlas_node_id}"
    if description:
        header += f"\nSummary:\n{description}"
    parts = [header]
    if inputs:
        parts.append("Inputs:\n" + "\n".join(format_port(p) for p in inputs))
    if outputs:
        parts.append("Outputs:\n" + "\n".join(format_port(p) for p in outputs))
    return "\n\n".join(parts)


async def execute_search_nodes(
    args: SearchNodesInput,
    storage: StorageInterface,
    _scratch: Any,
) -> str:
    response = await storage.search_hybrid(
        args.query, Filter(artifact_type=[ArtifactType.FUNCTION]), limit=10
    )
    items = response.results.data
    if not items:
        return "Retrieved functions:\n\n(no results found)"
    entries = [
        _format_item(
            i,
            item.node.id,
            item.node.name,
            _to_short_description(
                item.node.brief_description or "", item.node.docstring
            ),
            [
                PortMetadata.model_validate(a.model_dump(exclude_none=True))
                for a in item.node.inputs
            ],
            [
                PortMetadata.model_validate(a.model_dump(exclude_none=True))
                for a in item.node.outputs
            ],
        )
        for i, item in enumerate(items, start=1)
        if isinstance(item.node, FunctionMetadata)
    ]
    return "Retrieved functions:\n\n" + "\n\n".join(entries)


async def execute_find_compatible_nodes(
    args: FindCompatibleNodesInput,
    storage: StorageInterface,
    _scratch: Any,
) -> str:
    f = Filter(
        artifact_type=[ArtifactType.FUNCTION],
        datatypes=[args.datatype] if args.datatype else None,
        units=[args.unit] if args.unit else None,
        quantities=[args.quantity] if args.quantity else None,
        port_type=args.port_type,
    )
    if args.query:
        response = await storage.search_semantic(args.query, f, limit=10)
    else:
        response = storage.search(query=None, filter=f, limit=10)
    items = response.results.data
    if not items:
        return "Retrieved functions:\n\n(no results found)"
    entries = [
        _format_item(
            i,
            item.node.id,
            item.node.name,
            _to_short_description(
                item.node.brief_description or "", item.node.docstring or ""
            ),
            [
                PortMetadata.model_validate(a.model_dump(exclude_none=True))
                for a in item.node.inputs
            ],
            [
                PortMetadata.model_validate(a.model_dump(exclude_none=True))
                for a in item.node.outputs
            ],
        )
        for i, item in enumerate(items, start=1)
        if isinstance(item.node, FunctionMetadata)
    ]
    return "Retrieved functions:\n\n" + "\n\n".join(entries)


async def execute_get_node_details(
    args: GetNodeDetailsInput,
    storage: StorageInterface,
    _scratch: Any,
) -> str:
    try:
        node = storage.read(args.atlas_node_id)
    except KeyError as exc:
        raise ToolError(f"Node '{args.atlas_node_id}' not found.") from exc
    if not isinstance(node, FunctionMetadata):
        raise ToolError(f"Node '{args.atlas_node_id}' is not a function node.")
    inputs = [
        PortMetadata.model_validate(a.model_dump(exclude_none=True))
        for a in node.inputs
    ]
    outputs = [
        PortMetadata.model_validate(a.model_dump(exclude_none=True))
        for a in node.outputs
    ]
    entry = _format_item(
        1,
        node.id,
        node.name,
        _to_short_description(node.brief_description or "", node.docstring),
        inputs,
        outputs,
    )
    return f"Node details:\n\n{entry}"
