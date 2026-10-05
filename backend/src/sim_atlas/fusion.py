"""Weighted reciprocal rank fusion of ranking legs.

Each leg (substring, keyword, semantic) scores nodes on its own scale — a
coverage ratio, an IDF sum, a cosine — so raw scores cannot be blended. Fusion
only looks at each node's rank within a leg. Pure functions only: no storage,
no I/O.
"""

from __future__ import annotations

from collections.abc import Sequence

# Substring and keyword are both lexical over the same identifiers and agree
# often, so equal weights would make the fused result two-thirds lexical by
# accident. Substring is weighted down to make that bias deliberate.
SUBSTRING_WEIGHT = 0.7
KEYWORD_WEIGHT = 1.0
SEMANTIC_WEIGHT = 1.0

RRF_K = 60


def reciprocal_rank_fusion(
    legs: Sequence[tuple[float, dict[str, float]]],
    k: int = RRF_K,
) -> dict[str, float]:
    """Fuse ``(weight, {node id: score})`` legs into ``{node id: fused score}``.

    A node contributes ``weight / (k + rank)`` from every leg that scored it
    and nothing from a leg that did not: absent is not the same as ranked
    last. Ranks are 1-based and ties keep the leg's insertion order.

    Weights are renormalised over the legs passed in, so pass only the legs
    that actually ran (e.g. omit semantic without an embedding provider). That
    keeps fused scores on the same scale whichever legs ran.
    """
    total_weight = sum(weight for weight, _ in legs)
    if total_weight <= 0.0:
        return {}

    fused: dict[str, float] = {}
    for weight, scores in legs:
        ranked = sorted(scores, key=lambda node_id: scores[node_id], reverse=True)
        for rank, node_id in enumerate(ranked, start=1):
            contribution = (weight / total_weight) / (k + rank)
            fused[node_id] = fused.get(node_id, 0.0) + contribution
    return fused
