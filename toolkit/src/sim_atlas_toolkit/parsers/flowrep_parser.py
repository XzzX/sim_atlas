import importlib
import inspect
import json
import logging
from http import HTTPStatus
from typing import Any, cast

import httpx
from flowrep.api.schemas import (
    AtomicRecipe,
    InputSource,
    WorkflowRecipe,
)
from flowrep.retrospective.datastructures import DagData

from sim_atlas_toolkit.models import (
    Annotation,
    ArtifactType,
    ExecutionResultRequest,
    FunctionRequest,
    IOValue,
    Reference,
    WfDefinition,
    WfEdge,
    WfFunctionNode,
    WfInputNode,
    WfNode,
    WfOutputNode,
    WorkflowRequest,
)
from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.parsers.metadata import (
    enrich_metadata,
    parse_return_annotation,
    parse_signature,
)
from sim_atlas_toolkit.settings import ToolkitSettings
from sim_atlas_toolkit.uploader import upload

logger = logging.getLogger(__name__)


def try_import(module: str, qualname: str | None) -> Any | None:
    if qualname is None:
        return None
    try:
        mod = importlib.import_module(module)
        obj = mod
        for attr in qualname.split("."):
            obj = getattr(obj, attr)
        return obj
    except Exception:
        return None


def extract_id(response: httpx.Response) -> str | None:
    if response.is_success:
        return response.json()["id"]
    if response.status_code == HTTPStatus.CONFLICT:
        return response.json()["id"]
    return None


def flowrep_to_wf_definition(
    wf: WorkflowRecipe, references: list[Reference]
) -> WfDefinition:
    reference_dict = {ref.label: ref.id for ref in references}

    nodes: list[WfNode] = []
    for node_id, node in wf.nodes.items():
        match node:
            case AtomicRecipe():
                inputs = [
                    Annotation(
                        label=inp, has_default_value=inp in node.inputs_with_defaults
                    )
                    for inp in node.inputs
                ]
                outputs = [Annotation(label=out) for out in node.outputs]
                nodes.append(
                    WfFunctionNode(
                        type="function",
                        node_id=node_id,
                        inputs=inputs,
                        outputs=outputs,
                        atlas_id=reference_dict.get(node_id),
                    )
                )
            case WorkflowRecipe():
                # Nested workflows are not supported in this conversion
                continue
            case _:
                raise ValueError(f"Unknown node type: {type(node)}")

    edges: list[WfEdge] = []

    for target, source in wf.input_edges.items():
        if not any(node.node_id == source.port for node in nodes):
            nodes.append(
                WfInputNode(
                    type="input",
                    node_id=source.port,
                    outputs=[Annotation(label=source.port)],
                )
            )

        edges.append(
            WfEdge(
                source_node=source.port,
                source_port=None,
                target_node=target.node,
                target_port=target.port,
            )
        )

    for target, source in wf.edges.items():
        edges.append(
            WfEdge(
                source_node=source.node,
                source_port=source.port,
                target_node=target.node,
                target_port=target.port,
            )
        )

    for target, source in wf.output_edges.items():
        match source:
            case InputSource():
                if not any(node.node_id == source.port for node in nodes):
                    nodes.append(
                        WfInputNode(
                            type="input",
                            node_id=source.port,
                            outputs=[Annotation(label=source.port)],
                        )
                    )
            case _:
                pass

        if not any(node.node_id == target.port for node in nodes):
            nodes.append(
                WfOutputNode(
                    type="output",
                    node_id=target.port,
                    inputs=[Annotation(label=target.port)],
                )
            )

        edges.append(
            WfEdge(
                source_node=source.node or source.port,
                source_port=None if isinstance(source, InputSource) else source.port,
                target_node=target.port,
                target_port=None,
            )
        )

    return WfDefinition(nodes=nodes, edges=edges)


async def parse_atomic_recipe(
    settings: ToolkitSettings,
    obj: Any,
    recipe: AtomicRecipe,
    ns: NodeStoreAPI,
) -> list[httpx.Response]:
    metadata = FunctionRequest.model_construct()

    metadata.source_code = inspect.getsource(obj) or ""
    metadata.docstring = inspect.getdoc(obj) or ""

    fr_inputs = [
        Annotation(
            label=inp,
            has_default_value=inp in recipe.reference.inputs_with_defaults,
        )
        for inp in recipe.inputs
    ]
    fr_outputs = [Annotation(label=out) for out in recipe.outputs]

    sig = inspect.signature(obj)
    sig_inputs = parse_signature(sig)
    sig_outputs = parse_return_annotation(sig)

    def merge_annotation(sig_ann: Annotation | None, fr_ann: Annotation) -> Annotation:
        if sig_ann is None:
            return fr_ann

        return Annotation(
            has_default_value=fr_ann.has_default_value,
            label=fr_ann.label,
            datatype=sig_ann.datatype,
            unit=sig_ann.unit,
            quantity=sig_ann.quantity,
            description=sig_ann.description,
        )

    metadata.inputs = [
        merge_annotation(sig_ann, fr_inp)
        for sig_ann, fr_inp in zip(sig_inputs, fr_inputs, strict=True)
    ]
    metadata.outputs = [
        merge_annotation(sig_ann, fr_out)
        for sig_ann, fr_out in zip(sig_outputs, fr_outputs, strict=True)
    ]

    metadata.name = f"{obj.__module__}.{obj.__qualname__}"
    metadata.artifact_type = ArtifactType.FUNCTION
    metadata.python_import = f"{obj.__module__}.{obj.__qualname__}"
    metadata.category = f"{obj.__module__}".replace(".", ">")
    metadata.keywords = ["flowrep"]

    await enrich_metadata(settings, metadata)
    return await ns.upload([metadata])


