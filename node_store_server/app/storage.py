from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import MutableMapping

from node_store_spec.models import (
    NodeFilter,
    SemanticSearchResponse,
)

from .models import NodeMetadata


class StorageInterface(MutableMapping[str, NodeMetadata], ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def filter(self, filter: NodeFilter | None = None) -> list[NodeMetadata]:
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
