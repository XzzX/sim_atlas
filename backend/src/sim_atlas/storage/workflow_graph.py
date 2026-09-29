"""Cross-references between catalog nodes, derived from the stored workflows.

``used_by`` (which workflows use a node) and port ``connections`` (which other
nodes a port is wired to) are never stored: they are computed here from the
workflows' ``uses`` and ``wf_definition`` edges and attached to a *copy* of a
node on the way out of storage, so the stored nodes are never mutated.
"""

from __future__ import annotations

from collections.abc import Mapping

from sim_atlas.models import (
    AnnotationResponse,
    ArtifactType,
    NodeMetadata,
    NodeResponse,
    Reference,
    WfFunctionNode,
)

# (node id, port label, is_output)
_PortKey = tuple[str, str, bool]


class WorkflowGraph:
    """An index of workflow usages and port wiring over one catalog snapshot.

    Build a new one whenever the catalog changes; lookups are then O(1) instead
    of a scan over every workflow per node and port.
    """

    def __init__(self, nodes: Mapping[str, NodeMetadata]) -> None:
        self._used_by: dict[str, list[Reference]] = {}
        port_counts: dict[_PortKey, dict[str, int]] = {}

        for wf in nodes.values():
            if wf.artifact_type != ArtifactType.WORKFLOW:
                continue

            usages: dict[str, int] = {}
            for use in wf.uses:
                usages[use.id] = usages.get(use.id, 0) + use.count
            for node_id, count in usages.items():
                self._used_by.setdefault(node_id, []).append(
                    Reference(
                        label=wf.name,
                        id=wf.id,
                        count=count,
                        artifact_type=wf.artifact_type,
                    )
                )

            atlas_ids = {
                n.node_id: n.atlas_id
                for n in wf.wf_definition.nodes
                if isinstance(n, WfFunctionNode) and n.atlas_id is not None
            }
            for edge in wf.wf_definition.edges:
                source = atlas_ids.get(edge.source_node)
                target = atlas_ids.get(edge.target_node)
                if source is None or target is None:
                    continue
                for own, port, is_output, other in (
                    (source, edge.source_port, True, target),
                    (target, edge.target_port, False, source),
                ):
                    if port is None or other not in nodes:
                        continue
                    counts = port_counts.setdefault((own, port, is_output), {})
                    counts[other] = counts.get(other, 0) + 1

        self._connections: dict[_PortKey, list[Reference]] = {
            key: sorted(
                (
                    Reference(
                        label=nodes[other_id].name,
                        id=other_id,
                        count=count,
                        artifact_type=nodes[other_id].artifact_type,
                    )
                    for other_id, count in counts.items()
                ),
                key=lambda r: (-r.count, r.label, r.id),
            )
            for key, counts in port_counts.items()
        }

    def used_by(self, node_id: str) -> list[Reference] | None:
        """Workflows whose ``uses`` reference *node_id*."""
        return self._used_by.get(node_id)

    def connections(
        self, node_id: str, port_label: str, is_output: bool
    ) -> list[Reference] | None:
        """Other nodes whose port is directly wired to this port."""
        return self._connections.get((node_id, port_label, is_output))

    def hydrate[N: NodeResponse](self, node: N) -> N:
        """A copy of *node* with ``used_by`` and port ``connections`` filled in."""

        def ports(
            annotations: list[AnnotationResponse], is_output: bool
        ) -> list[AnnotationResponse]:
            return [
                a.model_copy(
                    update={
                        "connections": self.connections(node.id, a.label, is_output)
                        if a.label
                        else None
                    }
                )
                for a in annotations
            ]

        return node.model_copy(
            update={
                "used_by": self.used_by(node.id),
                "inputs": ports(node.inputs, is_output=False),
                "outputs": ports(node.outputs, is_output=True),
            }
        )
