"""Utilities for comparing DataType values.

``collect_datatypes(dt)``
    Return the list of leaf DataType objects for facet generation.  Union
    members are split; generics are kept whole.  Each leaf gets its own
    pre-computed ``string`` field.

``datatype_matches(stored, filter_val)``
    Return True if *stored* and *filter_val* have a non-empty type
    intersection (symmetric, unlike the edge-compatibility check which is
    directional).

``node_to_str(node)``
    Canonical string representation of a TypeNode.  Used internally when
    building leaf DataType objects from union members.
"""

from __future__ import annotations

from .models import DataType, GenericNode, SimpleNode, UnionNode


# ---------------------------------------------------------------------------
# Canonical string rendering
# ---------------------------------------------------------------------------


def node_to_str(node: SimpleNode | GenericNode | UnionNode) -> str:
    """Return the canonical string for a TypeNode, e.g. "list[int]", "int | None"."""
    if isinstance(node, SimpleNode):
        return node.name
    if isinstance(node, GenericNode):
        return f"{node.name}[{', '.join(node_to_str(a) for a in node.args)}]"  # type: ignore[arg-type]
    return " | ".join(node_to_str(m) for m in node.members)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# collect_datatypes — for facet generation
# ---------------------------------------------------------------------------


def collect_datatypes(dt: DataType) -> list[DataType]:
    """Return leaf DataType objects for facet generation.

    Union members are split; generics are kept whole.

    Examples::

        collect_datatypes(DataType(ast=UnionNode([SimpleNode("int"), SimpleNode("float")]), ...))
            == [DataType(..., string="int"), DataType(..., string="float")]

        collect_datatypes(DataType(ast=GenericNode("list", [...]), string="list[int]"))
            == [DataType(ast=GenericNode("list", [...]), string="list[int]")]
    """
    if isinstance(dt.ast, UnionNode):
        result: list[DataType] = []
        for member in dt.ast.members:  # type: ignore[union-attr]
            leaf_str = node_to_str(member)  # type: ignore[arg-type]
            result.append(DataType(ast=member, string=leaf_str))
        return result
    return [dt]


# ---------------------------------------------------------------------------
# datatype_matches — for filter matching (symmetric intersection)
# ---------------------------------------------------------------------------


def _intersects(
    a: SimpleNode | GenericNode | UnionNode,
    b: SimpleNode | GenericNode | UnionNode,
) -> bool:
    """Return True if type *a* and type *b* have a non-empty intersection."""
    # Union on either side: any member pair intersecting is enough
    if isinstance(a, UnionNode):
        return any(_intersects(m, b) for m in a.members)  # type: ignore[arg-type]
    if isinstance(b, UnionNode):
        return any(_intersects(a, m) for m in b.members)  # type: ignore[arg-type]

    # Both non-union — names must match
    if a.name != b.name:
        return False

    # Same name — bare generic on either side is a wildcard
    a_args = a.args if isinstance(a, GenericNode) else []
    b_args = b.args if isinstance(b, GenericNode) else []
    if not a_args or not b_args:
        return True

    # Both parameterised: same arity and all arg pairs intersect
    if len(a_args) != len(b_args):
        return False
    return all(_intersects(aa, bb) for aa, bb in zip(a_args, b_args, strict=True))  # type: ignore[arg-type]


def datatype_matches(stored: DataType, filter_val: DataType) -> bool:
    """Return True if *stored* and *filter_val* have a non-empty type intersection.

    Examples::

        datatype_matches(dt("int | float"), dt("int"))         == True
        datatype_matches(dt("list[int]"),   dt("list"))        == True   # bare wildcard
        datatype_matches(dt("list[int]"),   dt("list[float]")) == False
        datatype_matches(dt("float"),       dt("float"))       == True
    """
    return _intersects(stored.ast, filter_val.ast)  # type: ignore[arg-type]
