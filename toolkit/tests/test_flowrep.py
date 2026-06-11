import flowrep as fr

from sim_atlas_toolkit.models import ArtifactType
from sim_atlas_toolkit.parsers.flowrep_parser import parse


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


def test_function_returns_one_record() -> None:
    metadata_list = parse(kinetic_energy)
    assert len(metadata_list) == 1
    metadata = metadata_list[0]
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
    print(metadata)
