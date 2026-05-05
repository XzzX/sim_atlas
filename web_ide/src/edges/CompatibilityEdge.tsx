import {
  BaseEdge,
  getBezierPath,
  useInternalNode,
  type EdgeProps,
} from "@xyflow/react";
import { checkCompatibility } from "@/highlight/typeCompatibility";
import { useHighlight } from "@/highlight/useHighlight";
import type { NodeData } from "@/nodes/FunctionNode";

export function CompatibilityEdge({
  id,
  source,
  target,
  sourceHandleId,
  targetHandleId,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  style,
}: EdgeProps) {
  const srcNode = useInternalNode(source);
  const tgtNode = useInternalNode(target);

  const srcAnn =
    srcNode?.type === "FunctionNode"
      ? ((srcNode.internals.userNode.data as NodeData).metadata.outputs.find(
          (p, i) => (p.label ?? i.toString()) === sourceHandleId,
        ) ?? null)
      : null;

  const tgtAnn =
    tgtNode?.type === "FunctionNode"
      ? ((tgtNode.internals.userNode.data as NodeData).metadata.inputs.find(
          (p, i) => (p.label ?? i.toString()) === targetHandleId,
        ) ?? null)
      : null;

  const compat = checkCompatibility(srcAnn, tgtAnn);

  const { highlightState } = useHighlight();
  const dimmed =
    highlightState.activeEdgeIds !== null &&
    !highlightState.activeEdgeIds.has(id);

  const stroke =
    compat === "type-mismatch"
      ? "var(--color-destructive)"
      : compat === "unit-mismatch"
        ? "var(--color-warning)"
        : undefined;

  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <BaseEdge
      path={edgePath}
      markerEnd={markerEnd}
      style={{
        ...style,
        ...(stroke ? { stroke } : {}),
        opacity: dimmed ? 0.1 : 1,
      }}
    />
  );
}
