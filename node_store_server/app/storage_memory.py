from __future__ import annotations

import os
import pickle

import numpy as np

from .ai import create_embedding
from .models import (
    NodeMetadata,
    NodeResponse,
    NodeType,
    ScoredSearchResponse,
)
from .storage import StorageInterface


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute the cosine similarity between two vectors.

    Args:
        vec1 (list[float]): The first vector.
        vec2 (list[float]): The second vector.

    Returns:
        float: The cosine similarity between the two vectors.
    """

    # Convert to numpy arrays
    array1 = np.array(vec1)
    array2 = np.array(vec2)

    # Compute cosine similarity
    dot_product = np.dot(array1, array2)
    norm1 = np.linalg.norm(array1)
    norm2 = np.linalg.norm(array2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot_product / (norm1 * norm2)
    return similarity


class InMemoryStorage(StorageInterface):
    """In-memory storage implementation for node metadata"""

    def __init__(self, start_clean: bool = False) -> None:
        self._storage: dict[str, NodeMetadata] = {}
        self._connected = False

        if not start_clean and os.path.exists("in-memory.pkl"):
            try:
                with open("in-memory.pkl", "rb") as f:
                    self._storage = pickle.load(f)
            except Exception:
                pass  # If loading fails, start with empty storage

        print(f"InMemoryStorage initialized with {len(self._storage)} items.")

    def connect(self) -> None:
        """Initialize the in-memory storage"""
        self._connected = True

    def close(self) -> None:
        """Close the storage (no-op for in-memory)"""
        self._connected = False

    def _save_to_disk(self) -> None:
        """Save the current storage state to disk"""

        with open("in-memory.pkl", "wb") as f:
            pickle.dump(self._storage, f)

    def __getitem__(self, key: str) -> NodeMetadata:
        return self._storage[key]

    def __setitem__(self, key: str, value: NodeMetadata) -> None:
        self._storage[key] = value
        self._save_to_disk()

    def __delitem__(self, key: str) -> None:
        del self._storage[key]
        self._save_to_disk()

    def __iter__(self):
        return iter(self._storage)

    def __len__(self) -> int:
        return len(self._storage)

    def filter(
        self, qualname: str | None = None, type: NodeType | None = None
    ) -> list[NodeMetadata]:
        def filter_item(item: NodeMetadata) -> bool:
            return (
                qualname.lower() in item.python_import.lower() if qualname else True
            ) and (item.node_type == type if type else True)

        return [item for item in self._storage.values() if filter_item(item)]

    def search(self, query: str) -> list[ScoredSearchResponse]:
        """
        Search for nodes matching the given query.

        Args:
            query: search query string

        Returns:
            List of matching node metadata
        """

        def skip_node(query: str, node: NodeMetadata) -> bool:
            return query.lower() not in node.python_import.lower()

        scored_results = [
            ScoredSearchResponse(score=1.0, node=node)
            for node in self._storage.values()
            if not skip_node(query, node)
        ]

        sorted_results = sorted(scored_results, key=lambda x: x.score, reverse=False)

        facets: dict[str, int] = {}
        for result in sorted_results:
            facets[result.node.node_type] = facets.get(result.node.node_type, 0) + 1

        return sorted_results

    def search_semantic(
        self, query: str, limit: int = 10
    ) -> list[ScoredSearchResponse]:
        """
        Perform semantic search on node metadata.

        Args:
            query: Natural language search query
            limit: Maximum number of results to return

        Returns:
            List of relevant node metadata, ordered by relevance
        """
        # Generate embedding for the query
        query_embedding = create_embedding(query)

        # Calculate similarities
        similarities: list[ScoredSearchResponse] = []
        for _node_hash, node in self._storage.items():
            if node.embedding is not None:
                similarity = cosine_similarity(query_embedding, node.embedding)
                similarities.append(
                    ScoredSearchResponse(
                        score=similarity,
                        node=NodeResponse(**node.model_dump()),
                    )
                )

        # Sort by similarity (descending) and limit results
        similarities.sort(key=lambda x: x.score, reverse=True)

        # Return only the node metadata (without scores)
        return similarities[:limit]
