import re
from typing import Literal

from pydantic import BaseModel, Field

from ...models import Annotation, GraphEdgeContext, GraphNodeContext
from ...storage_interface import StorageInterface
from ._errors import ToolError
from ._search import PortMetadata

_ADD_FUNCTION_NODE_DESCRIPTION_PARTS = (
    "Add a function node from the catalog to the graph. ",
    "Returns the assigned graph_id and the node's port metadata.",
)
ADD_FUNCTION_NODE_DESCRIPTION = "".join(_ADD_FUNCTION_NODE_DESCRIPTION_PARTS)

_ADD_INPUT_NODE_DESCRIPTION_PARTS = (
    "Add an input port node to the graph. ",
    "Returns the assigned graph_id.",
)
ADD_INPUT_NODE_DESCRIPTION = "".join(_ADD_INPUT_NODE_DESCRIPTION_PARTS)

_ADD_OUTPUT_NODE_DESCRIPTION_PARTS = (
    "Add an output port node to the graph. ",
    "Returns the assigned graph_id.",
)
ADD_OUTPUT_NODE_DESCRIPTION = "".join(_ADD_OUTPUT_NODE_DESCRIPTION_PARTS)

_ADD_EDGE_DESCRIPTION_PARTS = ("Connect two nodes in the graph via their ports.",)
ADD_EDGE_DESCRIPTION = "".join(_ADD_EDGE_DESCRIPTION_PARTS)

_REMOVE_EDGE_DESCRIPTION_PARTS = (
    "Remove an edge from the graph by matching all four of its endpoint identifiers.",
)
REMOVE_EDGE_DESCRIPTION = "".join(_REMOVE_EDGE_DESCRIPTION_PARTS)

_REMOVE_NODE_DESCRIPTION_PARTS = (
    "Remove a node from the graph by its graph_id. ",
    "Also removes all edges connected to that node.",
)
REMOVE_NODE_DESCRIPTION = "".join(_REMOVE_NODE_DESCRIPTION_PARTS)


class AddFunctionNodeInput(BaseModel):
    atlas_node_id: str = Field(description="The Atlas node id (UUID) to add.")
    label: str = Field(description="Display label for the node in the graph.")


class AddFunctionNodeResult(BaseModel):
    graph_id: str
    inputs: list[PortMetadata]
    outputs: list[PortMetadata]


class AddInputNodeInput(BaseModel):
    label: str = Field(description="Name of the input parameter.")
    value: str = Field(default="", description="Default value for the input.")


class AddInputNodeResult(BaseModel):
    graph_id: str


class AddOutputNodeInput(BaseModel):
    label: str = Field(description="Name of the output.")


class AddOutputNodeResult(BaseModel):
    graph_id: str


class AddEdgeInput(BaseModel):
    source_graph_id: str = Field(description="graph_id of the source node.")
    source_handle: str = Field(description="Name of the output port on the source node.")
    target_graph_id: str = Field(description="graph_id of the target node.")
    target_handle: str = Field(description="Name of the input port on the target node.")


class AddEdgeResult(BaseModel):
    ok: Literal[True] = True


class RemoveEdgeInput(BaseModel):
    source_graph_id: str = Field(description="graph_id of the source node.")
    source_handle: str = Field(description="Name of the output port on the source node.")
    target_graph_id: str = Field(description="graph_id of the target node.")
    target_handle: str = Field(description="Name of the input port on the target node.")


class RemoveEdgeResult(BaseModel):
    ok: Literal[True] = True


class RemoveNodeInput(BaseModel):
    graph_id: str = Field(description="The graph_id of the node to remove.")


class RemoveNodeResult(BaseModel):
    ok: Literal[True] = True


