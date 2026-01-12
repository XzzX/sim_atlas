from enum import StrEnum

from pydantic import BaseModel, Field


class NodeType(StrEnum):
    FUNCTION = "function"
    PYTHON_WORKFLOW_DEFINITION = "pwd"
    PYIRON_WORKFLOW_FUNCTION = "pyiron_workflow_function"
    PYIRON_CORE_NODE = "pyiron_core_node"


class Annotation(BaseModel):
    label: str | None = None
    datatype: str | None = None
    unit: str | None = None
    quantity: str | None = None


# class Argument(BaseModel):
#     name: str
#     datatype: str | None = None
#     unit: str | None = Field(None, pattern=r"^https://qudt\.org/vocab/unit/[\w]+$")
#     quantity: str | None = Field(
#         None, pattern=r"^https://qudt\.org/vocab/quantitykind/[\w]+$"
#     )


# class Return(BaseModel):
#     name: str | None = None
#     datatype: str | None = None
#     unit: str | None = Field(None, pattern=r"^https://qudt\.org/vocab/unit/[\w]+$")
#     quantity: str | None = Field(
#         None, pattern=r"^https://qudt\.org/vocab/quantitykind/[\w]+$"
#     )


class NodeRequest(BaseModel):
    """How does a node look like when being posted to the API"""

    author_name: str
    author_email: str

    node_type: NodeType

    python_import: str | None = None
    dependencies: list[str] | None = None

    source_code: str
    source_code_hash: str

    docstring: str
    inputs: dict[str, Annotation]
    outputs: dict[str, Annotation]


class NodeResponse(BaseModel):
    author_name: str
    author_email: str

    node_type: NodeType

    python_import: str | None = None
    dependencies: list[str] | None = None

    source_code: str
    source_code_hash: str

    docstring: str
    ai_docstring: str
    inputs: dict[str, Annotation]
    outputs: dict[str, Annotation]


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
