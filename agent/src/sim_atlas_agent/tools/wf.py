from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Annotated, Any, Literal, NotRequired, Union

from deepagents import DeepAgentState, create_deep_agent
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from pydantic import BaseModel, Field

# graph = {"nodes": {id: {"sim_atlas_id": str, "params": dict}},
#          "edges": [{"src","src_port","dst","dst_port"}]}
Graph = dict[str, Any]


# --------------------------------------------------------------------------
# ops
# --------------------------------------------------------------------------


class AddNode(BaseModel):
    """Create a node. Fails if node_id exists."""

    op: Literal["add_node"]
    node_id: str = Field(description="New unique id, snake_case.")
    sim_atlas_id: str = Field(
        description="The ID of the node in the SimAtlas system, exactly as returned by search/detailed_node_info."
    )
    params: dict = Field(default_factory=dict)


class RemoveNode(BaseModel):
    """Delete a node. cascade=True also drops its edges; otherwise fails if any remain."""

    op: Literal["remove_node"]
    node_id: str
    cascade: bool = False


class Connect(BaseModel):
    """Wire an output port to an input port. Port names come from detailed_node_info."""

    op: Literal["connect"]
    src: str
    src_port: str
    dst: str
    dst_port: str


class Disconnect(BaseModel):
    """Remove an existing edge."""

    op: Literal["disconnect"]
    src: str
    src_port: str
    dst: str
    dst_port: str


GraphOp = Annotated[
    AddNode | RemoveNode | Connect | Disconnect, Field(discriminator="op")
]
OP_CLASSES = (AddNode, RemoveNode, Connect, Disconnect)


# --------------------------------------------------------------------------
# op implementations: mutate in place, raise ValueError with a repair hint
# --------------------------------------------------------------------------


def _edges_of(g: Graph, node_id: str) -> list[dict]:
    return [e for e in g["edges"] if e["src"] == node_id or e["dst"] == node_id]


def _require(g: Graph, node_id: str) -> None:
    if node_id not in g["nodes"]:
        raise ValueError(f"no such node {node_id!r}. Existing: {sorted(g['nodes'])}")


def _add_node(g: Graph, node_id: str, sim_atlas_id: str, params: dict) -> None:
    if node_id in g["nodes"]:
        raise ValueError(
            f"node {node_id!r} already exists; pick another id, e.g. {node_id}_2."
        )
    g["nodes"][node_id] = {"sim_atlas_id": sim_atlas_id, "params": dict(params)}


def _remove_node(g: Graph, node_id: str, cascade: bool) -> None:
    _require(g, node_id)
    attached = _edges_of(g, node_id)
    if attached and not cascade:
        tags = [
            f"{e['src']}.{e['src_port']}->{e['dst']}.{e['dst_port']}" for e in attached
        ]
        raise ValueError(
            f"node {node_id!r} still has edges {tags}. Pass cascade=true, or rewire first."
        )
    g["edges"] = [e for e in g["edges"] if e["src"] != node_id and e["dst"] != node_id]
    del g["nodes"][node_id]


def _connect(g: Graph, src: str, src_port: str, dst: str, dst_port: str) -> None:
    _require(g, src)
    _require(g, dst)
    edge = {"src": src, "src_port": src_port, "dst": dst, "dst_port": dst_port}
    if edge in g["edges"]:
        raise ValueError(f"edge already exists: {src}.{src_port} -> {dst}.{dst_port}.")
    taken = [e for e in g["edges"] if e["dst"] == dst and e["dst_port"] == dst_port]
    if taken:
        o = taken[0]
        raise ValueError(
            f"input port {dst}.{dst_port} is already fed by {o['src']}.{o['src_port']}; "
            f"input ports take one producer. Disconnect that edge in the same batch."
        )
    g["edges"].append(edge)


def _disconnect(g: Graph, src: str, src_port: str, dst: str, dst_port: str) -> None:
    edge = {"src": src, "src_port": src_port, "dst": dst, "dst_port": dst_port}
    if edge not in g["edges"]:
        existing = [
            f"{e['src']}.{e['src_port']}->{e['dst']}.{e['dst_port']}"
            for e in g["edges"]
        ]
        raise ValueError(
            f"no such edge {src}.{src_port} -> {dst}.{dst_port}. Existing: {existing}"
        )
    g["edges"].remove(edge)


DISPATCH = {
    "add_node": _add_node,
    "remove_node": _remove_node,
    "connect": _connect,
    "disconnect": _disconnect,
}


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------
# Port *names* cannot be checked here: only the MCP server knows them. So this
# checks the invariants that hold regardless of node type.


