"""Utilities for parsing and comparing canonical Python type strings.

The canonical format is produced by the toolkit's ``type_to_str`` function:
  - simple types: ``"int"``, ``"None"``
  - generics:     ``"list[int]"``, ``"dict[str, float]"``
  - unions:       ``"int | float"``, ``"int | None"``

Two public functions are provided:

``collect_datatypes(s)``
    Return the set of top-level leaf type strings suitable for use as search
    facet values.  Union members are split; generics are kept whole.

``datatype_matches(stored, filter_val)``
    Return True if *stored* and *filter_val* have a non-empty intersection
    (symmetric, unlike the edge-compatibility check which is directional).
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Type AST
# ---------------------------------------------------------------------------


@dataclass
class SimpleNode:
    name: str
    kind: str = "simple"


@dataclass
class GenericNode:
    name: str
    args: list[SimpleNode | GenericNode | UnionNode]
    kind: str = "generic"


@dataclass
class UnionNode:
    members: list[SimpleNode | GenericNode | UnionNode]
    kind: str = "union"


TypeNode = SimpleNode | GenericNode | UnionNode


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


@dataclass
class _ParseCtx:
    src: str
    pos: int = 0


def _parse_type(s: str) -> TypeNode:
    return _parse_union(_ParseCtx(src=s.strip()))


def _parse_union(ctx: _ParseCtx) -> TypeNode:
    members: list[TypeNode] = [_parse_generic(ctx)]
    while ctx.src.startswith(" | ", ctx.pos):
        ctx.pos += 3  # consume " | "
        members.append(_parse_generic(ctx))
    return members[0] if len(members) == 1 else UnionNode(members=members)


def _parse_generic(ctx: _ParseCtx) -> TypeNode:
    name = _parse_name(ctx)
    if ctx.pos >= len(ctx.src) or ctx.src[ctx.pos] != "[":
        return SimpleNode(name=name)
    ctx.pos += 1  # consume "["
    args: list[TypeNode] = [_parse_union(ctx)]
    while ctx.pos < len(ctx.src) and ctx.src[ctx.pos] == ",":
        ctx.pos += 1  # consume ","
        if ctx.pos < len(ctx.src) and ctx.src[ctx.pos] == " ":
            ctx.pos += 1  # consume optional space
        args.append(_parse_union(ctx))
    ctx.pos += 1  # consume "]"
    return GenericNode(name=name, args=args)


def _parse_name(ctx: _ParseCtx) -> str:
    start = ctx.pos
    while ctx.pos < len(ctx.src) and (
        ctx.src[ctx.pos].isalnum() or ctx.src[ctx.pos] in "_."
    ):
        ctx.pos += 1
    return ctx.src[start : ctx.pos]


# ---------------------------------------------------------------------------
# collect_datatypes — for facet generation
# ---------------------------------------------------------------------------


def _collect_leaves(node: TypeNode, out: set[str]) -> None:
    """Recursively collect top-level union members as strings.

    Generics are kept whole (their args are not further decomposed).
    """
    if isinstance(node, UnionNode):
        for m in node.members:
            _collect_leaves(m, out)
    elif isinstance(node, GenericNode):
        # Reconstruct the canonical string for the whole generic
        out.add(_node_to_str(node))
    else:
        out.add(node.name)


def _node_to_str(node: TypeNode) -> str:
    if isinstance(node, SimpleNode):
        return node.name
    if isinstance(node, GenericNode):
        args_str = ", ".join(_node_to_str(a) for a in node.args)
        return f"{node.name}[{args_str}]"
    # UnionNode
    return " | ".join(_node_to_str(m) for m in node.members)


def collect_datatypes(s: str) -> set[str]:
    """Return the set of leaf datatype strings for facet generation.

    Union members are split; generics are kept as a single entry.

    Examples::

        collect_datatypes("int | float")   == {"int", "float"}
        collect_datatypes("list[int]")     == {"list[int]"}
        collect_datatypes("int | None")    == {"int", "None"}
    """
    node = _parse_type(s)
    out: set[str] = set()
    _collect_leaves(node, out)
    return out


# ---------------------------------------------------------------------------
# datatype_matches — for filter matching (symmetric intersection)
# ---------------------------------------------------------------------------


def _intersects(a: TypeNode, b: TypeNode) -> bool:
    """Return True if type *a* and type *b* have a non-empty intersection."""
    # Union on either side: any member pair intersecting is enough
    if isinstance(a, UnionNode):
        return any(_intersects(m, b) for m in a.members)
    if isinstance(b, UnionNode):
        return any(_intersects(a, m) for m in b.members)

    # Both non-union — names must match
    a_name = a.name
    b_name = b.name
    if a_name != b_name:
        return False

    # Same name — bare generic on either side is a wildcard
    a_args = a.args if isinstance(a, GenericNode) else []
    b_args = b.args if isinstance(b, GenericNode) else []
    if not a_args or not b_args:
        return True

    # Both parameterised: same arity and all arg pairs intersect
    if len(a_args) != len(b_args):
        return False
    return all(_intersects(aa, bb) for aa, bb in zip(a_args, b_args, strict=True))


def datatype_matches(stored: str, filter_val: str) -> bool:
    """Return True if *stored* and *filter_val* have a non-empty type intersection.

    Examples::

        datatype_matches("int | float", "int")      == True
        datatype_matches("list[int]", "list")        == True   # bare wildcard
        datatype_matches("list[int]", "list[float]") == False
        datatype_matches("float", "float")           == True   # exact match
    """
    return _intersects(_parse_type(stored), _parse_type(filter_val))
