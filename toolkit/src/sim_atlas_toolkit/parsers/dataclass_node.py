import dataclasses
import hashlib
import inspect
import textwrap
from collections.abc import Mapping
from typing import Any, get_type_hints

from sim_atlas_models import (
    Annotation,
    ArtifactType,
    NodeRequest,
)

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.node_store import NodeResult, NodeStatus
from sim_atlas_toolkit.parsers.metadata import (
    content_hash,
    enrich_from_docstring,
    parse_annotation,
)
from sim_atlas_toolkit.plugin import (
    Description,
    Enrichment,
    Identity,
    NodeDraft,
    ResolvedChild,
)
from sim_atlas_toolkit.provenance import apply_provenance


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


async def parse(ctx: ParseContext, obj: Any) -> list[NodeResult]:
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
    existing_pack = await ctx.store.read_node(pack_hash)
    existing_unpack = await ctx.store.read_node(unpack_hash)
    if existing_pack is not None and existing_unpack is not None:
        return [
            NodeResult(status=NodeStatus.EXISTS, node=existing_pack),
            NodeResult(status=NodeStatus.EXISTS, node=existing_unpack),
        ]

    category = module.replace(".", ">")

    field_annotations = _field_annotations(obj)
    dataclass_annotation = Annotation(label=qualname.lower(), datatype=python_import)

    pack_metadata = NodeRequest.model_construct(
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

    apply_provenance(pack_metadata, module)

    raw_doc = inspect.getdoc(obj) or ""
    enrich_from_docstring(raw_doc, pack_metadata)

    unpack_metadata = NodeRequest.model_construct(
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

    apply_provenance(unpack_metadata, module)

    return await ctx.store.create_nodes([pack_metadata, unpack_metadata])


def _virtual_sources(obj: type) -> tuple[str, str] | None:
    """The PACK and UNPACK node sources of dataclass *obj*, or ``None``."""
    try:
        raw_source = textwrap.dedent(inspect.getsource(obj).replace("\\r\\n", ""))
    except OSError:
        return None

    def note(kind: str, what: str) -> str:
        return (
            f"# NOTE: This is a virtual {kind} node for {obj.__qualname__}.\n"
            f"# {what}\n"
            "# The source code below is shown for reference only.\n"
        )

    pack = note(
        "PACK",
        "It takes the dataclass fields as individual inputs and constructs the dataclass instance.",
    )
    unpack = note(
        "UNPACK",
        "It takes a dataclass instance as input and exposes its fields as individual outputs.",
    )
    return pack + raw_source, unpack + raw_source


class DataclassParser:
    """Two-phase parser: a dataclass yields a PACK and an UNPACK node (ADR-0025)."""

    name = "dataclass"

    def identify(self, obj: Any) -> Identity | None:
        if not (dataclasses.is_dataclass(obj) and isinstance(obj, type)):
            return None
        if (sources := _virtual_sources(obj)) is None:
            return None
        node_ids = tuple(content_hash(s) for s in sources)
        return Identity(node_ids=node_ids, data=sources)

    def describe(
        self, obj: Any, identity: Identity, children: Mapping[str, ResolvedChild]
    ) -> Description:
        pack_hash, unpack_hash = identity.node_ids
        pack_source, unpack_source = identity.data
        module: str = obj.__module__
        qualname: str = obj.__qualname__
        python_import = f"{module}.{qualname}"
        category = module.replace(".", ">")

        pack_metadata = NodeRequest.model_construct(
            id=pack_hash,
            hash=pack_hash,
            name=f"[PACK] {python_import}",
            artifact_type=ArtifactType.FUNCTION,
            python_import=python_import,
            category=category,
            source_code=pack_source,
            docstring=pack_source,
            keywords=["pack", "dataclass"],
            inputs=_field_annotations(obj),
            outputs=[Annotation(label=qualname.lower(), datatype=python_import)],
        )
        apply_provenance(pack_metadata, module)
        enrich_from_docstring(inspect.getdoc(obj) or "", pack_metadata)

        unpack_metadata = NodeRequest.model_construct(
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
        apply_provenance(unpack_metadata, module)

        return Description(
            nodes=[
                NodeDraft(pack_metadata, Enrichment.NONE),
                NodeDraft(unpack_metadata, Enrichment.NONE),
            ]
        )
