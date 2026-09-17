"""Unit tests for the Python-shaped MCP renderers (no HTTP, no storage)."""

from __future__ import annotations

import pytest

from sim_atlas.mcp_server import _format
from sim_atlas.models import AnnotationResponse, PackageRef

from .test_storage_interface import make_node, make_workflow

# ---------------------------------------------------------------------------
# Signatures
# ---------------------------------------------------------------------------


def test_signature_uses_labels_datatypes_and_defaults() -> None:
    node = make_node(
        python_import="pkg.mod.compute",
        inputs=[
            AnnotationResponse(label="a", datatype="float"),
            AnnotationResponse(label="b", datatype="int", has_default_value=True),
        ],
        outputs=[AnnotationResponse(label="r", datatype="str")],
    )

    assert (
        _format.render_signature(node) == "def compute(a: float, b: int = ...) -> str"
    )


def test_signature_without_outputs_returns_none() -> None:
    node = make_node(python_import="pkg.sink", inputs=[], outputs=[])

    assert _format.render_signature(node) == "def sink() -> None"


def test_signature_with_two_outputs_uses_a_tuple() -> None:
    node = make_node(
        python_import="pkg.split",
        outputs=[
            AnnotationResponse(label="a", datatype="float"),
            AnnotationResponse(label="b", datatype="int"),
        ],
    )

    assert _format.render_signature(node).endswith("-> tuple[float, int]")


def test_signature_fills_missing_output_datatypes_with_any() -> None:
    node = make_node(
        python_import="pkg.split",
        outputs=[
            AnnotationResponse(label="a", datatype="float"),
            AnnotationResponse(label="b"),
        ],
    )

    assert _format.render_signature(node).endswith("-> tuple[float, Any]")


def test_signature_omits_the_arrow_for_one_untyped_output() -> None:
    node = make_node(python_import="pkg.f", outputs=[AnnotationResponse(label="r")])

    assert _format.render_signature(node) == "def f()"


def test_signature_falls_back_to_positional_parameter_names() -> None:
    node = make_node(
        python_import="pkg.f",
        inputs=[AnnotationResponse(), AnnotationResponse()],
        outputs=[],
    )

    assert _format.render_signature(node) == "def f(arg0, arg1) -> None"


def test_signature_falls_back_to_the_artifact_name_without_an_import() -> None:
    """flowrep artifacts carry a dotted ``name`` even when python_import is unset."""
    node = make_node(python_import="", name="dummy_module.flowrep.linear", outputs=[])

    assert _format.render_signature(node) == "def linear() -> None"


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------


def test_import_splits_module_and_qualname() -> None:
    node = make_node(python_import="pkg.mod.compute")

    assert _format.render_import(node) == "from pkg.mod import compute"


def test_import_without_a_dot_uses_a_plain_import() -> None:
    node = make_node(python_import="compute")

    assert _format.render_import(node) == "import compute"


def test_import_degrades_to_a_comment_for_a_function_without_an_import() -> None:
    node = make_node(python_import="")

    assert _format.render_import(node).startswith("# no import path recorded")


def test_import_degrades_and_points_at_the_source_tool_for_a_workflow() -> None:
    workflow = make_workflow(id="wf-9", python_import=None)

    rendered = _format.render_import(workflow)

    assert 'get_workflow_source("wf-9")' in rendered


# ---------------------------------------------------------------------------
# Install hints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("package", "expected"),
    [
        (
            PackageRef(ecosystem="pypi", name="mylib", version="1.4.0"),
            '# install: pip install "mylib==1.4.0"',
        ),
        (
            PackageRef(ecosystem="pypi", name="mylib"),
            "# install: pip install mylib",
        ),
        (
            PackageRef(
                ecosystem="conda", name="mylib", version="1.4.0", channel="conda-forge"
            ),
            "# install: conda install -c conda-forge mylib=1.4.0",
        ),
        (
            PackageRef(ecosystem="conda", name="mylib"),
            "# install: conda install mylib",
        ),
    ],
)
def test_install_lines(package: PackageRef, expected: str) -> None:
    node = make_node(packages=[package])

    assert _format.render_install(node) == [expected]


def test_install_degrades_to_the_top_level_module_without_packages() -> None:
    node = make_node(python_import="mylib.mod.compute", packages=[])

    assert _format.render_install(node) == [
        "# install: not recorded; the callable lives in the top-level module 'mylib'"
    ]


