"""Search and embedding policy above the StorageInterface seam (ADR-0023).

Everything here is the same whichever storage adapter is configured: whether a
search is hybrid or keyword-only (ADR-0018), embedding the query, and which
nodes get embedded from what text. The adapters do the ranking and storing;
they never read settings or call an embedding provider.
"""

from __future__ import annotations

from sim_atlas.embedding import create_embedding
from sim_atlas.models import Filter, NodeMetadata, ScoredSearchResponse
from sim_atlas.settings import load_settings
from sim_atlas.storage.storage_interface import StorageInterface


async def search(
    storage: StorageInterface,
    query: str | None,
    filter: Filter | None = None,
    page: int = 1,
    limit: int = 10,
    semantic: bool | None = None,
) -> ScoredSearchResponse:
    """Hybrid search when embeddings are configured, keyword search otherwise.

    ``semantic=False`` forces keyword-only search; ``None``/``True`` let the
    server decide. There is no query to embed without a query, so a blank one
    always searches by keyword (the filters alone).
    """
    if (
        semantic is not False
        and query
        and query.strip()
        and load_settings().embeddings_enabled
    ):
        query_embedding = (await create_embedding([query], input_type="query"))[0]
        return storage.search_hybrid(
            query, query_embedding, filter, page=page, limit=limit
        )
    return storage.search(query, filter, page=page, limit=limit)


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


async def enrich(storage: StorageInterface, only_ids: list[str] | None = None) -> None:
    nodes = storage.nodes()
    nodes_to_enrich = (
        [node for node in nodes if node.id in only_ids]
        if only_ids
        else [node for node in nodes if node.embedding is None]
    )
    await _embed(storage, [node for node in nodes_to_enrich if node.description])


async def embed_missing(storage: StorageInterface) -> None:
    await _embed(storage, [node for node in storage.nodes() if node.embedding is None])


async def _embed(storage: StorageInterface, nodes: list[NodeMetadata]) -> None:
    if not nodes:
        return
    embeddings = await create_embedding(
        [_embedding_text(node) for node in nodes], input_type="document"
    )
    storage.set_embeddings(
        {node.id: embedding for node, embedding in zip(nodes, embeddings, strict=True)}
    )
