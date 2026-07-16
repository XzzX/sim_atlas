# pyright: basic
from __future__ import annotations

import hashlib
import inspect
import textwrap
from http import HTTPStatus
from typing import Any

import httpx
from core import (  # pyright: ignore[reportMissingImports]
    Workflow,  # pyright: ignore[reportMissingImports]
)
from core.graph_to_workflow import (  # pyright: ignore[reportMissingImports]  # pyright: ignore[reportMissingImports]
    graph_to_workflow_code,
)
from core.groups import (  # pyright: ignore[reportMissingImports]
    WorkflowGroupFactory,
)
from core.node import (  # noqa: PLC0415 # pyright: ignore[reportMissingImports]  # pyright: ignore[reportMissingImports]
    GroupNode,
    Node,
)

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.models import (
    Annotation,
    ArtifactType,
    FunctionRequest,
    Reference,
    WfDefinition,
    WfEdge,
    WfFunctionNode,
    WfNode,
    WorkflowRequest,
)
from sim_atlas_toolkit.parsers.ai_enrichment import (
    generate_docstring,
    generate_workflow_docstring,
)
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    extract_id,
    type_to_str,
)
from sim_atlas_toolkit.settings import ToolkitSettings
from sim_atlas_toolkit.uploader import upload


async def parse_function_node(
    settings: ToolkitSettings, obj: Any
) -> list[httpx.Response]:
    if type(obj) is type and issubclass(obj, Node):
        obj = obj()

    if not isinstance(obj, Node):
        return []

    metadata = FunctionRequest.model_construct()
    match obj.node_type:
        case "function_node":
            metadata.source_code = textwrap.dedent(
                inspect.getsource(obj._original_func).replace("\r\n", "")
            )
            metadata.docstring = inspect.getdoc(obj._original_func) or ""
            metadata.keywords = ["aiflow", "function_node"]
        case "inp_dataclass_node":
            metadata.source_code = obj._source
            metadata.docstring = ""
            metadata.keywords = ["aiflow", "inp_dataclass_node"]
        case "out_dataclass_node":
            metadata.source_code = obj._source
            metadata.docstring = ""
            metadata.keywords = ["aiflow", "out_dataclass_node"]
        case _:
            pass

    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()
    response = await node_store_api.read_artifact(settings.api_url, hash)
    if response.status_code == HTTPStatus.OK:
        return [response]

    metadata.hash = hash
    metadata.id = hash

    metadata.python_import = obj._module_path
    metadata.name = metadata.python_import
    metadata.category = metadata.python_import.replace(".", ">")
    metadata.inputs = [
        Annotation(label=inp.label, datatype=type_to_str(inp.datatype))
        for inp in obj.inputs
    ]
    metadata.outputs = [
        Annotation(label=out.label, datatype=type_to_str(out.datatype))
        for out in obj.outputs
    ]

    metadata.docstring = await generate_docstring(
        settings, metadata.source_code, metadata.docstring
    )
    enrich_from_docstring(metadata.docstring, metadata)

    return await node_store_api.create_artifacts(
        settings.api_url, settings.api_token, [metadata]
    )


async def parse_group_node(settings: ToolkitSettings, obj: Any) -> list[httpx.Response]:
    if isinstance(obj, WorkflowGroupFactory):
        obj = obj()

    if not isinstance(obj, GroupNode):
        return []

    group_node: GroupNode = obj

    metadata = FunctionRequest.model_construct()

    metadata.source_code = graph_to_workflow_code(
        group_node.subgraph, group_node.label, "decorator", True
    )

    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()
    response = await node_store_api.read_artifact(settings.api_url, hash)
    if response.status_code == HTTPStatus.OK:
        return [response]

    metadata.hash = hash
    metadata.id = hash

    module: str = group_node._factory_module
    qualname: str = group_node._factory_name
    python_import = f"{module}.{qualname}"

    inputs = [
        Annotation(label=inp.label, datatype=type_to_str(inp.datatype))
        for inp in group_node.inputs
    ]
    outputs = [
        Annotation(label=out.label, datatype=type_to_str(out.datatype))
        for out in group_node.outputs
    ]

    metadata.name = group_node.label
    metadata.artifact_type = ArtifactType.FUNCTION
    metadata.python_import = python_import
    metadata.category = module.replace(".", ">")
    metadata.keywords = ["aiflow", "group_node"]
    metadata.inputs = inputs
    metadata.outputs = outputs
    metadata.docstring = ""

    return await node_store_api.create_artifacts(
        settings.api_url, settings.api_token, [metadata]
    )


async def to_wf_definition(
    settings: ToolkitSettings,
    graph: Any,
    references: list[Reference],
) -> WfDefinition:
    reference_dict = {ref.label: ref.id for ref in references}

    nodes: list[WfNode] = []
    for node_id, node in graph.nodes.items():
        node_metadata = await parse(settings, node)
        if not node_metadata:
            continue
        if node_metadata[0].status_code in (HTTPStatus.CREATED, HTTPStatus.CONFLICT):
            nodes.append(
                WfFunctionNode(
                    node_id=node_id,
                    inputs=node_metadata[0].json().get("inputs", []),
                    outputs=node_metadata[0].json().get("outputs", []),
                    atlas_id=reference_dict.get(node_id),
                )
            )

    edges: list[WfEdge] = []

    for edge in graph.edges:
        edges.append(
            WfEdge(
                source_node=edge.source,
                source_port=edge.sourceHandle,
                target_node=edge.target,
                target_port=edge.targetHandle,
            )
        )

    return WfDefinition(nodes=nodes, edges=edges)


async def parse_workflow(settings: ToolkitSettings, obj: Any) -> list[httpx.Response]:
    if not isinstance(obj, Workflow):
        return []

    wf: Workflow = obj

    metadata = WorkflowRequest.model_construct()
    metadata.source_code = graph_to_workflow_code(
        wf._graph, wf._graph.label, "decorator", True
    )

    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()
    response = await node_store_api.read_artifact(settings.api_url, hash)
    if response.status_code == HTTPStatus.OK:
        return [response]

    metadata.hash = hash
    metadata.id = hash

    metadata.name = wf._graph.label
    metadata.python_import = ""
    metadata.category = "workflow"

    metadata.docstring = ""
    metadata.keywords = ["aiflow"]
    metadata.inputs = []
    metadata.outputs = []

    uses_import = [(label, node) for label, node in wf._graph.nodes.items()]

    uses_upload = [
        (label, (await upload(settings, child))[0])
        for label, child in uses_import
        if child is not None
    ]

    metadata.uses = [
        Reference(label=label, id=atlas_id, count=1)
        for label, response in uses_upload
        if (atlas_id := extract_id(response)) is not None
    ]

    metadata.wf_definition = await to_wf_definition(settings, wf._graph, metadata.uses)

    metadata.docstring = await generate_workflow_docstring(
        settings,
        metadata.name,
        metadata.source_code,
        metadata.docstring or "",
        metadata.wf_definition,
    )
    enrich_from_docstring(metadata.docstring, metadata)

    return [
        await node_store_api.create_artifact(
            settings.api_url, settings.api_token, metadata
        )
    ]


async def parse(settings: ToolkitSettings, obj: Any) -> list[httpx.Response]:
    if metadata := await parse_workflow(settings, obj):
        return metadata

    if metadata := await parse_group_node(settings, obj):
        return metadata

    if metadata := await parse_function_node(settings, obj):
        return metadata

    return []
