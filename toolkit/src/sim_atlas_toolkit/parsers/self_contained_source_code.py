"""Extract a function from a package as a self-contained snippet.

    from extract_function import extract

    res = extract(my_func)          # or extract("mypkg.core:summarise")

    res.same_file                   # {name: {names defined in the same module}}
    res.unresolved                  # {name: {names that resolve to nothing}}
    res.code                        # the standalone snippet
    print(res.summary())

Every free name the function uses is resolved against the module it lives in:
  * bound by a module-level import  -> the minimal import line is emitted
  * bound by a module-level def/class/assignment -> that source is pulled in
    too, recursively (helpers of helpers included)
  * a builtin -> ignored
  * anything else -> collected in `unresolved`
"""

from __future__ import annotations

import ast
import builtins
import importlib
import importlib.util
import inspect
import os
import symtable
from dataclasses import dataclass, field
from typing import cast

__all__ = ["extract", "Extraction", "ExtractionError", "free_names"]

BUILTIN_NAMES = set(dir(builtins)) | {"__name__", "__file__", "__doc__", "__package__"}
DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


class ExtractionError(Exception):
    """Raised when the target can't be located or has no readable source."""


# --------------------------------------------------------------------------- #
# free-name analysis
# --------------------------------------------------------------------------- #


def free_names(node: ast.AST) -> set[str]:
    """Names a top-level def/class/assignment needs from its enclosing module.

    Uses symtable rather than a raw AST walk so that parameters, walrus targets,
    comprehension variables, nested functions and `global`/`nonlocal` are all
    scoped correctly.
    """
    src = ast.unparse(node)
    top = symtable.symtable(src, "<extract>", "exec")
    names: set[str] = set()
    _collect(top, names, is_top=True)
    if isinstance(node, DEF_NODES):
        names.discard(node.name)
    return names


def _collect(table: symtable.SymbolTable, acc: set[str], is_top: bool = False) -> None:
    for sym in table.get_symbols():
        if not sym.is_referenced():
            continue
        if is_top:
            # In the synthetic top-level table, decorators / default values /
            # annotations show up as referenced-but-not-assigned names.
            if not sym.is_assigned():
                acc.add(sym.get_name())
        elif sym.is_global():
            acc.add(sym.get_name())
    for child in table.get_children():
        _collect(child, acc)


# --------------------------------------------------------------------------- #
# module-level bindings
# --------------------------------------------------------------------------- #


@dataclass
class Binding:
    kind: str  # "import" | "def" | "assign"
    name: str
    text: str
    node: ast.AST | None = None


def _target_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [n for elt in target.elts for n in _target_names(elt)]
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    return []


def _render_import(
    stmt: ast.Import | ast.ImportFrom, alias: ast.alias, package: str | None
) -> str:
    if isinstance(stmt, ast.Import):
        if alias.asname:
            return f"import {alias.name} as {alias.asname}"
        return f"import {alias.name}"

    module = stmt.module or ""
    if stmt.level:
        if package:
            try:
                module = importlib.util.resolve_name("." * stmt.level + module, package)
            except (ImportError, ValueError):
                module = "." * stmt.level + module
        else:
            module = "." * stmt.level + module
    piece = alias.name if not alias.asname else f"{alias.name} as {alias.asname}"
    return f"from {module} import {piece}"


class ModuleIndex:
    """Everything bound at module level in one source file."""

    def __init__(self, source: str, filename: str, package: str | None) -> None:
        self.lines = source.splitlines()
        self.tree = ast.parse(source, filename=filename)
        self.package = package
        self.bindings: dict[str, Binding] = {}
        self.future: list[str] = []
        self.star_imports = any(
            isinstance(s, ast.ImportFrom) and any(a.name == "*" for a in s.names)
            for s in ast.walk(self.tree)
        )
        self._scan(self.tree.body)

    def source_of(self, node: ast.stmt) -> str:
        """Original source for a node, decorators included, comments preserved."""
        start = min(
            [node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])]
        )
        return "\n".join(self.lines[start - 1 : node.end_lineno])

    def _scan(self, body: list[ast.stmt]) -> None:
        for stmt in body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    name = alias.asname or alias.name.split(".")[0]
                    self.bindings[name] = Binding(
                        "import", name, _render_import(stmt, alias, self.package)
                    )
            elif isinstance(stmt, ast.ImportFrom):
                if stmt.module == "__future__":
                    self.future += [
                        f"from __future__ import {a.name}" for a in stmt.names
                    ]
                    continue
                for alias in stmt.names:
                    if alias.name == "*":
                        continue  # can't be narrowed; flagged via star_imports
                    name = alias.asname or alias.name
                    self.bindings[name] = Binding(
                        "import", name, _render_import(stmt, alias, self.package)
                    )
            elif isinstance(stmt, DEF_NODES):
                self.bindings[stmt.name] = Binding(
                    "def", stmt.name, self.source_of(stmt), stmt
                )
            elif isinstance(stmt, ast.Assign):
                text = self.source_of(stmt)
                for t in stmt.targets:
                    for n in _target_names(t):
                        self.bindings[n] = Binding("assign", n, text, stmt)
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                self.bindings[stmt.target.id] = Binding(
                    "assign", stmt.target.id, self.source_of(stmt), stmt
                )
            elif isinstance(stmt, ast.If):
                self._scan(stmt.body)  # `if TYPE_CHECKING:`, version guards
                self._scan(stmt.orelse)
            elif isinstance(stmt, ast.Try):
                self._scan(stmt.body)  # try: import ujson / except: import json
                for handler in stmt.handlers:
                    self._scan(handler.body)
                self._scan(stmt.orelse)


# --------------------------------------------------------------------------- #
# result
# --------------------------------------------------------------------------- #


