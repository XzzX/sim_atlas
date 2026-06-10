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


def test_keywords_is_empty() -> None:
    (record,) = parse(simple)
    assert record.keywords == []


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


# --- docstring enrichment tests ---


def google_docstring(x: float, y: float) -> float:
    """Add two numbers.

    Args:
        x: The first operand.
        y: The second operand.

    Returns:
        The sum of x and y.
    """
    return x + y


def numpy_docstring(x: float, y: float) -> float:
    """Add two numbers.

    Parameters
    ----------
    x : float
        The first operand.
    y : float
        The second operand.

    Returns
    -------
    float
        The sum of x and y.
    """
    return x + y


def no_docstring(x: float) -> float:
    return x


def test_google_docstring_input_descriptions() -> None:
    (record,) = parse(google_docstring)
    assert record.inputs[0].description == "The first operand."
    assert record.inputs[1].description == "The second operand."


def test_google_docstring_output_description() -> None:
    (record,) = parse(google_docstring)
    assert record.outputs[0].description == "The sum of x and y."


def test_numpy_docstring_input_descriptions() -> None:
    (record,) = parse(numpy_docstring)
    assert record.inputs[0].description == "The first operand."
    assert record.inputs[1].description == "The second operand."


def test_numpy_docstring_output_description() -> None:
    (record,) = parse(numpy_docstring)
    assert record.outputs[0].description == "The sum of x and y."


def test_no_docstring_descriptions_are_none() -> None:
    (record,) = parse(no_docstring)
    assert record.inputs[0].description is None
    assert record.outputs[0].description is None


def annotated_description_wins(
    x: Annotated[float, {"description": "from annotation"}],
) -> float:
    """Do something.

    Args:
        x: from docstring.
    """
    return x


def test_annotated_description_not_overwritten_by_docstring() -> None:
    (record,) = parse(annotated_description_wins)
    assert record.inputs[0].description == "from annotation"
