from __future__ import annotations

import os
import pickle

from bson.binary import Binary
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


def cosine_similarity(vec1: Binary, vec2: Binary) -> float:
    """Compute the cosine similarity between two BSON binary vectors.

    Args:
        vec1 (Binary): The first BSON binary vector.
        vec2 (Binary): The second BSON binary vector.

    Returns:
        float: The cosine similarity between the two vectors.
    """
    import numpy as np

    # Convert BSON Binary to numpy arrays
    array1 = np.array(vec1.as_vector().data)
    array2 = np.array(vec2.as_vector().data)

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
        import pickle

        with open("in-memory.pkl", "wb") as f:
            pickle.dump(self._storage, f)

    def create(self, node: NodeMetadata) -> str:
        """
        Create a new node metadata entry.

        Args:
            node: The node metadata to store

        Returns:
            The unique hash of the node

        Raises:
            ValueError: If node already exists
        """
        node_hash = node.source_code_hash
        if node_hash in self._storage:
            raise ValueError(f"Node with hash {node_hash} already exists")
        self._storage[node_hash] = node
        self._save_to_disk()

        return node_hash

    def list(self, filter: NodeFilter | None = None) -> list[NodeMetadata]:
        """
        Retrieve all node metadata entries.

        Returns:
            List of all node metadata
        """

        if filter is None:
            return list(self._storage.values())

        if filter.input is None:

            def input_filter(x):
                return True
        else:
            input_datatype_filter = (
                (lambda x: True)
                if filter.input.datatype is None
                else (
                    lambda x: filter.input.datatype
                    in (it.datatype for it in x.arguments)
                )
            )
            input_unit_filter = (
                (lambda x: True)
                if filter.input.unit is None
                else (lambda x: filter.input.unit in (it.unit for it in x.arguments))
            )
            input_quantity_filter = (
                (lambda x: True)
                if filter.input.quantity is None
                else (
                    lambda x: filter.input.quantity
                    in (it.quantity for it in x.arguments)
                )
            )

            def input_filter(x):
                return (
                    input_datatype_filter(x)
                    and input_unit_filter(x)
                    and input_quantity_filter(x)
                )

        if filter.output is None:

            def output_filter(x):
                return True
        else:
            output_datatype_filter = (
                (lambda x: True)
                if filter.output.datatype is None
                else (
                    lambda x: filter.output.datatype
                    in (it.datatype for it in x.returns)
                )
            )
            output_unit_filter = (
                (lambda x: True)
                if filter.output.unit is None
                else (lambda x: filter.output.unit in (it.unit for it in x.returns))
            )
            output_quantity_filter = (
                (lambda x: True)
                if filter.output.quantity is None
                else (
                    lambda x: filter.output.quantity
                    in (it.quantity for it in x.returns)
                )
            )

            def output_filter(x):
                return (
                    output_datatype_filter(x)
                    and output_unit_filter(x)
                    and output_quantity_filter(x)
                )

        return [
            item
            for item in self._storage.values()
            if input_filter(item) and output_filter(item)
        ]

    def read(self, node_hash: str) -> NodeMetadata | None:
        """
        Retrieve a specific node metadata entry by hash.

        Args:
            node_hash: The hash of the node to retrieve

        Returns:
            The node metadata if found, None otherwise
        """
        return self._storage.get(node_hash)

    def exists(self, node_hash: str) -> bool:
        """
        Check if a node metadata entry exists by hash.

        Args:
            node_hash: The hash of the node to check
        Returns:
            True if the node exists, False otherwise
        """
        return node_hash in self._storage

    def update(self, node_hash: str, node: NodeMetadata) -> bool:
        """
        Update an existing node metadata entry.

        Args:
            node_hash: The hash of the node to update
            node: The updated node metadata

        Returns:
            True if the node was updated, False if not found
        """
        if node_hash not in self._storage:
            return False

        self._storage[node_hash] = node
        self._save_to_disk()
        return True

    def delete(self, node_hash: str) -> bool:
        """
        Delete a node metadata entry.

        Args:
            node_hash: The hash of the node to delete

        Returns:
            True if the node was deleted, False if not found
        """
        if node_hash not in self._storage:
            return False

        del self._storage[node_hash]
        self._save_to_disk()
        return True

    def search(self, query: str) -> list[NodeMetadata]:
        """
        Search for nodes matching the given query.

        Args:
            query: search query string

        Returns:
            List of matching node metadata
        """
        results = []
        query_lower = query.lower()

        for node in self._storage.values():
            # Search in qualname, module, and docstring
            searchable_text = " ".join(
                [
                    node.qualname or "",
                    node.module or "",
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
        similarities = []
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
