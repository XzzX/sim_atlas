# pyright: basic

import hashlib
import inspect
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import httpx2

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.models import (
    ArtifactType,
    FunctionRequest,
)
from sim_atlas_toolkit.parsers.ai_enrichment import generate_docstring
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    parse_annotation,
    self_contain_source,
)
from sim_atlas_toolkit.provenance import apply_provenance
from sim_atlas_toolkit.settings import ToolkitSettings

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


async def parse(settings: ToolkitSettings, node: Any) -> list[httpx2.Response]:
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

    metadata = FunctionRequest.model_construct()

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
    metadata.artifact_type = ArtifactType.FUNCTION
    metadata.python_import = (
        f"{node.node_function.__module__}.{node.node_function.__qualname__}"
    )
    metadata.category = f"{node.node_function.__module__}".replace(".", ">")
    metadata.docstring = node.node_function.__doc__ or ""
    metadata.keywords = ["pyiron_workflow_function"]
    apply_provenance(metadata, node.node_function.__module__)

    metadata.docstring = await generate_docstring(
        settings, metadata.source_code, metadata.docstring
    )
    enrich_from_docstring(metadata.docstring, metadata)
    metadata.source_code = self_contain_source(
        settings, node.node_function, metadata.source_code
    )

    return await node_store_api.create_artifacts(
        settings.api_url, settings.api_token, [metadata]
    )
