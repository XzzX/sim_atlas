"""Semantic ranking: cosine similarity between a query and node embeddings.

The query embedding is computed by the caller (awaiting the embedding provider
is I/O), so ranking stays pure and synchronous. Pure functions only: no
storage, no I/O.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from sim_atlas.models import NodeMetadata


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute the cosine similarity between two vectors.

    Args:
        vec1 (np.ndarray): The first vector.
        vec2 (np.ndarray): The second vector.

    Returns:
        float: The cosine similarity between the two vectors.
    """
    # Compute cosine similarity
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot_product / (norm1 * norm2)
    return similarity


def rank(
    query_embedding: np.ndarray, nodes: Iterable[NodeMetadata]
) -> dict[str, float]:
    """Score *nodes* by cosine similarity to *query_embedding*.

    Only nodes that have an embedding are present; unembedded nodes are absent
    rather than scored zero. Every embedded node is present, however weak its
    similarity.
    """
    return {
        node.id: cosine_similarity(query_embedding, node.embedding)
        for node in nodes
        if node.embedding is not None
    }
