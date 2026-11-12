import { createContext } from "react";
import type { AnnotationResponse } from "sim-atlas-api-schema";

// --- Interaction state ---
export type InteractionState =
  | { mode: "idle" }
  | { mode: "node-hover"; nodeId: string }
  | {
      mode: "dragging";
      fromNodeId: string;
      fromHandleId: string;
      fromHandleType: "source" | "target";
      fromAnnotation: AnnotationResponse | null;
    };

// --- Derived highlight maps ---
export interface HighlightState {
  activeEdgeIds: Set<string> | null;
  activeNodeIds: Set<string> | null;
}

export interface HighlightContextValue {
  interaction: InteractionState;
  setInteraction: (state: InteractionState) => void;
  highlightState: HighlightState;
}

export const HighlightContext = createContext<HighlightContextValue | null>(
  null,
);
