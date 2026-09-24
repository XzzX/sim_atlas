"""Small text helpers shared by every node-rendering surface.

Deliberately tiny: the Web IDE agent and the MCP tool surface render nodes
very differently (port listings versus Python signatures), and only the pieces
that are genuinely identical belong here. See ADR-0019.
"""


def short_description(
    brief_description: str | None, docstring: str | None
) -> str | None:
    """The curated one-liner for a node, else the docstring's first line."""
    if brief_description:
        return brief_description
    lines = (docstring or "").splitlines()
    return lines[0] if lines else None
