"""Resolve which distribution a parsed object came from, and how to install it.

Everything here is best-effort (ADR-0012): each public entry point swallows
exceptions and degrades to an empty result, because provenance must never be
able to fail an upload. Results record what the *uploader's* environment
happened to contain — the absence of a conda entry does not mean a package is
unavailable on conda-forge.
"""

import importlib.metadata
import json
import logging
import os
import re
import sys
from email.utils import getaddresses
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple, cast
from urllib.parse import urlparse
from urllib.request import url2pathname

from sim_atlas_toolkit.models import ArtifactRequest, PackageRef

logger = logging.getLogger(__name__)

_NON_DISTRIBUTION_ROOTS = frozenset({"", "__main__", "builtins"})
_SITE_DIRS = frozenset({"site-packages", "dist-packages"})
_METADATA_SUFFIXES = (".dist-info", ".egg-info", ".egg-link")
_SOURCE_URL_KEYS = frozenset({"source", "code", "repository", "github"})


class _CondaPkg(NamedTuple):
    name: str
    version: str | None
    channel: str | None


class _CondaIndex(NamedTuple):
    by_path: dict[str, _CondaPkg]
    by_name: dict[str, _CondaPkg]


def _normalize(name: str) -> str:
    """PEP 503 normalisation, so ``PyYAML`` and ``pyyaml`` compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _site_key(relative_path: str) -> str | None:
    """Reduce an env-relative path to the site-packages child that owns it.

    ``lib/python3.13/site-packages/numpy/linalg/_umath.so`` and
    ``lib/python3.13/site-packages/six.py`` both collapse to one key per
    installed package. Distribution metadata directories yield ``None``.
    """
    parts = relative_path.split("/")
    for index, part in enumerate(parts[:-1]):
        if part not in _SITE_DIRS:
            continue
        child = parts[index + 1]
        if child.endswith(_METADATA_SUFFIXES):
            return None
        child = child.partition(".")[0]
        if not child:
            return None
        return "/".join([*parts[: index + 1], child])
    return None


@cache
def _env_prefix() -> Path | None:
    """The conda environment this interpreter runs in, if any.

    ``sys.prefix`` is checked first: an activated ``$CONDA_PREFIX`` can point at
    a *different* environment than the running interpreter, which would attribute
    packages to the wrong env. The variable still covers a venv layered on top of
    a conda env.
    """
    for candidate in (sys.prefix, os.environ.get("CONDA_PREFIX")):
        if not candidate:
            continue
        path = Path(candidate)
        if (path / "conda-meta").is_dir():
            return path.resolve()
    return None


def _channel(record: dict[str, Any]) -> str | None:
    """Reduce a conda record's channel to its short name (``conda-forge``)."""
    short = record.get("schannel")
    if isinstance(short, str) and short:
        return short
    raw = record.get("channel")
    if not isinstance(raw, str) or not raw:
        return None
    parts = raw.rstrip("/").split("/")
    subdir = record.get("subdir")
    if isinstance(subdir, str) and parts and parts[-1] == subdir:
        parts.pop()
    return parts[-1] if parts and parts[-1] else None


@cache
def _conda_index() -> _CondaIndex:
    """Index ``conda-meta/*.json`` once per process, by path and by name.

    A scientific environment holds hundreds of records covering hundreds of
    thousands of files, so the file lists are compressed to one key per
    site-packages child rather than kept verbatim.
    """
    prefix = _env_prefix()
    if prefix is None:
        return _CondaIndex({}, {})

    by_path: dict[str, _CondaPkg] = {}
    by_name: dict[str, _CondaPkg] = {}
    ambiguous: set[str] = set()

    for record_path in sorted((prefix / "conda-meta").glob("*.json")):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("unreadable conda record %s", record_path, exc_info=True)
            continue
        if not isinstance(record, dict):
            continue
        record_dict = cast(dict[str, Any], record)

        name = record_dict.get("name")
        if not isinstance(name, str) or not name:
            continue
        version = record_dict.get("version")
        pkg = _CondaPkg(
            name=name,
            version=version if isinstance(version, str) else None,
            channel=_channel(record_dict),
        )
        by_name.setdefault(_normalize(name), pkg)

        files = record_dict.get("files")
        if not isinstance(files, list):
            continue
        for entry in files:  # pyright: ignore[reportUnknownVariableType]
            if not isinstance(entry, str):
                continue
            key = _site_key(entry)
            if key is None:
                continue
            existing = by_path.get(key)
            if existing is None:
                by_path[key] = pkg
            elif existing.name != name:
                # Two packages claim the same import root (namespace packages).
                # Deferring to the name-based fallback beats guessing.
                ambiguous.add(key)

    for key in ambiguous:
        by_path.pop(key, None)

    return _CondaIndex(by_path, by_name)


