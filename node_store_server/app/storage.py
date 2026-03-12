from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import MutableMapping

from .models import (
    Filter,
    FilterOptions,
    NodeMetadata,
    ScoredSearchResponse,
)


class StorageInterface(MutableMapping[str, NodeMetadata], ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def get_filter_options(self) -> FilterOptions:
        pass

    @abstractmethod
    def search(self, query: str | None, filter: Filter) -> list[ScoredSearchResponse]:
        pass

    @abstractmethod
    def search_semantic(
        self, query: str, limit: int = 10
    ) -> list[ScoredSearchResponse]:
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
