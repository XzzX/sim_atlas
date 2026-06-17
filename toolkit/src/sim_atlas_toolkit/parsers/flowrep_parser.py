import inspect
from typing import Any

from sim_atlas_toolkit.models import ArtifactType
from sim_atlas_toolkit.parsers.metadata import (
    Metadata,
    enrich_from_docstring,
    parse_return_annotation,
    parse_signature,
)


def parse(obj: Any) -> list[Metadata]:
    try:
        from flowrep.api.schemas import AtomicRecipe  # noqa: PLC0415
    except ImportError:
        return []

    if not hasattr(obj, "flowrep_recipe"):
        return []

    match obj.flowrep_recipe:
        case AtomicRecipe() as recipe:
            source_code = inspect.getsource(obj) or ""
            docstring = inspect.getdoc(obj) or ""
            sig = inspect.signature(obj)
            inputs = parse_signature(sig)
            outputs = parse_return_annotation(sig)
            for inp, fr_inp in zip(inputs, recipe.inputs, strict=True):
                inp.label = fr_inp
                inp.has_default_value = fr_inp in recipe.reference.inputs_with_defaults
            for out, fr_out in zip(outputs, recipe.outputs, strict=True):
                out.label = fr_out

            metadata = Metadata(
                name=f"{obj.__module__}.{obj.__qualname__}",
                artifact_type=ArtifactType.FUNCTION,
                python_import=f"{obj.__module__}.{obj.__qualname__}",
                category=f"{obj.__module__}".replace(".", ">"),
                source_code=source_code,
                docstring=docstring,
                inputs=inputs,
                outputs=outputs,
                keywords=["flowrep"]
            )

            enrich_from_docstring(docstring, metadata)
            return [metadata]
        case _:
            return []
