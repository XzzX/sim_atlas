from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from sim_atlas_toolkit.models import (
    ExecutionResultRequest,
    ExecutionResultResponse,
    NodeRequest,
    NodeResponse,
)


class NodeStatus(StrEnum):
    """Outcome of storing a single node, mirroring the backend's status line."""

    CREATED = "created"
    EXISTS = "exists"


@dataclass(frozen=True, slots=True)
class NodeResult:
    """Outcome of storing (or deduplicating) a single node.

    Not a wire model: it is a control-flow value the store constructs, never
    parsed from or serialised to a request/response body.
    """

    status: NodeStatus
    node: NodeResponse


class NodeStoreError(Exception):
    """A ``NodeStore`` operation failed."""


class EmbeddingNotConfiguredError(NodeStoreError):
    """The store has no embedding provider configured (backend returns 503)."""


class NodeStore(ABC):
    """Persistence backend for parsed nodes.

    Implementations must tolerate concurrent use: ``orchestrator`` runs up to
    ``concurrency`` uploads in parallel.
    """

    @abstractmethod
    async def create_node(self, node: NodeRequest) -> NodeResult:
        """Store *node*.

        Returns ``NodeStatus.CREATED`` when the node was newly stored and
        ``NodeStatus.EXISTS`` when a node with the same id or hash was
        already present; ``result.node`` carries the stored node either way.

        Raises
        ------
        NodeStoreError
            The store could not be reached or rejected the request.
        """

    async def create_nodes(self, nodes: list[NodeRequest]) -> list[NodeResult]:
        """Store *nodes* in order. Sequential fan-out over ``create_node``."""
        return [await self.create_node(node) for node in nodes]

    @abstractmethod
    async def read_node(self, node_id: str) -> NodeResponse | None:
        """Return the stored node for *node_id*, or ``None`` if not stored.

        Raises
        ------
        NodeStoreError
            The store could not be reached or returned an unusable answer.
            A missing node is not an error.
        """

    @abstractmethod
    async def create_execution_result(
        self, execution_result: ExecutionResultRequest
    ) -> ExecutionResultResponse:
        """Store an execution result and return the stored record."""

    @abstractmethod
    async def trigger_embed(self) -> None:
        """Embed nodes that have no embedding yet.

        Raises
        ------
        EmbeddingNotConfiguredError
            The store has no embedding provider.
        NodeStoreError
            The request failed for any other reason.
        """
