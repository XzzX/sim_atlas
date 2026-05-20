import dataclasses
import inspect
import textwrap
from typing import Any, get_type_hints

from ..models import Annotation, NodeType
from .metadata import Metadata, parse_annotation


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


def parse(obj: Any) -> list[Metadata]:
    if not (dataclasses.is_dataclass(obj) and isinstance(obj, type)):
        return []

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

    module: str = obj.__module__
    qualname: str = obj.__qualname__
    python_import = f"{module}.{qualname}"
    category = module.replace(".", ">")
    keywords = module.split(".")
    raw_doc = inspect.getdoc(obj) or ""

    field_annotations = _field_annotations(obj)
    dataclass_annotation = Annotation(label=qualname, datatype=python_import)

    return [
        Metadata(
            name=f"[PACK] {python_import}",
            node_type=NodeType.PACK,
            python_import=python_import,
            category=category,
            source_code=pack_source,
            docstring=f"[PACK] {qualname}: {raw_doc}",
            keywords=keywords,
            inputs=field_annotations,
            outputs=[dataclass_annotation],
        ),
        Metadata(
            name=f"[UNPACK] {python_import}",
            node_type=NodeType.UNPACK,
            python_import=python_import,
            category=category,
            source_code=unpack_source,
            docstring=f"[UNPACK] {qualname}: {raw_doc}",
            keywords=keywords,
            inputs=[dataclass_annotation],
            outputs=field_annotations,
        ),
    ]
