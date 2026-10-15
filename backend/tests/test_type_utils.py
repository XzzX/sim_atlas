import pytest

from sim_atlas.type_utils import collect_datatypes, datatype_matches


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("int", {"int"}),
        ("int | None", {"int", "None"}),
        ("int|float", {"int", "float"}),
        (" int  |  float ", {"int", "float"}),
        ("list[int]", {"list[int]"}),
        ("dict[str,float]", {"dict[str, float]"}),
        ("dict[str, float] | None", {"dict[str, float]", "None"}),
        ("Callable[[int], str]", {"Callable[[int], str]"}),
        # unparseable input becomes one opaque entry instead of a truncated parse
        ("Literal['a', 'b']", {"Literal['a','b']"}),
        ("list[int", {"list[int"}),
        ("int|", {"int|"}),
    ],
)
def test_collect_datatypes(raw: str, expected: set[str]) -> None:
    assert collect_datatypes(raw) == expected


@pytest.mark.parametrize(
    ("stored", "filter_val", "expected"),
    [
        ("int | float", "float", True),
        ("int|float", "float", True),
        ("int | float", "int|float", True),
        ("int", "float", False),
        ("list[int]", "list", True),
        ("list[int]", "list[float]", False),
        ("dict[str, float]", "dict[str,float]", True),
        ("Literal['a', 'b']", "Literal['a','b']", True),
        ("Literal['a', 'b']", "Literal['a']", False),
        ("int|", "int", False),
    ],
)
def test_datatype_matches(stored: str, filter_val: str, expected: bool) -> None:
    assert datatype_matches(stored, filter_val) is expected
