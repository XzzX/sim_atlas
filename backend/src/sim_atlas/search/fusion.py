"""Weighted reciprocal rank fusion of ranking legs.

Each leg (substring, keyword, semantic) scores nodes on its own scale — a
coverage ratio, an IDF sum, a cosine — so raw scores cannot be blended. Fusion
only looks at each node's rank within a leg. Pure functions only: no storage,
no I/O.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple

# Substring and keyword are both lexical over the same identifiers and agree
# often, so equal weights would make the fused result two-thirds lexical by
# accident. Substring is weighted down to make that bias deliberate.
SUBSTRING_WEIGHT = 0.7
KEYWORD_WEIGHT = 1.0
SEMANTIC_WEIGHT = 1.0

RRF_K = 60


class Leg(NamedTuple):
    """One leg's ``{node id: score}`` and how much it counts in the fusion.

    A *partial* leg can only score some nodes — semantic ranking cannot score
    a node without an embedding — so a node's absence from it means "no
    opinion" rather than "no match". Absence from a full leg is a miss.
    """

    weight: float
    scores: dict[str, float]
    partial: bool = False


def _ranks(scores: dict[str, float]) -> dict[str, int]:
    """1-based competition ranks: tied scores share a rank."""
    ranks: dict[str, int] = {}
    previous: float | None = None
    rank = 0
    ordered = sorted(scores, key=lambda node_id: scores[node_id], reverse=True)
    for position, node_id in enumerate(ordered, start=1):
        if scores[node_id] != previous:
            rank, previous = position, scores[node_id]
        ranks[node_id] = rank
    return ranks


def reciprocal_rank_fusion(legs: Sequence[Leg], k: int = RRF_K) -> dict[str, float]:
    """Fuse *legs* into ``{node id: fused score}``.

    A node gains ``weight / (k + rank)`` from every leg that ranked it. Ties
    within a leg share a rank, so insertion order never decides between
    nodes a leg cannot tell apart.

    Weights are renormalised per node over the legs that could have scored
    it: every full leg, plus each partial leg that holds it. Pass only the
    legs that actually ran (e.g. omit semantic without an embedding
    provider), and a node the semantic leg cannot see — an unenriched node —
    is fused as if that leg had not run instead of losing its share.
    """
    full_weight = sum(leg.weight for leg in legs if not leg.partial)
    weighted: dict[str, float] = {}
    eligible_weight: dict[str, float] = {}
    for leg in legs:
        for node_id, rank in _ranks(leg.scores).items():
            weighted[node_id] = weighted.get(node_id, 0.0) + leg.weight / (k + rank)
            if leg.partial:
                eligible_weight[node_id] = (
                    eligible_weight.get(node_id, 0.0) + leg.weight
                )

    return {
        node_id: score / (full_weight + eligible_weight.get(node_id, 0.0))
        for node_id, score in weighted.items()
    }
