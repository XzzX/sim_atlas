import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sim_atlas_backend.ai import create_ai_descriptions, create_workflow_ai_descriptions
from sim_atlas_backend.exceptions import AINotConfiguredError
from sim_atlas_backend.settings import Settings


def _make_response(payload: dict[str, Any]) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(payload)
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture()
def settings_with_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(
        jwt_secret_key="x",
        jwt_algorithm="HS256",
        llm_api_key="test-key",
        llm_api_url="https://example.com",
        llm_chat_model="gpt-test",
    )
    monkeypatch.setattr("sim_atlas_backend.ai.load_settings", lambda: s)


def test_create_ai_descriptions_returns_three_tuple(
    settings_with_llm: None,
) -> None:
    payload: dict[str, Any] = {
        "summary": "Compute the melting point.",
        "description": "Determines the melting point of a material.",
        "args": {"temperature": "initial temperature in Kelvin"},
    }
    with patch("sim_atlas_backend.ai.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_response(payload)
        )
        mock_cls.return_value = mock_client

        summary, description, args = asyncio.run(
            create_ai_descriptions(
                "compute_melting_point",
                "Compute melting point.",
                "def compute_melting_point(): ...",
                output_labels=["temperature"],
            )
        )

    assert summary == "Compute the melting point."
    assert description == "Determines the melting point of a material."
    assert args == {"temperature": "initial temperature in Kelvin"}


def test_create_ai_descriptions_empty_args_when_not_returned(
    settings_with_llm: None,
) -> None:
    payload: dict[str, Any] = {
        "summary": "Short summary.",
        "description": "Longer description.",
    }
    with patch("sim_atlas_backend.ai.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_response(payload)
        )
        mock_cls.return_value = mock_client

        _, _, args = asyncio.run(create_ai_descriptions("fn", "", "def fn(): ..."))

    assert args == {}


def test_create_ai_descriptions_raises_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = Settings(jwt_secret_key="x", jwt_algorithm="HS256")
    monkeypatch.setattr("sim_atlas_backend.ai.load_settings", lambda: s)

    with pytest.raises(AINotConfiguredError):
        asyncio.run(create_ai_descriptions("fn", "", "def fn(): ...", []))


def test_create_ai_descriptions_strips_think_tags(
    settings_with_llm: None,
) -> None:
    payload: dict[str, Any] = {
        "summary": "Summary.",
        "description": "Desc.",
        "args": {},
    }
    raw = f"<think>internal reasoning</think>{json.dumps(payload)}"
    choice = MagicMock()
    choice.message.content = raw
    response = MagicMock()
    response.choices = [choice]

    with patch("sim_atlas_backend.ai.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=response)
        mock_cls.return_value = mock_client

        summary, _, _ = asyncio.run(create_ai_descriptions("fn", "", "def fn(): ..."))

    assert summary == "Summary."


def test_create_ai_descriptions_output_labels_in_prompt(
    settings_with_llm: None,
) -> None:
    payload: dict[str, Any] = {
        "summary": "S.",
        "description": "D.",
        "args": {"energy_final": "final energy of the system"},
    }
    with patch("sim_atlas_backend.ai.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_response(payload)
        )
        mock_cls.return_value = mock_client

        asyncio.run(
            create_ai_descriptions(
                "fn", "", "def fn(): ...", output_labels=["energy_final", "volume"]
            )
        )

    call_kwargs = mock_client.chat.completions.create.call_args
    prompt_content = call_kwargs.kwargs["messages"][0]["content"]
    assert "energy_final" in prompt_content
    assert "volume" in prompt_content


# ---------------------------------------------------------------------------
# create_workflow_ai_descriptions
# ---------------------------------------------------------------------------


def test_create_workflow_ai_descriptions_returns_two_tuple(
    settings_with_llm: None,
) -> None:
    payload: dict[str, Any] = {
        "summary": "Compute energy minimisation pipeline.",
        "description": "A workflow that minimises total energy via conjugate gradient.",
    }
    with patch("sim_atlas_backend.ai.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_response(payload)
        )
        mock_cls.return_value = mock_client

        summary, description = asyncio.run(
            create_workflow_ai_descriptions(
                "energy_minimisation",
                "Minimise total energy.",
                "- step1: Compute forces\n- step2: Update positions",
            )
        )

    assert summary == "Compute energy minimisation pipeline."
    assert (
        description == "A workflow that minimises total energy via conjugate gradient."
    )


def test_create_workflow_ai_descriptions_graph_text_in_prompt(
    settings_with_llm: None,
) -> None:
    payload: dict[str, Any] = {"summary": "S.", "description": "D."}
    with patch("sim_atlas_backend.ai.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_response(payload)
        )
        mock_cls.return_value = mock_client

        asyncio.run(
            create_workflow_ai_descriptions(
                "my_wf", "My workflow.", "- node_a: Compute forces"
            )
        )

    call_kwargs = mock_client.chat.completions.create.call_args
    prompt_content = call_kwargs.kwargs["messages"][0]["content"]
    assert "my_wf" in prompt_content
    assert "node_a: Compute forces" in prompt_content


def test_create_workflow_ai_descriptions_raises_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = Settings(jwt_secret_key="x", jwt_algorithm="HS256")
    monkeypatch.setattr("sim_atlas_backend.ai.load_settings", lambda: s)

    with pytest.raises(AINotConfiguredError):
        asyncio.run(create_workflow_ai_descriptions("wf", "", ""))