@cache
def _dists_by_root() -> dict[str, tuple[str, ...]]:
    """Map an import root to the distribution name(s) that provide it."""
    try:
        return {
            root: tuple(dists)
            for root, dists in importlib.metadata.packages_distributions().items()
        }
    except Exception:
        logger.debug("packages_distributions() failed", exc_info=True)
        return {}


def _module_path(module_name: str) -> Path | None:
    """Locate an already-imported module without importing anything.

    The collector imported the module before any parser ran, so ``sys.modules``
    is authoritative. A spoofed ``__module__`` (``functools.wraps``, dynamically
    created classes) must degrade to ``None`` rather than trigger an import.
    """
    module = sys.modules.get(module_name)
    if module is None:
        return None
    filename = getattr(module, "__file__", None)
    if isinstance(filename, str) and filename:
        return Path(filename).resolve()
    # PEP 420 namespace package: no __file__, but __path__ has the portions.
    for entry in getattr(module, "__path__", None) or ():
        if isinstance(entry, str) and entry:
            return Path(entry).resolve()
    return None


def _dist_owns(dist_name: str, module_name: str) -> bool:
    """Whether ``dist_name`` ships the files of ``module_name``."""
    wanted = tuple(module_name.split("."))[:2]
    try:
        files = importlib.metadata.distribution(dist_name).files or []
    except Exception:
        return False
    return any(tuple(file.parts[: len(wanted)]) == wanted for file in files)


@cache
def _local_dists() -> tuple[tuple[Path, str], ...]:
    """``(project root, distribution name)`` for distributions installed from a path.

    An editable install writes no package files into its ``RECORD`` and ships no
    ``top_level.txt``, so ``packages_distributions()`` cannot see it — and an
    editable install is exactly how a researcher has their own package set up.
    ``direct_url.json`` still records where it came from, which is enough to
    attribute a module by location.
    """
    found: list[tuple[Path, str]] = []
    try:
        distributions = list(importlib.metadata.distributions())
    except Exception:
        logger.debug("cannot enumerate distributions", exc_info=True)
        return ()

    for dist in distributions:
        try:
            raw = dist.read_text("direct_url.json")
            if not raw:
                continue
            url = cast(dict[str, Any], json.loads(raw)).get("url")
            name = dist.metadata["Name"]
            if not isinstance(url, str) or not url.startswith("file://") or not name:
                continue
            root = Path(url2pathname(urlparse(url).path)).resolve()
        except Exception:
            logger.debug("unreadable direct_url for %s", dist, exc_info=True)
            continue
        found.append((root, name))

    # Longest root first, so a nested project wins over its parent.
    return tuple(sorted(found, key=lambda item: len(item[0].parts), reverse=True))


def _local_dists_for(path: Path) -> tuple[str, ...]:
    return tuple(name for root, name in _local_dists() if path.is_relative_to(root))[:1]


def _pypi_refs(module_name: str, root: str, path: Path | None) -> list[PackageRef]:
    candidates = _dists_by_root().get(root, ())
    if not candidates and path is not None:
        candidates = _local_dists_for(path)
    if len(candidates) > 1:
        owned = tuple(d for d in candidates if _dist_owns(d, module_name))
        # An extra install line is recoverable; a missing one is not.
        candidates = owned or candidates

    refs: list[PackageRef] = []
    for dist in candidates:
        version: str | None = None
        try:
            version = importlib.metadata.version(dist)
        except Exception:
            logger.debug("no version for distribution %s", dist, exc_info=True)
        refs.append(PackageRef(ecosystem="pypi", name=dist, version=version))
    return refs


