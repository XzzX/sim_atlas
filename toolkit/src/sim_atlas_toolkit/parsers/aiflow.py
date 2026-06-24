# pyright: basic
from __future__ import annotations

import dataclasses
import inspect
import textwrap
from http import HTTPStatus
from typing import Any, get_type_hints

from requests import Response

from sim_atlas_toolkit import upload
from sim_atlas_toolkit.models import (
    Annotation,
    ArtifactRequest,
    ArtifactType,
    FunctionRequest,
    Reference,
    WorkflowRequest,
)
from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    parse_annotation,
    parse_return_annotation,
    parse_signature,
)

try:
    from core.node import FunctionNode  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    FunctionNode = None


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


def parse_function_node(obj: Any) -> FunctionRequest | None:
    try:
        func, node_instance = _resolve_func(obj)
    except (TypeError, ValueError):
        return None

    try:
        source_code = textwrap.dedent(inspect.getsource(func).replace("\r\n", ""))
    except OSError:
        return None

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

    metadata = FunctionRequest.model_construct()
    metadata.name = f"{module}.{qualname}"
    metadata.artifact_type = ArtifactType.FUNCTION
    metadata.python_import = f"{module}.{qualname}"
    metadata.category = module.replace(".", ">")
    metadata.source_code = source_code
    metadata.docstring = inspect.getdoc(func) or ""
    metadata.keywords = []
    metadata.inputs = inputs
    metadata.outputs = outputs

    enrich_from_docstring(inspect.getdoc(func) or "", metadata)

    return metadata


# ---------------------------------------------------------------------------
# Dataclass nodes
# ---------------------------------------------------------------------------


def parse_inp_dataclass_node(obj: Any) -> FunctionRequest | None:
    original_cls = getattr(obj, "_original_dataclass", None)
    if original_cls is None or not (
        dataclasses.is_dataclass(original_cls) and isinstance(original_cls, type)
    ):
        return None

    try:
        raw_source = textwrap.dedent(
            inspect.getsource(original_cls).replace("\r\n", "")
        )
    except OSError:
        return None

    module: str = original_cls.__module__
    qualname: str = original_cls.__qualname__
    python_import = f"{module}.{qualname}"
    raw_doc = inspect.getdoc(original_cls) or ""

    field_anns = _field_annotations(original_cls)
    dataclass_ann = Annotation(label="output", datatype=python_import)

    metadata = FunctionRequest.model_construct()
    metadata.name = f"[INP] {python_import}"
    metadata.artifact_type = ArtifactType.FUNCTION
    metadata.python_import = python_import
    metadata.category = module.replace(".", ">")
    metadata.source_code = raw_source
    metadata.docstring = f"[INP] {qualname}: {raw_doc}"
    metadata.keywords = ["inp_dataclass_node"]
    metadata.inputs = field_anns
    metadata.outputs = [dataclass_ann]

    enrich_from_docstring(raw_doc, metadata)

    return metadata


def parse_out_dataclass_node(obj: Any) -> FunctionRequest | None:
    original_cls = getattr(obj, "_original_dataclass", None)
    if original_cls is None or not (
        dataclasses.is_dataclass(original_cls) and isinstance(original_cls, type)
    ):
        return None

    try:
        raw_source = textwrap.dedent(
            inspect.getsource(original_cls).replace("\r\n", "")
        )
    except OSError:
        return None

    module: str = original_cls.__module__
    qualname: str = original_cls.__qualname__
    python_import = f"{module}.{qualname}"
    raw_doc = inspect.getdoc(original_cls) or ""

    field_anns = _field_annotations(original_cls)
    dataclass_ann = Annotation(label="input", datatype=python_import)

    metadata = FunctionRequest.model_construct()
    metadata.name = f"[OUT] {python_import}"
    metadata.artifact_type = ArtifactType.FUNCTION
    metadata.python_import = python_import
    metadata.category = module.replace(".", ">")
    metadata.source_code = raw_source
    metadata.docstring = f"[OUT] {qualname}: {raw_doc}"
    metadata.keywords = ["out_dataclass_node"]
    metadata.inputs = [dataclass_ann]
    metadata.outputs = field_anns

    enrich_from_docstring(raw_doc, metadata)

    return metadata


def parse_group_node(obj: Any) -> FunctionRequest | None:
    try:
        from core.groups import (  # pyright: ignore[reportMissingImports] # noqa: PLC0415
            WorkflowGroupFactory,
        )
    except ImportError:
        return None

    if not isinstance(obj, WorkflowGroupFactory):
        return None

    group_node: WorkflowGroupFactory = obj

    metadata = FunctionRequest.model_construct()

    try:
        raw_source = textwrap.dedent(inspect.getsource(group_node).replace("\r\n", ""))
    except OSError:
        return None

    raw_doc = inspect.getdoc(group_node) or ""

    module: str = group_node.__module__
    qualname: str = group_node.__qualname__
    python_import = f"{module}.{qualname}"

    inputs = [Annotation(label=inp) for inp in group_node.input_aliases]
    outputs = [Annotation(label=inp) for inp in group_node.output_aliases]

    metadata.name = group_node.group_name
    metadata.artifact_type = ArtifactType.FUNCTION
    metadata.python_import = python_import
    metadata.category = module.replace(".", ">")
    metadata.source_code = raw_source
    metadata.docstring = raw_doc
    metadata.keywords = ["aiflow", "group_node"]
    metadata.inputs = inputs
    metadata.outputs = outputs

    enrich_from_docstring(raw_doc, metadata)

    return metadata


def parse_workflow(obj: Any, ns: NodeStoreAPI) -> WorkflowRequest | None:
    try:
        from core import (  # pyright: ignore[reportMissingImports] # noqa: PLC0415
            Workflow,  # pyright: ignore[reportMissingImports]
        )
        from core.graph_to_workflow import (  # pyright: ignore[reportMissingImports] # noqa: PLC0415
            graph_to_workflow_code,
        )
    except ImportError:
        return None

    if not isinstance(obj, Workflow):
        return None

    wf: Workflow = obj

    metadata = WorkflowRequest.model_construct()

    metadata.name = wf._graph.label
    metadata.python_import = ""
    metadata.category = "workflow"
    metadata.source_code = graph_to_workflow_code(
        wf._graph, wf._graph.label, "decorator", True
    )
    metadata.docstring = ""
    metadata.keywords = ["aiflow"]
    metadata.inputs = []
    metadata.outputs = []

    children_import = [(label, node) for label, node in wf._graph.nodes.items()]

    children_upload = [
        (label, upload(ns, child)[0])
        for label, child in children_import
        if child is not None
    ]

    def extract_id(response: Response) -> str | None:
        if response.ok:
            return response.json()["id"]
        if response.status_code == HTTPStatus.CONFLICT:
            return response.json()["detail"]["id"]
        return None

    metadata.children = [
        Reference(label=label, id=atlas_id)
        for label, response in children_upload
        if (atlas_id := extract_id(response)) is not None
    ]

    return metadata


def parse(obj: Any, ns: NodeStoreAPI) -> list[ArtifactRequest]:
    if metadata := parse_workflow(obj, ns):
        return [metadata]

    if metadata := parse_group_node(obj):
        return [metadata]

    if metadata := parse_function_node(obj):
        return [metadata]

    if metadata := parse_inp_dataclass_node(obj):
        return [metadata]

    if metadata := parse_out_dataclass_node(obj):
        return [metadata]

    return []
