import dataclasses
import json
from http import HTTPStatus
from typing import Any, cast

import flowrep as fr
import httpx
import pytest
from flowrep.api.schemas import WorkflowRecipe
from flowrep.retrospective.datastructures import DagData

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.models import (
    ArtifactType,
    Reference,
    WfFunctionNode,
    WfInputNode,
    WfOutputNode,
    WorkflowRequest,
)
from sim_atlas_toolkit.parsers import flowrep_parser
from sim_atlas_toolkit.parsers.flowrep_parser import flowrep_to_wf_definition, parse
from sim_atlas_toolkit.settings import ToolkitSettings

from .mock_api import install_mock_node_store


@fr.atomic
def kinetic_energy(mass: float, velocity: float = 1.0) -> float:
    """Calculate kinetic energy.

    Compute the kinetic energy of an object from its mass and velocity.
    This helper is used to verify that documented atomic functions are
    parsed correctly by the flowrep integration.

    Args:
        mass: Mass of the object.
        velocity: Velocity of the object.

    Returns:
        The kinetic energy as a floating-point value.
    """
    kinetic_energy = 0.5 * mass * velocity**2
    return kinetic_energy


@fr.atomic
def add(a: float, b: float) -> float:
    """Returns the sum of a and b."""
    return a + b


@fr.atomic
def mul(a: float, b: float) -> float:
    """Returns the product of a and b."""
    return a * b


@fr.workflow
def linear(x: float, slope: float, intercept: float) -> float:
    """y = slope * x + intercept"""
    scaled = mul(x, slope)  # type: ignore
    result = add(scaled, intercept)  # type: ignore
    return result  # type: ignore


@fr.workflow
def diamond(x: float, y: float) -> float:
    """Fan-out from x/y into two branches, fan-in into a final multiply."""
    a = mul(x, y)  # type: ignore
    b = add(x, y)  # type: ignore
    c = mul(a, b)  # type: ignore
    return c  # type: ignore


@fr.workflow
def reused_twice(x: float, y: float) -> float:
    """Calls `mul` twice under different labels."""
    a = mul(x, y)  # type: ignore
    b = mul(a, y)  # type: ignore
    return b  # type: ignore


@fr.workflow
def identity(x: float) -> float:
    """Passes its input straight through to its output."""
    return x


@fr.workflow
def outer(x: float, slope: float, intercept: float) -> float:
    """Calls the nested `linear` workflow."""
    result = linear(x, slope, intercept)  # type: ignore
    return result  # type: ignore


@fr.workflow
def multi_out(x: float, y: float) -> float:
    """Declared return type doesn't match the actual number of outputs."""
    a = mul(x, y)  # type: ignore
    b = mul(a, y)  # type: ignore
    return a, b  # type: ignore


@fr.atomic
def to_none(x: float) -> float | None:
    """Always returns None."""
    return None


@fr.atomic
def duplicate(x: float) -> list[float]:
    """Returns x duplicated in a list."""
    return [x, x]


@fr.workflow
def mixed_outputs(x: float) -> tuple[float | None, list[float]]:
    """Workflow whose outputs are not JSON primitives."""
    a = to_none(x)  # type: ignore
    b = duplicate(x)  # type: ignore
    return a, b  # type: ignore


@fr.atomic
def documented_mismatch(a: float, b: float) -> float:
    """Adds two numbers, with a mismatched docstring.

    Args:
        a: First value.
        c: Nonexistent parameter, should be silently ignored.

    Returns:
        First return value.
        Second return value, silently dropped since there's only one output.
    """
    return a + b


@fr.atomic
def bare(x: float) -> float:
    return x + 1.0


def undecorated_add(a: float, b: float) -> float:
    """A plain function flowrep can still auto-parse."""
    return a + b


def unsupported_varargs(*args: float) -> float:
    """A signature flowrep's auto-parser cannot handle."""
    return sum(args)


