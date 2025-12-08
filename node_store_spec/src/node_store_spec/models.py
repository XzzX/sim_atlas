from enum import StrEnum

from pydantic import BaseModel


class NodeType(StrEnum):
    FUNCTION = "function"
    PYTHON_WORKFLOW_DEFINITION = "pwd"
    PYIRON_WORKFLOW_FUNCTION = "pyiron_workflow_function"


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


class PythonImport(BaseModel):
    module: str
    qualname: str
    version: str | None = None


class NodeRequest(BaseModel):
    """How does a node look like when being posted to the API"""

    author: str
    email: str

    node_type: NodeType

    python_import: PythonImport | None = None
    dependencies: list[str] | None = None

    source_code: str
    source_code_hash: str

    docstring: str | None = None
    arguments: dict[str, Annotation | None] | None = None
    returns: Annotation | None = None
    returns_unpacked: dict[str, Annotation | None] | None = None


class NodeResponse(BaseModel):
    """How does a node look like when being returned from the API"""

    author: str
    email: str

    node_type: NodeType

    python_import: PythonImport | None = None
    dependencies: list[str] | None = None

    source_code: str
    source_code_hash: str

    docstring: str | None = None
    ai_docstring: str
    arguments: dict[str, Annotation | None] | None = None
    returns: Annotation | None = None
    returns_unpacked: dict[str, Annotation | None] | None = None


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
    input: ArgumentFilter | None = None
    output: ArgumentFilter | None = None
