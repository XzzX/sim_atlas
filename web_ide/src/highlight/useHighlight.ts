import { useContext } from "react";
import { HighlightContext, type HighlightContextValue } from "./highlightTypes";

export function useHighlight(): HighlightContextValue {
  const ctx = useContext(HighlightContext);
  if (!ctx) throw new Error("useHighlight must be used inside HighlightProvider");
  return ctx;
}
