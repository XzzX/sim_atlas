import inspect
import textwrap
from typing import Any

from sim_atlas_toolkit.models import ArtifactType
from sim_atlas_toolkit.parsers.metadata import (
    Metadata,
    enrich_from_docstring,
    parse_return_annotation,
    parse_signature,
)


def parse(obj: Any) -> list[Metadata]:
    if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
        return []

    if inspect.isbuiltin(obj):
        source_code = f"{obj.__name__}{inspect.signature(obj)}"
    else:
        source_code = inspect.getsource(obj)
    source_code = textwrap.dedent(source_code.replace("\\r\\n", ""))

    sig = inspect.signature(obj)
    inputs = parse_signature(sig)
    outputs = parse_return_annotation(sig)

    metadata = Metadata(
        name=f"{obj.__module__}.{obj.__qualname__}",
        artifact_type=ArtifactType.FUNCTION,
        python_import=f"{obj.__module__}.{obj.__qualname__}",
        category=f"{obj.__module__}".replace(".", ">"),
        source_code=source_code,
        docstring=inspect.getdoc(obj) or "",
        keywords=[],
        inputs=inputs,
        outputs=outputs,
    )

    enrich_from_docstring(inspect.getdoc(obj) or "", metadata)

    return [metadata]
