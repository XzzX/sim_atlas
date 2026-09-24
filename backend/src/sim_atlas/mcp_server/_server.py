"""The read-only MCP tool surface for CLI coding agents (ADR-0019).

Independent of ``sim_atlas.agent``: the Web IDE agent builds React Flow graphs,
this surface hands Python to an agent that already has its own model. Tool
descriptions here are prompt text — they decide whether the catalog is consulted
at all, so edit them with that in mind.
"""

from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from sim_atlas.dependencies import get_storage
from sim_atlas.mcp_server import _format
from sim_atlas.models import ArtifactType, Filter

SERVER_INSTRUCTIONS = """\
Simulation Atlas is a searchable catalog of real, installable Python functions
and flowrep workflows for scientific simulation, contributed by research groups.

Use it BEFORE writing numerical or simulation code by hand — structure loading,
unit conversions, physics kernels, post-processing, multi-step pipelines. Every
entry is an importable callable in a real Python package, with recorded
parameter datatypes, physical units and quantities. Importing a curated,
unit-annotated function beats re-deriving one.

Typical loop: search_functions("<what the code should do, in full sentences>")
-> read the `def ...` signature and `from ... import ...` line in the result
-> get_function(id) if you need the full docstring -> import it and call it in
the user's script. find_by_signature is for the mechanical case: "what consumes
a temperature in K" / "what produces a list[Atoms]".

This catalog is read-only and cannot be written to from here. It does not
install anything: the `# install:` line is a hint for the user to confirm, and
the catalog's contents are best-effort metadata, not a guarantee that a package
is present in the current environment. If two or three searches turn up nothing
relevant, stop searching and write the code yourself."""

READ_ONLY = {
    "readOnlyHint": True,
    "idempotentHint": True,
    "openWorldHint": False,
}

_KIND_TO_TYPES: dict[str, list[ArtifactType] | None] = {
    "function": [ArtifactType.FUNCTION],
    "workflow": [ArtifactType.WORKFLOW],
    "any": None,
}

_MATCH_TO_PORT_TYPE: dict[str, Literal["inputs", "outputs", "both"]] = {
    "parameter": "inputs",
    "return": "outputs",
    "any": "both",
}

mcp = FastMCP("Simulation Atlas", instructions=SERVER_INSTRUCTIONS)


@mcp.tool(annotations=READ_ONLY)
async def search_functions(
    query: Annotated[
        str,
        Field(
            description=(
                "A full-sentence description of what the code should do, in "
                "domain language. 'compute the gradient of a temperature field "
                "on an unstructured mesh' works; 'gradient' does not. Include "
                "the physical quantities, the data structures and the scientific "
                "intent — the index matches meaning and wording both, and "
                "rewards detail."
            )
        ),
    ],
    kind: Annotated[
        Literal["function", "workflow", "any"],
        Field(
            description=(
                "'function' (default) for single callables to import and call. "
                "'workflow' for complete multi-step pipelines, useful as worked "
                "examples of how the catalog's functions compose. 'any' for both."
            )
        ),
    ] = "function",
) -> str:
    """Search the Simulation Atlas for existing simulation code by natural-language intent.

    Use this FIRST, before writing any non-trivial scientific or numerical
    routine: file/structure I/O, unit and coordinate conversions, physics
    kernels, solvers, analysis and post-processing. The catalog holds real
    callables from installed research packages, annotated with parameter
    datatypes, physical units and quantities.

    Returns, per hit: the reconstructed call signature, the exact import
    statement, an install hint, the catalog id, a one-line summary, and
    per-parameter unit/quantity notes. Source code is NOT returned — import the
    function, do not copy it.

    Follow up with get_function(id) for the full docstring, or
    get_workflow_source(id) for a workflow's executable Python.
    """
    storage = get_storage()
    response = await storage.search_hybrid(
        query,
        Filter(artifact_type=_KIND_TO_TYPES[kind]),
        page=1,
        limit=_format.MAX_RESULTS,
    )
    return _format.render_results(query, response)


