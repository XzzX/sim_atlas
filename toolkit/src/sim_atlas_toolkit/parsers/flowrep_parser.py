import inspect
from typing import Annotated, Any, get_args, get_origin

from ..models import Annotation, ArtifactType
from .metadata import (
    Metadata,
    enrich_from_docstring,
    parse_annotation,
    parse_return_annotation,
    parse_signature,
)


def _parse_arguments(sig: inspect.Signature) -> list[Annotation]:
    arguments: list[Annotation] = []
    for param_name, param in sig.parameters.items():
        ann = parse_annotation(param.annotation)
        ann.label = param_name
        arguments.append(ann)
    return arguments


def _parse_and_unpack_annotation(annotation: Any) -> list[Annotation]:
    origin = get_origin(annotation)
    args = get_args(annotation)

    # unpack one level of Annotated
    if origin is Annotated:
        origin = get_origin(args[0])
        args = get_args(args[0])

    if origin is tuple:
        annotations: list[Annotation] = []
        for i, arg in enumerate(args):
            ann = parse_annotation(arg)
            ann.label = ann.label if ann.label is not None else str(i)
            annotations.append(ann)
        return annotations

    ann = parse_annotation(annotation)
    if not ann.label:
        ann.label = "return"
    return [ann]


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
            enrich_from_docstring(docstring, inputs, outputs)
            return [
                Metadata(
                    name=f"{obj.__module__}.{obj.__qualname__}",
                    artifact_type=ArtifactType.FUNCTION,
                    python_import=f"{obj.__module__}.{obj.__qualname__}",
                    category=f"{obj.__module__}".replace(".", ">"),
                    source_code=source_code,
                    docstring=docstring,
                    keywords=[],
                    inputs=inputs,
                    outputs=outputs,
                )
            ]
        case _:
            return []
