import sys
import types
from collections.abc import Callable
from typing import Any

import pytest

from sim_atlas_toolkit.models import (
    Annotation,
    FunctionRequest,
    WfDefinition,
    WorkflowRequest,
)
from sim_atlas_toolkit.parsers.metadata import enrich_metadata, enrich_workflow_metadata
from sim_atlas_toolkit.settings import ToolkitSettings

GENERATED = """Compute a sum.

Args:
    x: the x value.
"""


def _install_fake_generator(
    monkeypatch: pytest.MonkeyPatch, fn: Callable[..., Any]
) -> list[str]:
    """Replace the (openai-dependent) ai_enrichment module with a stub.

    Returns a list that records the source code passed to each generator call.
    """
    calls: list[str] = []

    async def recording(url: str, key: str, model: str, source_code: str) -> str:
        calls.append(source_code)
        return await fn(url, key, model, source_code)

    module = types.ModuleType("sim_atlas_toolkit.parsers.ai_enrichment")
    module.generate_docstring = recording  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sim_atlas_toolkit.parsers.ai_enrichment", module)
    return calls


def _metadata(docstring: str = "") -> FunctionRequest:
    return FunctionRequest.model_construct(
        name="pkg.mod.func",
        source_code="def func(x):\n    return x",
        docstring=docstring,
        inputs=[Annotation(label="x")],
        outputs=[Annotation(label="return")],
    )


async def _fake_generate(url: str, key: str, model: str, source_code: str) -> str:
    return GENERATED


def _install_fake_workflow_generator(
    monkeypatch: pytest.MonkeyPatch, fn: Callable[..., Any]
) -> list[str]:
    """Replace the (openai-dependent) ai_enrichment module with a stub.

    Returns a list that records the docstring passed to each generator call.
    """
    calls: list[str] = []

    async def recording(
        settings: ToolkitSettings,
        name: str,
        source_code: str,
        docstring: str,
        wf_definition: WfDefinition,
    ) -> str:
        calls.append(docstring)
        return await fn(settings, name, source_code, docstring, wf_definition)

    module = types.ModuleType("sim_atlas_toolkit.parsers.ai_enrichment")
    module.generate_workflow_docstring = recording  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sim_atlas_toolkit.parsers.ai_enrichment", module)
    return calls


def _workflow_metadata(docstring: str = "") -> WorkflowRequest:
    return WorkflowRequest.model_construct(
        name="pkg.mod.workflow",
        source_code="def workflow(x):\n    return x",
        docstring=docstring,
        inputs=[Annotation(label="x")],
        outputs=[Annotation(label="return")],
        wf_definition=WfDefinition(nodes=[], edges=[]),
    )


async def _fake_generate_workflow(
    settings: ToolkitSettings,
    name: str,
    source_code: str,
    docstring: str,
    wf_definition: WfDefinition,
) -> str:
    return GENERATED


async def test_no_settings_does_not_generate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_generator(monkeypatch, _fake_generate)
    metadata = _metadata()

    await enrich_metadata(ToolkitSettings(), metadata)

    assert calls == []
    assert metadata.docstring == ""


async def test_disabled_does_not_generate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_generator(monkeypatch, _fake_generate)
    metadata = _metadata()

    await enrich_metadata(ToolkitSettings(llm_enabled=False), metadata)

    assert calls == []


async def test_generates_when_docstring_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fake_generator(monkeypatch, _fake_generate)
    metadata = _metadata()
    settings = ToolkitSettings(
        llm_enabled=True, llm_url="http://llm", llm_key="k", llm_model="m"
    )

    await enrich_metadata(settings, metadata)

    assert calls == ["def func(x):\n    return x"]
    assert metadata.docstring == GENERATED
    # griffe parsed the generated docstring
    assert metadata.brief_description == "Compute a sum."
    assert metadata.inputs[0].description == "the x value."


async def test_existing_docstring_not_overwritten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fake_generator(monkeypatch, _fake_generate)
    metadata = _metadata(docstring="An existing docstring.")
    settings = ToolkitSettings(
        llm_enabled=True,
        llm_url="http://llm",
        llm_key="k",
        llm_model="m",
        llm_overwrite=False,
    )

    await enrich_metadata(settings, metadata)

    assert calls == []
    assert metadata.docstring == "An existing docstring."


