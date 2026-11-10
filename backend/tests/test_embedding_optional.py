"""Embedding providers are optional extras; core install must work without them.

These tests pass with or without the extras installed: CI runs them in both a
full and a core-only environment.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import sim_atlas.storage.file_system_storage as fss
from sim_atlas import embedding
from sim_atlas.embedding import EmbeddingConfig, Provider, create_embedding
from sim_atlas.exceptions import AINotConfiguredError
from sim_atlas.settings import Settings
from sim_atlas.storage.file_system_storage import FileSystemStorage
from sim_atlas.storage.storage_interface import get_storage_backend

from .test_storage_interface import make_node

_AI_MODULES = (
    "fastembed",
    "onnxruntime",
    "openai",
    "voyageai",
    "tokenizers",
    "huggingface_hub",
)
_PROVIDERS: tuple[Provider, ...] = ("fastembed", "openai", "voyageai")


def _installed(_provider: Provider) -> bool:
    return True


def _not_installed(_provider: Provider) -> bool:
    return False


@pytest.fixture(autouse=True)
def _clear_embedder_cache() -> Any:
    embedding._embedder.cache_clear()  # pyright: ignore[reportPrivateUsage]
    yield
    embedding._embedder.cache_clear()  # pyright: ignore[reportPrivateUsage]


def _run(code: str, cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_importing_the_app_loads_no_ai_package(tmp_path: Path) -> None:
    env = {**os.environ, "SIM_ATLAS_JWT_SECRET": "test-secret"}
    _run(
        "import sys, sim_atlas.main\n"
        f"loaded = sorted(m for m in {_AI_MODULES!r} if m in sys.modules)\n"
        "assert not loaded, loaded\n",
        tmp_path,
        env,
    )


def test_embedding_and_storage_work_without_settings(tmp_path: Path) -> None:
    """Library use needs no settings, no server stack and writes no config file."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SIM_ATLAS_")}
    _run(
        "import asyncio, sys\n"
        "import numpy as np\n"
        "import sim_atlas.storage.file_system_storage as fss\n"
        "from sim_atlas.embedding import EmbeddingConfig\n"
        "calls = []\n"
        "async def fake(config, documents, input_type='document'):\n"
        "    calls.append(config)\n"
        "    return np.ones((len(documents), 3), dtype=np.float32)\n"
        "fss.create_embedding = fake\n"
        "cfg = EmbeddingConfig('fastembed')\n"
        "storage = fss.FileSystemStorage(path=None, embedding_config=cfg)\n"
        "asyncio.run(storage.search_hybrid('anything'))\n"
        "assert calls == [cfg], calls\n"
        "for m in ('sim_atlas.settings', 'fastapi'):\n"
        "    assert m not in sys.modules, m\n",
        tmp_path,
        env,
    )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_missing_extra_raises_with_install_hint(
    provider: Provider, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(embedding, "provider_installed", _not_installed)
    config = EmbeddingConfig(provider, model="m", api_key="k")

    assert not config.ready
    with pytest.raises(AINotConfiguredError, match=rf"sim-atlas\[{provider}\]"):
        asyncio.run(create_embedding(config, ["x"]))


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_factory_import_error_raises_with_install_hint(
    provider: Provider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even if find_spec is fooled, a failing import still gives the hint."""
    monkeypatch.setattr(embedding, "provider_installed", _installed)
    monkeypatch.setitem(sys.modules, provider, None)  # makes `import` fail

    with pytest.raises(AINotConfiguredError, match=rf"sim-atlas\[{provider}\]"):
        asyncio.run(
            create_embedding(EmbeddingConfig(provider, model="m", api_key="k"), ["x"])
        )


@pytest.mark.parametrize("provider", ["openai", "voyageai"])
@pytest.mark.parametrize(
    ("model", "api_key", "missing"),
    [(None, "k", "embedding_model"), ("m", None, "embedding_api_key")],
)
def test_hosted_providers_need_model_and_key(
    provider: Provider,
    model: str | None,
    api_key: str | None,
    missing: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(embedding, "provider_installed", _installed)
    config = EmbeddingConfig(provider, model=model, api_key=api_key)

    assert config.problem is not None and missing in config.problem
    with pytest.raises(AINotConfiguredError, match=missing):
        asyncio.run(create_embedding(config, ["x"]))


def test_api_key_is_not_in_repr() -> None:
    assert "secret" not in repr(EmbeddingConfig("openai", api_key="secret"))


def test_create_embedding_returns_float32_array_in_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(embedding, "provider_installed", _installed)
    batches: list[list[str]] = []

    def _fake_factory(config: EmbeddingConfig) -> embedding.Embedder:
        async def embed(documents: list[str], input_type: str) -> np.ndarray:
            rows: list[list[float]] = []
            for batch in embedding._batches(documents, config.batch_size):  # pyright: ignore[reportPrivateUsage]
                batches.append(batch)
                rows += [[float(len(d)), 1.0] for d in batch]
            return np.array(rows, dtype=np.float32)

        return embed

    monkeypatch.setattr(embedding, "_fastembed_embedder", _fake_factory)
    docs = ["a", "bb", "ccc", "dddd", "eeeee"]

    result = asyncio.run(
        create_embedding(EmbeddingConfig("fastembed", batch_size=2), docs)
    )

    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float32
    assert result.shape == (5, 2)
    assert batches == [["a", "bb"], ["ccc", "dddd"], ["eeeee"]]


def test_uninstalled_provider_falls_back_to_keyword_search(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The generated config names fastembed; a core-only install must still serve."""
    monkeypatch.setattr(embedding, "provider_installed", _not_installed)
    settings = Settings(jwt_secret="x", embedding_provider="fastembed")
    monkeypatch.setattr("sim_atlas.settings.load_settings", lambda: settings)
    monkeypatch.setattr(Settings, "config_dir", property(lambda _self: tmp_path))

    assert not settings.embeddings_enabled

    with caplog.at_level(logging.WARNING):
        storage = get_storage_backend()
    try:
        assert "sim-atlas[fastembed]" in caplog.text
        assert isinstance(storage, FileSystemStorage)

        async def _boom(*_args: Any, **_kwargs: Any) -> np.ndarray:
            raise AssertionError("create_embedding must not be called")

        monkeypatch.setattr(fss, "create_embedding", _boom)
        asyncio.run(storage.search_hybrid("anything"))
    finally:
        storage.close()


def test_storage_without_config_rejects_semantic_operations() -> None:
    storage = FileSystemStorage(path=None)
    storage.create_node(make_node(description="Does a thing"))
    with pytest.raises(AINotConfiguredError):
        asyncio.run(storage.search_semantic("anything"))
    with pytest.raises(AINotConfiguredError):
        asyncio.run(storage.embed_missing())
