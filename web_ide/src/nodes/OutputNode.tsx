import { Position, type NodeProps, type Node } from "@xyflow/react";
import { BaseNode, BaseNodeContent } from "@/components/base-node";
import { LabeledHandle } from "@/components/labeled-handle";

// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
export type OutputDataElement = {
  label: string;
};
export type OutputNodeType = Node<OutputDataElement>;

export function OutputNode({ data }: NodeProps<OutputNodeType>) {
  return (
    <BaseNode>
      <BaseNodeContent className="pl-0 pr-0 pt-3 pb-3 rounded-md bg-output-node-background">
        <LabeledHandle
          title={data.label}
          type="target"
          position={Position.Left}
        />
      </BaseNodeContent>
    </BaseNode>
  );
}
