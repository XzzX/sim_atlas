import { useState, type ReactNode } from "react";
import type { Edge } from "@xyflow/react";
import { useHighlightState } from "./useHighlightState";
import { HighlightContext, type InteractionState } from "./highlightTypes";

export function HighlightProvider({
  children,
  edges,
}: {
  children: ReactNode;
  edges: Edge[];
}) {
  const [interaction, setInteraction] = useState<InteractionState>({
    mode: "idle",
  });
  const highlightState = useHighlightState(edges, interaction);
  return (
    <HighlightContext.Provider
      value={{ interaction, setInteraction, highlightState }}
    >
      {children}
    </HighlightContext.Provider>
  );
}
