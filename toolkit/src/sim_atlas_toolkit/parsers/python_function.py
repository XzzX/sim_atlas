import hashlib
import inspect
import textwrap
from collections.abc import Mapping
from typing import Any

from sim_atlas_models import ArtifactType, NodeRequest

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.node_store import NodeResult, NodeStatus
from sim_atlas_toolkit.parsers.ai_enrichment import generate_docstring
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    parse_return_annotation,
    parse_signature,
    self_contain_source,
)
from sim_atlas_toolkit.plugin import (
    Description,
    Enrichment,
    Identity,
    NodeDraft,
    ResolvedChild,
)
from sim_atlas_toolkit.provenance import apply_provenance


async def parse(ctx: ParseContext, obj: Any) -> list[NodeResult]:
    if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
        return []

    metadata = NodeRequest.model_construct(artifact_type=ArtifactType.FUNCTION)

    if inspect.isbuiltin(obj):
        source_code = f"{obj.__name__}{inspect.signature(obj)}"
    else:
        source_code = inspect.getsource(obj)
    metadata.source_code = textwrap.dedent(source_code.replace("\\r\\n", ""))
    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()
    metadata.hash = hash
    metadata.id = hash

    if (existing := await ctx.store.read_node(hash)) is not None:
        return [NodeResult(status=NodeStatus.EXISTS, node=existing)]

    metadata.name = f"{obj.__module__}.{obj.__qualname__}"
    metadata.python_import = f"{obj.__module__}.{obj.__qualname__}"
    metadata.category = f"{obj.__module__}".replace(".", ">")
    metadata.source_code = source_code
    metadata.docstring = inspect.getdoc(obj) or ""
    metadata.keywords = ["python"]
    apply_provenance(metadata, obj.__module__)

    sig = inspect.signature(obj)
    metadata.inputs = parse_signature(sig)
    metadata.outputs = parse_return_annotation(sig)

    metadata.docstring = await generate_docstring(
        ctx, metadata.source_code, metadata.docstring
    )
    enrich_from_docstring(metadata.docstring, metadata)
    metadata.source_code = self_contain_source(ctx.settings, obj, metadata.source_code)

    return await ctx.store.create_nodes([metadata])


class PythonFunctionParser:
    """Two-phase parser for plain Python functions and builtins (ADR-0025)."""

    name = "python_function"

    def identify(self, obj: Any) -> Identity | None:
        if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
            return None
        if inspect.isbuiltin(obj):
            source_code = f"{obj.__name__}{inspect.signature(obj)}"
        else:
            source_code = inspect.getsource(obj)
        # The id hashes the dedented source, while the node stores the source
        # as found; keep both exactly as the legacy ``parse`` does.
        dedented = textwrap.dedent(source_code.replace("\\r\\n", ""))
        node_id = hashlib.sha256(dedented.encode("utf-8")).hexdigest()
        return Identity(node_ids=(node_id,), data=source_code)

    def describe(
        self, obj: Any, identity: Identity, children: Mapping[str, ResolvedChild]
    ) -> Description:
        (node_id,) = identity.node_ids
        sig = inspect.signature(obj)
        metadata = NodeRequest.model_construct(
            artifact_type=ArtifactType.FUNCTION,
            id=node_id,
            hash=node_id,
            name=f"{obj.__module__}.{obj.__qualname__}",
            python_import=f"{obj.__module__}.{obj.__qualname__}",
            category=f"{obj.__module__}".replace(".", ">"),
            source_code=identity.data,
            docstring=inspect.getdoc(obj) or "",
            keywords=["python"],
            inputs=parse_signature(sig),
            outputs=parse_return_annotation(sig),
        )
        apply_provenance(metadata, obj.__module__)
        return Description(
            nodes=[NodeDraft(metadata, Enrichment.FUNCTION, source_obj=obj)]
        )