async def test_flowrep_atomic(monkeypatch: pytest.MonkeyPatch) -> None:
    store = install_mock_node_store(monkeypatch)
    responses = await parse(ToolkitSettings(), kinetic_energy)
    assert len(responses) == 1
    assert len(store.uploaded) == 1
    metadata = store.uploaded[-1]
    assert metadata.artifact_type == ArtifactType.FUNCTION
    assert [a.label for a in metadata.inputs] == ["mass", "velocity"]
    assert metadata.inputs[0].datatype == "float"
    assert metadata.inputs[0].description == "Mass of the object."
    assert not metadata.inputs[0].has_default_value
    assert metadata.inputs[1].datatype == "float"
    assert metadata.inputs[1].description == "Velocity of the object."
    assert metadata.inputs[1].has_default_value
    assert len(metadata.outputs) == 1
    assert metadata.outputs[0].datatype == "float"
    assert metadata.outputs[0].label == "kinetic_energy"
    assert (
        metadata.outputs[0].description
        == "The kinetic energy as a floating-point value."
    )
    assert metadata.brief_description == "Calculate kinetic energy."
    assert (
        metadata.description
        == "Calculate kinetic energy.\n\nCompute the kinetic energy of an object from its mass and velocity.\nThis helper is used to verify that documented atomic functions are\nparsed correctly by the flowrep integration."
    )


async def test_flowrep_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    store = install_mock_node_store(monkeypatch)
    responses = await parse(ToolkitSettings(), linear)
    assert len(responses) == 1
    assert len(store.uploaded) == 3  # noqa: PLR2004
    metadata = store.uploaded[-1]
    assert isinstance(metadata, WorkflowRequest)
    assert metadata.artifact_type == ArtifactType.WORKFLOW
    assert [a.label for a in metadata.inputs] == ["x", "slope", "intercept"]
    assert all(a.datatype == "float" for a in metadata.inputs)
    assert all(a.description is None for a in metadata.inputs)
    assert not any(a.has_default_value for a in metadata.inputs)
    assert len(metadata.outputs) == 1
    assert metadata.outputs[0].datatype == "float"
    assert metadata.outputs[0].label == "result"
    assert metadata.outputs[0].description is None
    assert metadata.brief_description == "y = slope * x + intercept"
    assert metadata.description == "y = slope * x + intercept"
    assert len(metadata.uses) == 2  # noqa: PLR2004
    assert metadata.uses[0].label == "mul_0"
    assert metadata.uses[1].label == "add_0"


async def test_flowrep_execution_result(monkeypatch: pytest.MonkeyPatch) -> None:
    store = install_mock_node_store(monkeypatch)
    dag = fr.tools.run_recipe(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        linear.flowrep_recipe,  # pyright: ignore[reportFunctionMemberAccess]
        x=2.0,
        slope=3.0,
        intercept=1.0,
    )
    responses = await parse(ToolkitSettings(), dag)
    assert len(responses) == 1
    assert len(store.uploaded_execution_results) == 1
    execution_result = store.uploaded_execution_results[-1]
    assert execution_result.artifact_id
    inputs = {io.label: io.value for io in execution_result.inputs}
    assert inputs == {"x": 2.0, "slope": 3.0, "intercept": 1.0}
    assert json.loads(execution_result.outputs) == {"result": 7.0}


def test_flowrep_to_wf_definition_diamond() -> None:
    wf_def = flowrep_to_wf_definition(diamond.flowrep_recipe, references=[])  # type: ignore[attr-defined]

    node_types = {node.node_id: type(node) for node in wf_def.nodes}
    assert node_types == {
        "mul_0": WfFunctionNode,
        "add_0": WfFunctionNode,
        "mul_1": WfFunctionNode,
        "x": WfInputNode,
        "y": WfInputNode,
        "c": WfOutputNode,
    }

    edges = {
        (e.source_node, e.source_port, e.target_node, e.target_port)
        for e in wf_def.edges
    }
    assert edges == {
        ("x", None, "mul_0", "a"),
        ("y", None, "mul_0", "b"),
        ("x", None, "add_0", "a"),
        ("y", None, "add_0", "b"),
        ("mul_0", "output_0", "mul_1", "a"),
        ("add_0", "output_0", "mul_1", "b"),
        ("mul_1", "output_0", "c", None),
    }


def test_flowrep_to_wf_definition_passthrough_output() -> None:
    """The synthesized WfOutputNode is skipped here: its node_id ("x") collides
    with the WfInputNode already added for the same workflow input, and the
    dedup check only compares node_id, not node type. Pre-existing behavior,
    unrelated to this change's fixes — characterized as-is."""
    wf_def = flowrep_to_wf_definition(identity.flowrep_recipe, references=[])  # type: ignore[attr-defined]

    assert len(wf_def.nodes) == 1
    node = wf_def.nodes[0]
    assert isinstance(node, WfInputNode)
    assert node.node_id == "x"

    assert len(wf_def.edges) == 1
    edge = wf_def.edges[0]
    assert (edge.source_node, edge.source_port, edge.target_node, edge.target_port) == (
        "x",
        None,
        "x",
        None,
    )


