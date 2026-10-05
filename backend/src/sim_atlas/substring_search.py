"""Substring ranking over node identifiers: the predictable, exact leg.

The query is matched as one literal substring of the node's name or import
path, which is what a type-ahead box or a list filter needs: no typo
tolerance, no word-order freedom, no surprises. It finds what the token-based
keyword leg cannot — a fragment in the middle of a token.

Only identifier fields are matched. Without IDF nothing would damp a hit in
prose ("add" in "padding", "address", "added"), so docstrings and descriptions
are left to the other legs.

Scoring is tiered first, coverage second::

    score = band(tier) + coverage,   coverage = len(query) / len(field)

The bands are 1.0 apart and coverage is at most 1, so a hit in a lower tier
never overtakes a higher one. Within a tier, the hit that accounts for more of
its field ranks first ("add" puts ``Add`` above ``AddCationAdatoms``). Pure
functions only: no storage, no I/O.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from sim_atlas.keyword_search import token_starts
from sim_atlas.models import NodeMetadata

_NAME_PREFIX_BAND = 3.0
_NAME_WORD_START_BAND = 2.0
_NAME_SUBSTRING_BAND = 1.0
_IMPORT_SUBSTRING_BAND = 0.0


def _score(needle: str, node: NodeMetadata, fold: Callable[[str], str]) -> float | None:
    """The tiered score of *needle* in *node*, or None if it does not occur."""
    name = fold(node.name)
    if needle in name:
        coverage = len(needle) / len(name)
        if name.startswith(needle):
            return _NAME_PREFIX_BAND + coverage
        if any(name.startswith(needle, start) for start in token_starts(node.name)):
            return _NAME_WORD_START_BAND + coverage
        return _NAME_SUBSTRING_BAND + coverage

    python_import = fold(node.python_import or "")
    if needle in python_import:
        return _IMPORT_SUBSTRING_BAND + len(needle) / len(python_import)
    return None


def rank(
    query: str,
    nodes: Iterable[NodeMetadata],
    *,
    case_sensitive: bool = False,
) -> dict[str, float]:
    """Score *nodes* against *query*, as ``{node id: score}``.

    Only nodes whose name or import path contains the stripped query are
    present; the rest are absent rather than scored zero. A blank query
    matches nothing.
    """
    fold: Callable[[str], str] = str if case_sensitive else str.lower
    needle = fold(query.strip())
    if not needle:
        return {}

    scores: dict[str, float] = {}
    for node in nodes:
        score = _score(needle, node, fold)
        if score is not None:
            scores[node.id] = score
    return scores
