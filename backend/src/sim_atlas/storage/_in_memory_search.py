"""In-process ranking for adapters that hold every node in memory.

A database-backed adapter would answer the same StorageInterface queries with
its own engine; these functions are how an in-memory one answers them. Pure
functions only: no storage, no I/O, no settings, and the nodes passed in are
never mutated. Results are unhydrated; the adapter fills in the derived
``used_by``/``connections`` references.
"""

from __future__ import annotations

from collections.abc import Iterable
from math import ceil

import numpy as np

from sim_atlas import keyword_search
from sim_atlas.models import (
    Filter,
    NodeMetadata,
    ScoredSearchItem,
    ScoredSearchResponse,
    SearchResults,
    Suggestion,
)
from sim_atlas.node_text import short_description
from sim_atlas.storage._node_filter import NodeFilter

# Reciprocal-rank-fusion constant for merging the semantic and keyword ranks.
_RRF_K = 60


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Cosine similarity of two vectors; 0.0 when either has zero norm."""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return np.dot(vec1, vec2) / (norm1 * norm2)


def paginate(
    items: list[ScoredSearchItem], page: int = 1, limit: int = 10
) -> ScoredSearchResponse:
    safe_page = max(page, 1)
    safe_limit = max(limit, 1)
    total_items = len(items)
    total_pages = ceil(total_items / safe_limit) if total_items else 0

    start = (safe_page - 1) * safe_limit
    end = start + safe_limit

    return ScoredSearchResponse(
        results=SearchResults(
            data=items[start:end],
            page=safe_page,
            limit=safe_limit,
            total_items=total_items,
            total_pages=total_pages,
        )
    )


def _filtered(
    nodes: Iterable[NodeMetadata], filter: Filter | None
) -> list[NodeMetadata]:
    item_filter = NodeFilter(filter or Filter())
    return [node for node in nodes if item_filter(node)]


def keyword_ranked(
    nodes: Iterable[NodeMetadata],
    query: str | None,
    filter: Filter | None,
    drop_unmatched: bool,
) -> list[ScoredSearchItem]:
    """BM25 over the filtered nodes, best first; see ``StorageInterface.search``."""
    filtered = _filtered(nodes, filter)

    if not query or not query.strip():
        scored = [ScoredSearchItem(score=1.0, node=node) for node in filtered]
    else:
        scores = keyword_search.rank(query, filtered)
        scored = [
            ScoredSearchItem(score=scores.get(node.id, 0.0), node=node)
            for node in filtered
            if not drop_unmatched or scores.get(node.id, 0.0) > 0.0
        ]

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored


def hybrid_ranked(
    nodes: Iterable[NodeMetadata],
    query: str,
    query_embedding: np.ndarray,
    filter: Filter | None,
) -> list[ScoredSearchItem]:
    """Semantic (cosine) and keyword (BM25) ranks merged via RRF, best first.

    Both legs see every filtered node: unenriched nodes that have no
    embedding can still surface through the BM25 keyword rank, and nodes
    whose wording misses the query entirely can still surface through the
    semantic rank.
    """
    filtered = _filtered(nodes, filter)

    # --- semantic rank (only nodes with embeddings) ---
    sem_scores: list[tuple[str, float]] = [
        (node.id, cosine_similarity(query_embedding, node.embedding))
        for node in filtered
        if node.embedding is not None
    ]
    sem_scores.sort(key=lambda x: x[1], reverse=True)
    sem_rank: dict[str, int] = {
        node_id: r + 1 for r, (node_id, _) in enumerate(sem_scores)
    }

    # --- keyword rank (all filtered nodes) ---
    kw_scores = sorted(
        keyword_search.rank(query, filtered).items(),
        key=lambda x: x[1],
        reverse=True,
    )
    kw_rank: dict[str, int] = {
        node_id: r + 1 for r, (node_id, _) in enumerate(kw_scores)
    }

    # --- RRF merge ---
    candidate_ids = set(sem_rank) | set(kw_rank)
    node_lookup: dict[str, NodeMetadata] = {n.id: n for n in filtered}
    scored: list[ScoredSearchItem] = [
        ScoredSearchItem(
            score=(1 / (_RRF_K + sem_rank[nid]) if nid in sem_rank else 0.0)
            + (1 / (_RRF_K + kw_rank[nid]) if nid in kw_rank else 0.0),
            node=node_lookup[nid],
        )
        for nid in candidate_ids
    ]
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored


def _suggest_tier(node: NodeMetadata, needle: str) -> int | None:
    """The best-matching tier for *needle* against *node*, or None."""
    name = node.name.lower()
    if name.startswith(needle):
        return 0
    if any(token.startswith(needle) for token in keyword_search.tokenize(node.name)):
        return 1
    if needle in name:
        return 2
    if needle in (node.python_import or "").lower():
        return 3
    return None


def _to_suggestion(node: NodeMetadata) -> Suggestion:
    return Suggestion(
        id=node.id,
        name=node.name,
        python_import=node.python_import,
        artifact_type=node.artifact_type,
        short_description=short_description(node.brief_description, node.docstring),
    )


def suggest(
    nodes: Iterable[NodeMetadata], query: str, filter: Filter | None, limit: int
) -> list[Suggestion]:
    """Name/import matches only, tiered and sorted; see ``StorageInterface.suggest``.

    Matches first, then filters the survivors — ``NodeFilter`` allocates
    ``inputs + outputs`` per node even with no port filter set, so
    matching first keeps the cost proportional to the match count instead
    of to the catalog size.
    """
    needle = query.strip().lower()
    if not needle:
        return []

    tiered: list[tuple[int, NodeMetadata]] = []
    for node in nodes:
        tier = _suggest_tier(node, needle)
        if tier is not None:
            tiered.append((tier, node))

    item_filter = NodeFilter(filter or Filter())
    matching = [(tier, n) for tier, n in tiered if item_filter(n)]
    matching.sort(
        key=lambda pair: (
            pair[0],
            len(pair[1].name),
            pair[1].name.lower(),
            pair[1].id,
        )
    )

    return [_to_suggestion(node) for _, node in matching[:limit]]