def test_flowrep_to_wf_definition_nested_workflow() -> None:
    references = [Reference(label="linear_0", id="linear-id", count=1)]
    wf_def = flowrep_to_wf_definition(outer.flowrep_recipe, references)  # type: ignore[attr-defined]

    function_nodes = {
        n.node_id: n for n in wf_def.nodes if isinstance(n, WfFunctionNode)
    }
    assert set(function_nodes) == {"linear_0"}
    assert function_nodes["linear_0"].atlas_id == "linear-id"
    assert [a.label for a in function_nodes["linear_0"].inputs] == [
        "x",
        "slope",
        "intercept",
    ]
    assert [a.label for a in function_nodes["linear_0"].outputs] == ["result"]

    input_node_ids = {n.node_id for n in wf_def.nodes if isinstance(n, WfInputNode)}
    assert input_node_ids == {"x", "slope", "intercept"}
    output_node_ids = {n.node_id for n in wf_def.nodes if isinstance(n, WfOutputNode)}
    assert output_node_ids == {"result"}


async def test_flowrep_atomic_no_docstring(monkeypatch: pytest.MonkeyPatch) -> None:
    store = install_mock_node_store(monkeypatch)
    responses = await parse(ToolkitSettings(), bare)
    assert len(responses) == 1
    metadata = store.uploaded[-1]
    assert metadata.docstring == ""
    assert metadata.brief_description is None
    assert metadata.description is None
    assert metadata.inputs[0].description is None


async def test_flowrep_atomic_docstring_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)
    responses = await parse(ToolkitSettings(), documented_mismatch)
    assert len(responses) == 1
    metadata = store.uploaded[-1]
    assert metadata.inputs[0].description == "First value."
    assert metadata.inputs[1].description is None
    assert len(metadata.outputs) == 1
    assert metadata.outputs[0].description == "First return value."


async def test_flowrep_atomic_skips_upload_when_already_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)

    async def existing_artifact(api_url: str, artifact_id: str) -> httpx.Response:
        return httpx.Response(200, json={"id": artifact_id})

    monkeypatch.setattr(node_store_api, "read_artifact", existing_artifact)

    responses = await parse(ToolkitSettings(), kinetic_energy)
    assert len(responses) == 1
    assert responses[0].status_code == HTTPStatus.OK
    assert store.uploaded == []


async def test_flowrep_workflow_skips_upload_when_already_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)

    async def existing_artifact(api_url: str, artifact_id: str) -> httpx.Response:
        return httpx.Response(200, json={"id": artifact_id})

    monkeypatch.setattr(node_store_api, "read_artifact", existing_artifact)

    responses = await parse(ToolkitSettings(), linear)
    assert len(responses) == 1
    assert responses[0].status_code == HTTPStatus.OK
    assert store.uploaded == []


async def test_flowrep_workflow_reuses_function_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)
    responses = await parse(ToolkitSettings(), reused_twice)
    assert len(responses) == 1
    metadata = store.uploaded[-1]
    assert isinstance(metadata, WorkflowRequest)
    assert [ref.label for ref in metadata.uses] == ["mul_0", "mul_1"]
    assert len(store.uploaded) == 3  # noqa: PLR2004


async def test_flowrep_workflow_output_arity_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)
    responses = await parse(ToolkitSettings(), multi_out)
    assert len(responses) == 1
    metadata = store.uploaded[-1]
    assert isinstance(metadata, WorkflowRequest)
    assert [a.label for a in metadata.outputs] == ["a", "b"]
    assert all(a.datatype is None for a in metadata.outputs)


async def test_flowrep_workflow_nested_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)
    responses = await parse(ToolkitSettings(), outer)
    assert len(responses) == 1
    assert len(store.uploaded) == 4  # noqa: PLR2004  (mul, add, linear, outer)
    metadata = store.uploaded[-1]
    assert isinstance(metadata, WorkflowRequest)
    assert [ref.label for ref in metadata.uses] == ["linear_0"]
    nested_node = next(
        n for n in metadata.wf_definition.nodes if n.node_id == "linear_0"
    )
    assert isinstance(nested_node, WfFunctionNode)
    assert nested_node.atlas_id == metadata.uses[0].id


