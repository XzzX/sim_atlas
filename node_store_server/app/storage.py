from __future__ import annotations

from abc import ABC, abstractmethod

from node_store_tools.models import (
    NodeFilter,
    SemanticSearchResponse,
)

from .models import NodeMetadata


class StorageInterface(ABC):
    """Abstract interface for node metadata storage"""

    @abstractmethod
    def connect(self) -> None:
        """Initialize and connect to the storage backend"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection to the storage backend"""
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def exists(self, node_hash: str) -> bool:
        """
        Check if a node metadata entry exists.

        Args:
            node_hash: The hash of the node to check

        Returns:
            True if the node exists, False otherwise
        """
        pass

    @abstractmethod
    def list(self, filter: NodeFilter | None = None) -> list[NodeMetadata]:
        """
        Retrieve all node metadata entries.

        Returns:
            List of all node metadata
        """
        pass

    @abstractmethod
    def read(self, node_hash: str) -> NodeMetadata | None:
        """
        Retrieve a specific node metadata entry by hash.

        Args:
            node_hash: The hash of the node to retrieve

        Returns:
            The node metadata if found, None otherwise
        """
        pass

    @abstractmethod
    def update(self, node_hash: str, node: NodeMetadata) -> bool:
        """
        Update an existing node metadata entry.

        Args:
            node_hash: The hash of the node to update
            node: The updated node metadata

        Returns:
            True if the node was updated, False if not found
        """
        pass

    @abstractmethod
    def delete(self, node_hash: str) -> bool:
        """
        Delete a node metadata entry.

        Args:
            node_hash: The hash of the node to delete

        Returns:
            True if the node was deleted, False if not found
        """
        pass

    @abstractmethod
    def search(self, query: str) -> list[NodeMetadata]:
        """
        Search for nodes matching the given query.

        Args:
            query: search query string

        Returns:
            List of matching node metadata
        """
        pass

    @abstractmethod
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
        pass


def get_storage_backend() -> StorageInterface:
    """
    Factory function to get the configured storage backend.

    Returns:
        An instance of the configured storage backend

    Raises:
        ValueError: If the configured backend is not supported
    """

    from .storage_memory import InMemoryStorage

    return InMemoryStorage()
