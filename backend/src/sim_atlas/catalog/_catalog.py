from __future__ import annotations

from math import ceil

import numpy as np

from sim_atlas import keyword_search
from sim_atlas.catalog._node_filter import NodeFilter, filter_options
from sim_atlas.catalog._workflow_graph import WorkflowGraph
from sim_atlas.embedding import create_embedding
from sim_atlas.models import (
    Filter,
    FilterOptions,
    NodeMetadata,
    ScoredSearchItem,
    ScoredSearchResponse,
    SearchResults,
    Suggestion,
)
from sim_atlas.node_text import short_description
from sim_atlas.settings import load_settings
from sim_atlas.storage.storage_interface import StorageInterface

# Reciprocal-rank-fusion constant for merging the semantic and keyword ranks.
_RRF_K = 60


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Cosine similarity of two vectors; 0.0 when either has zero norm."""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return np.dot(vec1, vec2) / (norm1 * norm2)


def _paginate(
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


def _embedding_text(node: NodeMetadata) -> str:
    description = node.description or ""
    port_lines = [
        f"{a.label}: {a.description}"
        for a in node.inputs + node.outputs
        if a.label and a.description
    ]
    if not port_lines:
        return description
    return description + "\n" + "\n".join(port_lines)


class Catalog:
    """Discovery over the stored nodes: search, suggest, facets and detail reads.

    Everything a reader sees goes through here, so ranking, filtering and the
    derived ``used_by``/``connections`` references live in one module whatever
    storage adapter sits underneath. Nodes handed out are hydrated copies; the
    stored nodes are never mutated. Writes go to the storage directly.
    """

    def __init__(self, storage: StorageInterface) -> None:
        self._storage = storage

    def read_node(self, id: str) -> NodeMetadata:
        """The node for *id*, hydrated. Raises KeyError if not found."""
        node = self._storage.read_node(id)
        return WorkflowGraph(self._index()).hydrate(node)

    def get_filter_options(self) -> FilterOptions:
        return filter_options(self._storage.nodes())

    def search(
        self,
        query: str | None,
        filter: Filter | None = None,
        page: int = 1,
        limit: int = 10,
        drop_unmatched: bool = True,
    ) -> ScoredSearchResponse:
        """Keyword search: BM25 over the filtered nodes.

        With ``drop_unmatched`` (the default) the query is a constraint and
        nodes it does not touch are excluded. With ``drop_unmatched=False``
        the filters alone decide membership and the query only orders what they
        returned, so adding a query can never shrink the result set.
        """
        filtered = self._filtered(filter)

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
        return self._hydrated_page(scored, page=page, limit=limit)

    async def search_hybrid(
        self,
        query: str | None,
        filter: Filter | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> ScoredSearchResponse:
        """Hybrid search combining semantic (cosine) and keyword ranking via RRF.

        Falls back to keyword-only search when there is no query to embed or no
        embedding provider is configured, so search always works even without AI
        (ADR-0018).

        Both legs see every filtered node: unenriched nodes that have no
        embedding can still surface through the BM25 keyword rank, and nodes
        whose wording misses the query entirely can still surface through the
        semantic rank.
        """
        if not query or not query.strip() or not load_settings().embeddings_enabled:
            return self.search(query, filter, page=page, limit=limit)

        filtered = self._filtered(filter)

        # --- semantic rank (only nodes with embeddings) ---
        query_embedding = (await create_embedding([query], input_type="query"))[0]
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
        return self._hydrated_page(scored, page=page, limit=limit)

    def suggest(
        self, query: str, filter: Filter | None = None, limit: int = 10
    ) -> list[Suggestion]:
        """Cheap type-ahead lookup: name/import matches only, tiered and sorted.

        Unlike ``search``, this never touches docstrings, descriptions or
        embeddings, and never builds the ``used_by``/connections graph — it
        exists to be fast (ADR-0020). Returns ``[]`` for a blank query.

        Matches first, then filters the survivors — ``NodeFilter`` allocates
        ``inputs + outputs`` per node even with no port filter set, so
        matching first keeps the cost proportional to the match count instead
        of to the catalog size.
        """
        needle = query.strip().lower()
        if not needle:
            return []

        tiered: list[tuple[int, NodeMetadata]] = []
        for node in self._storage.nodes():
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

    async def enrich(self, only_ids: list[str] | None = None) -> None:
        nodes = self._storage.nodes()
        nodes_to_enrich = (
            [node for node in nodes if node.id in only_ids]
            if only_ids
            else [node for node in nodes if node.embedding is None]
        )
        await self._embed([node for node in nodes_to_enrich if node.description])

    async def embed_missing(self) -> None:
        await self._embed(
            [node for node in self._storage.nodes() if node.embedding is None]
        )

    async def _embed(self, nodes: list[NodeMetadata]) -> None:
        if not nodes:
            return
        embeddings = await create_embedding(
            [_embedding_text(node) for node in nodes], input_type="document"
        )
        self._storage.update_nodes(
            [
                node.model_copy(update={"embedding": embedding})
                for node, embedding in zip(nodes, embeddings, strict=True)
            ]
        )

    def _index(self) -> dict[str, NodeMetadata]:
        return {node.id: node for node in self._storage.nodes()}

    def _filtered(self, filter: Filter | None) -> list[NodeMetadata]:
        item_filter = NodeFilter(filter or Filter())
        return [node for node in self._storage.nodes() if item_filter(node)]

    def _hydrated_page(
        self, items: list[ScoredSearchItem], page: int, limit: int
    ) -> ScoredSearchResponse:
        response = _paginate(items, page=page, limit=limit)
        if response.results.data:
            graph = WorkflowGraph(self._index())
            for item in response.results.data:
                item.node = graph.hydrate(item.node)
        return response
