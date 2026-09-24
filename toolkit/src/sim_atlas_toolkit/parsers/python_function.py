import hashlib
import inspect
import textwrap
from typing import Any

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.models import ArtifactType, NodeRequest
from sim_atlas_toolkit.node_store import NodeResult, NodeStatus
from sim_atlas_toolkit.parsers.ai_enrichment import generate_docstring
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    parse_return_annotation,
    parse_signature,
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

    return await ctx.store.create_nodes([metadata])
