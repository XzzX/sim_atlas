from __future__ import annotations

from abc import ABC, abstractmethod

from sim_atlas.models import ExecutionResultMetadata, NodeMetadata


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
        """Return the node for *id*. Raises KeyError if not found."""
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
    def nodes(self) -> list[NodeMetadata]:
        """Every stored node, in insertion order.

        The returned nodes are the stored objects themselves, not copies:
        callers must treat them as read-only.
        """
        pass

    @abstractmethod
    def update_nodes(self, values: list[NodeMetadata]) -> None:
        """Replace several existing nodes, keyed by their ``id``, in one write.

        Raises KeyError, and writes nothing, if any of them is not stored.
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
