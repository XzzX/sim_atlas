from sim_atlas.agent.tools import get_tool_prompt_guidance_lines
from sim_atlas.models import AgentRequest, Annotation, GraphNodeContext
from sim_atlas.storage_interface import StorageInterface


def _port_str(a: Annotation) -> str:
    s = f"{a.label}:{a.datatype or '?'}"
    if a.unit:
        s += f"[{a.unit}]"
    if a.quantity:
        s += f"({a.quantity})"
    if a.description:
        s += f" — {a.description}"
    return s


def _node_to_context(node: GraphNodeContext) -> str:
    inputs = ", ".join(_port_str(a) for a in node.inputs)
    outputs = ", ".join(_port_str(a) for a in node.outputs)
    desc = f" - {node.short_description}" if node.short_description else ""
    atlas = f" (atlas_id={node.atlas_node_id})" if node.node_kind == "function" else ""
    return f"  [{node.node_kind}:{node.graph_id}] {node.name}{atlas}{desc}\n    in: {inputs}\n    out: {outputs}"


def build_system_prompt(request: AgentRequest, storage: StorageInterface) -> str:
    node_lines = "\n".join(_node_to_context(n) for n in request.nodes)
    edge_lines = "\n".join(
        f"  {e.source_graph_id}/{e.source_handle} -> {e.target_graph_id}/{e.target_handle}"
        for e in request.edges
    )
    opts = storage.get_filter_options()
    filter_section = (
        "## Available filter values\n"
        "Use only values from these lists when supplying filter arguments to "
        "find_compatible_nodes.\n"
        f"datatypes: {', '.join(sorted(opts.datatypes)) or '(none)'}\n"
        f"units: {', '.join(sorted(opts.units)) or '(none)'}\n"
        f"quantities: {', '.join(sorted(opts.quantities)) or '(none)'}"
    )
    tool_guidance = "\n".join(f"- {line}" for line in get_tool_prompt_guidance_lines())

    return f"""You are an expert workflow builder for scientific simulation pipelines.
You have access to a catalog of simulation nodes (functions) that can be searched and connected.

## Current graph

### Nodes
{node_lines or "  (empty)"}

### Edges
{edge_lines or "  (none)"}

## Your role
You are an editor of an existing workflow graph.
Treat the current graph as intentional work that should be preserved unless change is necessary.
Make the minimum changes needed to satisfy the user's request.
Prefer adding new nodes and edges over modifying or removing existing ones.
Only remove or rewire existing nodes when the user explicitly asks, or when it is genuinely necessary to produce a correct result.

## Tools
- If you face doubts, hard to solve problems, inconsistencies, or multiple options, ask the user a clarification question in plain text instead of guessing.
{tool_guidance}
- When you are finished, respond with a concise summary of only the changes you made.

{filter_section}
"""
