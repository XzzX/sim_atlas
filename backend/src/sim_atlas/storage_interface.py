from __future__ import annotations

from abc import ABC, abstractmethod

from sim_atlas.models import (
    ExecutionResultMetadata,
    Filter,
    FilterOptions,
    ScoredSearchResponse,
    StoredArtifact,
)


class ArtifactAlreadyExistsError(Exception):
    """Raised when an artifact with the same id already exists in storage."""

    def __init__(self, id: str) -> None:
        super().__init__(f"Artifact with id '{id}' already exists.")
        self.id = id


class ArtifactDuplicateError(Exception):
    """Raised when an artifact with the same hash already exists in storage."""

    def __init__(self, id: str) -> None:
        super().__init__(f"Artifact with id '{id}' already exists.")
        self.id = id


class ExecutionResultAlreadyExistsError(Exception):
    """Raised when an execution result with the same id already exists in storage."""

    def __init__(self, id: str) -> None:
        super().__init__(f"Execution result with id '{id}' already exists.")
        self.id = id


class ExecutionResultDuplicateError(Exception):
    """Raised when an execution result with the same hash already exists in storage."""

    def __init__(self, id: str) -> None:
        super().__init__(f"Execution result with id '{id}' already exists.")
        self.id = id


class StorageInterface(ABC):
    @abstractmethod
    def create_artifact(
        self, value: StoredArtifact, check_source_hash: bool = True
    ) -> str:
        """Store a new artifact.

        Returns
        -------
        str
            The artifact id.

        Raises
        ------
        ArtifactAlreadyExistsError
            Raised if an artifact with the same id already exists

        ArtifactDuplicateError
            Raised if ``check_source_hash`` is True and an artifact with the same
            non-empty ``hash`` already exists.
        """
        pass

    @abstractmethod
    def read_artifact(self, id: str) -> StoredArtifact:
        """Return the artifact for *id*. Raises KeyError if not found."""
        pass

    @abstractmethod
    def update_artifact(self, id: str, value: StoredArtifact) -> StoredArtifact:
        """Replace an existing artifact. Raises KeyError if not found."""
        pass

    @abstractmethod
    def delete_artifact(self, id: str) -> None:
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
    async def search_semantic(
        self, query: str, filter: Filter | None = None, page: int = 1, limit: int = 10
    ) -> ScoredSearchResponse:
        pass

    @abstractmethod
    async def search_hybrid(
        self, query: str, filter: Filter | None = None, page: int = 1, limit: int = 10
    ) -> ScoredSearchResponse:
        pass

    @abstractmethod
    async def enrich(self, only_ids: list[str] | None = None) -> None:
        pass

    @abstractmethod
    def create_execution_result(
        self, value: ExecutionResultMetadata, check_hash: bool = True
    ) -> str:
        """Store a new execution result.

        Returns
        -------
        str
            The execution result id.

        Raises
        ------
        ExecutionResultAlreadyExistsError
            Raised if an execution result with the same id already exists.

        ExecutionResultDuplicateError
            Raised if ``check_hash`` is True and a result with the same
            non-empty ``hash`` already exists.
        """
        pass

    @abstractmethod
    def read_execution_result(self, id: str) -> ExecutionResultMetadata:
        """Return the execution result for *id*. Raises KeyError if not found."""
        pass

    @abstractmethod
    def update_execution_result(
        self, id: str, value: ExecutionResultMetadata
    ) -> ExecutionResultMetadata:
        """Replace an existing execution result. Raises KeyError if not found."""
        pass

    @abstractmethod
    def delete_execution_result(self, id: str) -> None:
        """Remove the execution result for *id*. Raises KeyError if not found."""
        pass

    @abstractmethod
    def read_execution_results_by_artifact(
        self, artifact_id: str
    ) -> list[ExecutionResultMetadata]:
        """Return all execution results for the given artifact_id."""
        pass


def get_storage_backend() -> StorageInterface:
    """
    Factory function to get the configured storage backend.

    Returns:
        An instance of the configured storage backend

    Raises:
        ValueError: If the configured backend is not supported
    """

    from sim_atlas.file_system_storage import FileSystemStorage  # noqa: PLC0415
    from sim_atlas.settings import load_settings  # noqa: PLC0415

    return FileSystemStorage(path=load_settings().config_dir)