def validate(g: Graph) -> list[str]:
    errs, seen, fed = [], set(), {}
    for e in g["edges"]:
        tag = f"{e['src']}.{e['src_port']}->{e['dst']}.{e['dst_port']}"
        for end in ("src", "dst"):
            if e[end] not in g["nodes"]:
                errs.append(f"edge {tag}: {end} node {e[end]!r} does not exist")
        if tag in seen:
            errs.append(f"duplicate edge {tag}")
        seen.add(tag)
        key = (e["dst"], e["dst_port"])
        if key in fed:
            errs.append(f"input port {key[0]}.{key[1]} has more than one producer")
        fed[key] = True

    # check for cycles: Kahn's algorithm, O(V+E)
    indeg = {n: 0 for n in g["nodes"]}
    for e in g["edges"]:
        if e["dst"] in indeg:
            indeg[e["dst"]] += 1
    queue = [n for n, d in indeg.items() if d == 0]
    seen_n = 0
    while queue:
        cur = queue.pop()
        seen_n += 1
        for e in g["edges"]:
            if e["src"] == cur and e["dst"] in indeg:
                indeg[e["dst"]] -= 1
                if indeg[e["dst"]] == 0:
                    queue.append(e["dst"])
    if seen_n < len(g["nodes"]):
        stuck = sorted(n for n, d in indeg.items() if d > 0)
        errs.append(f"cycle detected among {stuck}")
    return errs


def render(g: Graph) -> str:
    nodes = "\n".join(
        f"- {nid} ({n['sim_atlas_id']}) params={json.dumps(n['params'], sort_keys=True)}"
        for nid, n in sorted(g["nodes"].items())
    )
    edges = "\n".join(
        f"- {e['src']}.{e['src_port']} -> {e['dst']}.{e['dst_port']}"
        for e in sorted(g["edges"], key=lambda e: (e["src"], e["src_port"], e["dst"]))
    )
    return f"{len(g['nodes'])} nodes, {len(g['edges'])} edges\n\nNODES\n{nodes or '(none)'}\n\nEDGES\n{edges or '(none)'}"


# --------------------------------------------------------------------------
# transaction core: plain function, testable without a model
# --------------------------------------------------------------------------


def apply_ops_core(graph: Graph, ops: list[Any]) -> tuple[bool, Graph, str]:
    """All-or-nothing. Returns (ok, new_or_original_graph, message)."""
    g = deepcopy(graph)  # without this, a half-applied batch corrupts real state
    for i, op in enumerate(ops):
        payload = op.model_dump() if isinstance(op, BaseModel) else dict(op)
        name = payload.pop("op", None)
        fn = DISPATCH.get(name)
        if fn is None:
            return (
                False,
                graph,
                f"REJECTED, unchanged. op {i}: unknown op {name!r}; valid: {sorted(DISPATCH)}",
            )
        try:
            fn(g, **payload)
        except (TypeError, ValueError) as exc:
            return False, graph, f"REJECTED, unchanged. op {i} ({name}): {exc}"

    errs = validate(g)
    if errs:
        return (
            False,
            graph,
            "REJECTED, unchanged. Validation failed:\n"
            + "\n".join(f"- {e}" for e in errs),
        )
    return True, g, f"Applied {len(ops)} op(s).\n\n{render(g)}"


# --------------------------------------------------------------------------
# state + tools
# --------------------------------------------------------------------------


class GraphState(DeepAgentState):
    graph: Graph


@tool
def graph_view(state: Annotated[GraphState, InjectedState]) -> str:
    """The graph currently being edited: its nodes, their types and params, and all edges.
    Call this before making changes and whenever you are unsure of the current state."""
    return render(state["graph"])


@tool
def apply_ops(
    intent: str,
    ops: list[GraphOp],
    state: Annotated[GraphState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Atomically apply a batch of graph edits. Either every op succeeds or nothing changes.

    Ops run in order, so a batch may pass through a state that would not validate on
    its own (e.g. a briefly dangling edge); only the end state is checked. Put a
    disconnect and its replacement connect in the SAME call.
    On REJECTED nothing changed: read the reason, fix it, retry.

    `intent` is one line describing what this batch accomplishes.
    """
    ok, new_graph, message = apply_ops_core(state["graph"], ops)
    update: dict[str, Any] = {
        "messages": [ToolMessage(message, tool_call_id=tool_call_id)]
    }
    if ok:
        update["graph"] = new_graph
    return Command(update=update)


# --------------------------------------------------------------------------
# agent
# --------------------------------------------------------------------------
# Generated from the op classes so the prompt cannot drift from the code.


def _ops_reference() -> str:
    out = []
    for cls in OP_CLASSES:
        name = cls.model_fields["op"].annotation.__args__[0]
        req = [n for n, f in cls.model_fields.items() if n != "op" and f.is_required()]
        out.append(
            f"- {name}({', '.join(req)}): {' '.join((cls.__doc__ or '').split())}"
        )
    return "\n".join(out)
