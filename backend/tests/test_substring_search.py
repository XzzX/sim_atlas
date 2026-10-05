"""Unit tests for substring ranking over node identifiers."""

from __future__ import annotations

from sim_atlas.models import NodeMetadata
from sim_atlas.search import substring

from .test_storage_interface import make_node


def _node(name: str, python_import: str | None = None, **kwargs: str) -> NodeMetadata:
    return make_node(
        name=name,
        python_import=python_import if python_import is not None else name,
        source_code=f"def {name.replace('.', '_')}(): pass",
        **kwargs,
    )


def _order(query: str, nodes: list[NodeMetadata]) -> list[str]:
    scores = substring.rank(query, nodes)
    by_id = {node.id: node.name for node in nodes}
    return [by_id[key] for key in sorted(scores, key=lambda k: scores[k], reverse=True)]


def test_coverage_beats_field_length_within_a_tier() -> None:
    """'add' accounts for all of Add but a fifth of AddCationAdatoms."""
    nodes = [_node("AddCationAdatoms"), _node("Add")]
    assert _order("add", nodes) == ["Add", "AddCationAdatoms"]


def test_a_lower_tier_never_overtakes_a_higher_one() -> None:
    """Coverage orders hits within a tier only, never across tiers."""
    prefix = _node("AddCationAdatoms")
    word_start = _node("x_add_y")
    substring = _node("padd")
    import_only = _node("Other", python_import="add")
    nodes = [import_only, substring, word_start, prefix]
    assert _order("add", nodes) == ["AddCationAdatoms", "x_add_y", "padd", "Other"]


def test_a_camel_case_part_counts_as_a_word_start() -> None:
    nodes = [_node("agrain"), _node("BuildMgGrainBoundary")]
    assert _order("grain", nodes) == ["BuildMgGrainBoundary", "agrain"]


def test_an_exact_name_scores_highest() -> None:
    exact = _node("Add")
    scores = substring.rank("add", [exact])
    assert scores[exact.id] == 4.0  # noqa: PLR2004


def test_import_coverage_is_against_the_import_path() -> None:
    short = _node("a", python_import="lib.solver")
    long = _node("b", python_import="lib.deeply.nested.solver")
    assert _order("solver", [long, short]) == ["a", "b"]


def test_case_insensitive_by_default() -> None:
    node = _node("CalcMD")
    assert node.id in substring.rank("calcmd", [node])
    assert node.id in substring.rank("CALCMD", [node])


def test_case_sensitive_matching() -> None:
    node = _node("CalcMD")
    assert node.id in substring.rank("MD", [node], case_sensitive=True)
    assert substring.rank("md", [node], case_sensitive=True) == {}


def test_query_is_stripped() -> None:
    node = _node("calculate_energy")
    assert node.id in substring.rank("  calc  ", [node])


def test_non_matches_are_absent_rather_than_zero_scored() -> None:
    hit, miss = _node("calc"), _node("other")
    assert set(substring.rank("calc", [hit, miss])) == {hit.id}


def test_prose_fields_are_never_matched() -> None:
    node = _node(
        "opaque",
        docstring="Adds padding to the address.",
        brief_description="An added helper.",
        description="Addition.",
    )
    assert substring.rank("add", [node]) == {}


def test_a_fragment_inside_a_token_matches() -> None:
    """What the token-based keyword leg cannot do."""
    node = _node("buildmggrainboundary")
    assert node.id in substring.rank("grain", [node])


def test_a_query_spanning_separators_matches() -> None:
    node = _node("get_temperature")
    assert node.id in substring.rank("t_temp", [node])


def test_blank_query_matches_nothing() -> None:
    assert substring.rank("   ", [_node("calc")]) == {}


def test_empty_corpus_matches_nothing() -> None:
    assert substring.rank("calc", []) == {}
