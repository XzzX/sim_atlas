from __future__ import annotations

from abc import ABC, abstractmethod

from .models import (
    Filter,
    FilterOptions,
    NodeMetadata,
    ScoredSearchResponse,
)


class StorageInterface(ABC):
    @abstractmethod
    def create(self, value: NodeMetadata) -> str:
        """Store a new node. Returns the id. Raises ValueError if node already exists."""
        pass

    @abstractmethod
    def read(self, id: str) -> NodeMetadata:
        """Return the node for *id*. Raises KeyError if not found."""
        pass

    @abstractmethod
    def update(self, id: str, value: NodeMetadata) -> NodeMetadata:
        """Replace an existing node. Raises KeyError if not found."""
        pass

    @abstractmethod
    def delete(self, id: str) -> None:
        """Remove the node for *id*. Raises KeyError if not found."""
        pass

    @abstractmethod
    def exists(self, id: str) -> bool:
        """Return True if *id* is present in storage."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored nodes."""
        pass

    @abstractmethod
    def get_filter_options(self) -> FilterOptions:
        pass

    @abstractmethod
    def search(
        self,
        query: str | None,
        filter: Filter | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> ScoredSearchResponse:
        pass

    @abstractmethod
    def search_semantic(
        self, query: str, filter: Filter | None = None, page: int = 1, limit: int = 10
    ) -> ScoredSearchResponse:
        pass

    @abstractmethod
    def enrich(self) -> None:
        pass


def get_storage_backend() -> StorageInterface:
    """
    Factory function to get the configured storage backend.

    Returns:
        An instance of the configured storage backend

    Raises:
        ValueError: If the configured backend is not supported
    """

    from .file_system_storage import FileSystemStorage  # noqa: PLC0415

    return FileSystemStorage()