def _conda_refs(
    root: str, path: Path | None, dist_names: list[str]
) -> list[PackageRef]:
    index = _conda_index()
    if not index.by_path and not index.by_name:
        return []

    prefix = _env_prefix()
    pkg: _CondaPkg | None = None

    # Primary: attribute the module's own file to the package that ships it.
    if prefix is not None and path is not None:
        if not path.is_relative_to(prefix):
            # An editable checkout or a path entry outside the environment. A
            # same-named record inside it describes different code, so attributing
            # it would be worse than saying nothing.
            return []
        key = _site_key(path.relative_to(prefix).as_posix())
        if key is not None:
            pkg = index.by_path.get(key)

    # Fallback: match on the distribution name, then the import root.
    if pkg is None:
        for name in [*dist_names, root]:
            pkg = index.by_name.get(_normalize(name))
            if pkg is not None:
                break

    if pkg is None:
        return []
    return [
        PackageRef(
            ecosystem="conda", name=pkg.name, version=pkg.version, channel=pkg.channel
        )
    ]


def _dedup(refs: list[PackageRef]) -> list[PackageRef]:
    seen: set[tuple[str, str, str | None, str | None]] = set()
    unique: list[PackageRef] = []
    for ref in refs:
        key = (ref.ecosystem, ref.name, ref.version, ref.channel)
        if key in seen:
            continue
        seen.add(key)
        unique.append(ref)
    return unique


def _resolve(module_name: str) -> tuple[PackageRef, ...]:
    root = module_name.partition(".")[0]
    if root in _NON_DISTRIBUTION_ROOTS or root in sys.stdlib_module_names:
        return ()
    path = _module_path(module_name) or _module_path(root)
    pypi = _pypi_refs(module_name, root, path)
    conda = _conda_refs(root, path, [ref.name for ref in pypi])
    return tuple(_dedup(conda + pypi))


@cache
def packages_for_module(module_name: str | None) -> tuple[PackageRef, ...]:
    """Distributions providing ``module_name``, conda entries first.

    Returns a tuple because the cache hands the same object to every caller;
    callers that store it must copy it into a list.
    """
    if not module_name:
        return ()
    try:
        return _resolve(module_name)
    except Exception:
        logger.debug("provenance lookup failed for %r", module_name, exc_info=True)
        return ()


def _first_author(core: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract the first ``(name, email)`` pair from Core Metadata.

    Packages built by modern tooling omit ``Author`` entirely and put RFC 5322
    ``Name <email>`` pairs in ``Author-email``, so copying the field verbatim
    would store the whole comma-separated list as the author's name.
    """
    raw: Any = core.get("author_email")
    entries: list[Any] = cast(list[Any], raw) if isinstance(raw, list) else [raw]
    name: str | None = None
    email: str | None = None
    addresses = [entry for entry in entries if isinstance(entry, str)]
    for parsed_name, parsed_email in getaddresses(addresses):
        name = parsed_name or None
        email = parsed_email or None
        break

    author: Any = core.get("author")
    if isinstance(author, list):
        author = cast(list[Any], author)[0] if author else None
    if isinstance(author, str) and author:
        name = author
    return name, email


def _fill_from_distribution(metadata: ArtifactRequest, dist_name: str) -> None:
    if requires := importlib.metadata.requires(dist_name):
        metadata.dependencies = requires

    core: dict[str, Any] = importlib.metadata.metadata(dist_name).json

    name, email = _first_author(core)
    if name:
        metadata.author_name = name
    if email:
        metadata.author_email = email

    raw_urls: Any = core.get("project_url") or []
    project_urls: list[Any] = (
        [raw_urls] if isinstance(raw_urls, str) else list(raw_urls)
    )
    for item in project_urls:
        if not isinstance(item, str):
            continue
        key, _, url = item.partition(",")
        match key.strip().lower():
            case "homepage":
                metadata.homepage_url = url.strip()
            case "documentation":
                metadata.documentation_url = url.strip()
            case key_lower if key_lower in _SOURCE_URL_KEYS:
                metadata.source_url = url.strip()
            case _:
                pass

    if not metadata.homepage_url and (home_page := core.get("home_page")):
        metadata.homepage_url = home_page


def apply_provenance(metadata: ArtifactRequest, module_name: str | None) -> None:
    """Populate ``packages`` plus author/URL/dependency metadata on a request.

    Call this from a parser once the module of origin is known. Never raises.
    """
    packages = packages_for_module(module_name)
    metadata.packages = list(packages)

    dist_name = next((p.name for p in packages if p.ecosystem == "pypi"), None)
    if dist_name is None:
        return
    try:
        _fill_from_distribution(metadata, dist_name)
    except Exception:
        logger.debug("distribution metadata failed for %s", dist_name, exc_info=True)
