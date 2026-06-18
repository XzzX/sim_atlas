# pyright: basic
from __future__ import annotations

import dataclasses
import inspect
import textwrap
from typing import Any, get_type_hints

from sim_atlas_toolkit.models import Annotation, ArtifactType
from sim_atlas_toolkit.parsers.metadata import (
    Metadata,
    Reference,
    enrich_from_docstring,
    parse_annotation,
    parse_return_annotation,
    parse_signature,
)

try:
    from core.node import FunctionNode  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    FunctionNode = None

try:
    from core.workflow import Workflow  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    Workflow = None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Function nodes
# ---------------------------------------------------------------------------


def _is_aiflow_function_node(obj: Any) -> bool:
    if hasattr(obj, "_original_func"):
        return True
    if FunctionNode is not None:
        if inspect.isclass(obj) and issubclass(obj, FunctionNode):
            return True
        if isinstance(obj, FunctionNode):
            return True
    return False


def _resolve_func(wrapped: Any) -> tuple[Any, Any]:
    node_instance = None
    func = None

    if hasattr(wrapped, "_original_func"):
        func = wrapped._original_func
    elif hasattr(wrapped, "func"):
        func = wrapped.func
        node_instance = wrapped
    elif (
        FunctionNode is not None
        and inspect.isclass(wrapped)
        and issubclass(wrapped, FunctionNode)
    ):
        node_instance = wrapped()
        func = node_instance.func
    elif callable(wrapped):
        func = wrapped
    else:
        raise TypeError(f"Unsupported object type: {type(wrapped)!r}")

    if func is None:
        raise ValueError("Could not resolve original function.")

    if node_instance is None and inspect.isclass(wrapped):
        try:
            node_instance = wrapped()
        except Exception:
            node_instance = None

    return func, node_instance


def parse_function_node(obj: Any) -> list[Metadata]:
    try:
        func, node_instance = _resolve_func(obj)
    except (TypeError, ValueError):
        return []

    try:
        source_code = textwrap.dedent(inspect.getsource(func).replace("\r\n", ""))
    except OSError:
        return []

    sig = inspect.signature(func)
    inputs = parse_signature(sig)
    for ann, param in zip(inputs, sig.parameters.values(), strict=False):
        ann.has_default_value = param.default is not inspect.Parameter.empty

    if (
        node_instance is not None
        and hasattr(node_instance, "outputs")
        and hasattr(node_instance.outputs, "ports")
    ):
        port_names = list(node_instance.outputs.ports.keys())
        return_anns = parse_return_annotation(sig)
        outputs: list[Annotation] = []
        for i, name in enumerate(port_names):
            ann = return_anns[i] if i < len(return_anns) else Annotation()
            ann.label = name
            outputs.append(ann)
    else:
        outputs = parse_return_annotation(sig)

    module = getattr(func, "__module__", "") or ""
    qualname = getattr(func, "__qualname__", func.__name__)

    metadata = Metadata(
        name=f"{module}.{qualname}",
        artifact_type=ArtifactType.FUNCTION,
        python_import=f"{module}.{qualname}",
        category=module.replace(".", ">"),
        source_code=source_code,
        docstring=inspect.getdoc(func) or "",
        keywords=[],
        inputs=inputs,
        outputs=outputs,
    )

    enrich_from_docstring(inspect.getdoc(func) or "", metadata)

    return [metadata]


# ---------------------------------------------------------------------------
# Dataclass nodes
# ---------------------------------------------------------------------------


def parse_inp_dataclass_node(obj: Any) -> list[Metadata]:
    original_cls = getattr(obj, "_original_dataclass", None)
    if original_cls is None or not (
        dataclasses.is_dataclass(original_cls) and isinstance(original_cls, type)
    ):
        return []

    try:
        raw_source = textwrap.dedent(
            inspect.getsource(original_cls).replace("\r\n", "")
        )
    except OSError:
        return []

    module: str = original_cls.__module__
    qualname: str = original_cls.__qualname__
    python_import = f"{module}.{qualname}"
    raw_doc = inspect.getdoc(original_cls) or ""

    field_anns = _field_annotations(original_cls)
    dataclass_ann = Annotation(label="output", datatype=python_import)

    metadata = Metadata(
        name=f"[INP] {python_import}",
        artifact_type=ArtifactType.FUNCTION,
        python_import=python_import,
        category=module.replace(".", ">"),
        source_code=raw_source,
        docstring=f"[INP] {qualname}: {raw_doc}",
        keywords=["inp_dataclass_node"],
        inputs=field_anns,
        outputs=[dataclass_ann],
    )

    enrich_from_docstring(raw_doc, metadata)

    return [metadata]


