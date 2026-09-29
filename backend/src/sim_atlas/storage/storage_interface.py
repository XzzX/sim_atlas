from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from sim_atlas.models import (
    ExecutionResultMetadata,
    Filter,
    FilterOptions,
    NodeMetadata,
    ScoredSearchResponse,
    Suggestion,
)


class NodeAlreadyExistsError(Exception):
    """Raised when a node with the same id already exists in storage."""

    def __init__(self, node: NodeMetadata) -> None:
        super().__init__(f"Node with id '{node.id}' already exists.")
        self.node = node


class NodeDuplicateError(Exception):
    """Raised when a node with the same hash already exists in storage."""

    def __init__(self, node: NodeMetadata) -> None:
        super().__init__(f"Node with id '{node.id}' already exists.")
        self.node = node


class ExecutionResultAlreadyExistsError(Exception):
    """Raised when an execution result with the same id already exists in storage."""

    def __init__(self, execution_result: ExecutionResultMetadata) -> None:
        super().__init__(
            f"Execution result with id '{execution_result.id}' already exists."
        )
        self.execution_result = execution_result


class ExecutionResultDuplicateError(Exception):
    """Raised when an execution result with the same hash already exists in storage."""

    def __init__(self, execution_result: ExecutionResultMetadata) -> None:
        super().__init__(
            f"Execution result with id '{execution_result.id}' already exists."
        )
        self.execution_result = execution_result


class StorageInterface(ABC):
    @abstractmethod
    def create_node(
        self, value: NodeMetadata, check_source_hash: bool = True
    ) -> NodeMetadata:
        """Store a new node.

        Returns
        -------
        str
            The node id.

        Raises
        ------
        NodeAlreadyExistsError
            Raised if a node with the same id already exists

        NodeDuplicateError
            Raised if ``check_source_hash`` is True and a node with the same
            non-empty ``hash`` already exists.
        """
        pass

    @abstractmethod
    def read_node(self, id: str) -> NodeMetadata:
        """Return the node for *id*, hydrated. Raises KeyError if not found.

        Every node a read method returns (``read_node``, ``search``,
        ``search_hybrid``) carries its derived ``used_by`` and per-port
        ``connections`` references, computed from the stored workflows.
        """
        pass

    @abstractmethod
    def update_node(self, id: str, value: NodeMetadata) -> NodeMetadata:
        """Replace an existing node. Raises KeyError if not found."""
        pass

    @abstractmethod
    def delete_node(self, id: str) -> None:
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
        drop_unmatched: bool = True,
    ) -> ScoredSearchResponse:
        """Keyword search over the stored nodes.

        When ``drop_unmatched`` is False the query only ranks the nodes the
        filters selected, instead of also excluding the ones it does not match.
        """
        pass

    @abstractmethod
    def suggest(
        self, query: str, filter: Filter | None = None, limit: int = 10
    ) -> list[Suggestion]:
        """Cheap type-ahead lookup: name/import matches only, best-first.

        Unlike ``search``, this never touches docstrings, descriptions or
        embeddings, and never runs the ``used_by``/connections enrichment —
        it exists to be fast. Returns ``[]`` for a blank query.
        """
        pass

    @abstractmethod
    def search_hybrid(
        self,
        query: str,
        query_embedding: np.ndarray,
        filter: Filter | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> ScoredSearchResponse:
        """Semantic plus keyword search, fused into one ranking.

        *query_embedding* is the caller's embedding of *query*; the adapter
        never calls an embedding provider itself. Nodes without a stored
        embedding must still be reachable through the keyword side. Choosing
        between this and ``search`` (ADR-0018) is the caller's job.
        """
        pass

    @abstractmethod
    def nodes(self) -> list[NodeMetadata]:
        """Every stored node, unhydrated, for batch jobs such as embedding.

        Not a read path: the nodes may be the stored objects themselves, so
        callers must treat them as read-only.
        """
        pass

    @abstractmethod
    def set_embeddings(self, embeddings: dict[str, np.ndarray]) -> None:
        """Store an embedding per node id, in one write.

        Raises KeyError, and writes nothing, if any id is not stored.
        """
        pass

    @abstractmethod
    def create_execution_result(
        self, value: ExecutionResultMetadata, check_hash: bool = True
    ) -> ExecutionResultMetadata:
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
    def read_execution_results_by_node(
        self, node_id: str
    ) -> list[ExecutionResultMetadata]:
        """Return all execution results whose ``artifact_id`` matches *node_id*."""
        pass


def get_storage_backend() -> StorageInterface:
    """
    Factory function to get the configured storage backend.

    Returns:
        An instance of the configured storage backend

    Raises:
        ValueError: If the configured backend is not supported
    """

    from sim_atlas.settings import load_settings  # noqa: PLC0415
    from sim_atlas.storage.file_system_storage import FileSystemStorage  # noqa: PLC0415

    return FileSystemStorage(path=load_settings().config_dir)
