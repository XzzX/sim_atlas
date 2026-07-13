import dataclasses
import inspect
import textwrap
from typing import Any, get_type_hints

import httpx

from sim_atlas_toolkit.models import (
    Annotation,
    ArtifactType,
    FunctionRequest,
)
from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.parsers.metadata import (
    enrich_metadata,
    parse_annotation,
)


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


async def parse(obj: Any, ns: NodeStoreAPI) -> list[httpx.Response]:
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

    category = module.replace(".", ">")
    raw_doc = inspect.getdoc(obj) or ""

    field_annotations = _field_annotations(obj)
    dataclass_annotation = Annotation(label=qualname.lower(), datatype=python_import)

    pack_metadata = FunctionRequest.model_construct(
        name=f"[PACK] {python_import}",
        artifact_type=ArtifactType.FUNCTION,
        python_import=python_import,
        category=category,
        source_code=pack_source,
        docstring=raw_doc,
        keywords=["pack", "dataclass"],
        inputs=field_annotations,
        outputs=[dataclass_annotation],
    )

    await enrich_metadata(pack_metadata, ns.enrichment_settings)
    pack_metadata.docstring = f"[PACK] {qualname}: {pack_metadata.docstring}"

    unpack_metadata = FunctionRequest.model_construct(
        name=f"[UNPACK] {python_import}",
        artifact_type=ArtifactType.FUNCTION,
        python_import=python_import,
        category=category,
        source_code=unpack_source,
        docstring=f"[UNPACK] {qualname}: {raw_doc}",
        keywords=["unpack", "dataclass"],
        inputs=pack_metadata.outputs,
        outputs=pack_metadata.inputs,
    )

    return await ns.upload([pack_metadata, unpack_metadata])
