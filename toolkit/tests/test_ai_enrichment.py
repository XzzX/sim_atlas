from typing import Any

import httpx
import pytest

pytest.importorskip("openai")

from sim_atlas_toolkit import node_store_api  # noqa: E402
from sim_atlas_toolkit.models import (  # noqa: E402
    Annotation,
    FunctionResponse,
    WfDefinition,
    WfEdge,
    WfFunctionNode,
    WfInputNode,
    WfOutputNode,
)

# Testing the internal graph-rendering helper directly, not just its public
# wrapper, to pin down the rendered text without invoking the LLM client.
from sim_atlas_toolkit.parsers.ai_enrichment import (  # noqa: E402
    _render_wf_graph,  # pyright: ignore[reportPrivateUsage]
    clean_response,
)


def test_plain_text_passthrough() -> None:
    assert clean_response("Compute a sum.") == "Compute a sum."


def test_strips_think_block() -> None:
    raw = "<think>Let me reason about this.</think>\n\nCompute a sum."
    assert clean_response(raw) == "Compute a sum."


def test_strips_think_block_case_insensitive_multiline() -> None:
    raw = "<THINK>\nline one\nline two\n</THINK>Compute a sum."
    assert clean_response(raw) == "Compute a sum."


def test_strips_lone_closing_think_tag() -> None:
    # Reasoning models that emit no opening tag.
    raw = "internal reasoning here</think>Compute a sum."
    assert clean_response(raw) == "Compute a sum."


def test_unwraps_code_fence() -> None:
    raw = "```python\nCompute a sum.\n\nArgs:\n    x: the value.\n```"
    assert clean_response(raw) == "Compute a sum.\n\nArgs:\n    x: the value."


def test_unwraps_triple_quotes() -> None:
    assert clean_response('"""Compute a sum."""') == "Compute a sum."


def test_combined_think_and_fence() -> None:
    raw = "<think>reason</think>\n```\nCompute a sum.\n```"
    assert clean_response(raw) == "Compute a sum."


def test_single_quote_char_not_overstripped() -> None:
    assert clean_response('"') == '"'


def _function_response(name: str, brief_description: str) -> dict[str, Any]:
    return FunctionResponse(
        id="atlas-1",
        hash="hash-1",
        name=name,
        category="cat",
        keywords=[],
        author_name="a",
        author_email="a@example.com",
        creator_name="a",
        creator_email="a@example.com",
        creation_timestamp="2024-01-01T00:00:00Z",
        python_import="pkg.mod.func",
        source_code="def func(): ...",
        docstring="",
        brief_description=brief_description,
        inputs=[],
        outputs=[],
    ).model_dump(mode="json")


async def test_render_wf_graph_fetches_node_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def read_artifact(api_url: str, artifact_id: str) -> httpx.Response:
        assert artifact_id == "atlas-1"
        return httpx.Response(
            200, json=_function_response("pkg.mod.relax", "Relax a structure.")
        )

    monkeypatch.setattr(node_store_api, "read_artifact", read_artifact)

    wf_definition = WfDefinition(
        nodes=[
            WfInputNode(node_id="structure", outputs=[Annotation(label="structure")]),
            WfFunctionNode(
                node_id="relax",
                inputs=[Annotation(label="structure")],
                outputs=[Annotation(label="relaxed")],
                atlas_id="atlas-1",
            ),
            WfOutputNode(node_id="relaxed", inputs=[Annotation(label="relaxed")]),
        ],
        edges=[
            WfEdge(
                source_node="structure", target_node="relax", target_port="structure"
            ),
            WfEdge(source_node="relax", source_port="relaxed", target_node="relaxed"),
        ],
    )

    graph = await _render_wf_graph("http://api", wf_definition)

    assert "pkg.mod.relax" in graph
    assert "Relax a structure." in graph
    assert "structure -> relax.structure" in graph
    assert "relax.relaxed -> relaxed" in graph


async def test_render_wf_graph_degrades_on_missing_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def read_artifact(api_url: str, artifact_id: str) -> httpx.Response:
        return httpx.Response(404)

    monkeypatch.setattr(node_store_api, "read_artifact", read_artifact)

    wf_definition = WfDefinition(
        nodes=[
            WfFunctionNode(
                node_id="missing",
                inputs=[Annotation(label="x")],
                outputs=[Annotation(label="y")],
                atlas_id="does-not-exist",
            ),
        ],
        edges=[],
    )

    graph = await _render_wf_graph("http://api", wf_definition)

    assert "missing" in graph
    assert "no description available" in graph


async def test_render_wf_graph_no_atlas_id() -> None:
    wf_definition = WfDefinition(
        nodes=[
            WfFunctionNode(
                node_id="local",
                inputs=[Annotation(label="x")],
                outputs=[Annotation(label="y")],
                atlas_id=None,
            ),
        ],
        edges=[],
    )

    graph = await _render_wf_graph("http://api", wf_definition)

    assert "local" in graph
    assert "no description available" in graph