def _slugify(text: str) -> str:
    """Convert a label into a filesystem-safe, LLM-readable id slug."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_") or "node"


class ScratchGraph:
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


async def execute_add_function_node(
    args: AddFunctionNodeInput,
    storage: StorageInterface,
    scratch: ScratchGraph,
) -> AddFunctionNodeResult:
    if not storage.exists(args.atlas_node_id):
        raise ToolError(f"Node '{args.atlas_node_id}' not found in catalog.")
    node = storage.read(args.atlas_node_id)
    graph_id = scratch.new_graph_id(args.label)
    scratch.nodes[graph_id] = GraphNodeContext(
        graph_id=graph_id,
        node_kind="function",
        atlas_node_id=args.atlas_node_id,
        name=args.label,
        short_description=node.ai_summary or node.docstring.splitlines()[0]
        if node.docstring
        else None,
        inputs=node.inputs,
        outputs=node.outputs,
    )
    return AddFunctionNodeResult(
        graph_id=graph_id,
        inputs=[PortMetadata.model_validate(a.model_dump(exclude_none=True)) for a in node.inputs],
        outputs=[PortMetadata.model_validate(a.model_dump(exclude_none=True)) for a in node.outputs],
    )


async def execute_add_input_node(
    args: AddInputNodeInput,
    _storage: StorageInterface,
    scratch: ScratchGraph,
) -> AddInputNodeResult:
    graph_id = scratch.new_graph_id(args.label)
    scratch.nodes[graph_id] = GraphNodeContext(
        graph_id=graph_id,
        node_kind="input",
        atlas_node_id=None,
        name=args.label,
        inputs=[],
        outputs=[Annotation(label="output")],
    )
    return AddInputNodeResult(graph_id=graph_id)


async def execute_add_output_node(
    args: AddOutputNodeInput,
    _storage: StorageInterface,
    scratch: ScratchGraph,
) -> AddOutputNodeResult:
    graph_id = scratch.new_graph_id(args.label)
    scratch.nodes[graph_id] = GraphNodeContext(
        graph_id=graph_id,
        node_kind="output",
        atlas_node_id=None,
        name=args.label,
        inputs=[Annotation(label="input")],
        outputs=[],
    )
    return AddOutputNodeResult(graph_id=graph_id)


async def execute_add_edge(
    args: AddEdgeInput,
    _storage: StorageInterface,
    scratch: ScratchGraph,
) -> AddEdgeResult:
    if args.source_graph_id not in scratch.nodes:
        raise ToolError(f"Source node '{args.source_graph_id}' not in graph.")
    if args.target_graph_id not in scratch.nodes:
        raise ToolError(f"Target node '{args.target_graph_id}' not in graph.")
    scratch.edges.append(
        GraphEdgeContext(
            source_graph_id=args.source_graph_id,
            source_handle=args.source_handle,
            target_graph_id=args.target_graph_id,
            target_handle=args.target_handle,
        )
    )
    return AddEdgeResult()


async def execute_remove_edge(
    args: RemoveEdgeInput,
    _storage: StorageInterface,
    scratch: ScratchGraph,
) -> RemoveEdgeResult:
    before = len(scratch.edges)
    scratch.edges = [
        edge
        for edge in scratch.edges
        if not (
            edge.source_graph_id == args.source_graph_id
            and edge.source_handle == args.source_handle
            and edge.target_graph_id == args.target_graph_id
            and edge.target_handle == args.target_handle
        )
    ]
    if len(scratch.edges) == before:
        raise ToolError(
            "No edge found from "
            f"'{args.source_graph_id}/{args.source_handle}' "
            f"to '{args.target_graph_id}/{args.target_handle}'."
        )
    return RemoveEdgeResult()


async def execute_remove_node(
    args: RemoveNodeInput,
    _storage: StorageInterface,
    scratch: ScratchGraph,
) -> RemoveNodeResult:
    if args.graph_id not in scratch.nodes:
        raise ToolError(f"Node '{args.graph_id}' not in graph.")
    del scratch.nodes[args.graph_id]
    scratch.edges = [
        edge
        for edge in scratch.edges
        if args.graph_id not in {edge.source_graph_id, edge.target_graph_id}
    ]
    return RemoveNodeResult()


def _validate_io_node(
    gid: str,
    node: GraphNodeContext,
    output_labels: dict[str, set[str]],
    input_labels: dict[str, set[str]],
) -> list[str]:
    """Check structural constraints for input/output nodes."""
    errors: list[str] = []
    if node.node_kind == "input" and output_labels[gid] != {"output"}:
        errors.append(
            f"Input node '{gid}' must have exactly one output port named "
            f"'output', but has: {sorted(output_labels[gid])}."
        )
    elif node.node_kind == "output" and input_labels[gid] != {"input"}:
        errors.append(
            f"Output node '{gid}' must have exactly one input port named "
            f"'input', but has: {sorted(input_labels[gid])}."
        )
    return errors


def validate_graph(scratch: ScratchGraph, storage: StorageInterface) -> list[str]:
    """Return a list of validation error strings (empty means valid)."""
    errors: list[str] = []

    output_labels: dict[str, set[str]] = {}
    input_labels: dict[str, set[str]] = {}
    for gid, node in scratch.nodes.items():
        output_labels[gid] = {a.label for a in node.outputs if a.label is not None}
        input_labels[gid] = {a.label for a in node.inputs if a.label is not None}

    for gid, node in scratch.nodes.items():
        if node.node_kind == "function":
            if node.atlas_node_id is None or not storage.exists(node.atlas_node_id):
                errors.append(
                    f"Node '{gid}' references atlas_node_id '{node.atlas_node_id}' "
                    "which no longer exists in the catalog."
                )
        else:
            errors.extend(_validate_io_node(gid, node, output_labels, input_labels))

    for edge in scratch.edges:
        src = edge.source_graph_id
        tgt = edge.target_graph_id
        if src not in scratch.nodes:
            errors.append(f"Edge source node '{src}' does not exist in graph.")
            continue
        if tgt not in scratch.nodes:
            errors.append(f"Edge target node '{tgt}' does not exist in graph.")
            continue

        src_handle = edge.source_handle
        tgt_handle = edge.target_handle
        if src_handle not in output_labels[src]:
            errors.append(
                f"Edge source handle '{src}/{src_handle}' does not exist; "
                f"available outputs: {sorted(output_labels[src])}."
            )
        if tgt_handle not in input_labels[tgt]:
            errors.append(
                f"Edge target handle '{tgt}/{tgt_handle}' does not exist; "
                f"available inputs: {sorted(input_labels[tgt])}."
            )

    return errors
