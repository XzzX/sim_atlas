import flowrep as fr

from sim_atlas_toolkit.models import ArtifactType, WorkflowRequest
from sim_atlas_toolkit.parsers.flowrep_parser import parse

from .mock_api import NodeStoreAPI


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


def test_flowrep_atomic() -> None:
    ns = NodeStoreAPI()
    responses = parse(kinetic_energy, ns)  # pyright: ignore[reportArgumentType]
    assert len(responses) == 1
    assert len(ns.uploaded) == 1
    metadata = ns.uploaded[-1]
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


def test_flowrep_workflow() -> None:
    ns = NodeStoreAPI()
    responses = parse(linear, ns)  # pyright: ignore[reportArgumentType]
    assert len(responses) == 1
    assert len(ns.uploaded) == 3  # noqa: PLR2004
    metadata = ns.uploaded[-1]
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
    assert len(metadata.children) == 2  # noqa: PLR2004
    assert metadata.children[0].label == "mul_0"
    assert metadata.children[1].label == "add_0"
