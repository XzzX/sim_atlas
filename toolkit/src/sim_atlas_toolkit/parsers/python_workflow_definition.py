import hashlib
from collections.abc import Mapping
from typing import Any

from sim_atlas_models import (
    Annotation,
    ArtifactType,
    NodeRequest,
)

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.node_store import NodeResult
from sim_atlas_toolkit.parsers.metadata import content_hash
from sim_atlas_toolkit.plugin import (
    Description,
    Enrichment,
    Identity,
    NodeDraft,
    ResolvedChild,
)


async def parse(ctx: ParseContext, obj: Any) -> list[NodeResult]:
    try:
        from python_workflow_definition.models import (  # noqa: PLC0415
            PythonWorkflowDefinitionInputNode,
            PythonWorkflowDefinitionOutputNode,
            PythonWorkflowDefinitionWorkflow,
        )
    except ImportError:
        return []

    if not isinstance(obj, PythonWorkflowDefinitionWorkflow):
        return []

    metadata = NodeRequest.model_construct(artifact_type=ArtifactType.FUNCTION)

    metadata.source_code = obj.model_dump_json(indent=2)
    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()
    metadata.hash = hash
    metadata.id = hash

    metadata.inputs = []
    metadata.outputs = []
    for node in obj.nodes:
        if isinstance(node, PythonWorkflowDefinitionInputNode):
            ann = Annotation(label=node.name)
            metadata.inputs.append(ann)
        if isinstance(node, PythonWorkflowDefinitionOutputNode):
            ann = Annotation(label=node.name)
            metadata.outputs.append(ann)

    metadata.name = "python_workflow_definition_workflow"
    metadata.python_import = ""
    metadata.category = "workflow"
    metadata.docstring = ""
    metadata.keywords = ["python_workflow_definition"]

    return await ctx.store.create_nodes([metadata])


class PythonWorkflowDefinitionParser:
    """Two-phase parser for ``python_workflow_definition`` workflows (ADR-0025)."""

    name = "python_workflow_definition"

    def identify(self, obj: Any) -> Identity | None:
        try:
            from python_workflow_definition.models import (  # noqa: PLC0415
                PythonWorkflowDefinitionWorkflow,
            )
        except ImportError:
            return None
        if not isinstance(obj, PythonWorkflowDefinitionWorkflow):
            return None
        source_code = obj.model_dump_json(indent=2)
        return Identity(node_ids=(content_hash(source_code),), data=source_code)

    def describe(
        self, obj: Any, identity: Identity, children: Mapping[str, ResolvedChild]
    ) -> Description:
        from python_workflow_definition.models import (  # noqa: PLC0415
            PythonWorkflowDefinitionInputNode,
            PythonWorkflowDefinitionOutputNode,
        )

        (node_id,) = identity.node_ids
        metadata = NodeRequest.model_construct(
            artifact_type=ArtifactType.FUNCTION,
            id=node_id,
            hash=node_id,
            source_code=identity.data,
            inputs=[
                Annotation(label=node.name)
                for node in obj.nodes
                if isinstance(node, PythonWorkflowDefinitionInputNode)
            ],
            outputs=[
                Annotation(label=node.name)
                for node in obj.nodes
                if isinstance(node, PythonWorkflowDefinitionOutputNode)
            ],
            name="python_workflow_definition_workflow",
            python_import="",
            category="workflow",
            docstring="",
            keywords=["python_workflow_definition"],
        )
        return Description(nodes=[NodeDraft(metadata, Enrichment.NONE)])
