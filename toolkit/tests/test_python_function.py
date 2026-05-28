from typing import Annotated

from sim_atlas_toolkit.models import ArtifactType
from sim_atlas_toolkit.parsers.python_function import parse


def simple(x: int, y: float) -> str:
    """A simple function."""
    return str(x + y)


def no_return(x: int) -> None:
    pass


def tuple_return(x: int) -> tuple[int, float]:
    return x, float(x)


def annotated_tuple_return(
    x: int,
) -> Annotated[
    tuple[
        Annotated[int, {"label": "count", "unit": "items"}],
        Annotated[float, {"label": "ratio", "quantity": "dimensionless"}],
    ],
    {},
]:
    return x, float(x)


class NotCallable:
    pass


def test_function_returns_one_record() -> None:
    assert len(parse(simple)) == 1


def test_function_node_type() -> None:
    (record,) = parse(simple)
    assert record.artifact_type == ArtifactType.FUNCTION


def test_function_input_labels() -> None:
    (record,) = parse(simple)
    assert [a.label for a in record.inputs] == ["x", "y"]


def test_function_input_datatypes() -> None:
    (record,) = parse(simple)
    assert record.inputs[0].datatype == "int"
    assert record.inputs[1].datatype == "float"


def test_function_output_datatype() -> None:
    (record,) = parse(simple)
    assert len(record.outputs) == 1
    assert record.outputs[0].datatype == "str"


def test_no_return_annotation_label() -> None:
    (record,) = parse(no_return)
    assert len(record.outputs) == 1
    assert record.outputs[0].label == "return"


def test_tuple_return_multiple_outputs() -> None:
    (record,) = parse(tuple_return)
    assert len(record.outputs) == 2  # noqa: PLR2004


def test_tuple_return_output_datatypes() -> None:
    (record,) = parse(tuple_return)
    assert record.outputs[0].datatype == "int"
    assert record.outputs[1].datatype == "float"


def test_annotated_tuple_return_labels() -> None:
    (record,) = parse(annotated_tuple_return)
    assert record.outputs[0].label == "count"
    assert record.outputs[1].label == "ratio"


def test_annotated_tuple_return_unit() -> None:
    (record,) = parse(annotated_tuple_return)
    assert record.outputs[0].unit == "items"


def test_annotated_tuple_return_quantity() -> None:
    (record,) = parse(annotated_tuple_return)
    assert record.outputs[1].quantity == "dimensionless"


def test_non_function_returns_empty() -> None:
    assert parse(NotCallable) == []


def test_builtin_returns_one_record() -> None:
    assert len(parse(len)) == 1


def annotated_with_description(
    x: Annotated[
        float,
        {
            "label": "temperature",
            "unit": "K",
            "description": "initial temperature of the simulation box",
        },
    ],
) -> float:
    return x


def test_annotated_description_on_input() -> None:
    (record,) = parse(annotated_with_description)
    assert record.inputs[0].description == "initial temperature of the simulation box"


def test_annotated_description_does_not_affect_other_fields() -> None:
    (record,) = parse(annotated_with_description)
    # label comes from the parameter name, not the Annotated dict
    assert record.inputs[0].label == "x"
    assert record.inputs[0].unit == "K"
