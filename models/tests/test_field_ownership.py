"""Field ownership (ADR-0024): requests carry only client-owned fields.

The server-owned fields of each request/response pair are derived from the
models themselves, so a field newly added to a response model is covered
without touching these tests.
"""

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from sim_atlas_models import (
    Annotation,
    AnnotationResponse,
    ArtifactType,
    ExecutionResultRequest,
    ExecutionResultResponse,
    IOValue,
    NodeExistsRequest,
    NodeExistsResponse,
    NodeRequest,
    NodeResponse,
    PackageRef,
    Reference,
    ReferenceResponse,
    WfDefinition,
    WfEdge,
    WfFunctionNode,
    WfInputNode,
    WfOutputNode,
)

SERVER_FIELDS: dict[str, Any] = {
    "creator_name": "Creator",
    "creator_email": "creator@example.com",
    "creation_timestamp": "2026-01-01T00:00:00+00:00",
}

ANNOTATION = Annotation(label="x", datatype="float", unit="eV")
REFERENCE = Reference(label="child", id="c" * 64, count=2)
REFERENCE_RESPONSE = ReferenceResponse(
    label="child", id="c" * 64, count=2, artifact_type=ArtifactType.FUNCTION
)
WF_DEFINITION = WfDefinition(
    nodes=[
        WfInputNode(node_id="in", outputs=[ANNOTATION]),
        WfFunctionNode(
            node_id="f", inputs=[ANNOTATION], outputs=[ANNOTATION], atlas_id="c" * 64
        ),
        WfOutputNode(node_id="out", inputs=[ANNOTATION]),
    ],
    edges=[WfEdge(source_node="in", target_node="f", target_port="x")],
)
NODE_REQUEST = NodeRequest(
    artifact_type=ArtifactType.WORKFLOW,
    name="wf",
    category="test",
    keywords=["k"],
    packages=[PackageRef(ecosystem="pypi", name="pkg", version="1.0")],
    source_code="def wf(x): ...",
    inputs=[ANNOTATION],
    outputs=[ANNOTATION],
    see_also=[REFERENCE],
    uses=[REFERENCE],
    wf_definition=WF_DEFINITION,
)
EXECUTION_RESULT_REQUEST = ExecutionResultRequest(
    author_name="a",
    author_email="a@example.com",
    artifact_id="c" * 64,
    inputs=[IOValue(label="x", value=1.0)],
    outputs="2.0",
)

ANNOTATION_RESPONSE = AnnotationResponse(
    **ANNOTATION.model_dump(), connections=[REFERENCE_RESPONSE]
)
NODE_RESPONSE = NodeResponse.model_validate(
    NODE_REQUEST.model_dump()
    | SERVER_FIELDS
    | {
        "id": "w" * 64,
        "hash": "w" * 64,
        "inputs": [ANNOTATION_RESPONSE.model_dump()],
        "uses": [REFERENCE_RESPONSE.model_dump()],
        "used_by": [REFERENCE_RESPONSE.model_dump()],
    }
)
EXECUTION_RESULT_RESPONSE = ExecutionResultResponse.model_validate(
    EXECUTION_RESULT_REQUEST.model_dump() | SERVER_FIELDS | {"id": "e1"}
)

# (a valid request, a fully populated response of the matching response model)
PAIRS: list[tuple[BaseModel, BaseModel]] = [
    (REFERENCE, REFERENCE_RESPONSE),
    (ANNOTATION, ANNOTATION_RESPONSE),
    (NODE_REQUEST, NODE_RESPONSE),
    (EXECUTION_RESULT_REQUEST, EXECUTION_RESULT_RESPONSE),
]

# One valid instance of every model a client sends, nested ones included.
REQUEST_SAMPLES: list[BaseModel] = [
    ANNOTATION,
    REFERENCE,
    PackageRef(ecosystem="conda", name="pkg", channel="conda-forge"),
    *WF_DEFINITION.nodes,
    *WF_DEFINITION.edges,
    WF_DEFINITION,
    NODE_REQUEST,
    IOValue(label="x", value="v"),
    EXECUTION_RESULT_REQUEST,
    NodeExistsRequest(ids=["a", "b"]),
]

RESPONSE_SAMPLES: list[BaseModel] = [
    *(response for _, response in PAIRS),
    NodeExistsResponse(existing=["a"]),
]


def _name(value: object) -> str:
    return type(value).__name__


def server_owned(request: BaseModel, response: BaseModel) -> set[str]:
    return set(type(response).model_fields) - set(type(request).model_fields)


SERVER_OWNED_CASES = [
    pytest.param(request, response, field, id=f"{_name(request)}.{field}")
    for request, response in PAIRS
    for field in sorted(server_owned(request, response))
]


@pytest.mark.parametrize(("request_sample", "response", "field"), SERVER_OWNED_CASES)
def test_request_rejects_every_server_owned_field(
    request_sample: BaseModel, response: BaseModel, field: str
) -> None:
    payload = request_sample.model_dump() | {field: response.model_dump()[field]}
    with pytest.raises(ValidationError, match="extra_forbidden"):
        type(request_sample).model_validate(payload)


@pytest.mark.parametrize(("request_sample", "response"), PAIRS, ids=_name)
def test_every_response_adds_server_owned_fields(
    request_sample: BaseModel, response: BaseModel
) -> None:
    assert server_owned(request_sample, response)


@pytest.mark.parametrize(("request_sample", "_"), PAIRS, ids=_name)
def test_request_samples_are_valid(request_sample: BaseModel, _: BaseModel) -> None:
    type(request_sample).model_validate(request_sample.model_dump())


@pytest.mark.parametrize(
    ("field", "item"),
    [
        ("inputs", ANNOTATION_RESPONSE),
        ("outputs", ANNOTATION_RESPONSE),
        ("uses", REFERENCE_RESPONSE),
        ("see_also", REFERENCE_RESPONSE),
    ],
)
def test_node_request_rejects_server_owned_fields_in_nested_items(
    field: str, item: BaseModel
) -> None:
    payload = NODE_REQUEST.model_dump()
    payload[field] = [item.model_dump()]
    with pytest.raises(ValidationError, match="extra_forbidden"):
        NodeRequest.model_validate(payload)


@pytest.mark.parametrize("sample", REQUEST_SAMPLES, ids=_name)
def test_request_models_reject_unknown_fields(sample: BaseModel) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        type(sample).model_validate(sample.model_dump() | {"unknown_field": 1})


@pytest.mark.parametrize("sample", RESPONSE_SAMPLES, ids=_name)
def test_response_models_ignore_unknown_fields(sample: BaseModel) -> None:
    parsed = type(sample).model_validate(sample.model_dump() | {"unknown_field": 1})
    assert parsed == sample


def test_node_response_validates_from_request_dump_plus_server_fields() -> None:
    response = NodeResponse.model_validate(
        NODE_REQUEST.model_dump() | SERVER_FIELDS | {"id": "w" * 64, "hash": "w" * 64}
    )
    assert response.model_dump(include=set(NodeRequest.model_fields)) == (
        NODE_REQUEST.model_dump()
        | {
            "id": "w" * 64,
            "hash": "w" * 64,
            "inputs": [
                a.model_dump() | {"connections": None} for a in NODE_REQUEST.inputs
            ],
            "outputs": [
                a.model_dump() | {"connections": None} for a in NODE_REQUEST.outputs
            ],
            "uses": [
                r.model_dump() | {"artifact_type": None} for r in NODE_REQUEST.uses
            ],
            "see_also": [
                r.model_dump() | {"artifact_type": None} for r in NODE_REQUEST.see_also
            ],
        }
    )
