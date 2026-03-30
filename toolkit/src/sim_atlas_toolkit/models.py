from enum import StrEnum

from pydantic import BaseModel


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
    author_name: str = "unknown"
    author_email: str = "unknown"

    name: str
    node_type: NodeType
    category: str
    keywords: list[str]

    homepage_url: str = ""
    documentation_url: str = ""
    source_url: str = ""

    python_import: str
    dependencies: list[str] | None = None

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

    name: str
    node_type: NodeType
    category: str
    keywords: list[str]

    homepage_url: str
    documentation_url: str
    source_url: str

    python_import: str
    dependencies: list[str] | None = None

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


class NodeMetadata(NodeResponse):
    embedding: list[float] | None = None


class Filter(BaseModel):
    category: str | None = None
    type: list[NodeType] | None = None
    author: list[str] | None = None
    keywords: list[str] | None = None
    datatypes: list[str] | None = None
    units: list[str] | None = None
    quantities: list[str] | None = None


class FilterOptions(BaseModel):
    category: dict[str, list[str]]
    type: list[NodeType]
    author: list[str]
    keywords: list[str]
    datatypes: list[str]
    units: list[str]
    quantities: list[str]
