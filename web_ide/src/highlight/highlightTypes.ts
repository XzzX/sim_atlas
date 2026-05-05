import { createContext } from "react";
import type { Annotation } from "@/interfaces/BackendSchema";
import type { CompatibilityResult } from "./typeCompatibility";

// --- Interaction state ---
export type InteractionState =
  | { mode: "idle" }
  | { mode: "node-hover"; nodeId: string }
  | {
      mode: "dragging";
      fromNodeId: string;
      fromHandleId: string;
      fromHandleType: "source" | "target";
      fromAnnotation: Annotation | null;
    };

// --- Derived highlight maps ---
export interface HighlightState {
  edgeCompatibility: Map<string, CompatibilityResult>;
  activeEdgeIds: Set<string> | null;
  activeNodeIds: Set<string> | null;
  handleCompatibility: Map<string, CompatibilityResult>;
}

export interface HighlightContextValue {
  interaction: InteractionState;
  setInteraction: (state: InteractionState) => void;
  highlightState: HighlightState;
}

export const HighlightContext = createContext<HighlightContextValue | null>(
  null,
);
