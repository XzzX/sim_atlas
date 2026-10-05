"""Golden query set: end-to-end ranking quality of ``search_hybrid``.

Each case is a query a user would plausibly type and the node it must find in
the top N. The catalog mixes the shapes the legs disagree on — CamelCase and
snake_case names, aiflow-style names that are full import paths, an
unenriched node — so a change to a leg or to the fusion weights that trades
one shape for another fails here. This is what the fusion weights are tuned
against.

Embeddings come from a deterministic stand-in that maps words onto a handful
of concept dimensions, so "hot" lands near "temperature" the way a real
embedding model would put it, without any network access.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import numpy as np
import pytest

import sim_atlas.storage.file_system_storage as fss
from sim_atlas.models import NodeMetadata
from sim_atlas.storage.file_system_storage import FileSystemStorage

from .test_storage_interface import make_node, make_workflow

_CONCEPTS: list[set[str]] = [
    {"temperature", "thermal", "heat", "hot", "kelvin"},
    {"energy", "energies", "potential"},
    {"grain", "boundary", "boundaries", "interface"},
    {"crystal", "crystals", "lattice", "bulk"},
    {"molecular", "dynamics", "trajectory", "simulation"},
    {"read", "load", "parse"},
    {"write", "save", "export", "dump"},
    {"file", "disk"},
    {"mesh", "grid", "gradient", "field"},
    {"atoms", "atomic", "structure", "structures"},
    {"plot", "figure", "visualize"},
    {"add", "sum", "numbers"},
]


def _fake_vector(text: str) -> np.ndarray:
    words = re.findall(r"[a-z]+", text.lower())
    return np.array(
        [sum(word in concept for word in words) for concept in _CONCEPTS],
        dtype=np.float32,
    )


async def _fake_create_embedding(
    documents: list[str], input_type: str = "document"
) -> np.ndarray:
    return np.vstack([_fake_vector(document) for document in documents])


class _FakeSettings:
    def __init__(self, *, embeddings: bool) -> None:
        self.embeddings_enabled = embeddings


def _function(name: str, python_import: str, description: str | None) -> NodeMetadata:
    """An enriched node carries its description in every field enrichment fills."""
    return make_node(
        name=name,
        python_import=python_import,
        category=python_import.replace(".", ">"),
        brief_description=description,
        description=description,
        docstring=description,
        source_code=f"def {name.rsplit('.', 1)[-1]}(): pass",
    )


def _aiflow(python_import: str, description: str) -> NodeMetadata:
    """aiflow function nodes use the full import path as their name."""
    return _function(python_import, python_import, description)


_CATALOG: dict[str, NodeMetadata] = {
    "grain_boundary": _aiflow(
        "pyiron_nodes.atomistic.structure.BuildMgGrainBoundary",
        "Build a magnesium grain boundary structure from two tilted crystals.",
    ),
    "bulk": _aiflow(
        "pyiron_nodes.atomistic.structure.Bulk",
        "Create a bulk crystal lattice of a chemical element.",
    ),
    "adatoms": _aiflow(
        "pyiron_nodes.atomistic.structure.AddCationAdatoms",
        "Add cation adatoms onto a surface structure.",
    ),
    "add": _aiflow("pyiron_nodes.math.Add", "Add two numbers."),
    "calc_md": _aiflow(
        "pyiron_nodes.atomistic.calculator.CalcMD",
        "Run a molecular dynamics simulation at a fixed temperature.",
    ),
    "calc_static": _aiflow(
        "pyiron_nodes.atomistic.calculator.CalcStatic",
        "Compute the static potential energy of an atomic structure.",
    ),
    "temperature": _function(
        "get_temperature",
        "ase.md.get_temperature",
        "Instantaneous temperature of atoms from their kinetic energy.",
    ),
    "potential_energy": _function(
        "get_potential_energy",
        "ase.calculators.get_potential_energy",
        "Potential energy of atoms.",
    ),
    "read": _function(
        "read_structure", "ase.io.read_structure", "Load atoms from a file on disk."
    ),
    "write": _function(
        "write_structure", "ase.io.write_structure", "Save atoms to a file on disk."
    ),
    "gradient": _function(
        "gradient_on_mesh",
        "mylib.mesh.gradient_on_mesh",
        "Gradient of a scalar field on an unstructured mesh.",
    ),
    "plot": _function(
        "plot_energy_curve",
        "mylib.plot.plot_energy_curve",
        "Plot an energy curve as a figure.",
    ),
    # Never enriched: no description, so no embedding either.
    "unenriched": _function("anneal_sample", "lab.thermal.anneal_sample", None),
    "workflow": make_workflow(name="temperature_pipeline"),
}

# (query, catalog key that must appear, within the top N, needs embeddings)
_CASES: list[tuple[str, str, int, bool]] = [
    # CamelCase names
    ("BuildMgGrainBoundary", "grain_boundary", 1, False),
    ("grain", "grain_boundary", 1, False),
    ("GrainBound", "grain_boundary", 1, False),
    ("CalcMD", "calc_md", 1, False),
    ("md", "calc_md", 1, False),
    ("add", "add", 1, False),
    ("AddCation", "adatoms", 1, False),
    # snake_case names
    ("get_temperature", "temperature", 1, False),
    ("temperature", "temperature", 2, False),
    ("temp", "temperature", 2, False),
    ("read_structure", "read", 1, False),
    # typos
    ("temprature", "temperature", 1, False),
    ("potential enrgy", "potential_energy", 1, False),
    # exact import path
    ("ase.io.read_structure", "read", 1, False),
    ("pyiron_nodes.math", "add", 1, False),
    # multi-word prose
    ("compute the gradient of a temperature field on a mesh", "gradient", 1, False),
    ("plot the energy", "plot", 1, False),
    ("load atoms from a file", "read", 3, False),
    ("how hot are the atoms", "temperature", 3, True),
    ("crystal lattice", "bulk", 1, False),
    # unenriched node: only the lexical legs can reach it
    ("anneal", "unenriched", 1, False),
    ("thermal anneal", "unenriched", 1, False),
    # workflows have no import path
    ("temperature_pipeline", "workflow", 1, False),
]


def _storage(monkeypatch: pytest.MonkeyPatch, *, embeddings: bool) -> FileSystemStorage:
    monkeypatch.setattr(
        fss, "load_settings", lambda: _FakeSettings(embeddings=embeddings)
    )
    monkeypatch.setattr(fss, "create_embedding", _fake_create_embedding)
    storage = FileSystemStorage(path=None)
    for node in _CATALOG.values():
        storage.create_node(node.model_copy(deep=True))
    if embeddings:
        asyncio.run(storage.enrich())
    return storage


def _top(storage: FileSystemStorage, query: str, n: int) -> list[str]:
    key_by_id = {node.id: key for key, node in _CATALOG.items()}
    response = asyncio.run(storage.search_hybrid(query, limit=n))
    return [key_by_id[item.node.id] for item in response.results.data]


def _params(*, embeddings: bool) -> list[Any]:
    return [
        pytest.param(query, expected, n, id=query)
        for query, expected, n, needs_embeddings in _CASES
        if embeddings or not needs_embeddings
    ]


@pytest.mark.parametrize(("query", "expected", "n"), _params(embeddings=True))
def test_hybrid_with_embeddings(
    monkeypatch: pytest.MonkeyPatch, query: str, expected: str, n: int
) -> None:
    storage = _storage(monkeypatch, embeddings=True)
    assert expected in _top(storage, query, n)


@pytest.mark.parametrize(("query", "expected", "n"), _params(embeddings=False))
def test_hybrid_without_embeddings(
    monkeypatch: pytest.MonkeyPatch, query: str, expected: str, n: int
) -> None:
    storage = _storage(monkeypatch, embeddings=False)
    assert expected in _top(storage, query, n)


def test_the_unenriched_node_has_no_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guards the premise of the unenriched cases above."""
    storage = _storage(monkeypatch, embeddings=True)
    assert storage.read_node(_CATALOG["unenriched"].id).embedding is None
    assert storage.read_node(_CATALOG["temperature"].id).embedding is not None