async def test_flowrep_execution_result_no_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_mock_node_store(monkeypatch)
    dag = cast(
        DagData,
        fr.tools.run_recipe(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            linear.flowrep_recipe,  # pyright: ignore[reportFunctionMemberAccess]
            x=2.0,
            slope=3.0,
            intercept=1.0,
        ),
    )
    recipe = cast(WorkflowRecipe, cast(Any, dag).recipe)
    dag = dataclasses.replace(dag, recipe=recipe.model_copy(update={"reference": None}))
    responses = await parse(ToolkitSettings(), dag)
    assert responses == []


def _no_import(module: str, qualname: str | None) -> Any | None:
    return None


async def test_flowrep_execution_result_unresolvable_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_mock_node_store(monkeypatch)
    monkeypatch.setattr(flowrep_parser, "try_import", _no_import)
    dag = fr.tools.run_recipe(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        linear.flowrep_recipe,  # pyright: ignore[reportFunctionMemberAccess]
        x=2.0,
        slope=3.0,
        intercept=1.0,
    )
    responses = await parse(ToolkitSettings(), dag)
    assert responses == []


async def test_flowrep_execution_result_workflow_upload_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_mock_node_store(monkeypatch)

    async def fake_upload(
        settings: ToolkitSettings, obj: object
    ) -> list[httpx.Response]:
        return []

    monkeypatch.setattr(flowrep_parser, "upload", fake_upload)
    dag = fr.tools.run_recipe(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        linear.flowrep_recipe,  # pyright: ignore[reportFunctionMemberAccess]
        x=2.0,
        slope=3.0,
        intercept=1.0,
    )
    responses = await parse(ToolkitSettings(), dag)
    assert responses == []


def _no_id(response: httpx.Response) -> str | None:
    return None


async def test_flowrep_execution_result_missing_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_mock_node_store(monkeypatch)
    monkeypatch.setattr(flowrep_parser, "extract_id", _no_id)
    dag = fr.tools.run_recipe(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        linear.flowrep_recipe,  # pyright: ignore[reportFunctionMemberAccess]
        x=2.0,
        slope=3.0,
        intercept=1.0,
    )
    responses = await parse(ToolkitSettings(), dag)
    assert responses == []


async def test_flowrep_execution_result_preserves_non_primitive_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)
    dag = fr.tools.run_recipe(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        mixed_outputs.flowrep_recipe,  # pyright: ignore[reportFunctionMemberAccess]
        x=2.0,
    )
    responses = await parse(ToolkitSettings(), dag)
    assert len(responses) == 1
    outputs = json.loads(store.uploaded_execution_results[-1].outputs)
    assert outputs == {"a": None, "b": [2.0, 2.0]}


async def test_parse_returns_empty_for_unsupported_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_mock_node_store(monkeypatch)

    class NotAFlowrepObject:
        pass

    responses = await parse(ToolkitSettings(), NotAFlowrepObject())
    assert responses == []


async def test_parse_falls_back_to_auto_parse_for_undecorated_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)
    responses = await parse(ToolkitSettings(), undecorated_add)
    assert len(responses) == 1
    assert store.uploaded[-1].name.endswith("undecorated_add")


async def test_parse_swallows_auto_parse_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_mock_node_store(monkeypatch)
    responses = await parse(ToolkitSettings(), unsupported_varargs)
    assert responses == []


async def test_extract_id_handles_conflict_on_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The create-artifact path treats 409 CONFLICT like a successful create
    (see `extract_id`), distinct from the (unfixed) duplicate-hash check on
    `read_artifact`, which only short-circuits on 200 OK."""
    store = install_mock_node_store(monkeypatch)

    async def create_artifacts_conflict(
        api_url: str, api_key: str | None, artifacts: list[object]
    ) -> list[httpx.Response]:
        store.uploaded.extend(artifacts)  # type: ignore[arg-type]
        return [httpx.Response(409, json={"id": "existing-id"}) for _ in artifacts]

    monkeypatch.setattr(node_store_api, "create_artifacts", create_artifacts_conflict)

    responses = await parse(ToolkitSettings(), linear)
    assert len(responses) == 1
    assert responses[0].status_code == HTTPStatus.CONFLICT
    metadata = store.uploaded[-1]
    assert isinstance(metadata, WorkflowRequest)
    assert all(ref.id == "existing-id" for ref in metadata.uses)
