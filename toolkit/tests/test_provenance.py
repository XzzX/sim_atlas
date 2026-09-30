"""Tests for package-provenance detection.

Conda detection is exercised without a conda environment: the ``site-packages``
tree never has to exist on disk, because every lookup is string math over
``conda-meta/*.json`` records.
"""

import json
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from sim_atlas_toolkit import provenance
from sim_atlas_toolkit.models import (
    ArtifactType,
    NodeRequest,
    PackageRef,
    node_request_adapter,
)
from sim_atlas_toolkit.provenance import (
    _channel,  # pyright: ignore[reportPrivateUsage]
    _conda_index,  # pyright: ignore[reportPrivateUsage]
    _dists_by_root,  # pyright: ignore[reportPrivateUsage]
    _env_prefix,  # pyright: ignore[reportPrivateUsage]
    _site_key,  # pyright: ignore[reportPrivateUsage]
    apply_provenance,
    packages_for_module,
)

SITE = "lib/python3.13/site-packages"


@pytest.fixture(autouse=True)
def clear_caches() -> Any:
    """``functools.cache`` would otherwise leak one test's fake env into the next."""
    caches = (packages_for_module, _env_prefix, _conda_index, _dists_by_root)
    for fn in caches:
        fn.cache_clear()
    yield
    for fn in caches:
        fn.cache_clear()


def _fake_dists(**roots: tuple[str, ...]) -> Callable[[], dict[str, tuple[str, ...]]]:
    """Stand in for the environment-wide import-root -> distribution mapping."""
    return lambda: dict(roots)


def _write_env(prefix: Path, *records: dict[str, Any]) -> Path:
    meta = prefix / "conda-meta"
    meta.mkdir(parents=True, exist_ok=True)
    for record in records:
        name = record["name"]
        version = record.get("version", "0")
        (meta / f"{name}-{version}-0.json").write_text(json.dumps(record))
    return prefix


def _record(name: str, version: str = "1.0", **kwargs: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": name,
        "version": version,
        "channel": "https://conda.anaconda.org/conda-forge/linux-64",
        "subdir": "linux-64",
        "files": [f"{SITE}/{name}/__init__.py"],
    }
    record.update(kwargs)
    return record


def _fake_module(
    monkeypatch: pytest.MonkeyPatch, name: str, file: Path
) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(file)
    monkeypatch.setitem(sys.modules, name, module)
    return module


# ---------------------------------------------------------------------------
# conda detection
# ---------------------------------------------------------------------------


def test_conda_package_is_found_by_file_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_env(tmp_path, _record("fakepkg", files=[f"{SITE}/fakepkg/core.py"]))
    _fake_module(monkeypatch, "fakepkg", tmp_path / SITE / "fakepkg" / "core.py")
    monkeypatch.setattr(sys, "prefix", str(tmp_path))

    conda = [p for p in packages_for_module("fakepkg") if p.ecosystem == "conda"]

    assert conda == [
        PackageRef(
            ecosystem="conda", name="fakepkg", version="1.0", channel="conda-forge"
        )
    ]


def test_conda_prefix_env_var_is_used_when_sys_prefix_is_not_a_conda_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    env = _write_env(tmp_path / "env", _record("fakepkg"))
    _fake_module(monkeypatch, "fakepkg", env / SITE / "fakepkg" / "__init__.py")
    monkeypatch.setattr(sys, "prefix", str(plain))
    monkeypatch.setenv("CONDA_PREFIX", str(env))

    conda = [p for p in packages_for_module("fakepkg") if p.ecosystem == "conda"]

    assert [p.name for p in conda] == ["fakepkg"]


def test_sys_prefix_wins_over_conda_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An activated env can differ from the running interpreter's own env."""
    running = _write_env(tmp_path / "running", _record("fakepkg", version="2.0"))
    activated = _write_env(tmp_path / "activated", _record("fakepkg", version="9.9"))
    _fake_module(monkeypatch, "fakepkg", running / SITE / "fakepkg" / "__init__.py")
    monkeypatch.setattr(sys, "prefix", str(running))
    monkeypatch.setenv("CONDA_PREFIX", str(activated))

    conda = [p for p in packages_for_module("fakepkg") if p.ecosystem == "conda"]

    assert [p.version for p in conda] == ["2.0"]


def test_without_a_conda_env_no_conda_entries_are_produced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    assert all(p.ecosystem != "conda" for p in packages_for_module("pydantic"))


def test_conda_package_is_found_by_normalized_name_when_the_path_misses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """conda names its packages after the pypi distribution, lowercased."""
    _write_env(tmp_path, _record("pyyaml", files=[]))
    _fake_module(monkeypatch, "yaml", tmp_path / SITE / "yaml" / "__init__.py")
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(provenance, "_dists_by_root", _fake_dists(yaml=("PyYAML",)))

    conda = [p for p in packages_for_module("yaml") if p.ecosystem == "conda"]

    assert [p.name for p in conda] == ["pyyaml"]


def test_an_import_root_claimed_by_two_packages_falls_back_to_the_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_env(
        tmp_path,
        _record("zope.interface", files=[f"{SITE}/zope/interface/__init__.py"]),
        _record("zope.event", files=[f"{SITE}/zope/event/__init__.py"]),
    )
    monkeypatch.setattr(sys, "prefix", str(tmp_path))

    index = _conda_index()

    assert f"{SITE}/zope" not in index.by_path
    assert index.by_name["zope-interface"].name == "zope.interface"


