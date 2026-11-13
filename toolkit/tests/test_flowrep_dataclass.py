"""Dataclasses are uploaded only as ``@flowrep.dataclass``: one constructor node.

Field access in a flowrep workflow (``p.x``) becomes ``get_attr`` fed by a
constant node holding the field name (#233).
"""

import dataclasses
from typing import Annotated

import flowrep as fr
import pytest
from sim_atlas_models import Annotation, ArtifactType, WfConstantNode, WfEdge

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.settings import ToolkitSettings
from sim_atlas_toolkit.uploader import upload

from .mock_api import MockNodeStore


@fr.dataclass
class Point:
    """Represent a 2D point.

    Attributes
    ----------
    x : float
        Horizontal coordinate of the point.
    y : float
        Vertical coordinate of the point.
    """

    x: float
    y: Annotated[float, {"unit": "m", "quantity": "length"}] = 3.0


@fr.workflow
def x_of(a: float, b: float) -> float:
    """Build a point and read its x coordinate."""
    p = Point(a, b)  # type: ignore[call-arg]  # flowrep.dataclass hides __init__ from pyright
    x = p.x
    return x


@dataclasses.dataclass
class PlainPoint:
    x: float


def _ctx(store: MockNodeStore) -> ParseContext:
    return ParseContext(ToolkitSettings(), store)


async def test_flowrep_dataclass_is_one_constructor_node() -> None:
    store = MockNodeStore()

    results = await upload(_ctx(store), Point)

    assert len(results) == 1
    [node] = store.uploaded
    assert node.artifact_type == ArtifactType.FUNCTION
    assert node.name == f"{__name__}.Point"
    assert node.python_import == f"{__name__}.Point"
    assert [
        (a.label, a.datatype, a.unit, a.quantity, a.has_default_value, a.description)
        for a in node.inputs
    ] == [
        ("x", "float", None, None, False, "Horizontal coordinate of the point."),
        ("y", "float", "m", "length", True, "Vertical coordinate of the point."),
    ]
    assert [a.label for a in node.outputs] == ["instance"]
    assert node.source_code.startswith("@fr.dataclass\nclass Point:")
    assert "NOTE" not in node.source_code


async def test_plain_dataclass_is_not_uploaded() -> None:
    store = MockNodeStore()

    with pytest.raises(ValueError, match="No parser available"):
        await upload(_ctx(store), PlainPoint)

    assert store.uploaded == []


async def test_field_access_uploads_get_attr_and_a_constant_node() -> None:
    store = MockNodeStore()

    await upload(_ctx(store), x_of)

    workflow = store.uploaded[-1]
    assert workflow.artifact_type == ArtifactType.WORKFLOW
    assert {n.python_import for n in store.uploaded[:-1]} == {
        f"{__name__}.Point",
        "flowrep.std.get_attr",
    }
    assert {r.label for r in workflow.uses} == {"Point_0", "get_attr_0"}
    assert workflow.wf_definition is not None
    constants = [
        n for n in workflow.wf_definition.nodes if isinstance(n, WfConstantNode)
    ]
    assert constants == [
        WfConstantNode(
            node_id="constant_0",
            value="x",
            outputs=[Annotation(label="constant")],
        )
    ]
    assert (
        WfEdge(
            source_node="constant_0",
            source_port="constant",
            target_node="get_attr_0",
            target_port="name",
        )
        in workflow.wf_definition.edges
    )
