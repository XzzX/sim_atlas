import base64
import gzip
from typing import Annotated, Literal

import numpy as np
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
)
from sim_atlas_models import ArtifactType, ExecutionResultResponse, NodeResponse


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


class NodeMetadata(NodeResponse):
    embedding: NdArray | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Filter(BaseModel):
    category: str | None = None
    artifact_type: list[ArtifactType] | None = None
    author: list[str] | None = None
    keywords: list[str] | None = None
    datatypes: list[str] | None = None
    units: list[str] | None = None
    quantities: list[str] | None = None
    port_type: Literal["inputs", "outputs", "both"] | None = None


class FilterOptions(BaseModel):
    category: dict[str, list[str]]
    artifact_type: list[ArtifactType]
    author: list[str]
    keywords: list[str]
    datatypes: list[str]
    units: list[str]
    quantities: list[str]


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


type SearchMode = Literal["keyword", "substring", "semantic", "hybrid"]


class SearchRequest(BaseModel):
    query: str | None = None
    filter: Filter | None = None
    semantic: bool | None = None
    # Takes precedence over ``semantic``. When omitted, ``semantic=false``
    # means keyword and anything else means hybrid.
    mode: SearchMode | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100)


class Suggestion(BaseModel):
    """A single type-ahead hit: enough to render a row and navigate to it."""

    id: str
    name: str
    python_import: str | None = None
    artifact_type: ArtifactType
    short_description: str | None = None
    keywords: list[str]


class SuggestRequest(BaseModel):
    query: str
    filter: Filter | None = None
    limit: int = Field(default=10, ge=1, le=25)


class ExecutionResultMetadata(ExecutionResultResponse):
    hash: str = ""
