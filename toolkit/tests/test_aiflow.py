"""Tests for the aiflow parser, including Workflow instance parsing."""

from sim_atlas_toolkit.models import ArtifactType
from sim_atlas_toolkit.parsers.aiflow import (
    _is_aiflow_workflow,
    parse,
    parse_workflow,
)


# ---------------------------------------------------------------------------
# Minimal stubs that duck-type as aiflow Workflow / FunctionNode objects
# ---------------------------------------------------------------------------


class _Ports:
    """Minimal stand-in for an aiflow IO panel with a ``ports`` dict."""

    def __init__(self, **ports: object) -> None:
        self.ports: dict[str, object] = dict(ports)


class _ChildNode:
    """Placeholder for a child FunctionNode inside a workflow."""


class _MockWorkflow:
    """Calculate result = a + b.

    Args:
        a: First operand.
        b: Second operand.

    Returns:
        result: Sum of the two operands.
    """

    def __init__(self) -> None:
        child_add = _ChildNode()
        self.inputs = _Ports(a=None, b=None)
        self.outputs = _Ports(result=None)
        self.nodes: dict[str, object] = {"add_0": child_add}


class _MockWorkflowNoNodes:
    """Workflow with no children or docstring."""

    def __init__(self) -> None:
        self.inputs = _Ports(x=None)
        self.outputs = _Ports(y=None)
        self.nodes: dict[str, object] = {}


class _NotAWorkflow:
    """Object that looks superficially similar but lacks ``nodes``."""

    def __init__(self) -> None:
        self.inputs = _Ports(x=None)
        self.outputs = _Ports(y=None)
        # no ``nodes`` attribute


# ---------------------------------------------------------------------------
# Tests for _is_aiflow_workflow
# ---------------------------------------------------------------------------


def test_is_workflow_true_for_mock() -> None:
    wf = _MockWorkflow()
    assert _is_aiflow_workflow(wf) is True


def test_is_workflow_false_for_class() -> None:
    assert _is_aiflow_workflow(_MockWorkflow) is False


def test_is_workflow_false_without_nodes() -> None:
    assert _is_aiflow_workflow(_NotAWorkflow()) is False


def test_is_workflow_false_for_plain_object() -> None:
    assert _is_aiflow_workflow(object()) is False


def test_is_workflow_false_for_string() -> None:
    assert _is_aiflow_workflow("hello") is False


# ---------------------------------------------------------------------------
# Tests for parse_workflow
# ---------------------------------------------------------------------------


def test_parse_workflow_artifact_type() -> None:
    wf = _MockWorkflow()
    (metadata,) = parse_workflow(wf)
    assert metadata.artifact_type == ArtifactType.WORKFLOW


def test_parse_workflow_keywords() -> None:
    wf = _MockWorkflow()
    (metadata,) = parse_workflow(wf)
    assert "aiflow" in metadata.keywords


def test_parse_workflow_inputs() -> None:
    wf = _MockWorkflow()
    (metadata,) = parse_workflow(wf)
    assert [a.label for a in metadata.inputs] == ["a", "b"]


def test_parse_workflow_outputs() -> None:
    wf = _MockWorkflow()
    (metadata,) = parse_workflow(wf)
    assert [a.label for a in metadata.outputs] == ["result"]


def test_parse_workflow_children() -> None:
    wf = _MockWorkflow()
    (metadata,) = parse_workflow(wf)
    assert len(metadata.children) == 1
    assert metadata.children[0].label == "add_0"
    assert isinstance(metadata.children[0].obj, _ChildNode)


def test_parse_workflow_no_children() -> None:
    wf = _MockWorkflowNoNodes()
    (metadata,) = parse_workflow(wf)
    assert metadata.children == []


def test_parse_workflow_docstring_enrichment() -> None:
    wf = _MockWorkflow()
    (metadata,) = parse_workflow(wf)
    assert metadata.brief_description == "Calculate result = a + b."
    assert metadata.inputs[0].description == "First operand."
    assert metadata.inputs[1].description == "Second operand."
    assert metadata.outputs[0].description == "Sum of the two operands."


def test_parse_workflow_name_contains_qualname() -> None:
    wf = _MockWorkflow()
    (metadata,) = parse_workflow(wf)
    assert "_MockWorkflow" in metadata.name


def test_parse_workflow_category() -> None:
    wf = _MockWorkflow()
    (metadata,) = parse_workflow(wf)
    # module "tests.test_aiflow" → category "tests>test_aiflow"
    expected = type(wf).__module__.replace(".", ">")
    assert metadata.category == expected


# ---------------------------------------------------------------------------
# Tests for parse (dispatch)
# ---------------------------------------------------------------------------


def test_parse_dispatches_to_workflow() -> None:
    wf = _MockWorkflow()
    result = parse(wf)
    assert len(result) == 1
    assert result[0].artifact_type == ArtifactType.WORKFLOW


def test_parse_returns_empty_for_plain_object() -> None:
    assert parse(object()) == []


def test_parse_returns_empty_for_non_workflow_class() -> None:
    assert parse(_NotAWorkflow) == []
