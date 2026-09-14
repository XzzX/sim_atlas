import asyncio

import httpx
from flowrep import base_models, edge_models
from flowrep.prospective.atomic_recipe import AtomicRecipe
from flowrep.prospective.constant_recipe import ConstantRecipe
from flowrep.prospective.workflow_recipe import WorkflowRecipe
from pyiron_snippets import versions

from sim_atlas_agent.models.sim_atlas import (
    ArtifactResponse,
    FunctionResponse,
    artifact_response_adapter,
)
from sim_atlas_agent.tools.wf import Graph


async def read_artifact(
    api_url: str,
    sim_atlas_id: str,
) -> ArtifactResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/artifacts/{sim_atlas_id}")
    response.raise_for_status()
    return artifact_response_adapter.validate_python(response.json())


def _reference_from_artifact(artifact: FunctionResponse) -> base_models.PythonReference:
    module, separator, qualname = artifact.python_import.rpartition(".")
    if not separator or not module or not qualname:
        raise ValueError(
            f"function artifact {artifact.id!r} has an invalid python import "
            f"path: {artifact.python_import!r}"
        )
    return base_models.PythonReference(
        info=versions.VersionInfo(module=module, qualname=qualname),
        inputs_with_defaults=[
            annotation.label
            for annotation in artifact.inputs
            if annotation.label and annotation.has_default_value
        ],
    )


async def graph_to_flowrep(api_url: str, g: Graph) -> WorkflowRecipe:
    """Convert the agent's graph format into a serializable FlowRep recipe."""
    node_ids = list(g["nodes"])
    artifacts = await asyncio.gather(
        *(
            read_artifact(api_url, g["nodes"][node_id]["sim_atlas_id"])
            for node_id in node_ids
        )
    )

    nodes: dict[str, AtomicRecipe | ConstantRecipe] = {}
    functions: dict[str, FunctionResponse] = {}
    for node_id, artifact in zip(node_ids, artifacts, strict=True):
        if not isinstance(artifact, FunctionResponse):
            raise TypeError(f"node {node_id!r} refers to a workflow, not a function")
        functions[node_id] = artifact
        inputs = [
            annotation.label for annotation in artifact.inputs if annotation.label
        ]
        nodes[node_id] = AtomicRecipe(
            inputs=inputs,
            outputs=[
                annotation.label for annotation in artifact.outputs if annotation.label
            ],
            reference=_reference_from_artifact(artifact),
        )

    edges: edge_models.Edges = {}
    connected_inputs: set[tuple[str, str]] = set()
    connected_outputs: set[tuple[str, str]] = set()
    for edge in g["edges"]:
        source = (edge["src"], edge["src_port"])
        target = (edge["dst"], edge["dst_port"])
        if source[0] not in functions or source[1] not in nodes[source[0]].outputs:
            raise ValueError(f"unknown output port: {source[0]}.{source[1]}")
        if target[0] not in functions or target[1] not in nodes[target[0]].inputs:
            raise ValueError(f"unknown input port: {target[0]}.{target[1]}")
        edges[edge_models.TargetHandle(node=target[0], port=target[1])] = (
            edge_models.SourceHandle(node=source[0], port=source[1])
        )
        connected_inputs.add(target)
        connected_outputs.add(source)

    for node_id, node_data in g["nodes"].items():
        for port, value in node_data["params"].items():
            if port not in nodes[node_id].inputs:
                raise ValueError(f"unknown input port: {node_id}.{port}")
            if (node_id, port) in connected_inputs:
                raise ValueError(
                    f"input port {node_id}.{port} has both a parameter and an edge"
                )
            constant_label = f"{node_id}_{port}_value"
            nodes[constant_label] = ConstantRecipe(constant=value)
            edges[edge_models.TargetHandle(node=node_id, port=port)] = (
                edge_models.SourceHandle(
                    node=constant_label, port=ConstantRecipe.std_label
                )
            )
            connected_inputs.add((node_id, port))

    input_edges: edge_models.InputEdges = {}
    output_edges: edge_models.OutputEdges = {}
    workflow_inputs: list[str] = []
    workflow_outputs: list[str] = []
    for node_id, artifact in functions.items():
        for port in nodes[node_id].inputs:
            if (node_id, port) not in connected_inputs:
                label = f"{node_id}_{port}"
                workflow_inputs.append(label)
                input_edges[edge_models.TargetHandle(node=node_id, port=port)] = (
                    edge_models.InputSource(port=label)
                )
        for port in nodes[node_id].outputs:
            if (node_id, port) not in connected_outputs:
                label = f"{node_id}_{port}"
                workflow_outputs.append(label)
                output_edges[edge_models.OutputTarget(port=label)] = (
                    edge_models.SourceHandle(node=node_id, port=port)
                )

    return WorkflowRecipe(
        inputs=workflow_inputs,
        outputs=workflow_outputs,
        nodes=nodes,
        input_edges=input_edges,
        edges=edges,
        output_edges=output_edges,
    )
