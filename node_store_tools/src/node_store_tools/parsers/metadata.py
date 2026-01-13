from node_store_spec.models import Annotation, NodeType
from pydantic import BaseModel


class Metadata(BaseModel):
    node_type: NodeType

    python_import: str | None
    source_code: str
    source_code_hash: str

    docstring: str
    inputs: dict[str, Annotation]
    outputs: dict[str, Annotation]