async def parse_workflow_recipe(
    settings: ToolkitSettings,
    obj: Any,
    recipe: WorkflowRecipe,
    ns: NodeStoreAPI,
) -> list[httpx.Response]:
    metadata = WorkflowRequest.model_construct()

    metadata.source_code = recipe.model_dump_json(indent=2)
    metadata.docstring = inspect.getdoc(obj) or ""

    fr_inputs = [
        Annotation(label=inp, has_default_value=inp in recipe.inputs_with_defaults)
        for inp in recipe.inputs
    ]
    fr_outputs = [Annotation(label=out) for out in recipe.outputs]

    sig = inspect.signature(obj)
    sig_inputs = parse_signature(sig)
    sig_outputs = parse_return_annotation(sig)

    def merge_annotation(sig_ann: Annotation | None, fr_ann: Annotation) -> Annotation:
        if sig_ann is None:
            return fr_ann

        return Annotation(
            has_default_value=fr_ann.has_default_value,
            label=fr_ann.label,
            datatype=sig_ann.datatype,
            unit=sig_ann.unit,
            quantity=sig_ann.quantity,
            description=sig_ann.description,
        )

    metadata.inputs = [
        merge_annotation(sig_ann, fr_inp)
        for sig_ann, fr_inp in zip(sig_inputs, fr_inputs, strict=True)
    ]
    metadata.outputs = [
        merge_annotation(sig_ann, fr_out)
        for sig_ann, fr_out in zip(sig_outputs, fr_outputs, strict=True)
    ]

    uses_import = [
        (label, try_import(node.reference.info.module, node.reference.info.qualname))
        for label, node in recipe.nodes.items()
        if isinstance(node, AtomicRecipe) and node.reference.info.qualname is not None
    ]

    uses_upload = [
        (label, (await upload(settings, ns, child))[0])
        for label, child in uses_import
        if child is not None
    ]

    uses = [
        Reference(label=label, id=atlas_id, count=1)
        for label, response in uses_upload
        if (atlas_id := extract_id(response)) is not None
    ]

    metadata.name = f"{obj.__module__}.{obj.__qualname__}"
    metadata.artifact_type = ArtifactType.WORKFLOW
    metadata.python_import = f"{obj.__module__}.{obj.__qualname__}"
    metadata.category = f"{obj.__module__}".replace(".", ">")
    metadata.keywords = ["flowrep"]
    metadata.uses = uses
    metadata.wf_definition = flowrep_to_wf_definition(recipe, uses)

    await enrich_metadata(settings, metadata)

    return await ns.upload([metadata])


async def parse_workflow_instance(
    settings: ToolkitSettings, wf_instance: DagData, ns: NodeStoreAPI
) -> list[httpx.Response]:
    logger.debug("parsing workflow instance")

    # DagData's generic base (flowrep) doesn't parameterize NodeData[RecipeType],
    # so `.recipe` is unresolved to pyright; cast it back to its real type.
    recipe = cast(WorkflowRecipe, cast(Any, wf_instance).recipe)
    if recipe.reference is None:
        return []
    wf_obj = try_import(recipe.reference.info.module, recipe.reference.info.qualname)
    if wf_obj is None:
        return []
    wf_responses = await upload(settings, ns, wf_obj)
    if len(wf_responses) == 0:
        return []
    wf_id = extract_id(wf_responses[0])
    if wf_id is None:
        return []
    logger.debug(
        f"workflow recipe: status_code {wf_responses[0].status_code}, id {wf_id}"
    )

    inputs = [
        IOValue(label=k, value=v.value)
        for k, v in wf_instance.input_ports.items()
        if isinstance(v.value, (bool, int, float, str))
    ]

    outputs = json.dumps(
        {
            k: v.value
            for k, v in wf_instance.output_ports.items()
            if isinstance(v.value, (bool, int, float, str))
        }
    )

    execution_metadata = ExecutionResultRequest(
        artifact_id=wf_id,
        author_name="Unknown",
        author_email="unknown@example.com",
        inputs=inputs,
        outputs=outputs,
    )
    return [await ns.upload_execution_result(execution_metadata)]


async def parse(
    settings: ToolkitSettings, obj: Any, ns: NodeStoreAPI
) -> list[httpx.Response]:
    if isinstance(obj, DagData):
        return await parse_workflow_instance(settings, obj, ns)

    if not hasattr(obj, "flowrep_recipe"):
        return []

    match obj.flowrep_recipe:
        case AtomicRecipe() as recipe:
            return await parse_atomic_recipe(settings, obj, recipe, ns)

        case WorkflowRecipe() as recipe:
            return await parse_workflow_recipe(settings, obj, recipe, ns)

        case _:
            return []
