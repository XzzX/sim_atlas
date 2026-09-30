import uuid
from datetime import UTC, datetime

from sim_atlas_toolkit.models import (
    ExecutionResultRequest,
    ExecutionResultResponse,
    NodeRequest,
    NodeResponse,
)
from sim_atlas_toolkit.node_store import (
    EmbeddingNotConfiguredError,
    NodeResult,
    NodeStatus,
    NodeStore,
)


def _to_response(node: NodeRequest) -> NodeResponse:
    """Mirror the backend's ``compose_node``: fill in the server-assigned fields."""
    return NodeResponse(
        **node.model_dump(exclude={"id", "hash"}),
        id=node.id or str(uuid.uuid4()),
        hash=node.hash or str(uuid.uuid4()),
        creator_name="test",
        creator_email="test@example.com",
        creation_timestamp=datetime.now(UTC).isoformat(),
    )


class MockNodeStore(NodeStore):
    """In-memory NodeStore recording what the pipeline uploaded.

    Nodes are keyed by both ``id`` and ``hash`` because the backend derives
    one from the other (ADR-0005), which is what lets a parser's
    ``read_node(hash)`` dedup check find a node an earlier ``create_node``
    stored.
    """

    def __init__(self) -> None:
        self.uploaded: list[NodeRequest] = []
        self.uploaded_execution_results: list[ExecutionResultRequest] = []
        self.embed_triggers: int = 0
        self.embed_available: bool = True
        self._nodes: dict[str, NodeResponse] = {}

    def preexisting(self, node: NodeResponse) -> NodeResponse:
        """Seed a node as already stored; later reads and creates find it."""
        self._nodes[node.id] = node
        self._nodes[node.hash] = node
        return node

    async def create_node(self, node: NodeRequest) -> NodeResult:
        self.uploaded.append(node)
        if (existing := self._lookup(node)) is not None:
            return NodeResult(status=NodeStatus.EXISTS, node=existing)
        stored = _to_response(node)
        self.preexisting(stored)
        return NodeResult(status=NodeStatus.CREATED, node=stored)

    async def read_node(self, node_id: str) -> NodeResponse | None:
        return self._nodes.get(node_id)

    async def create_execution_result(
        self, execution_result: ExecutionResultRequest
    ) -> ExecutionResultResponse:
        self.uploaded_execution_results.append(execution_result)
        return ExecutionResultResponse(
            **execution_result.model_dump(),
            id=str(uuid.uuid4()),
            creator_name="test",
            creator_email="test@example.com",
            creation_timestamp=datetime.now(UTC).isoformat(),
        )

    async def trigger_embed(self) -> None:
        if not self.embed_available:
            raise EmbeddingNotConfiguredError("no embedding provider configured")
        self.embed_triggers += 1

    def _lookup(self, node: NodeRequest) -> NodeResponse | None:
        for key in (node.id, node.hash):
            if key is not None and (found := self._nodes.get(key)) is not None:
                return found
        return None
