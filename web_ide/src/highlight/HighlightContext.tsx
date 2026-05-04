import { useState, type ReactNode } from "react";
import type { Edge } from "@xyflow/react";
import type { WorkflowNode } from "@/nodes/nodes";
import { useHighlightState } from "./useHighlightState";
import {
  HighlightContext,
  type InteractionState,
} from "./highlightTypes";

export function HighlightProvider({
  children,
  nodes,
  edges,
}: {
  children: ReactNode;
  nodes: WorkflowNode[];
  edges: Edge[];
}) {
  const [interaction, setInteraction] = useState<InteractionState>({
    mode: "idle",
  });
  const highlightState = useHighlightState(nodes, edges, interaction);
  return (
    <HighlightContext.Provider value={{ interaction, setInteraction, highlightState }}>
      {children}
    </HighlightContext.Provider>
  );
}
