import importlib
import inspect
from typing import Any

from sim_atlas_toolkit.models import Annotation, ArtifactType
from sim_atlas_toolkit.parsers.metadata import (
    Metadata,
    Reference,
    enrich_from_docstring,
    parse_return_annotation,
    parse_signature,
)


def parse(obj: Any) -> list[Metadata]:
    try:
        from flowrep.api.schemas import (  # noqa: PLC0415
            AtomicRecipe,
            WorkflowRecipe,
        )
    except ImportError:
        return []

    if not hasattr(obj, "flowrep_recipe"):
        return []

    match obj.flowrep_recipe:
        case AtomicRecipe() as recipe:
            source_code = inspect.getsource(obj) or ""
            docstring = inspect.getdoc(obj) or ""

            fr_inputs = [
                Annotation(
                    label=inp,
                    has_default_value=inp in recipe.reference.inputs_with_defaults,
                )
                for inp in recipe.inputs
            ]
            fr_outputs = [Annotation(label=out) for out in recipe.outputs]

            sig = inspect.signature(obj)
            sig_inputs = parse_signature(sig)
            sig_outputs = parse_return_annotation(sig)

            def merge_annotation(
                sig_ann: Annotation | None, fr_ann: Annotation
            ) -> Annotation:
                if sig_ann is None:
                    return fr_ann

                return Annotation(
                    has_default_value=fr_ann.has_default_value,
                    label=fr_ann.label,
                    datatype=sig_ann.datatype,
                    unit=sig_ann.unit,
                    quantity=sig_ann.quantity,
                    description=sig_ann.description,
                )

            inputs = [
                merge_annotation(sig_ann, fr_inp)
                for sig_ann, fr_inp in zip(sig_inputs, fr_inputs, strict=True)
            ]
            outputs = [
                merge_annotation(sig_ann, fr_out)
                for sig_ann, fr_out in zip(sig_outputs, fr_outputs, strict=True)
            ]

            metadata = Metadata(
                name=f"{obj.__module__}.{obj.__qualname__}",
                artifact_type=ArtifactType.FUNCTION,
                python_import=f"{obj.__module__}.{obj.__qualname__}",
                category=f"{obj.__module__}".replace(".", ">"),
                source_code=source_code,
                docstring=docstring,
                inputs=inputs,
                outputs=outputs,
                keywords=["flowrep"],
            )

            enrich_from_docstring(docstring, metadata)
            return [metadata]
        
        case WorkflowRecipe() as recipe:
            source_code = recipe.model_dump_json(indent=2)
            docstring = inspect.getdoc(obj) or ""

            fr_inputs = [
                Annotation(
                    label=inp, has_default_value=inp in recipe.inputs_with_defaults
                )
                for inp in recipe.inputs
            ]
            fr_outputs = [Annotation(label=out) for out in recipe.outputs]

            sig = inspect.signature(obj)
            sig_inputs = parse_signature(sig)
            sig_outputs = parse_return_annotation(sig)

            def merge_annotation(
                sig_ann: Annotation | None, fr_ann: Annotation
            ) -> Annotation:
                if sig_ann is None:
                    return fr_ann

                return Annotation(
                    has_default_value=fr_ann.has_default_value,
                    label=fr_ann.label,
                    datatype=sig_ann.datatype,
                    unit=sig_ann.unit,
                    quantity=sig_ann.quantity,
                    description=sig_ann.description,
                )

            inputs = [
                merge_annotation(sig_ann, fr_inp)
                for sig_ann, fr_inp in zip(sig_inputs, fr_inputs, strict=True)
            ]
            outputs = [
                merge_annotation(sig_ann, fr_out)
                for sig_ann, fr_out in zip(sig_outputs, fr_outputs, strict=True)
            ]

            def try_instantiate(module: str, qualname: str) -> Any | None:
                try:
                    mod = importlib.import_module(module)
                    obj = mod
                    for attr in qualname.split("."):
                        obj = getattr(obj, attr)
                    return obj
                except Exception:
                    return None

            children = [
                Reference(
                    label=label,
                    obj=try_instantiate(
                        node.reference.info.module, node.reference.info.qualname
                    ),
                )
                for label, node in recipe.nodes.items()
                if isinstance(node, AtomicRecipe)
                and node.reference.info.qualname is not None
            ]

            metadata = Metadata(
                name=f"{obj.__module__}.{obj.__qualname__}",
                artifact_type=ArtifactType.FUNCTION,
                python_import=f"{obj.__module__}.{obj.__qualname__}",
                category=f"{obj.__module__}".replace(".", ">"),
                source_code=source_code,
                docstring=docstring,
                inputs=inputs,
                outputs=outputs,
                keywords=["flowrep"],
                children=children,
            )
            return [metadata]
        
        case _:
            return []
