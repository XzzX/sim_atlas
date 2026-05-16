import json
import re
from typing import Any

from ..models import Annotation, GraphEdgeContext, GraphNodeContext
from ..storage_interface import StorageInterface


def _slugify(text: str) -> str:
    """Convert a label into a filesystem-safe, LLM-readable id slug."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_") or "node"


class ScratchGraph:
    def __init__(
        self, nodes: list[GraphNodeContext], edges: list[GraphEdgeContext]
    ) -> None:
        self.nodes: dict[str, GraphNodeContext] = {n.graph_id: n for n in nodes}
        self.edges: list[GraphEdgeContext] = list(edges)

    def new_graph_id(self, label: str) -> str:
        """Return a unique, human-readable id derived from *label*."""
        base = _slugify(label)
        if base not in self.nodes:
            return base
        i = 2
        while f"{base}_{i}" in self.nodes:
            i += 1
        return f"{base}_{i}"


def _handle_add_node(
    tool_name: str,
    tool_args: dict[str, Any],
    storage: StorageInterface,
    scratch: ScratchGraph,
) -> str:
    if tool_name == "add_function_node":
        atlas_node_id: str = tool_args["atlas_node_id"]
        label: str = tool_args["label"]
        if not storage.exists(atlas_node_id):
            return json.dumps(
                {"error": f"Node '{atlas_node_id}' not found in catalog."}
            )
        node = storage.read(atlas_node_id)
        graph_id = scratch.new_graph_id(label)
        scratch.nodes[graph_id] = GraphNodeContext(
            graph_id=graph_id,
            node_kind="function",
            atlas_node_id=atlas_node_id,
            name=label,
            short_description=node.ai_summary or node.docstring.splitlines()[0]
            if node.docstring
            else None,
            inputs=node.inputs,
            outputs=node.outputs,
        )
        return json.dumps(
            {
                "graph_id": graph_id,
                "inputs": [a.model_dump(exclude_none=True) for a in node.inputs],
                "outputs": [a.model_dump(exclude_none=True) for a in node.outputs],
            }
        )

    if tool_name == "add_input_node":
        label_in: str = tool_args["label"]
        graph_id = scratch.new_graph_id(label_in)
        scratch.nodes[graph_id] = GraphNodeContext(
            graph_id=graph_id,
            node_kind="input",
            atlas_node_id=None,
            name=label_in,
            inputs=[],
            outputs=[Annotation(label="output")],
        )
        return json.dumps({"graph_id": graph_id})

    # add_output_node
    label_out: str = tool_args["label"]
    graph_id = scratch.new_graph_id(label_out)
    scratch.nodes[graph_id] = GraphNodeContext(
        graph_id=graph_id,
        node_kind="output",
        atlas_node_id=None,
        name=label_out,
        inputs=[Annotation(label="input")],
        outputs=[],
    )
    return json.dumps({"graph_id": graph_id})


def _handle_remove_edge(tool_args: dict[str, Any], scratch: ScratchGraph) -> str:
    src: str = tool_args["source_graph_id"]
    src_h: str = tool_args["source_handle"]
    tgt: str = tool_args["target_graph_id"]
    tgt_h: str = tool_args["target_handle"]
    before = len(scratch.edges)
    scratch.edges = [
        e
        for e in scratch.edges
        if not (
            e.source_graph_id == src
            and e.source_handle == src_h
            and e.target_graph_id == tgt
            and e.target_handle == tgt_h
        )
    ]
    if len(scratch.edges) == before:
        return json.dumps(
            {"error": f"No edge found from '{src}/{src_h}' to '{tgt}/{tgt_h}'."}
        )
    return json.dumps({"ok": True})


def _handle_graph_ops(
    tool_name: str, tool_args: dict[str, Any], scratch: ScratchGraph
) -> str:
    if tool_name == "add_edge":
        source_graph_id: str = tool_args["source_graph_id"]
        source_handle: str = tool_args["source_handle"]
        target_graph_id: str = tool_args["target_graph_id"]
        target_handle: str = tool_args["target_handle"]
        if source_graph_id not in scratch.nodes:
            return json.dumps(
                {"error": f"Source node '{source_graph_id}' not in graph."}
            )
        if target_graph_id not in scratch.nodes:
            return json.dumps(
                {"error": f"Target node '{target_graph_id}' not in graph."}
            )
        scratch.edges.append(
            GraphEdgeContext(
                source_graph_id=source_graph_id,
                source_handle=source_handle,
                target_graph_id=target_graph_id,
                target_handle=target_handle,
            )
        )
        return json.dumps({"ok": True})

    if tool_name == "remove_edge":
        return _handle_remove_edge(tool_args, scratch)

    # remove_node
    graph_id_to_remove: str = tool_args["graph_id"]
    if graph_id_to_remove not in scratch.nodes:
        return json.dumps({"error": f"Node '{graph_id_to_remove}' not in graph."})
    del scratch.nodes[graph_id_to_remove]
    scratch.edges = [
        e
        for e in scratch.edges
        if graph_id_to_remove not in {e.source_graph_id, e.target_graph_id}
    ]
    return json.dumps({"ok": True})


_ADD_NODE_TOOLS = {"add_function_node", "add_input_node", "add_output_node"}


def execute_graph_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    storage: StorageInterface,
    scratch: ScratchGraph,
) -> str:
    if tool_name in _ADD_NODE_TOOLS:
        return _handle_add_node(tool_name, tool_args, storage, scratch)
    return _handle_graph_ops(tool_name, tool_args, scratch)


def _validate_io_node(
    gid: str,
    node: GraphNodeContext,
    output_labels: dict[str, set[str]],
    input_labels: dict[str, set[str]],
) -> list[str]:
    """Check structural constraints for input/output nodes."""
    errors: list[str] = []
    if node.node_kind == "input" and output_labels[gid] != {"output"}:
        errors.append(
            f"Input node '{gid}' must have exactly one output port named "
            f"'output', but has: {sorted(output_labels[gid])}."
        )
    elif node.node_kind == "output" and input_labels[gid] != {"input"}:
        errors.append(
            f"Output node '{gid}' must have exactly one input port named "
            f"'input', but has: {sorted(input_labels[gid])}."
        )
    return errors


def validate_graph(scratch: ScratchGraph, storage: StorageInterface) -> list[str]:
    """Return a list of validation error strings (empty means valid)."""
    errors: list[str] = []

    # Build port-label lookup sets for every node in the graph.
    output_labels: dict[str, set[str]] = {}
    input_labels: dict[str, set[str]] = {}
    for gid, node in scratch.nodes.items():
        output_labels[gid] = {a.label for a in node.outputs if a.label is not None}
        input_labels[gid] = {a.label for a in node.inputs if a.label is not None}

    # Check every catalog-backed node exists in storage.
    # Also verify that input/output nodes have the correct port structure.
    for gid, node in scratch.nodes.items():
        if node.node_kind == "function":
            if node.atlas_node_id is None or not storage.exists(node.atlas_node_id):
                errors.append(
                    f"Node '{gid}' references atlas_node_id '{node.atlas_node_id}' "
                    "which no longer exists in the catalog."
                )
        else:
            errors.extend(_validate_io_node(gid, node, output_labels, input_labels))

    # Check every edge references real nodes and real ports.
    for edge in scratch.edges:
        src = edge.source_graph_id
        tgt = edge.target_graph_id

        if src not in scratch.nodes:
            errors.append(
                f"Edge references source node '{src}' which is not in the graph."
            )
        else:
            available = sorted(output_labels[src])
            if edge.source_handle not in output_labels[src]:
                errors.append(
                    f"Edge source handle '{edge.source_handle}' does not exist on "
                    f"node '{src}'. Available output ports: {available}."
                )

        if tgt not in scratch.nodes:
            errors.append(
                f"Edge references target node '{tgt}' which is not in the graph."
            )
        else:
            available_in = sorted(input_labels[tgt])
            if edge.target_handle not in input_labels[tgt]:
                errors.append(
                    f"Edge target handle '{edge.target_handle}' does not exist on "
                    f"node '{tgt}'. Available input ports: {available_in}."
                )

    return errors
