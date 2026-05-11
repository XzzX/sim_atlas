from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# TypeNode discriminated union
# ---------------------------------------------------------------------------


class SimpleNode(BaseModel):
    kind: Literal["simple"] = "simple"
    name: str


class GenericNode(BaseModel):
    kind: Literal["generic"] = "generic"
    name: str
    args: list[TypeNode]


class UnionNode(BaseModel):
    kind: Literal["union"] = "union"
    members: list[TypeNode]


TypeNode = Annotated[SimpleNode | GenericNode | UnionNode, Field(discriminator="kind")]
GenericNode.model_rebuild()
UnionNode.model_rebuild()


class DataType(BaseModel):
    """A Python type annotation as both a structured AST and its canonical string."""

    ast: TypeNode
    string: str


class NodeType(StrEnum):
    FUNCTION = "function"
    PYTHON_WORKFLOW_DEFINITION = "python_workflow_definition"
    PYIRON_WORKFLOW_FUNCTION = "pyiron_workflow_function"
    PYIRON_CORE_NODE = "pyiron_core_node"


class Annotation(BaseModel):
    has_default_value: bool = False
    label: str | None = None
    datatype: DataType | None = None
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

    docstring: str
    inputs: list[Annotation]
    outputs: list[Annotation]


class NodeResponse(BaseModel):
    author_name: str
    author_email: str

    creator_name: str
    creator_email: str
    creation_timestamp: str

    id: str
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

    docstring: str
    ai_summary: str
    ai_description: str
    inputs: list[Annotation]
    outputs: list[Annotation]


class ScoredSearchItem(BaseModel):
    score: float
    node: NodeResponse


class SearchResults(BaseModel):
    data: list[ScoredSearchItem]
    page: int
    limit: int
    total_items: int
    total_pages: int


class ScoredSearchResponse(BaseModel):
    results: SearchResults
    aggregations: dict[str, dict[str, int]] | None = None


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
