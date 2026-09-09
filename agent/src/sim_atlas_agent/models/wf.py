from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator


class AnnotationRequest(BaseModel):
    has_default_value: bool = False
    label: str | None = None
    datatype: str | None = None
    unit: str | None = None
    quantity: str | None = None
    description: str | None = None


class WfInputNode(BaseModel):
    type: Literal["input"] = "input"
    node_id: str
    outputs: list[AnnotationRequest]


class WfOutputNode(BaseModel):
    type: Literal["output"] = "output"
    node_id: str
    inputs: list[AnnotationRequest]


class WfFunctionNode(BaseModel):
    type: Literal["function"] = "function"
    node_id: str
    inputs: list[AnnotationRequest]
    outputs: list[AnnotationRequest]
    atlas_id: str | None


WfNode = Annotated[
    WfInputNode | WfOutputNode | WfFunctionNode,
    Discriminator("type"),
]


class WfEdge(BaseModel):
    source_node: str
    source_port: str | None = None
    target_node: str
    target_port: str | None = None


class WfDefinition(BaseModel):
    nodes: list[WfNode]
    edges: list[WfEdge]
