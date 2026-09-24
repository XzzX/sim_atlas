import contextlib
import hashlib
import inspect
import json
import logging
from typing import Any, cast

import flowrep as fr
from flowrep.api.schemas import (
    AtomicRecipe,
    InputSource,
    NotData,
    WorkflowRecipe,
)
from flowrep.retrospective.datastructures import DagData

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.models import (
    Annotation,
    ArtifactType,
    ExecutionResultRequest,
    IOValue,
    NodeRequest,
    Reference,
    WfDefinition,
    WfEdge,
    WfFunctionNode,
    WfInputNode,
    WfNode,
    WfOutputNode,
)
from sim_atlas_toolkit.node_store import NodeResult, NodeStatus
from sim_atlas_toolkit.parsers.ai_enrichment import (
    generate_docstring,
    generate_workflow_docstring,
)
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    parse_return_annotation,
    parse_signature,
    try_import,
)
from sim_atlas_toolkit.provenance import apply_provenance
from sim_atlas_toolkit.uploader import upload

logger = logging.getLogger(__name__)


def flowrep_to_wf_definition(
    wf: WorkflowRecipe, references: list[Reference]
) -> WfDefinition:
    reference_dict = {ref.label: ref.id for ref in references}

    nodes: list[WfNode] = []
    for node_id, node in wf.nodes.items():
        match node:
            case AtomicRecipe() | WorkflowRecipe():
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
    ctx: ParseContext,
    obj: Any,
    recipe: AtomicRecipe,
) -> list[NodeResult]:
    metadata = NodeRequest.model_construct(artifact_type=ArtifactType.FUNCTION)
    metadata.source_code = inspect.getsource(obj) or ""
    metadata.docstring = inspect.getdoc(obj) or ""

    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()
    if (existing := await ctx.store.read_node(hash)) is not None:
        return [NodeResult(status=NodeStatus.EXISTS, node=existing)]
    metadata.hash = hash
    metadata.id = hash

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
    metadata.outputs = (
        [
            merge_annotation(sig_ann, fr_out)
            for sig_ann, fr_out in zip(sig_outputs, fr_outputs, strict=True)
        ]
        if len(sig_outputs) == len(fr_outputs)
        else fr_outputs
    )

    metadata.name = f"{obj.__module__}.{obj.__qualname__}"
    metadata.python_import = f"{obj.__module__}.{obj.__qualname__}"
    metadata.category = f"{obj.__module__}".replace(".", ">")
    metadata.keywords = ["flowrep"]
    apply_provenance(metadata, obj.__module__)

    metadata.docstring = await generate_docstring(
        ctx, metadata.source_code, metadata.docstring
    )
    enrich_from_docstring(metadata.docstring, metadata)
    return await ctx.store.create_nodes([metadata])


async def parse_workflow_recipe(
    ctx: ParseContext,
    obj: Any,
    recipe: WorkflowRecipe,
) -> list[NodeResult]:
    unreferenced_recipe = recipe.model_copy(update={"reference": None})
    rendered = fr.tools.flowrep2python(unreferenced_recipe)

    metadata = NodeRequest.model_construct(artifact_type=ArtifactType.WORKFLOW)
    metadata.source_code = rendered.source
    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()

    if (existing := await ctx.store.read_node(hash)) is not None:
        return [NodeResult(status=NodeStatus.EXISTS, node=existing)]

    metadata.hash = hash
    metadata.id = hash

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
    metadata.outputs = (
        [
            merge_annotation(sig_ann, fr_out)
            for sig_ann, fr_out in zip(sig_outputs, fr_outputs, strict=True)
        ]
        if len(sig_outputs) == len(fr_outputs)
        else fr_outputs
    )

    uses_import = [
        (label, try_import(node.reference.info.module, node.reference.info.qualname))
        for label, node in recipe.nodes.items()
        if isinstance(node, (AtomicRecipe, WorkflowRecipe))
        and node.reference is not None
        and node.reference.info.qualname is not None
    ]

    uses_upload = [
        (label, (await upload(ctx, child))[0])
        for label, child in uses_import
        if child is not None
    ]

    uses = [
        Reference(label=label, id=result.node.id, count=1)
        for label, result in uses_upload
    ]

    metadata.name = f"{obj.__module__}.{obj.__qualname__}"
    metadata.python_import = f"{obj.__module__}.{obj.__qualname__}"
    metadata.category = f"{obj.__module__}".replace(".", ">")
    metadata.keywords = ["flowrep"]
    apply_provenance(metadata, obj.__module__)
    metadata.uses = uses
    with contextlib.suppress(Exception):
        metadata.wf_definition = flowrep_to_wf_definition(recipe, uses)

    metadata.docstring = await generate_workflow_docstring(
        ctx,
        metadata.name,
        metadata.source_code,
        metadata.docstring or "",
        metadata.wf_definition,
    )
    enrich_from_docstring(metadata.docstring, metadata)

    return await ctx.store.create_nodes([metadata])


async def parse_workflow_instance(
    ctx: ParseContext,
    wf_instance: DagData,
) -> list[NodeResult]:
    logger.debug("parsing workflow instance")

    # DagData's generic base (flowrep) doesn't parameterize NodeData[RecipeType],
    # so `.recipe` is unresolved to pyright; cast it back to its real type.
    recipe = cast(WorkflowRecipe, cast(Any, wf_instance).recipe)
    if recipe.reference is None:
        return []
    wf_obj = try_import(recipe.reference.info.module, recipe.reference.info.qualname)
    if wf_obj is None:
        return []
    wf_results = await upload(ctx, wf_obj)
    if len(wf_results) == 0:
        return []
    wf_result = wf_results[0]
    logger.debug(f"workflow recipe: status {wf_result.status}, id {wf_result.node.id}")

    inputs = [
        IOValue(label=k, value=v.value)
        for k, v in wf_instance.input_ports.items()
        if isinstance(v.value, (bool, int, float, str))
    ]

    outputs = json.dumps(
        {
            k: v.value
            for k, v in wf_instance.output_ports.items()
            if not isinstance(v.value, NotData)
        },
        default=str,
    )

    execution_metadata = ExecutionResultRequest(
        artifact_id=wf_result.node.id,
        author_name="Unknown",
        author_email="unknown@example.com",
        inputs=inputs,
        outputs=outputs,
    )
    # The execution result is a side effect of parsing the instance; the
    # workflow node this run executed is what the pipeline reports upward.
    await ctx.store.create_execution_result(execution_metadata)
    return wf_results


async def parse(
    ctx: ParseContext,
    obj: Any,
) -> list[NodeResult]:
    if isinstance(obj, DagData):
        return await parse_workflow_instance(ctx, obj)

    match getattr(obj, "flowrep_recipe", None):
        case AtomicRecipe() as recipe:
            return await parse_atomic_recipe(ctx, obj, recipe)

        case WorkflowRecipe() as recipe:
            return await parse_workflow_recipe(ctx, obj, recipe)

        case _:
            pass

    try:
        if inspect.isfunction(obj):
            recipe = fr.parse_atomic(obj)
            return await parse_atomic_recipe(ctx, obj, recipe)
    except Exception:
        return []

    return []
