from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import MutableMapping
from dataclasses import dataclass

from .models import (
    NodeMetadata,
    NodeType,
    ScoredSearchResponse,
)


@dataclass
class FilterOptions:
    category: str | None = None
    type: list[NodeType] | None = None
    author: list[str] | None = None
    keywords: list[str] | None = None


class StorageInterface(MutableMapping[str, NodeMetadata], ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def filter(self, filter: FilterOptions) -> list[ScoredSearchResponse]:
        pass

    @abstractmethod
    def search(
        self, query: str | None, filter: FilterOptions
    ) -> list[ScoredSearchResponse]:
        """
        Search for nodes matching the given query.

        Args:
            query: search query string
            filter: filter options

        Returns:
            List of matching node metadata
        """
        pass

    @abstractmethod
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
        pass


def get_storage_backend() -> StorageInterface:
    """
    Factory function to get the configured storage backend.

    Returns:
        An instance of the configured storage backend

    Raises:
        ValueError: If the configured backend is not supported
    """

    from .storage_memory import InMemoryStorage  # noqa: PLC0415

    return InMemoryStorage()
