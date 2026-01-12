from node_store_spec.models import NodeResponse


class NodeMetadata(NodeResponse):
    embedding: list[float] | None = None
