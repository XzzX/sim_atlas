from __future__ import annotations

import os
import pickle

import numpy as np
from numba import njit

from .ai import create_embedding
from .models import (
    NodeMetadata,
    NodeResponse,
    ScoredSearchResponse,
)
from .storage import FilterOptions, StorageInterface


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


class NodeFilter:
    def __init__(self, filter_options: FilterOptions) -> None:
        self.category = (
            filter_options.category.lower() if filter_options.category else None
        )
        self.type = filter_options.type if filter_options.type else None
        self.author = filter_options.author if filter_options.author else None
        self.keywords = filter_options.keywords if filter_options.keywords else None

    def __call__(self, node: NodeMetadata) -> bool:
        if self.category and not node.category.startswith(self.category):
            return False

        if self.type and node.node_type not in self.type:
            return False

        if self.author and node.author_name not in self.author:
            return False

        if self.keywords and not any(kw in node.keywords for kw in self.keywords):
            return False

        return True


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

    def filter(self, filter: FilterOptions) -> list[ScoredSearchResponse]:
        item_filter: NodeFilter = NodeFilter(filter)

        return [
            ScoredSearchResponse(score=1.0, node=item)
            for item in self._storage.values()
            if item_filter(item)
        ]

    def search(
        self, query: str | None, filter: FilterOptions
    ) -> list[ScoredSearchResponse]:
        """
        Search for nodes matching the given query.

        Args:
            query: search query string

        Returns:
            List of matching node metadata
        """

        from .fuzzy_scoring import weighted_fuzzy_match

        item_filter: NodeFilter = NodeFilter(filter)
        filtered_nodes = (item for item in self._storage.values() if item_filter(item))

        scored_results = (
            ScoredSearchResponse(
                score=score,
                node=item,
            )
            for score, item in (
                (weighted_fuzzy_match(query, item.python_import)[0], item)
                for item in filtered_nodes
            )
            if score > 0.0  # Only include results with a positive score
        )

        sorted_results = sorted(scored_results, key=lambda x: x.score, reverse=True)

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
