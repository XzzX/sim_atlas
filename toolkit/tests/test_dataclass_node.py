import dataclasses
from typing import Annotated

from sim_atlas_toolkit.models import ArtifactType
from sim_atlas_toolkit.parsers.dataclass_node import parse


@dataclasses.dataclass
class Point:
    """A 2D point."""

    x: float
    y: float


@dataclasses.dataclass
class WithDefaults:
    name: str
    values: list[int] = dataclasses.field(default_factory=lambda: [0])
    tag: str = "default"


@dataclasses.dataclass
class WithInitFalse:
    x: float
    _computed: float = dataclasses.field(init=False, default=0.0)


@dataclasses.dataclass
class WithAnnotated:
    velocity: Annotated[
        float, {"unit": "m/s", "label": "speed", "quantity": "velocity"}
    ]


class NotADataclass:
    pass


def test_basic_returns_two_records() -> None:
    assert len(parse(Point)) == 2  # noqa: PLR2004


def test_pack_node_type() -> None:
    pack, _ = parse(Point)
    assert pack.artifact_type == ArtifactType.FUNCTION


def test_unpack_node_type() -> None:
    _, unpack = parse(Point)
    assert unpack.artifact_type == ArtifactType.FUNCTION


def test_pack_name() -> None:
    pack, _ = parse(Point)
    assert pack.name == f"[PACK] {Point.__module__}.Point"


def test_unpack_name() -> None:
    _, unpack = parse(Point)
    assert unpack.name == f"[UNPACK] {Point.__module__}.Point"


def test_python_import_identical() -> None:
    pack, unpack = parse(Point)
    assert pack.python_import == unpack.python_import
    assert pack.python_import == f"{Point.__module__}.Point"


def test_pack_inputs_labels() -> None:
    pack, _ = parse(Point)
    assert [a.label for a in pack.inputs] == ["x", "y"]


def test_pack_inputs_datatypes() -> None:
    pack, _ = parse(Point)
    assert all(a.datatype == "float" for a in pack.inputs)


def test_pack_output_is_dataclass_annotation() -> None:
    pack, _ = parse(Point)
    assert len(pack.outputs) == 1
    assert pack.outputs[0].label == "Point"
    assert pack.outputs[0].datatype == f"{Point.__module__}.Point"


def test_unpack_input_is_dataclass_annotation() -> None:
    _, unpack = parse(Point)
    assert len(unpack.inputs) == 1
    assert unpack.inputs[0].label == "Point"
    assert unpack.inputs[0].datatype == f"{Point.__module__}.Point"


def test_unpack_outputs_labels() -> None:
    _, unpack = parse(Point)
    assert [a.label for a in unpack.outputs] == ["x", "y"]


def test_docstring_pack_prefix() -> None:
    pack, _ = parse(Point)
    assert pack.docstring.startswith("[PACK] Point: ")
    assert "2D point" in pack.docstring


def test_docstring_unpack_prefix() -> None:
    _, unpack = parse(Point)
    assert unpack.docstring.startswith("[UNPACK] Point: ")


def test_default_factory() -> None:
    pack, _ = parse(WithDefaults)
    by_label = {a.label: a for a in pack.inputs}
    assert by_label["values"].has_default_value is True


def test_default_literal() -> None:
    pack, _ = parse(WithDefaults)
    by_label = {a.label: a for a in pack.inputs}
    assert by_label["tag"].has_default_value is True


def test_no_default_value() -> None:
    pack, _ = parse(WithDefaults)
    by_label = {a.label: a for a in pack.inputs}
    assert by_label["name"].has_default_value is False


def test_init_false_excluded_from_pack_inputs() -> None:
    pack, _ = parse(WithInitFalse)
    assert "_computed" not in [a.label for a in pack.inputs]


def test_init_false_excluded_from_unpack_outputs() -> None:
    _, unpack = parse(WithInitFalse)
    assert "_computed" not in [a.label for a in unpack.outputs]


def test_annotated_field_unit() -> None:
    pack, _ = parse(WithAnnotated)
    assert pack.inputs[0].unit == "m/s"


def test_annotated_field_quantity() -> None:
    pack, _ = parse(WithAnnotated)
    assert pack.inputs[0].quantity == "velocity"


def test_annotated_field_label_override() -> None:
    pack, _ = parse(WithAnnotated)
    assert pack.inputs[0].label == "speed"


def test_annotated_field_datatype() -> None:
    pack, _ = parse(WithAnnotated)
    assert pack.inputs[0].datatype == "float"


def test_non_dataclass_class_returns_empty() -> None:
    assert parse(NotADataclass) == []


def test_pack_keywords() -> None:
    pack, _ = parse(Point)
    assert pack.keywords == ["pack"]


def test_unpack_keywords() -> None:
    _, unpack = parse(Point)
    assert unpack.keywords == ["unpack"]


def test_dataclass_instance_returns_empty() -> None:
    assert parse(Point(1.0, 2.0)) == []


def test_dynamic_dataclass_no_source_returns_empty() -> None:
    DynClass = dataclasses.make_dataclass("DynClass", [("x", int)])
    assert parse(DynClass) == []
