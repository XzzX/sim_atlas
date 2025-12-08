from node_store_spec.models import Annotation, NodeType
from pydantic import BaseModel


class Metadata(BaseModel):
    node_type: NodeType

    source_code: str
    source_code_hash: str

    docstring: str | None = None
    arguments: dict[str, Annotation | None] | None = None
    returns: Annotation | None = None
    returns_unpacked: dict[str, Annotation | None] | None = None
