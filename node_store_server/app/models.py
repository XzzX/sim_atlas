from enum import StrEnum

from pydantic import BaseModel, Field


class NodeType(StrEnum):
    FUNCTION = "function"
    PYTHON_WORKFLOW_DEFINITION = "python_workflow_definition"
    PYIRON_WORKFLOW_FUNCTION = "pyiron_workflow_function"
    PYIRON_CORE_NODE = "pyiron_core_node"


class Annotation(BaseModel):
    has_default_value: bool = False
    label: str | None = None
    datatype: str | None = None
    unit: str | None = None
    quantity: str | None = None


class NodeRequest(BaseModel):
    """How does a node look like when being posted to the API"""

    author_name: str
    author_email: str

    node_type: NodeType
    category: str

    python_import: str
    dependencies: list[str] | None = None

    keywords: list[str]

    source_code: str
    source_code_hash: str

    docstring: str
    inputs: list[Annotation]
    outputs: list[Annotation]


class NodeResponse(BaseModel):
    author_name: str
    author_email: str

    creator_name: str
    creator_email: str
    creation_timestamp: str

    node_type: NodeType
    category: str

    python_import: str
    dependencies: list[str] | None = None

    keywords: list[str]

    source_code: str
    source_code_hash: str

    docstring: str
    ai_docstring: str
    inputs: list[Annotation]
    outputs: list[Annotation]


class NodeIndex(BaseModel):
    module: str
    qualname: str
    source_code_hash: str


class ScoredSearchResponse(BaseModel):
    score: float
    node: NodeResponse


class ArgumentFilter(BaseModel):
    datatype: str | None = None
    unit: str | None = None
    quantity: str | None = None


class NodeFilter(BaseModel):
    input: ArgumentFilter = Field(default_factory=ArgumentFilter)
    output: ArgumentFilter = Field(default_factory=ArgumentFilter)


class NodeMetadata(NodeResponse):
    embedding: list[float] | None = None


class Filter(BaseModel):
    category: str | None = None
    type: list[NodeType] | None = None
    author: list[str] | None = None
    keywords: list[str] | None = None


class FilterOptions(BaseModel):
    category: dict[str, set[str]]
    type: set[NodeType]
    author: set[str]
    keywords: set[str]
