import { useMemo } from "react";
import type { Edge } from "@xyflow/react";
import type { WorkflowNode } from "@/nodes/nodes";
import type { FunctionNodeType } from "@/nodes/FunctionNode";
import type { InteractionState, HighlightState } from "./highlightTypes";
import {
  checkCompatibility,
  type CompatibilityResult,
} from "./typeCompatibility";

export function useHighlightState(
  nodes: WorkflowNode[],
  edges: Edge[],
  interaction: InteractionState,
): HighlightState {
  // Build node lookup map for fast access
  const nodeMap = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  // Always-on: resolve each edge's compatibility
  const edgeCompatibility = useMemo(() => {
    const map = new Map<string, CompatibilityResult>();
    for (const edge of edges) {
      const srcNode = nodeMap.get(edge.source);
      const tgtNode = nodeMap.get(edge.target);
      let srcAnnotation = null;
      let tgtAnnotation = null;
      if (srcNode?.type === "FunctionNode") {
        const fn = srcNode as FunctionNodeType;
        srcAnnotation =
          fn.data.metadata.outputs.find(
            (p, i) => (p.label ?? i.toString()) === edge.sourceHandle,
          ) ?? null;
      }
      if (tgtNode?.type === "FunctionNode") {
        const fn = tgtNode as FunctionNodeType;
        tgtAnnotation =
          fn.data.metadata.inputs.find(
            (p, i) => (p.label ?? i.toString()) === edge.targetHandle,
          ) ?? null;
      }
      map.set(edge.id, checkCompatibility(srcAnnotation, tgtAnnotation));
    }
    return map;
  }, [edges, nodeMap]);

  // Stub values — slice 5 will replace activeNodeIds with real logic
  const activeEdgeIds = useMemo<Set<string> | null>(() => {
    if (interaction.mode !== "handle-hover") return null;
    const { nodeId, handleId } = interaction;
    const ids = new Set<string>();
    for (const edge of edges) {
      if (
        (edge.source === nodeId && edge.sourceHandle === handleId) ||
        (edge.target === nodeId && edge.targetHandle === handleId)
      ) {
        ids.add(edge.id);
      }
    }
    return ids;
  }, [edges, interaction]);
  const activeNodeIds = useMemo<Set<string> | null>(
    () => null,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [nodes, interaction],
  );
  const handleCompatibility = useMemo<Map<string, CompatibilityResult>>(() => {
    const map = new Map<string, CompatibilityResult>();
    if (interaction.mode !== "dragging") return map;
    const { fromNodeId, fromAnnotation } = interaction;
    for (const node of nodes) {
      if (node.id === fromNodeId) continue;
      if (node.type !== "FunctionNode") continue;
      const fn = node as FunctionNodeType;
      fn.data.metadata.inputs.forEach((ann, i) => {
        map.set(`${node.id}::${ann.label ?? i.toString()}`, checkCompatibility(fromAnnotation, ann));
      });
      fn.data.metadata.outputs.forEach((ann, i) => {
        map.set(`${node.id}::${ann.label ?? i.toString()}`, checkCompatibility(fromAnnotation, ann));
      });
    }
    return map;
  }, [nodes, interaction]);

  return {
    edgeCompatibility,
    activeEdgeIds,
    activeNodeIds,
    handleCompatibility,
  };
}
