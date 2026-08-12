import os
from typing import Any

import pytest
from pydantic import ValidationError
from pydantic_settings import CliApp

from sim_atlas_toolkit import cli
from sim_atlas_toolkit.cli import UploadCommand
from sim_atlas_toolkit.settings import ToolkitSettings

USAGE_ERROR = 2


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith("SIM_ATLAS_"):
            monkeypatch.delenv(name)


@pytest.fixture
def calls(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[ToolkitSettings, dict[str, Any]]]:
    recorded: list[tuple[ToolkitSettings, dict[str, Any]]] = []

    def fake_upload_modules(settings: ToolkitSettings, **kwargs: Any) -> None:
        recorded.append((settings, kwargs))

    monkeypatch.setattr(cli, "upload_modules", fake_upload_modules)
    return recorded


def test_full_flag_set(calls: list[tuple[ToolkitSettings, dict[str, Any]]]) -> None:
    CliApp.run(
        UploadCommand,
        cli_args=[
            "pkg.first",
            "pkg.second",
            "--api-url",
            "http://backend/api/v1",
            "--api-token",
            "tok",
            "--recursive",
            "filesystem",
            "--update-existing",
            "--allowed-modules",
            "foo",
            "--allowed-modules",
            "bar",
            "--concurrency",
            "3",
            "--no-embed",
            "--llm-docstrings",
            "missing",
            "--llm-url",
            "http://llm",
            "--llm-model",
            "model",
        ],
    )

    settings, kwargs = calls[0]
    assert settings.api_url == "http://backend/api/v1"
    assert settings.api_token == "tok"
    assert settings.embed is False
    assert settings.llm_docstrings == "missing"
    assert kwargs == {
        "modules": ["pkg.first", "pkg.second"],
        "recursive": "filesystem",
        "update_existing": True,
        "module_allowlist": ["foo", "bar"],
        "concurrency": 3,
    }


def test_defaults(calls: list[tuple[ToolkitSettings, dict[str, Any]]]) -> None:
    CliApp.run(
        UploadCommand,
        cli_args=["pkg", "--api-url", "http://backend", "--api-token", "tok"],
    )

    settings, kwargs = calls[0]
    assert settings.embed is True
    assert settings.llm_docstrings == "no"
    assert kwargs == {
        "modules": ["pkg"],
        "recursive": "no",
        "update_existing": False,
        "module_allowlist": [],
        "concurrency": 10,
    }


def test_credentials_from_env(
    calls: list[tuple[ToolkitSettings, dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIM_ATLAS_API_URL", "http://env-backend")
    monkeypatch.setenv("SIM_ATLAS_API_TOKEN", "env-tok")

    CliApp.run(UploadCommand, cli_args=["pkg"])

    settings, _ = calls[0]
    assert settings.api_url == "http://env-backend"
    assert settings.api_token == "env-tok"


def test_cli_overrides_env(
    calls: list[tuple[ToolkitSettings, dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIM_ATLAS_API_URL", "http://env-backend")

    CliApp.run(
        UploadCommand,
        cli_args=["pkg", "--api-url", "http://flag-backend", "--api-token", "tok"],
    )

    settings, _ = calls[0]
    assert settings.api_url == "http://flag-backend"


def test_missing_api_token_raises(
    calls: list[tuple[ToolkitSettings, dict[str, Any]]],
) -> None:
    with pytest.raises(ValidationError):
        CliApp.run(UploadCommand, cli_args=["pkg", "--api-url", "http://backend"])

    assert not calls


def test_enrichment_without_llm_config_raises(
    calls: list[tuple[ToolkitSettings, dict[str, Any]]],
) -> None:
    with pytest.raises(ValidationError):
        CliApp.run(
            UploadCommand,
            cli_args=[
                "pkg",
                "--api-url",
                "http://backend",
                "--api-token",
                "tok",
                "--llm-docstrings",
                "overwrite",
            ],
        )

    assert not calls


def test_main_reports_validation_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["sim-atlas-upload", "pkg"])

    assert cli.main() == USAGE_ERROR
    assert "api_url" in capsys.readouterr().err
