import dataclasses
from typing import Annotated

from sim_atlas_toolkit.models import ArtifactType
from sim_atlas_toolkit.parsers.dataclass_node import parse
from sim_atlas_toolkit.settings import ToolkitSettings

from .mock_api import NodeStoreAPI


@dataclasses.dataclass
class Point:
    """Represent a 2D point.

    This test fixture models a point in a two-dimensional Cartesian space and
    provides a simple dataclass shape for parser coverage.

    Attributes
    ----------
    x : float
        Horizontal coordinate of the point.
    y : float
        Vertical coordinate of the point.
    """

    x: float
    y: Annotated[float, {"unit": "m", "quantity": "length"}] = 3.0


def test_dataclass_parser() -> None:
    ns = NodeStoreAPI()
    settings = ToolkitSettings(api_url="https://example.invalid", api_token="token")
    responses = parse(Point, ns, settings)  # pyright: ignore[reportArgumentType]
    assert len(responses) == 2  # noqa: PLR2004
    assert len(ns.uploaded) == 2  # noqa: PLR2004

    pack_metadata = ns.uploaded[0]
    assert pack_metadata.artifact_type == ArtifactType.FUNCTION
    assert len(pack_metadata.inputs) == 2  # noqa: PLR2004
    assert [a.label for a in pack_metadata.inputs] == ["x", "y"]
    assert pack_metadata.inputs[0].datatype == "float"
    assert pack_metadata.inputs[0].unit is None
    assert pack_metadata.inputs[0].quantity is None
    assert not pack_metadata.inputs[0].has_default_value
    assert pack_metadata.inputs[0].description == "Horizontal coordinate of the point."
    assert pack_metadata.inputs[1].datatype == "float"
    assert pack_metadata.inputs[1].unit == "m"
    assert pack_metadata.inputs[1].quantity == "length"
    assert pack_metadata.inputs[1].has_default_value
    assert pack_metadata.inputs[1].description == "Vertical coordinate of the point."
    assert len(pack_metadata.outputs) == 1
    assert pack_metadata.outputs[0].label == "point"
    assert pack_metadata.outputs[0].datatype == "tests.test_dataclass_node.Point"

    unpack_metadata = ns.uploaded[1]
    assert unpack_metadata.artifact_type == ArtifactType.FUNCTION
    assert len(unpack_metadata.inputs) == 1
    assert unpack_metadata.inputs[0].label == "point"
    assert unpack_metadata.inputs[0].datatype == "tests.test_dataclass_node.Point"
    assert len(unpack_metadata.outputs) == 2  # noqa: PLR2004
    assert [a.label for a in unpack_metadata.outputs] == ["x", "y"]
    assert unpack_metadata.outputs[0].datatype == "float"
    assert unpack_metadata.outputs[0].unit is None
    assert unpack_metadata.outputs[0].quantity is None
    assert (
        unpack_metadata.outputs[0].description == "Horizontal coordinate of the point."
    )
    assert unpack_metadata.outputs[1].datatype == "float"
    assert unpack_metadata.outputs[1].unit == "m"
    assert unpack_metadata.outputs[1].quantity == "length"
    assert unpack_metadata.outputs[1].description == "Vertical coordinate of the point."
