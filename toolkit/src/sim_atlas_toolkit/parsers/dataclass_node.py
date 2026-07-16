import dataclasses
import hashlib
import inspect
import textwrap
from http import HTTPStatus
from typing import Any, get_type_hints

import httpx

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.models import (
    Annotation,
    ArtifactType,
    FunctionRequest,
)
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    parse_annotation,
)
from sim_atlas_toolkit.settings import ToolkitSettings


def _field_annotations(cls: type) -> list[Annotation]:
    try:
        hints = get_type_hints(cls, include_extras=True)
    except Exception:
        hints = {}

    result: list[Annotation] = []
    for f in dataclasses.fields(cls):  # type: ignore[arg-type]
        if not f.init:
            continue
        tp = hints.get(f.name)
        has_default = (
            f.default is not dataclasses.MISSING
            or f.default_factory is not dataclasses.MISSING  # type: ignore[misc]
        )
        ann = parse_annotation(tp) if tp is not None else Annotation()
        result.append(
            Annotation(
                label=ann.label if ann.label is not None else f.name,
                datatype=ann.datatype,
                unit=ann.unit,
                quantity=ann.quantity,
                has_default_value=has_default,
            )
        )
    return result


async def parse(settings: ToolkitSettings, obj: Any) -> list[httpx.Response]:
    if not (dataclasses.is_dataclass(obj) and isinstance(obj, type)):
        return []

    module: str = obj.__module__
    qualname: str = obj.__qualname__
    python_import = f"{module}.{qualname}"

    try:
        raw_source = textwrap.dedent(inspect.getsource(obj).replace("\\r\\n", ""))
    except OSError:
        return []

    pack_note = (
        f"# NOTE: This is a virtual PACK node for {qualname}.\n"
        "# It takes the dataclass fields as individual inputs and constructs the dataclass instance.\n"
        "# The source code below is shown for reference only.\n"
    )
    unpack_note = (
        f"# NOTE: This is a virtual UNPACK node for {qualname}.\n"
        "# It takes a dataclass instance as input and exposes its fields as individual outputs.\n"
        "# The source code below is shown for reference only.\n"
    )
    pack_source = pack_note + raw_source
    unpack_source = unpack_note + raw_source

    pack_hash = hashlib.sha256(pack_source.encode("utf-8")).hexdigest()
    unpack_hash = hashlib.sha256(unpack_source.encode("utf-8")).hexdigest()
    response_pack = await node_store_api.read_artifact(settings.api_url, pack_hash)
    response_unpack = await node_store_api.read_artifact(settings.api_url, unpack_hash)
    if (
        response_pack.status_code == HTTPStatus.OK
        and response_unpack.status_code == HTTPStatus.OK
    ):
        return [response_pack, response_unpack]

    category = module.replace(".", ">")

    field_annotations = _field_annotations(obj)
    dataclass_annotation = Annotation(label=qualname.lower(), datatype=python_import)

    pack_metadata = FunctionRequest.model_construct(
        id=pack_hash,
        hash=pack_hash,
        name=f"[PACK] {python_import}",
        artifact_type=ArtifactType.FUNCTION,
        python_import=python_import,
        category=category,
        source_code=pack_source,
        docstring=pack_source,
        keywords=["pack", "dataclass"],
        inputs=field_annotations,
        outputs=[dataclass_annotation],
    )

    raw_doc = inspect.getdoc(obj) or ""
    enrich_from_docstring(raw_doc, pack_metadata)

    unpack_metadata = FunctionRequest.model_construct(
        id=unpack_hash,
        hash=unpack_hash,
        name=f"[UNPACK] {python_import}",
        artifact_type=ArtifactType.FUNCTION,
        python_import=python_import,
        category=category,
        source_code=unpack_source,
        docstring=unpack_source,
        keywords=["unpack", "dataclass"],
        inputs=pack_metadata.outputs,
        outputs=pack_metadata.inputs,
    )

    return await node_store_api.create_artifacts(
        settings.api_url, settings.api_token, [pack_metadata, unpack_metadata]
    )