def _tidy_imports(lines: list[str]) -> list[str]:
    """Merge `from X import a` + `from X import b`, then sort."""
    plain: set[str] = set()
    grouped: dict[str, set[str]] = {}
    for line in dict.fromkeys(lines):
        if line.startswith("from "):
            module, _, names = line[5:].partition(" import ")
            grouped.setdefault(module, set()).add(names)
        else:
            plain.add(line)
    return sorted(plain) + [
        f"from {mod} import {', '.join(sorted(names))}"
        for mod, names in sorted(grouped.items())
    ]


@dataclass
class Extraction:
    target: str
    module: str
    code: str
    imports: list[str] = field(default_factory=list[str])
    future: list[str] = field(default_factory=list[str])
    definitions: list[str] = field(default_factory=list[str])
    same_file: dict[str, set[str]] = field(default_factory=dict[str, set[str]])
    unresolved: dict[str, set[str]] = field(default_factory=dict[str, set[str]])
    star_imports: bool = False

    @property
    def complete(self) -> bool:
        """True when every name was accounted for."""
        return not self.unresolved and not self.star_imports

    @property
    def direct_same_file(self) -> set[str]:
        """Same-file names the target itself uses (not those of its helpers)."""
        return self.same_file.get(self.target, set())

    def summary(self) -> str:
        out: list[str] = []
        if self.direct_same_file:
            out.append(
                f"{self.target} references in the same file: "
                + ", ".join(sorted(self.direct_same_file))
            )
            for other, deps in self.same_file.items():
                if other != self.target:
                    out.append(f"  {other} -> " + ", ".join(sorted(deps)))
        else:
            out.append(f"{self.target} references nothing else defined in its module")
        out.append(
            f"{len(self.imports)} import line(s), "
            f"{len(self.definitions)} definition(s) pulled in"
        )
        for owner, names in self.unresolved.items():
            out.append(f"UNRESOLVED in {owner}: " + ", ".join(sorted(names)))
        if self.star_imports:
            out.append(
                f"WARNING: {self.module} uses `import *`; "
                "some names may be unaccounted for"
            )
        return "\n".join(out)

    def write(self, path: str | os.PathLike[str]) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.code)

    def __str__(self) -> str:
        return self.code


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #


def _resolve_target(target: object) -> tuple[str, str]:
    if callable(target) and hasattr(target, "__name__"):
        mod = getattr(target, "__module__", None)
        if not mod:
            raise ExtractionError(f"{target!r} has no __module__")
        return mod, target.__name__
    if isinstance(target, tuple) and len(target) == 2:  # pyright: ignore[reportUnknownArgumentType] -- bare `tuple` isinstance narrowing can't carry element types  # noqa: PLR2004
        mod, name = cast(tuple[object, str], target)
        return (mod.__name__ if inspect.ismodule(mod) else str(mod)), name
    if isinstance(target, str):
        if ":" in target:
            mod, name = target.rsplit(":", 1)
        elif "." in target:
            mod, name = target.rsplit(".", 1)
        else:
            raise ExtractionError(
                "string target must look like 'package.module:function'"
            )
        return mod, name
    raise ExtractionError(f"don't know how to interpret target {target!r}")


def extract(target: object, *, recursive: bool = True) -> Extraction:
    """Pull `target` out of its module as standalone source.

    `target` may be the function object itself, a "package.module:name" string,
    or a (module, name) pair. With recursive=False the same-file helpers are
    reported but not inlined.
    """
    module_name, func_name = _resolve_target(target)

    mod = importlib.import_module(module_name)
    filename = getattr(mod, "__file__", None)
    if not filename:
        raise ExtractionError(
            f"{module_name} has no source file (builtin, frozen or namespace package)"
        )
    with open(filename, encoding="utf-8") as fh:
        source = fh.read()

    index = ModuleIndex(source, filename, getattr(mod, "__package__", None))
    if func_name not in index.bindings:
        raise ExtractionError(
            f"{func_name!r} is not defined at module level in {module_name} "
            "(methods and dynamically created functions aren't supported)"
        )

    imports: list[str] = []
    defs: list[Binding] = []
    same_file: dict[str, set[str]] = {}
    unresolved: dict[str, set[str]] = {}
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(name: str) -> None:
        if name in done or name in visiting:  # mutual recursion between helpers
            return
        visiting.add(name)
        binding = index.bindings[name]

        if binding.kind == "import":
            imports.append(binding.text)
        else:
            local: list[str] = []
            imported: list[str] = []
            missing: set[str] = set()
            for dep in sorted(free_names(cast(ast.AST, binding.node))):
                if dep in BUILTIN_NAMES:
                    continue
                if dep not in index.bindings:
                    missing.add(dep)
                elif index.bindings[dep].kind == "import":
                    imported.append(dep)
                else:
                    local.append(dep)
            if local:
                same_file[name] = set(local)
            if missing:
                unresolved[name] = missing
            for dep in imported:
                visit(dep)
            if recursive:
                for dep in local:
                    visit(dep)
            defs.append(binding)  # post-order: dependencies first

        visiting.discard(name)
        done.add(name)

    visit(func_name)

    tidy = _tidy_imports(imports)
    future = list(dict.fromkeys(index.future))
    chunks = [c for c in ("\n".join(future), "\n".join(tidy)) if c]
    chunks += [b.text for b in defs]
    code = "\n\n\n".join(chunks).rstrip() + "\n"

    return Extraction(
        target=func_name,
        module=module_name,
        code=code,
        imports=tidy,
        future=future,
        definitions=[b.name for b in defs],
        same_file=same_file,
        unresolved=unresolved,
        star_imports=index.star_imports,
    )
