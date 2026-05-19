import base64
import gzip
from enum import StrEnum
from typing import Annotated, Literal

import numpy as np
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainSerializer,
)


def nd_array_custom_before_validator(x: np.ndarray | dict[str, str]) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return x
    raw = gzip.decompress(base64.b64decode(x["data"]))
    return np.frombuffer(raw, dtype=np.dtype(x["dtype"]))


def nd_array_custom_serializer(x: np.ndarray) -> dict[str, str]:
    data = {
        "dtype": str(x.dtype),
        "data": base64.b64encode(gzip.compress(x.tobytes())).decode("utf-8"),
    }

    return data


NdArray = Annotated[
    np.ndarray,
    BeforeValidator(nd_array_custom_before_validator),
    PlainSerializer(nd_array_custom_serializer, return_type=dict[str, str]),
]


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
    embedding: NdArray | None = None
    source_code_hash: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Filter(BaseModel):
    category: str | None = None
    type: list[NodeType] | None = None
    author: list[str] | None = None
    keywords: list[str] | None = None
    datatypes: list[str] | None = None
    units: list[str] | None = None
    quantities: list[str] | None = None
    port_type: Literal["inputs", "outputs", "both"] | None = None


class FilterOptions(BaseModel):
    category: dict[str, list[str]]
    type: list[NodeType]
    author: list[str]
    keywords: list[str]
    datatypes: list[str]
    units: list[str]
    quantities: list[str]


# --- Agent models ---


class GraphNodeContext(BaseModel):
    """Compact representation of a node already placed in the graph."""

    graph_id: str
    node_kind: Literal["function", "input", "output"]
    atlas_node_id: str | None = None  # None for InputNode / OutputNode
    name: str
    short_description: str | None = None
    inputs: list[Annotation]
    outputs: list[Annotation]


class GraphEdgeContext(BaseModel):
    source_graph_id: str
    source_handle: str
    target_graph_id: str
    target_handle: str


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentRequest(BaseModel):
    query: str
    nodes: list[GraphNodeContext]
    edges: list[GraphEdgeContext]
    history: list[HistoryMessage] = []


class AgentResponse(BaseModel):
    nodes: list[GraphNodeContext]
    edges: list[GraphEdgeContext]
    message: str
