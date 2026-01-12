from node_store_spec.models import Annotation, NodeType
from pydantic import BaseModel


class Metadata(BaseModel):
    node_type: NodeType

    source_code: str
    source_code_hash: str

    docstring: str | None = None
    inputs: dict[str, Annotation]
    outputs: dict[str, Annotation]
