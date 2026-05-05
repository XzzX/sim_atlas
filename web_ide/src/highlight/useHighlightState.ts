import { useMemo } from "react";
import type { Edge } from "@xyflow/react";
import type { InteractionState, HighlightState } from "./highlightTypes";

export function useHighlightState(
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
  return {
    activeEdgeIds,
    activeNodeIds,
  };
}
