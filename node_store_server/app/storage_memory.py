from __future__ import annotations

import os
import pickle
from collections.abc import Callable

import numpy as np
from node_store_spec.models import (
    NodeFilter,
    SemanticSearchResponse,
)

from .ai import create_embedding
from .models import (
    NodeMetadata,
    NodeResponse,
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

    def __init__(self):
        self._storage: dict[str, NodeMetadata] = {}
        self._connected = False

        # Load from file if it exists
        if os.path.exists("in-memory.pkl"):
            try:
                with open("in-memory.pkl", "rb") as f:
                    self._storage = pickle.load(f)
            except Exception:
                pass  # If loading fails, start with empty storage

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

    def filter(self, filter: NodeFilter | None = None) -> list[NodeMetadata]:
        if filter is None:
            return list(self._storage.values())

        input_datatype_filter: Callable[[NodeMetadata], bool] = (
            (lambda x: True)
            if filter.input.datatype is None
            else (
                lambda x: filter.input.datatype
                in (it.datatype for it in x.inputs.values())
            )
        )
        input_unit_filter: Callable[[NodeMetadata], bool] = (
            (lambda x: True)
            if filter.input.unit is None
            else (lambda x: filter.input.unit in (it.unit for it in x.inputs.values()))
        )
        input_quantity_filter: Callable[[NodeMetadata], bool] = (
            (lambda x: True)
            if filter.input.quantity is None
            else (
                lambda x: filter.input.quantity
                in (it.quantity for it in x.inputs.values())
            )
        )

        output_datatype_filter: Callable[[NodeMetadata], bool] = (
            (lambda x: True)
            if filter.output.datatype is None
            else (
                lambda x: filter.output.datatype
                in (it.datatype for it in x.outputs.values())
            )
        )
        output_unit_filter: Callable[[NodeMetadata], bool] = (
            (lambda x: True)
            if filter.output.unit is None
            else (
                lambda x: filter.output.unit in (it.unit for it in x.outputs.values())
            )
        )
        output_quantity_filter: Callable[[NodeMetadata], bool] = (
            (lambda x: True)
            if filter.output.quantity is None
            else (
                lambda x: filter.output.quantity
                in (it.quantity for it in x.outputs.values())
            )
        )

        def filter_item(item: NodeMetadata) -> bool:
            return (
                input_datatype_filter(item)
                and input_unit_filter(item)
                and input_quantity_filter(item)
                and output_datatype_filter(item)
                and output_unit_filter(item)
                and output_quantity_filter(item)
            )

        return [item for item in self._storage.values() if filter_item(item)]

    def search(self, query: str) -> list[NodeMetadata]:
        """
        Search for nodes matching the given query.

        Args:
            query: search query string

        Returns:
            List of matching node metadata
        """
        results: list[NodeMetadata] = []
        query_lower = query.lower()

        for node in self._storage.values():
            # Search in qualname, module, and docstring
            searchable_text = " ".join(
                [
                    node.python_import or "",
                    node.docstring or "",
                    node.ai_docstring or "",
                ]
            ).lower()

            if query_lower in searchable_text:
                results.append(node)

        return results

    def search_semantic(
        self, query: str, limit: int = 10
    ) -> list[SemanticSearchResponse]:
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
        similarities: list[SemanticSearchResponse] = []
        for _node_hash, node in self._storage.items():
            if node.embedding is not None:
                similarity = cosine_similarity(query_embedding, node.embedding)
                similarities.append(
                    SemanticSearchResponse(
                        score=similarity,
                        node=NodeResponse(**node.model_dump()),
                    )
                )

        # Sort by similarity (descending) and limit results
        similarities.sort(key=lambda x: x.score, reverse=True)

        # Return only the node metadata (without scores)
        return similarities[:limit]