def test_install_is_omitted_without_packages_or_import() -> None:
    node = make_node(python_import="", packages=[])

    assert _format.render_install(node) == []


def test_install_caps_the_number_of_packages() -> None:
    node = make_node(
        packages=[
            PackageRef(ecosystem="pypi", name=f"p{i}")
            for i in range(_format.MAX_PACKAGES + 2)
        ]
    )

    lines = _format.render_install(node)

    assert len(lines) == _format.MAX_PACKAGES + 1
    assert lines[-1] == "# …and 2 more package(s)"


# ---------------------------------------------------------------------------
# Result blocks
# ---------------------------------------------------------------------------


def test_hit_annotates_units_and_quantities() -> None:
    node = make_node(
        id="n1",
        python_import="pkg.f",
        inputs=[
            AnnotationResponse(
                label="t", datatype="float", unit="K", quantity="temperature"
            )
        ],
        outputs=[],
    )

    rendered = _format.render_hit(node)

    assert "# t — unit: K; quantity: temperature" in rendered
    assert "# id: n1 (function)" in rendered


def test_hit_skips_ports_that_add_nothing_to_the_signature() -> None:
    node = make_node(
        python_import="pkg.f",
        inputs=[AnnotationResponse(label="x", datatype="int")],
        outputs=[],
    )

    assert "# x —" not in _format.render_hit(node)


def test_hit_truncates_a_long_summary() -> None:
    node = make_node(brief_description="word " * 200)

    summary = [
        line
        for line in _format.render_hit(node).splitlines()
        if line.startswith("# word")
    ]

    assert summary and summary[0].endswith("…")
    assert len(summary[0]) <= _format.MAX_DESCRIPTION_CHARS + 2


def test_hit_marks_workflows_and_points_at_the_source_tool() -> None:
    workflow = make_workflow(id="wf-1", python_import="pkg.flows.linear")

    rendered = _format.render_hit(workflow)

    assert "# id: wf-1 (workflow)" in rendered
    assert 'get_workflow_source("wf-1")' in rendered


def test_no_matches_tells_the_agent_when_to_stop() -> None:
    rendered = _format.render_no_matches("something")

    assert "No matches" in rendered
    assert "write the code yourself" in rendered


# ---------------------------------------------------------------------------
# Workflow source
# ---------------------------------------------------------------------------


def test_source_truncates_long_workflows() -> None:
    workflow = make_workflow(
        source_code="\n".join(
            f"line_{i} = {i}" for i in range(_format.MAX_SOURCE_LINES + 50)
        )
    )

    rendered = _format.render_source(workflow)

    assert "[truncated: showing the first" in rendered
    assert f"line_{_format.MAX_SOURCE_LINES + 10}" not in rendered


def test_source_labels_a_json_workflow_definition() -> None:
    workflow = make_workflow(source_code='{\n  "nodes": []\n}')

    assert "not executable Python" in _format.render_source(workflow)


def test_source_reports_an_empty_workflow_body() -> None:
    workflow = make_workflow(id="wf-2", source_code="")

    assert "No source code is stored for workflow 'wf-2'" in _format.render_source(
        workflow
    )


# ---------------------------------------------------------------------------
# Detail view
# ---------------------------------------------------------------------------


def test_detail_truncates_a_very_long_docstring() -> None:
    node = make_node(docstring="x" * (_format.MAX_DOCSTRING_CHARS + 500))

    assert "[docstring truncated]" in _format.render_detail(node)


def test_detail_lists_parameters_and_links() -> None:
    node = make_node(
        python_import="pkg.f",
        inputs=[AnnotationResponse(label="a", datatype="float", unit="m")],
        outputs=[AnnotationResponse(label="r", datatype="float")],
        documentation_url="https://docs.example",
        source_url="https://src.example",
        homepage_url="",
    )

    rendered = _format.render_detail(node)

    assert "Parameters:" in rendered
    assert "  a: float — unit: m" in rendered
    assert "Returns:" in rendered
    assert "Links: docs https://docs.example | source https://src.example" in rendered


def test_detail_omits_empty_sections() -> None:
    node = make_node(
        python_import="pkg.f",
        inputs=[],
        outputs=[],
        docstring="",
        documentation_url="",
        source_url="",
        homepage_url="",
    )

    rendered = _format.render_detail(node)

    assert "Parameters:" not in rendered
    assert "Docstring:" not in rendered
    assert "Links:" not in rendered
