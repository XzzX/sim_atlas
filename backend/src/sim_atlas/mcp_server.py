from fastmcp import FastMCP
from pydantic import BaseModel

from sim_atlas.dependencies import get_storage
from sim_atlas.models import (
    AnnotationResponse,
    Filter,
    FunctionMetadata,
    FunctionResponse,
    Reference,
    StoredArtifact,
    WorkflowResponse,
)

mcp = FastMCP("Simulation Atlas")


@mcp.tool
async def search(query: str) -> str:
    """Search the node catalog and return a sorted list of matching nodes.

    Args:
        query (str): The search query.

    Returns:
        str: sim-atlas-id and brief description, one per line.
    """
    storage = get_storage()
    response = storage.search(
        query,
        Filter(artifact_type=["function"], keywords=["flowrep"]),
        page=1,
        limit=50,
    )

    def node_to_str(node: FunctionResponse | WorkflowResponse) -> str:
        return f"{node.id}: {node.brief_description}"

    return "\n".join([node_to_str(item.node) for item in response.results.data])


@mcp.tool
async def cookbook(sim_atlas_id: str) -> str:
    """Get ids for nodes that are related to the given node, e.g. similar nodes or nodes that are often used together.

    Args:
        sim_atlas_id (str): The ID of the node to retrieve related nodes for.

    Returns:
        str: A list of related node IDs, one per line.
    """

    storage = get_storage()
    response = storage.read_artifact(sim_atlas_id)
    input_references = ((c.id for c in i.connections) for i in response.inputs)
    output_references = ((c.id for c in o.connections) for o in response.outputs)

    def node_to_str(node: FunctionResponse | WorkflowResponse) -> str:
        return f"{node.id}: {node.brief_description}"

    return "\n".join(
        [node_to_str(item.node) for item in (input_references | output_references)]
    )


def _format_references(refs: list[Reference] | None) -> str:
    if not refs:
        return "(none)"
    return ", ".join(f"{r.label} ({r.id}) x{r.count}" for r in refs)


def _format_port(p: AnnotationResponse) -> str:
    type_info = p.datatype or "any"
    if p.unit:
        type_info += f", unit={p.unit}"
    if p.quantity:
        type_info += f", quantity={p.quantity}"
    required = "optional" if p.has_default_value else "required"
    line = f" - {p.label} ({type_info}, {required}): {p.description}"
    if p.connections:
        line += f"\n     connected in practice to: {_format_references(p.connections)}"
    return line


def _artifact_to_str(artifact: StoredArtifact) -> str:
    sections = [
        f"sim-atlas-id: {artifact.id}",
        f"description: \n{artifact.brief_description}",
        "inputs:\n" + "\n".join(_format_port(p) for p in artifact.inputs),
        "outputs:\n" + "\n".join(_format_port(p) for p in artifact.outputs),
        f"see also: {_format_references(artifact.see_also)}",
    ]
    if isinstance(artifact, FunctionMetadata):
        sections.append(f"used in workflows: {_format_references(artifact.used_by)}")
    else:
        sections.append(f"uses: {_format_references(artifact.uses)}")
    return "\n\n".join(sections)


@mcp.tool
async def detailed_node_info(sim_atlas_ids: list[str]) -> str:
    """Get detailed information about a specific nodes.

    Args:
        sim_atlas_ids (list[str]): The IDs of the nodes to retrieve.

    Returns:
        str: Details about the nodes, including their inputs and outputs
            (with real-world connections observed in stored workflows) and
            related/usage references.
    """
    storage = get_storage()
    responses = [storage.read_artifact(sim_atlas_id) for sim_atlas_id in sim_atlas_ids]

    return "\n\n===\n\n".join([_artifact_to_str(response) for response in responses])


mcp_app = mcp.http_app(path="/")