@mcp.tool(annotations=READ_ONLY)
async def find_by_signature(
    query: Annotated[
        str | None,
        Field(
            description=(
                "Optional full-sentence intent used to order the filtered "
                "candidates. It only ranks them — it never removes a candidate "
                "the filters below matched."
            )
        ),
    ] = None,
    datatype: Annotated[
        str | None,
        Field(
            description=(
                "Python type string exactly as annotated, e.g. 'float', "
                "'list[int]', 'numpy.ndarray'."
            )
        ),
    ] = None,
    unit: Annotated[
        str | None,
        Field(description="Physical unit, e.g. 'K', 'eV', 'angstrom'."),
    ] = None,
    quantity: Annotated[
        str | None,
        Field(description="Physical quantity, e.g. 'temperature', 'energy'."),
    ] = None,
    match: Annotated[
        Literal["parameter", "return", "any"],
        Field(
            description=(
                "'parameter' (default): the value must be accepted as an "
                "argument — use this to find what can CONSUME a value you "
                "already have. 'return': the value must be produced — use this "
                "to find what can PRODUCE a value you need. 'any': either side."
            )
        ),
    ] = "parameter",
) -> str:
    """Find catalog functions by the shape of their signature: datatype, physical unit, or quantity.

    Use this when you already hold a value and need something that takes it ("I
    have a temperature in K — what accepts it?"), or when you need to produce a
    specific value ("what returns a list[Atoms]?"). This is the mechanical,
    type-driven counterpart to search_functions' intent-driven search; reach for
    it when chaining calls in a pipeline.

    At least one of datatype, unit or quantity is required — this tool does not
    list the catalog. Use search_functions when you only have intent. Output
    format is identical to search_functions.
    """
    if not (datatype or unit or quantity):
        raise ToolError(
            "find_by_signature needs at least one of datatype, unit or quantity. "
            "Use search_functions(query=...) for intent-based discovery."
        )

    storage = get_storage()
    node_filter = Filter(
        artifact_type=[ArtifactType.FUNCTION],
        datatypes=[datatype] if datatype else None,
        units=[unit] if unit else None,
        quantities=[quantity] if quantity else None,
        port_type=_MATCH_TO_PORT_TYPE[match],
    )
    # The annotation filters are the constraint; the optional query only orders
    # what they matched, so it can never shrink the result set. Keyword ranking
    # is used even where embeddings are configured: semantic ranking silently
    # skips nodes that have no embedding yet, which would turn this tool's
    # tie-breaker back into a filter.
    response = storage.search(
        query=query,
        filter=node_filter,
        limit=_format.MAX_RESULTS,
        drop_unmatched=False,
    )
    return _format.render_results(query, response)


@mcp.tool(annotations=READ_ONLY)
async def get_function(
    id: Annotated[
        str,
        Field(
            description=(
                "The catalog id from a search result's '# id:' line. Not the "
                "function name and not the import path."
            )
        ),
    ],
) -> str:
    """Get the full catalog entry for one function or workflow: signature, import, complete docstring, and per-parameter units.

    Use after search_functions or find_by_signature when a hit looks right and
    you need the full documentation before calling it — argument meanings,
    units, defaults, related entries, and which workflows already use it.

    Accepts function and workflow ids alike. Source code is not included: import
    the function rather than copying it. For a workflow's executable Python, call
    get_workflow_source(id).
    """
    storage = get_storage()
    try:
        node = storage.read_node(id)
    except KeyError as exc:
        raise ToolError(
            f"No catalog entry with id '{id}'. Ids come from the '# id:' line of "
            "a search result — call search_functions(...) first."
        ) from exc
    return _format.render_detail(node)


@mcp.tool(annotations=READ_ONLY)
async def get_workflow_source(
    id: Annotated[
        str,
        Field(
            description=(
                "The catalog id of a workflow entry, from a search result's "
                "'# id:' line."
            )
        ),
    ],
) -> str:
    """Get the stored executable Python of a catalog workflow.

    Workflows are multi-step pipelines built from catalog functions. Read one as
    a worked example of how these functions compose — the wiring, the argument
    order, the units that line up — then adapt it, rather than guessing at a
    pipeline from individual signatures.

    Only valid for workflow ids; for a single function, get_function(id) plus the
    import line is all you need.
    """
    storage = get_storage()
    try:
        node = storage.read_node(id)
    except KeyError as exc:
        raise ToolError(
            f"No catalog entry with id '{id}'. Ids come from the '# id:' line of "
            "a search result — call search_functions(...) first."
        ) from exc
    if node.artifact_type != ArtifactType.WORKFLOW:
        raise ToolError(
            f"'{id}' is a function, not a workflow. You do not need its source — "
            f"import it and call it; use get_function('{id}') for its signature "
            "and docs."
        )
    return _format.render_source(node)


mcp_app = mcp.http_app(path="/")
