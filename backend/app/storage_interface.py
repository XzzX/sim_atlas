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
