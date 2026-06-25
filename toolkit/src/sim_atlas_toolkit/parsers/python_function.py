import inspect
import textwrap
from typing import Any

from sim_atlas_toolkit.models import ArtifactRequest, FunctionRequest
from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    parse_return_annotation,
    parse_signature,
)


def parse(obj: Any, _: NodeStoreAPI) -> list[ArtifactRequest]:
    if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
        return []

    metadata = FunctionRequest.model_construct()

    if inspect.isbuiltin(obj):
        source_code = f"{obj.__name__}{inspect.signature(obj)}"
    else:
        source_code = inspect.getsource(obj)
    source_code = textwrap.dedent(source_code.replace("\\r\\n", ""))

    metadata.name = f"{obj.__module__}.{obj.__qualname__}"
    metadata.python_import = f"{obj.__module__}.{obj.__qualname__}"
    metadata.category = f"{obj.__module__}".replace(".", ">")
    metadata.source_code = source_code
    metadata.docstring = inspect.getdoc(obj) or ""
    metadata.keywords = ["python"]

    sig = inspect.signature(obj)
    metadata.inputs = parse_signature(sig)
    metadata.outputs = parse_return_annotation(sig)

    enrich_from_docstring(inspect.getdoc(obj) or "", metadata)

    return [metadata]
