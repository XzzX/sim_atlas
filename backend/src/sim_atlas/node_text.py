"""Small text helpers shared by every node-rendering surface.

Deliberately tiny: node-rendering surfaces such as the MCP tool surface render
nodes in their own way, and only the pieces that are genuinely identical belong
here. See ADR-0019.
"""


def short_description(
    brief_description: str | None, docstring: str | None
) -> str | None:
    """The curated one-liner for a node, else the docstring's first line."""
    if brief_description:
        return brief_description
    lines = (docstring or "").splitlines()
    return lines[0] if lines else None
