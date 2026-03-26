import type { Annotation, NodeMetadata } from "./NodeMetadata";

export interface NodeFilter {
  datatype?: string;
  unit?: string;
  quantity?: string;
  portType: "inputs" | "outputs" | "both";
  nodeType?: string;
}

export function nodeMatchesFilter(
  node: NodeMetadata,
  filter: Partial<NodeFilter>,
): boolean {
  if (filter.nodeType && node.node_type !== filter.nodeType) {
    return false;
  }

  const annotationsToCheck: Annotation[] = [];
  if (filter.portType === "inputs" || filter.portType === "both") {
    annotationsToCheck.push(...node.inputs);
  }
  if (filter.portType === "outputs" || filter.portType === "both") {
    annotationsToCheck.push(...node.outputs);
  }

  for (const annotation of annotationsToCheck) {
    if (annotationMatchesFilter(annotation, filter)) {
      return true;
    }
  }

  return false;
}

function annotationMatchesFilter(
  annotation: Annotation,
  filter: Partial<NodeFilter>,
): boolean {
  if (filter.datatype && annotation.datatype !== filter.datatype) {
    return false;
  }
  if (filter.unit && annotation.unit !== filter.unit) {
    return false;
  }
  if (filter.quantity && annotation.quantity !== filter.quantity) {
    return false;
  }
  return true;
}