def parse_out_dataclass_node(obj: Any) -> list[Metadata]:
    original_cls = getattr(obj, "_original_dataclass", None)
    if original_cls is None or not (
        dataclasses.is_dataclass(original_cls) and isinstance(original_cls, type)
    ):
        return []

    try:
        raw_source = textwrap.dedent(
            inspect.getsource(original_cls).replace("\r\n", "")
        )
    except OSError:
        return []

    module: str = original_cls.__module__
    qualname: str = original_cls.__qualname__
    python_import = f"{module}.{qualname}"
    raw_doc = inspect.getdoc(original_cls) or ""

    field_anns = _field_annotations(original_cls)
    dataclass_ann = Annotation(label="input", datatype=python_import)

    metadata = Metadata(
        name=f"[OUT] {python_import}",
        artifact_type=ArtifactType.FUNCTION,
        python_import=python_import,
        category=module.replace(".", ">"),
        source_code=raw_source,
        docstring=f"[OUT] {qualname}: {raw_doc}",
        keywords=["out_dataclass_node"],
        inputs=[dataclass_ann],
        outputs=field_anns,
    )

    enrich_from_docstring(raw_doc, metadata)

    return [metadata]


# ---------------------------------------------------------------------------
# Workflow instances
# ---------------------------------------------------------------------------


def _is_aiflow_workflow(obj: Any) -> bool:
    """Return True if *obj* is an aiflow Workflow instance.

    Performs an ``isinstance`` check against ``core.workflow.Workflow`` when
    that class is importable, and falls back to duck-typing otherwise: the
    object must not be a class, must not be a function node, and must expose
    ``inputs.ports``, ``outputs.ports``, and a ``nodes`` dict.
    """
    if Workflow is not None and isinstance(obj, Workflow):
        return True
    return (
        not inspect.isclass(obj)
        and not _is_aiflow_function_node(obj)
        and hasattr(obj, "inputs")
        and hasattr(getattr(obj, "inputs", None), "ports")
        and hasattr(obj, "outputs")
        and hasattr(getattr(obj, "outputs", None), "ports")
        and isinstance(getattr(obj, "nodes", None), dict)
    )


def parse_workflow(obj: Any) -> list[Metadata]:
    """Parse an aiflow ``Workflow`` instance into a :class:`Metadata` record.

    Extracts inputs and outputs from ``obj.inputs.ports`` / ``obj.outputs.ports``
    and collects child nodes from ``obj.nodes`` as :class:`Reference` entries,
    mirroring the representation produced by the flowrep workflow parser.
    """
    cls = type(obj)
    module: str = getattr(cls, "__module__", "") or ""
    qualname: str = getattr(cls, "__qualname__", None) or getattr(cls, "__name__", "Workflow")

    try:
        source_code = textwrap.dedent(inspect.getsource(cls).replace("\r\n", ""))
    except OSError:
        source_code = ""

    docstring = inspect.getdoc(obj) or inspect.getdoc(cls) or ""

    inputs: list[Annotation] = []
    inputs_obj = getattr(obj, "inputs", None)
    if inputs_obj is not None and hasattr(inputs_obj, "ports"):
        for port_name in inputs_obj.ports:
            inputs.append(Annotation(label=str(port_name)))

    outputs: list[Annotation] = []
    outputs_obj = getattr(obj, "outputs", None)
    if outputs_obj is not None and hasattr(outputs_obj, "ports"):
        for port_name in outputs_obj.ports:
            outputs.append(Annotation(label=str(port_name)))

    children: list[Reference] = []
    for label, node in (getattr(obj, "nodes", None) or {}).items():
        children.append(Reference(label=str(label), obj=node))

    name = f"{module}.{qualname}" if module else qualname

    metadata = Metadata(
        name=name,
        artifact_type=ArtifactType.WORKFLOW,
        python_import=name,
        category=module.replace(".", ">"),
        source_code=source_code,
        docstring=docstring,
        keywords=["aiflow"],
        inputs=inputs,
        outputs=outputs,
        children=children,
    )

    enrich_from_docstring(docstring, metadata)

    return [metadata]


def parse(obj: Any) -> list[Metadata]:
    """Parse an aiflow object and return a list of :class:`Metadata` records.

    Supported input forms:

    * **FunctionNode** – a ``FunctionNode`` subclass or instance (including
      objects with a ``_original_func`` attribute).
    * **Workflow instance** – an instance of ``core.workflow.Workflow`` (or
      any object that duck-types as one: non-class, non-function-node, with
      ``inputs.ports``, ``outputs.ports``, and a ``nodes`` dict).
    * **inp_dataclass_node** – an object with ``node_type == "inp_dataclass_node"``
      and a ``_original_dataclass`` attribute pointing at a dataclass type.
    * **out_dataclass_node** – an object with ``node_type == "out_dataclass_node"``
      and a ``_original_dataclass`` attribute pointing at a dataclass type.
    """
    if _is_aiflow_function_node(obj):
        return parse_function_node(obj)

    if _is_aiflow_workflow(obj):
        return parse_workflow(obj)

    node_type = getattr(obj, "node_type", None)

    if node_type == "inp_dataclass_node":
        return parse_inp_dataclass_node(obj)

    if node_type == "out_dataclass_node":
        return parse_out_dataclass_node(obj)

    return []
