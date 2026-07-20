import hashlib
import inspect
import textwrap
from http import HTTPStatus
from typing import Any

import httpx

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.models import FunctionRequest
from sim_atlas_toolkit.parsers.ai_enrichment import generate_docstring
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    parse_return_annotation,
    parse_signature,
)
from sim_atlas_toolkit.settings import ToolkitSettings


async def parse(settings: ToolkitSettings, obj: Any) -> list[httpx.Response]:
    if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
        return []

    metadata = FunctionRequest.model_construct()

    if inspect.isbuiltin(obj):
        source_code = f"{obj.__name__}{inspect.signature(obj)}"
    else:
        source_code = inspect.getsource(obj)
    metadata.source_code = textwrap.dedent(source_code.replace("\\r\\n", ""))
    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()
    metadata.hash = hash
    metadata.id = hash

    response = await node_store_api.read_artifact(settings.api_url, hash)
    if response.status_code == HTTPStatus.OK:
        return [response]

    metadata.name = f"{obj.__module__}.{obj.__qualname__}"
    metadata.python_import = f"{obj.__module__}.{obj.__qualname__}"
    metadata.category = f"{obj.__module__}".replace(".", ">")
    metadata.source_code = source_code
    metadata.docstring = inspect.getdoc(obj) or ""
    metadata.keywords = ["python"]

    sig = inspect.signature(obj)
    metadata.inputs = parse_signature(sig)
    metadata.outputs = parse_return_annotation(sig)

    metadata.docstring = await generate_docstring(
        settings, metadata.source_code, metadata.docstring
    )
    enrich_from_docstring(metadata.docstring, metadata)

    return await node_store_api.create_artifacts(
        settings.api_url, settings.api_token, [metadata]
    )
