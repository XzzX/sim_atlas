# pyright: basic

import hashlib
import inspect
from collections.abc import Mapping
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from sim_atlas_models import (
    ArtifactType,
    NodeRequest,
)

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.node_store import NodeResult
from sim_atlas_toolkit.parsers.ai_enrichment import generate_docstring
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    parse_annotation,
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

# The legacy node API (``Function``, ``NOT_DATA``) moved under ``pyiron_workflow._legacy``
# in 0.18; from there on nodes are flowrep recipes and are handled by ``flowrep_parser``.
_MAX_VERSION = (0, 18)


def supports_legacy_api(raw_version: str) -> bool:
    major, _, rest = raw_version.partition(".")
    minor, _, _ = rest.partition(".")
    try:
        return (int(major), int(minor)) < _MAX_VERSION
    except ValueError:
        return False


@cache
def _legacy_api_available() -> bool:
    try:
        installed = version("pyiron_workflow")
    except PackageNotFoundError:
        return False
    return supports_legacy_api(installed)


async def parse(ctx: ParseContext, node: Any) -> list[NodeResult]:
    if not isinstance(node, type):
        return []

    if not _legacy_api_available():
        return []

    # Unresolvable when a >=0.18 pyiron_workflow is installed, which is exactly what
    # the version guard above rules out; the ImportError branch covers it at runtime.
    try:
        from pyiron_workflow.api import (  # noqa: PLC0415
            NOT_DATA,  # pyright: ignore[reportAttributeAccessIssue]
        )
        from pyiron_workflow.nodes.function import (  # noqa: PLC0415 # pyright: ignore[reportMissingImports]
            Function,
        )
    except ImportError:
        return []

    if not issubclass(node, Function):
        return []

    metadata = NodeRequest.model_construct(artifact_type=ArtifactType.FUNCTION)

    metadata.source_code = inspect.getsource(node.node_function)
    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()
    metadata.hash = hash
    metadata.id = hash

    metadata.inputs = []
    metadata.outputs = []
    for k, v in node.preview_inputs().items():
        ann = parse_annotation(v[0])
        ann.label = k
        ann.has_default_value = v[1] != NOT_DATA
        metadata.inputs.append(ann)
    for k, v in node.preview_outputs().items():
        ann = parse_annotation(v)
        ann.label = k
        metadata.outputs.append(ann)

    metadata.name = f"{node.node_function.__module__}.{node.node_function.__qualname__}"
    metadata.python_import = (
        f"{node.node_function.__module__}.{node.node_function.__qualname__}"
    )
    metadata.category = f"{node.node_function.__module__}".replace(".", ">")
    metadata.docstring = node.node_function.__doc__ or ""
    metadata.keywords = ["pyiron_workflow_function"]
    apply_provenance(metadata, node.node_function.__module__)

    metadata.docstring = await generate_docstring(
        ctx, metadata.source_code, metadata.docstring
    )
    enrich_from_docstring(metadata.docstring, metadata)
    metadata.source_code = self_contain_source(
        ctx.settings, node.node_function, metadata.source_code
    )

    return await ctx.store.create_nodes([metadata])


def _legacy_function_class() -> Any | None:
    """``pyiron_workflow``'s legacy ``Function`` node class, if usable."""
    if not _legacy_api_available():
        return None
    try:
        from pyiron_workflow.nodes.function import (  # noqa: PLC0415 # pyright: ignore[reportMissingImports]
            Function,
        )
    except ImportError:
        return None
    return Function


class PyironWorkflowParser:
    """Two-phase parser for legacy ``pyiron_workflow`` function nodes (ADR-0025)."""

    name = "pyiron_workflow"

    def identify(self, obj: Any) -> Identity | None:
        if not isinstance(obj, type):
            return None
        function_class = _legacy_function_class()
        if function_class is None or not issubclass(obj, function_class):
            return None
        source_code = inspect.getsource(obj.node_function)
        node_id = hashlib.sha256(source_code.encode("utf-8")).hexdigest()
        return Identity(node_ids=(node_id,), data=source_code)

    def describe(
        self, obj: Any, identity: Identity, children: Mapping[str, ResolvedChild]
    ) -> Description:
        from pyiron_workflow.api import (  # noqa: PLC0415
            NOT_DATA,  # pyright: ignore[reportAttributeAccessIssue]
        )

        (node_id,) = identity.node_ids
        function = obj.node_function
        inputs = []
        for k, v in obj.preview_inputs().items():
            ann = parse_annotation(v[0])
            ann.label = k
            ann.has_default_value = v[1] != NOT_DATA
            inputs.append(ann)
        outputs = []
        for k, v in obj.preview_outputs().items():
            ann = parse_annotation(v)
            ann.label = k
            outputs.append(ann)

        metadata = NodeRequest.model_construct(
            artifact_type=ArtifactType.FUNCTION,
            id=node_id,
            hash=node_id,
            source_code=identity.data,
            inputs=inputs,
            outputs=outputs,
            name=f"{function.__module__}.{function.__qualname__}",
            python_import=f"{function.__module__}.{function.__qualname__}",
            category=f"{function.__module__}".replace(".", ">"),
            docstring=function.__doc__ or "",
            keywords=["pyiron_workflow_function"],
        )
        apply_provenance(metadata, function.__module__)
        return Description(
            nodes=[NodeDraft(metadata, Enrichment.FUNCTION, source_obj=function)]
        )
