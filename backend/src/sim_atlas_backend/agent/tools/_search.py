from typing import Any, Literal

from pydantic import BaseModel, Field

from ...models import Filter
from ...storage_interface import StorageInterface
from ._errors import ToolError

_SEARCH_NODES_DESCRIPTION_PARTS = (
    "Search the node catalog using natural language. ",
    "Returns a list of nodes with their id, name, port metadata, and a short description. ",
    "Optionally narrow results by port attributes (datatypes, units, quantities), ",
    "keywords, or port_type to restrict matching to input or output ports.",
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
    limit: int = Field(default=10, description="Maximum number of results to return.")
    datatypes: list[str] | None = Field(
        default=None,
        description="Restrict to nodes that have ports with these datatypes (e.g. ['float', 'int']).",
    )
    units: list[str] | None = Field(
        default=None,
        description="Restrict to nodes that have ports with these physical units (e.g. ['K', 'eV']).",
    )
    quantities: list[str] | None = Field(
        default=None,
        description="Restrict to nodes that have ports with these physical quantities (e.g. ['temperature']).",
    )
    keywords: list[str] | None = Field(
        default=None,
        description="Restrict to nodes associated with these keywords.",
    )
    port_type: Literal["inputs", "outputs", "both"] | None = Field(
        default=None,
        description="Whether port filters apply to input ports, output ports, or both.",
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
    limit: int = Field(default=10, description="Maximum number of results to return.")


class FindCompatibleNodesResult(BaseModel):
    results: list[SearchNodeItem]


class GetNodeDetailsInput(BaseModel):
    atlas_node_id: str = Field(description="The Atlas node id (SHA256 hash) to look up.")


class GetNodeDetailsResult(BaseModel):
    atlas_node_id: str
    name: str
    docstring: str
    inputs: list[PortMetadata]
    outputs: list[PortMetadata]


def _to_short_description(ai_summary: str | None, docstring: str) -> str | None:
    if ai_summary:
        return ai_summary
    lines = docstring.splitlines()
    return lines[0] if lines else None


async def execute_search_nodes(
    args: SearchNodesInput,
    storage: StorageInterface,
    _scratch: Any,
) -> SearchNodesResult:
    f = Filter(
        datatypes=args.datatypes,
        units=args.units,
        quantities=args.quantities,
        keywords=args.keywords,
        port_type=args.port_type,
    )
    filter_arg = f if f.model_fields_set else None
    response = storage.search_hybrid(args.query, filter_arg, limit=args.limit)
    return SearchNodesResult(
        results=[
            SearchNodeItem(
                atlas_node_id=item.node.id,
                name=item.node.name,
                short_description=_to_short_description(
                    item.node.ai_summary, item.node.docstring
                ),
                inputs=[
                    PortMetadata.model_validate(a.model_dump(exclude_none=True))
                    for a in item.node.inputs
                ],
                outputs=[
                    PortMetadata.model_validate(a.model_dump(exclude_none=True))
                    for a in item.node.outputs
                ],
                score=round(item.score, 4),
            )
            for item in response.results.data
        ]
    )


async def execute_find_compatible_nodes(
    args: FindCompatibleNodesInput,
    storage: StorageInterface,
    _scratch: Any,
) -> FindCompatibleNodesResult:
    f = Filter(
        datatypes=[args.datatype] if args.datatype else None,
        units=[args.unit] if args.unit else None,
        quantities=[args.quantity] if args.quantity else None,
        port_type=args.port_type,
    )
    if args.query:
        response = storage.search_semantic(args.query, f, limit=args.limit)
    else:
        response = storage.search(query=None, filter=f, limit=args.limit)
    return FindCompatibleNodesResult(
        results=[
            SearchNodeItem(
                atlas_node_id=item.node.id,
                name=item.node.name,
                short_description=_to_short_description(
                    item.node.ai_summary, item.node.docstring
                ),
                inputs=[
                    PortMetadata.model_validate(a.model_dump(exclude_none=True))
                    for a in item.node.inputs
                ],
                outputs=[
                    PortMetadata.model_validate(a.model_dump(exclude_none=True))
                    for a in item.node.outputs
                ],
            )
            for item in response.results.data
        ]
    )


async def execute_get_node_details(
    args: GetNodeDetailsInput,
    storage: StorageInterface,
    _scratch: Any,
) -> GetNodeDetailsResult:
    try:
        node = storage.read(args.atlas_node_id)
    except KeyError as exc:
        raise ToolError(f"Node '{args.atlas_node_id}' not found.") from exc
    return GetNodeDetailsResult(
        atlas_node_id=node.id,
        name=node.name,
        docstring=node.ai_description or node.docstring,
        inputs=[PortMetadata.model_validate(a.model_dump(exclude_none=True)) for a in node.inputs],
        outputs=[PortMetadata.model_validate(a.model_dump(exclude_none=True)) for a in node.outputs],
    )
