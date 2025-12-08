from node_store_tools.models import NodeResponse


class NodeMetadata(NodeResponse):
    embedding: bytes | None = None
