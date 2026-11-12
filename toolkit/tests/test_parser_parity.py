"""The two-phase parsers store exactly what their legacy ``parse`` stores.

Each fixture object is uploaded once through the legacy ``parse`` and once
through ``run_pipeline`` with the new parser, each into its own store. The
identified ids and every uploaded request must match. (#227 turns these into
golden values when the legacy code is deleted.)
"""

import textwrap
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import Any

import pytest
from sim_atlas_models import NodeRequest

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.node_store import NodeResult
from sim_atlas_toolkit.parsers import (
    python_function,
    python_workflow_definition,
)
from sim_atlas_toolkit.pipeline import GroupResult, run_pipeline
from sim_atlas_toolkit.plugin import Parser
from sim_atlas_toolkit.settings import ToolkitSettings

from .mock_api import MockNodeStore

LegacyParse = Callable[[ParseContext, Any], Awaitable[list[NodeResult]]]


def documented(x: int, y: float = 1.0) -> str:
    """Add two numbers.

    Parameters
    ----------
    x : int
        The first value.
    y : float
        The second value.

    Returns
    -------
    str
        The sum as a string.
    """
    return str(x + y)


def undocumented(z: int) -> int:
    return z * 2


def _indented() -> Callable[[int], int]:
    # Defined one level deep: its source is indented, which the hash ignores
    # (dedent) but the stored source keeps.
    def inner(a: int) -> int:
        """Return *a*."""
        return a

    return inner


def _pwd_workflow() -> Any:
    models = pytest.importorskip("python_workflow_definition.models")
    return models.PythonWorkflowDefinitionWorkflow.model_validate(
        {
            "version": "0.1.0",
            "nodes": [
                {"id": 0, "type": "input", "name": "a", "value": 1},
                {"id": 1, "type": "function", "value": "tests.mod.double"},
                {"id": 2, "type": "output", "name": "result"},
            ],
            "edges": [
                {"source": 0, "sourcePort": None, "target": 1, "targetPort": "x"},
                {"source": 1, "sourcePort": None, "target": 2, "targetPort": None},
            ],
        }
    )


CASES: list[tuple[str, LegacyParse, Callable[[], Parser], Callable[[], Any]]] = [
    (
        "function",
        python_function.parse,
        python_function.PythonFunctionParser,
        lambda: documented,
    ),
    (
        "undocumented",
        python_function.parse,
        python_function.PythonFunctionParser,
        lambda: undocumented,
    ),
    (
        "indented",
        python_function.parse,
        python_function.PythonFunctionParser,
        _indented,
    ),
    (
        "builtin",
        python_function.parse,
        python_function.PythonFunctionParser,
        lambda: len,
    ),
    (
        "pwd",
        python_workflow_definition.parse,
        python_workflow_definition.PythonWorkflowDefinitionParser,
        _pwd_workflow,
    ),
]

SETTINGS = {
    "plain": ToolkitSettings(embed=False),
    "llm+self-contained": ToolkitSettings(
        embed=False,
        llm_docstrings="missing",
        llm_url="http://llm",
        llm_key="k",
        llm_model="m",
        self_contained_source=True,
    ),
}


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """A deterministic LLM, so both paths get the same generated docstring."""
    openai = pytest.importorskip("openai")

    class _Completions:
        async def create(self, **kwargs: Any) -> SimpleNamespace:
            content = textwrap.dedent(
                """\
                Do the thing.

                Parameters
                ----------
                z : int
                    Generated description.
                """
            )
            message = SimpleNamespace(content=content)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class _AsyncOpenAI:
        def __init__(self, api_key: str, base_url: str) -> None:
            self.chat = SimpleNamespace(completions=_Completions())

    monkeypatch.setattr(openai, "AsyncOpenAI", _AsyncOpenAI)


def _dump(nodes: list[NodeRequest]) -> list[dict[str, Any]]:
    return [n.model_dump(mode="json") for n in nodes]


@pytest.mark.parametrize("settings", SETTINGS.values(), ids=SETTINGS.keys())
@pytest.mark.parametrize(
    ("legacy", "new", "make"), [c[1:] for c in CASES], ids=[c[0] for c in CASES]
)
async def test_new_parser_stores_what_legacy_parse_stores(
    legacy: LegacyParse,
    new: Callable[[], Parser],
    make: Callable[[], Any],
    settings: ToolkitSettings,
) -> None:
    obj = make()
    legacy_store, new_store = MockNodeStore(), MockNodeStore()
    await legacy(ParseContext(settings, legacy_store), obj)
    parser = new()

    identity = parser.identify(obj)
    result = await run_pipeline(
        {"mod": [obj]}, [parser], ParseContext(settings, new_store)
    )

    assert identity is not None
    assert [identity.node_id] == [n.id for n in legacy_store.uploaded]
    assert _dump(new_store.uploaded) == _dump(legacy_store.uploaded)
    assert result["mod"] == GroupResult(created=1, existing=0, errors=0, unparsed=0)


@pytest.mark.parametrize(
    "new",
    [c[2] for c in CASES],
    ids=[c[0] for c in CASES],
)
@pytest.mark.parametrize("obj", [42, "text", None, object()], ids=repr)
def test_parsers_decline_foreign_objects(new: Callable[[], Parser], obj: Any) -> None:
    assert new().identify(obj) is None
