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

    python_import: str | None = None
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

    node_type: NodeType

    python_import: str | None = None
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


class SemanticSearchResponse(BaseModel):
    score: float
    node: NodeResponse


class ArgumentFilter(BaseModel):
    datatype: str | None = None
    unit: str | None = None
    quantity: str | None = None


class NodeFilter(BaseModel):
    input: ArgumentFilter = Field(default_factory=ArgumentFilter)
    output: ArgumentFilter = Field(default_factory=ArgumentFilter)