async def test_overwrite_regenerates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_generator(monkeypatch, _fake_generate)
    metadata = _metadata(docstring="An existing docstring.")
    settings = ToolkitSettings(
        llm_enabled=True,
        llm_url="http://llm",
        llm_key="k",
        llm_model="m",
        llm_overwrite=True,
    )

    await enrich_metadata(settings, metadata)

    assert len(calls) == 1
    assert metadata.docstring == GENERATED


async def test_generation_failure_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(url: str, key: str, model: str, source_code: str) -> str:
        raise RuntimeError("llm down")

    _install_fake_generator(monkeypatch, boom)
    metadata = _metadata(docstring="Kept docstring.")
    settings = ToolkitSettings(
        llm_enabled=True,
        llm_url="http://llm",
        llm_key="k",
        llm_model="m",
        llm_overwrite=True,
    )

    # Must not raise; existing docstring is preserved and still enriched.
    await enrich_metadata(settings, metadata)

    assert metadata.docstring == "Kept docstring."


async def test_workflow_no_settings_does_not_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fake_workflow_generator(monkeypatch, _fake_generate_workflow)
    metadata = _workflow_metadata()

    await enrich_workflow_metadata(ToolkitSettings(), metadata)

    assert calls == []
    assert metadata.docstring == ""


async def test_workflow_disabled_does_not_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fake_workflow_generator(monkeypatch, _fake_generate_workflow)
    metadata = _workflow_metadata()

    await enrich_workflow_metadata(ToolkitSettings(llm_enabled=False), metadata)

    assert calls == []


async def test_workflow_generates_when_docstring_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fake_workflow_generator(monkeypatch, _fake_generate_workflow)
    metadata = _workflow_metadata()
    settings = ToolkitSettings(
        llm_enabled=True, llm_url="http://llm", llm_key="k", llm_model="m"
    )

    await enrich_workflow_metadata(settings, metadata)

    assert calls == [""]
    assert metadata.docstring == GENERATED
    # griffe parsed the generated docstring
    assert metadata.brief_description == "Compute a sum."
    assert metadata.inputs[0].description == "the x value."


async def test_workflow_existing_docstring_not_overwritten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fake_workflow_generator(monkeypatch, _fake_generate_workflow)
    metadata = _workflow_metadata(docstring="An existing docstring.")
    settings = ToolkitSettings(
        llm_enabled=True,
        llm_url="http://llm",
        llm_key="k",
        llm_model="m",
        llm_overwrite=False,
    )

    await enrich_workflow_metadata(settings, metadata)

    assert calls == []
    assert metadata.docstring == "An existing docstring."


async def test_workflow_overwrite_regenerates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_workflow_generator(monkeypatch, _fake_generate_workflow)
    metadata = _workflow_metadata(docstring="An existing docstring.")
    settings = ToolkitSettings(
        llm_enabled=True,
        llm_url="http://llm",
        llm_key="k",
        llm_model="m",
        llm_overwrite=True,
    )

    await enrich_workflow_metadata(settings, metadata)

    assert len(calls) == 1
    assert metadata.docstring == GENERATED


async def test_workflow_generation_failure_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(
        settings: ToolkitSettings,
        name: str,
        source_code: str,
        docstring: str,
        wf_definition: WfDefinition,
    ) -> str:
        raise RuntimeError("llm down")

    _install_fake_workflow_generator(monkeypatch, boom)
    metadata = _workflow_metadata(docstring="Kept docstring.")
    settings = ToolkitSettings(
        llm_enabled=True,
        llm_url="http://llm",
        llm_key="k",
        llm_model="m",
        llm_overwrite=True,
    )

    # Must not raise; existing docstring is preserved and still enriched.
    await enrich_workflow_metadata(settings, metadata)

    assert metadata.docstring == "Kept docstring."


def test_settings_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIM_ATLAS_LLM_ENABLED", "true")
    monkeypatch.setenv("SIM_ATLAS_LLM_URL", "http://env-llm")
    monkeypatch.setenv("SIM_ATLAS_LLM_MODEL", "env-model")
    monkeypatch.setenv("SIM_ATLAS_LLM_OVERWRITE", "true")

    settings = ToolkitSettings()

    assert settings.llm_enabled is True
    assert settings.llm_url == "http://env-llm"
    assert settings.llm_model == "env-model"
    assert settings.llm_overwrite is True