def test_a_module_outside_the_env_prefix_gets_no_conda_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An editable checkout must not be attributed to a same-named env record."""
    env = _write_env(tmp_path / "env", _record("fakepkg"))
    checkout = tmp_path / "checkout" / "fakepkg" / "__init__.py"
    _fake_module(monkeypatch, "fakepkg", checkout)
    monkeypatch.setattr(sys, "prefix", str(env))
    monkeypatch.setattr(provenance, "_dists_by_root", _fake_dists())

    assert packages_for_module("fakepkg") == ()


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (
            {
                "channel": "https://conda.anaconda.org/conda-forge/linux-64",
                "subdir": "linux-64",
            },
            "conda-forge",
        ),
        ({"channel": "conda-forge"}, "conda-forge"),
        ({"channel": "https://repo.anaconda.com/pkgs/main/linux-64"}, "linux-64"),
        (
            {"schannel": "conda-forge", "channel": "https://example.com/x"},
            "conda-forge",
        ),
        ({}, None),
    ],
)
def test_channel_normalization(record: dict[str, Any], expected: str | None) -> None:
    assert _channel(record) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (f"{SITE}/numpy/linalg/_umath.so", f"{SITE}/numpy"),
        (f"{SITE}/six.py", f"{SITE}/six"),
        (
            f"{SITE}/_cffi_backend.cpython-313-x86_64-linux-gnu.so",
            f"{SITE}/_cffi_backend",
        ),
        (f"{SITE}/numpy-2.1.0.dist-info/METADATA", None),
        ("bin/python", None),
        ("Lib/site-packages/numpy/__init__.py", "Lib/site-packages/numpy"),
    ],
)
def test_site_key_forms(path: str, expected: str | None) -> None:
    assert _site_key(path) == expected


# ---------------------------------------------------------------------------
# pypi detection and fast paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_name", ["json", "sys", "builtins", "__main__", "", None]
)
def test_modules_without_a_distribution_yield_nothing(module_name: str | None) -> None:
    assert packages_for_module(module_name) == ()


def test_pypi_detection_uses_the_distribution_name() -> None:
    """``griffe`` is imported as ``griffe`` but distributed as ``griffelib``."""
    assert packages_for_module("pydantic.fields") == (
        PackageRef(
            ecosystem="pypi",
            name="pydantic",
            version=packages_for_module("pydantic.fields")[0].version,
        ),
    )
    assert [p.name for p in packages_for_module("griffe")] == ["griffelib"]


def test_a_conda_env_yields_both_a_conda_and_a_pypi_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The headline case: a conda-forge package ships .dist-info too, so one
    environment produces a conda entry and a pypi entry for the same module."""
    _write_env(tmp_path, _record("fakepkg", version="1.0"))
    _fake_module(monkeypatch, "fakepkg", tmp_path / SITE / "fakepkg" / "__init__.py")
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(
        provenance, "_dists_by_root", lambda: {"fakepkg": ("fake-pkg",)}
    )

    refs = packages_for_module("fakepkg")

    assert [p.ecosystem for p in refs] == ["conda", "pypi"]
    assert [p.name for p in refs] == ["fakepkg", "fake-pkg"]
    assert refs[0].channel == "conda-forge"


def test_results_are_cached_and_immutable() -> None:
    first = packages_for_module("pydantic")
    assert first is packages_for_module("pydantic")
    assert isinstance(first, tuple)


# ---------------------------------------------------------------------------
# apply_provenance
# ---------------------------------------------------------------------------


def test_apply_provenance_populates_packages_and_distribution_metadata() -> None:
    metadata = NodeRequest.model_construct(artifact_type=ArtifactType.FUNCTION)

    apply_provenance(metadata, "pydantic.fields")

    assert [p.name for p in metadata.packages] == ["pydantic"]
    assert isinstance(metadata.packages, list)
    assert metadata.dependencies
    assert metadata.author_name != "unknown"


def test_apply_provenance_is_a_no_op_for_stdlib_modules() -> None:
    metadata = NodeRequest.model_construct(artifact_type=ArtifactType.FUNCTION)

    apply_provenance(metadata, "json")

    assert metadata.packages == []
    assert metadata.author_name == "unknown"


def test_apply_provenance_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_name: str) -> tuple[PackageRef, ...]:
        raise RuntimeError("provenance exploded")

    monkeypatch.setattr(provenance, "_resolve", boom)
    metadata = NodeRequest.model_construct(artifact_type=ArtifactType.FUNCTION)

    apply_provenance(metadata, "pydantic")

    assert metadata.packages == []


def test_packages_survive_the_upload_serialization_round_trip() -> None:
    request = NodeRequest.model_construct(
        artifact_type=ArtifactType.FUNCTION,
        name="x",
        category="c",
        keywords=[],
        python_import="m.x",
        source_code="def x(): pass",
        docstring="",
        inputs=[],
        outputs=[],
    )
    request.packages = [
        PackageRef(
            ecosystem="conda", name="numpy", version="2.1", channel="conda-forge"
        )
    ]

    restored = node_request_adapter.validate_python(request.model_dump())

    assert restored.packages == request.packages
