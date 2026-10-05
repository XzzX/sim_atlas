"""Unit tests for typo-tolerant keyword ranking.

Every query here is sentence-shaped, because that is what the MCP tool
descriptions instruct agents to send and what whole-query substring matching
could never find.
"""

from __future__ import annotations

import pytest

from sim_atlas.models import AnnotationResponse, NodeMetadata
from sim_atlas.search import keyword

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
    """Node names ranked best-first."""
    scores = keyword.rank(query, _CORPUS)
    by_id = {node.id: node.name for node in _CORPUS}
    return [
        by_id[key]
        for key, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    ]


def test_sentence_shaped_query_ranks_the_right_node_first() -> None:
    """The regression: a full sentence must match, and match the better entry."""
    ranked = _order("compute the gradient of a temperature field on a mesh")
    assert ranked[0] == "gradient_on_mesh"


def test_sentence_shaped_query_discriminates_between_entries() -> None:
    """The same filler words, a different domain term, the other winner."""
    ranked = _order("compute the temperature of an atomic structure")
    assert ranked[0] == "get_temperature"


def test_filler_words_alone_do_not_outrank_domain_terms() -> None:
    """IDF must keep 'compute the' from deciding the ranking."""
    scores = keyword.rank("compute the gradient", _CORPUS)
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
    assert node.id in keyword.rank("fn_a", [node])


def test_unmatched_nodes_are_absent_rather_than_zero_scored() -> None:
    scores = keyword.rank("crystallography", _CORPUS)
    assert scores == {}


def test_name_outweighs_docstring() -> None:
    """The same term is worth more in the callable's name than in prose."""
    in_name = make_node(
        name="diffusion", docstring="unrelated", source_code="def diffusion(): pass"
    )
    in_docstring = make_node(
        name="unrelated", docstring="diffusion", source_code="def unrelated(): pass"
    )
    scores = keyword.rank("diffusion", [in_name, in_docstring])
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
    assert node.id in keyword.rank("displacement in angstrom", [node])


def test_query_without_usable_tokens_scores_nothing() -> None:
    assert keyword.rank("   ", _CORPUS) == {}


def test_empty_corpus_scores_nothing() -> None:
    assert keyword.rank("anything", []) == {}


# ---------------------------------------------------------------------------
# Partial-word matching (the trailing token is treated as a prefix)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prefix", ["t", "te", "tem", "temp", "tempe", "temper", "temperat"]
)
def test_partial_prefix_of_a_name_token_matches(prefix: str) -> None:
    """The regression: a query typed mid-word must already find the word."""
    assert _TEMPERATURE.id in keyword.rank(prefix, _CORPUS)


def test_only_the_trailing_token_is_prefix_expanded() -> None:
    """An earlier fragment gets no prefix completion, only near-spelling matching.

    "temp" is too far from "temperature" to count as a typo of it.
    """
    assert _TEMPERATURE.id not in keyword.rank("temp gradient", _CORPUS)


def test_prefix_expansion_keeps_the_exact_match_ranked_first() -> None:
    """Once the word is complete, the exact match still wins outright."""
    assert _order("temperature")[0] == "get_temperature"


def test_an_unmatched_prefix_scores_nothing() -> None:
    assert keyword.rank("crystall", _CORPUS) == {}


# ---------------------------------------------------------------------------
# Typo tolerance (every token also matches near spellings)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "temprature of an atomic structure",  # dropped letter
        "temperatrue of an atomic structure",  # swapped letters
        "atomic temperatures",  # plural
        "kinetik energy",  # wrong letter, docstring only
    ],
)
def test_misspelled_query_finds_the_node(query: str) -> None:
    assert _order(query)[0] == "get_temperature"


def test_typo_in_a_non_trailing_token_still_matches() -> None:
    """Fuzzy matching is not limited to the token being typed."""
    assert _GRADIENT.id in keyword.rank("gradiant on a mesh", _CORPUS)


def test_exact_spelling_outranks_a_near_spelling() -> None:
    exact = make_node(name="mesh_refine", source_code="def mesh_refine(): pass")
    near = make_node(name="meshes_refine", source_code="def meshes_refine(): pass")
    scores = keyword.rank("mesh refine", [exact, near])
    assert scores[exact.id] > scores[near.id]


def test_different_short_words_are_not_treated_as_typos() -> None:
    """Three letters are too few to tell a typo from another word."""
    bcc = make_node(name="bcc_lattice", source_code="def bcc_lattice(): pass")
    assert keyword.rank("fcc", [bcc]) == {}


