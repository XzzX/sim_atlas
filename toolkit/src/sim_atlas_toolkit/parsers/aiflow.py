# pyright: basic
from __future__ import annotations

import inspect
import textwrap
from http import HTTPStatus
from typing import Any

import requests
from requests import Response

from sim_atlas_toolkit import upload
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
from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.parsers.metadata import enrich_from_docstring, type_to_str


def parse_function_node(obj: Any, ns: NodeStoreAPI) -> list[requests.Response]:
    try:
        from core.node import (  # noqa: PLC0415 # pyright: ignore[reportMissingImports]
            Node,
        )

    except ImportError:
        return []

    if type(obj) is type and issubclass(obj, Node):
        obj = obj()

    if not isinstance(obj, Node):
        return []

    metadata = FunctionRequest.model_construct()
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

    enrich_from_docstring(metadata.docstring, metadata)

    return ns.upload([metadata])


def parse_group_node(obj: Any, ns: NodeStoreAPI) -> list[requests.Response]:
    try:
        from core.graph_to_workflow import (  # noqa: PLC0415 # pyright: ignore[reportMissingImports]
            graph_to_workflow_code,
        )
        from core.groups import (  # noqa: PLC0415 # pyright: ignore[reportMissingImports]
            WorkflowGroupFactory,
        )
        from core.node import (  # noqa: PLC0415 # pyright: ignore[reportMissingImports]
            GroupNode,
        )

    except ImportError:
        return []

    if isinstance(obj, WorkflowGroupFactory):
        obj = obj()

    if not isinstance(obj, GroupNode):
        return []

    group_node: GroupNode = obj

    metadata = FunctionRequest.model_construct()

    metadata.source_code = graph_to_workflow_code(
        group_node.subgraph, group_node.label, "decorator", True
    )

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

    return ns.upload([metadata])


def to_wf_definition(
    graph: Any, references: list[Reference], ns: NodeStoreAPI
) -> WfDefinition:
    reference_dict = {ref.label: ref.id for ref in references}

    nodes: list[WfNode] = []
    for node_id, node in graph.nodes.items():
        node_metadata = parse(node, ns)
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


def parse_workflow(obj: Any, ns: NodeStoreAPI) -> list[requests.Response]:
    try:
        from core import (  # pyright: ignore[reportMissingImports] # noqa: PLC0415
            Workflow,  # pyright: ignore[reportMissingImports]
        )
        from core.graph_to_workflow import (  # pyright: ignore[reportMissingImports] # noqa: PLC0415
            graph_to_workflow_code,
        )
    except ImportError:
        return []

    if not isinstance(obj, Workflow):
        return []

    wf: Workflow = obj

    metadata = WorkflowRequest.model_construct()

    metadata.name = wf._graph.label
    metadata.python_import = ""
    metadata.category = "workflow"
    metadata.source_code = graph_to_workflow_code(
        wf._graph, wf._graph.label, "decorator", True
    )
    metadata.docstring = ""
    metadata.keywords = ["aiflow"]
    metadata.inputs = []
    metadata.outputs = []

    children_import = [(label, node) for label, node in wf._graph.nodes.items()]

    children_upload = [
        (label, upload(ns, child)[0])
        for label, child in children_import
        if child is not None
    ]

    def extract_id(response: Response) -> str | None:
        if response.ok:
            return response.json()["id"]
        if response.status_code == HTTPStatus.CONFLICT:
            return response.json()["detail"]["id"]
        return None

    metadata.children = [
        Reference(label=label, id=atlas_id)
        for label, response in children_upload
        if (atlas_id := extract_id(response)) is not None
    ]

    metadata.wf_definition = to_wf_definition(wf._graph, metadata.children, ns)

    return ns.upload([metadata])


def parse(obj: Any, ns: NodeStoreAPI) -> list[requests.Response]:
    if metadata := parse_workflow(obj, ns):
        return metadata

    if metadata := parse_group_node(obj, ns):
        return metadata

    if metadata := parse_function_node(obj, ns):
        return metadata

    return []
