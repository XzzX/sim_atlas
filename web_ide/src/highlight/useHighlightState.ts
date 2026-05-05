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
  const activeEdgeIds = useMemo<Set<string> | null>(() => {
    if (interaction.mode !== "node-hover") return null;
    const { nodeId } = interaction;
    const ids = new Set<string>();
    for (const edge of edges) {
      if (edge.source === nodeId || edge.target === nodeId) {
        ids.add(edge.id);
      }
    }
    return ids;
  }, [edges, interaction]);
  const activeNodeIds = useMemo<Set<string> | null>(() => {
    if (interaction.mode !== "node-hover") return null;
    return new Set([interaction.nodeId]);
  }, [interaction]);
  const handleCompatibility = useMemo<Map<string, CompatibilityResult>>(() => {
    const map = new Map<string, CompatibilityResult>();
    if (interaction.mode !== "dragging") return map;
    const { fromNodeId, fromAnnotation, fromHandleType } = interaction;
    for (const node of nodes) {
      if (node.type !== "FunctionNode") continue;
      const fn = node as FunctionNodeType;
      const isSelf = node.id === fromNodeId;
      // dragging from a source (output) → highlight target (input) handles, and vice versa
      // self-connections (cycles) are never valid → mark them red
      if (fromHandleType === "source") {
        fn.data.metadata.inputs.forEach((ann, i) => {
          map.set(
            `${node.id}::${ann.label ?? i.toString()}`,
            isSelf ? "type-mismatch" : checkCompatibility(fromAnnotation, ann),
          );
        });
      } else {
        fn.data.metadata.outputs.forEach((ann, i) => {
          map.set(
            `${node.id}::${ann.label ?? i.toString()}`,
            isSelf ? "type-mismatch" : checkCompatibility(fromAnnotation, ann),
          );
        });
      }
    }
    return map;
  }, [nodes, interaction]);

  return {
    activeEdgeIds,
    activeNodeIds,
    handleCompatibility,
  };
}
