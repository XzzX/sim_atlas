"""Unit tests for BM25 keyword ranking.

Every query here is sentence-shaped, because that is what the MCP tool
descriptions instruct agents to send and what whole-query substring matching
could never find.
"""

from __future__ import annotations

import pytest

from sim_atlas import keyword_search
from sim_atlas.models import AnnotationResponse

from .test_storage_interface import make_node

_GRADIENT = make_node(
    name="gradient_on_mesh",
    python_import="mylib.mesh.gradient_on_mesh",
    brief_description="Gradient of a scalar field on an unstructured mesh.",
    docstring="Computes the gradient of a field over mesh cells.",
    source_code="def gradient_on_mesh(): pass",
)
_TEMPERATURE = make_node(
    name="get_temperature",
    python_import="ase.md.get_temperature",
    brief_description="Instantaneous temperature of an atomic structure.",
    docstring="Derives the temperature from the kinetic energy of the atoms.",
    source_code="def get_temperature(): pass",
)
_CORPUS = [_GRADIENT, _TEMPERATURE]


def _order(query: str) -> list[str]:
    """Artifact names ranked best-first."""
    scores = keyword_search.rank(query, _CORPUS)
    by_id = {artifact.id: artifact.name for artifact in _CORPUS}
    return [
        by_id[key]
        for key, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    ]


def test_sentence_shaped_query_ranks_the_right_artifact_first() -> None:
    """The regression: a full sentence must match, and match the better entry."""
    ranked = _order("compute the gradient of a temperature field on a mesh")
    assert ranked[0] == "gradient_on_mesh"


def test_sentence_shaped_query_discriminates_between_entries() -> None:
    """The same filler words, a different domain term, the other winner."""
    ranked = _order("compute the temperature of an atomic structure")
    assert ranked[0] == "get_temperature"


def test_filler_words_alone_do_not_outrank_domain_terms() -> None:
    """IDF must keep 'compute the' from deciding the ranking."""
    scores = keyword_search.rank("compute the gradient", _CORPUS)
    assert scores[_GRADIENT.id] > scores[_TEMPERATURE.id]


def test_identifiers_are_split_into_tokens() -> None:
    """A bare domain word finds a snake_case callable that contains it."""
    assert _order("unstructured mesh") == ["gradient_on_mesh"]


def test_dotted_import_paths_are_searchable() -> None:
    """The import path is indexed segment by segment."""
    assert "get_temperature" in _order("ase package")


def test_short_identifier_queries_survive_the_length_filter() -> None:
    """'fn_a' splits into two sub-3-char tokens; dropping both would find nothing."""
    node = make_node(name="fn_a", source_code="def fn_a(): pass")
    assert node.id in keyword_search.rank("fn_a", [node])


def test_unmatched_artifacts_are_absent_rather_than_zero_scored() -> None:
    scores = keyword_search.rank("crystallography", _CORPUS)
    assert scores == {}


def test_name_outweighs_docstring() -> None:
    """The same term is worth more in the callable's name than in prose."""
    in_name = make_node(
        name="diffusion", docstring="unrelated", source_code="def diffusion(): pass"
    )
    in_docstring = make_node(
        name="unrelated", docstring="diffusion", source_code="def unrelated(): pass"
    )
    scores = keyword_search.rank("diffusion", [in_name, in_docstring])
    assert scores[in_name.id] > scores[in_docstring.id]


def test_port_units_and_quantities_are_searchable() -> None:
    """Annotation metadata is part of the searchable text, not just prose."""
    node = make_node(
        name="opaque",
        source_code="def opaque(): pass",
        outputs=[
            AnnotationResponse(label="out", unit="angstrom", quantity="displacement")
        ],
    )
    assert node.id in keyword_search.rank("displacement in angstrom", [node])


def test_query_without_usable_tokens_scores_nothing() -> None:
    assert keyword_search.rank("   ", _CORPUS) == {}


def test_empty_corpus_scores_nothing() -> None:
    assert keyword_search.rank("anything", []) == {}


# ---------------------------------------------------------------------------
# Partial-word matching (the trailing token is treated as a prefix)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prefix", ["t", "te", "tem", "temp", "tempe", "temper", "temperat"]
)
def test_partial_prefix_of_a_name_token_matches(prefix: str) -> None:
    """The regression: a query typed mid-word must already find the word."""
    assert _TEMPERATURE.id in keyword_search.rank(prefix, _CORPUS)


def test_only_the_trailing_token_is_prefix_expanded() -> None:
    """An earlier, complete-looking token is matched exactly, not as a prefix."""
    assert _TEMPERATURE.id not in keyword_search.rank("temperat gradient", _CORPUS)


def test_prefix_expansion_keeps_the_exact_match_ranked_first() -> None:
    """Once the word is complete, the exact match still wins outright."""
    assert _order("temperature")[0] == "get_temperature"


def test_an_unmatched_prefix_scores_nothing() -> None:
    assert keyword_search.rank("crystall", _CORPUS) == {}