def test_unrelated_words_sharing_some_letters_do_not_match() -> None:
    mess = make_node(name="mess_cleanup", source_code="def mess_cleanup(): pass")
    assert keyword.rank("mesh grid", [mess]) == {}


def test_trigram_similarity_is_symmetric_and_one_for_identical_tokens() -> None:
    assert keyword.trigram_similarity("lammps", "lammps") == 1.0
    assert keyword.trigram_similarity("lamps", "lammps") == keyword.trigram_similarity(
        "lammps", "lamps"
    )


# ---------------------------------------------------------------------------
# Best-field scoring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("better", "worse"),
    [
        ({"name": "diffusion"}, {"brief_description": "diffusion"}),
        ({"brief_description": "diffusion"}, {"docstring": "diffusion"}),
    ],
)
def test_field_order_name_then_brief_then_docstring(
    better: dict[str, str], worse: dict[str, str]
) -> None:
    defaults = {"name": "unrelated", "docstring": "unrelated"}
    a = make_node(**{**defaults, **better, "source_code": "def a(): pass"})
    b = make_node(**{**defaults, **worse, "source_code": "def b(): pass"})
    scores = keyword.rank("diffusion", [a, b])
    assert scores[a.id] > scores[b.id]


def test_repeating_a_term_across_fields_adds_nothing() -> None:
    """A name echoed in the import path and keywords counts once, at name weight."""
    plain = make_node(
        name="diffusion",
        python_import="lib.other",
        keywords=[],
        source_code="def a(): pass",
    )
    echoed = make_node(
        name="diffusion",
        python_import="lib.diffusion",
        keywords=["diffusion"],
        docstring="diffusion diffusion diffusion",
        source_code="def b(): pass",
    )
    scores = keyword.rank("diffusion", [plain, echoed])
    assert scores[plain.id] == pytest.approx(scores[echoed.id])


def test_more_matched_terms_beat_a_single_name_hit() -> None:
    """Rare terms in prose outweigh one common word in the name."""
    common_in_name = make_node(name="compute", source_code="def a(): pass")
    terms_in_docstring = make_node(
        name="opaque",
        docstring="Gradient of the temperature field.",
        source_code="def b(): pass",
    )
    filler = [
        make_node(name="compute_x", source_code=f"def f{i}(): pass") for i in range(3)
    ]
    scores = keyword.rank(
        "compute the gradient of a temperature field",
        [common_in_name, terms_in_docstring, *filler],
    )
    assert scores[terms_in_docstring.id] > scores[common_in_name.id]


# ---------------------------------------------------------------------------
# CamelCase identifiers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "tokens"),
    [
        (
            "BuildMgGrainBoundary",
            ["build", "mg", "grain", "boundary", "buildmggrainboundary"],
        ),
        ("HTTPServerNode", ["http", "server", "node", "httpservernode"]),
        ("CalcMD", ["calc", "md", "calcmd"]),
        ("get_temperature", ["get", "temperature"]),
        ("ase.md.Add", ["ase", "md", "add"]),
    ],
)
def test_tokenize_splits_camel_case_and_keeps_the_whole_word(
    text: str, tokens: list[str]
) -> None:
    assert keyword.tokenize(text) == tokens


_GRAIN_BOUNDARY = make_node(
    name="BuildMgGrainBoundary",
    python_import="structures.BuildMgGrainBoundary",
    source_code="class BuildMgGrainBoundary: pass",
)
_CALC_MD = make_node(
    name="CalcMD",
    python_import="sim.CalcMD",
    source_code="class CalcMD: pass",
)
_CAMEL_CORPUS = [*_CORPUS, _GRAIN_BOUNDARY, _CALC_MD]


@pytest.mark.parametrize(
    ("query", "node"),
    [
        ("grain", _GRAIN_BOUNDARY),
        ("boundary", _GRAIN_BOUNDARY),
        ("md", _CALC_MD),
    ],
)
def test_a_camel_case_part_finds_the_node(query: str, node: NodeMetadata) -> None:
    assert node.id in keyword.rank(query, _CAMEL_CORPUS)


@pytest.mark.parametrize("query", ["buildmg", "BuildMgGrain", "BuildMgGrainBoundary"])
def test_the_whole_camel_case_word_still_matches(query: str) -> None:
    scores = keyword.rank(query, _CAMEL_CORPUS)
    assert max(scores, key=lambda key: scores[key]) == _GRAIN_BOUNDARY.id
