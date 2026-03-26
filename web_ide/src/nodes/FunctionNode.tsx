import {
  BaseNode,
  BaseNodeContent,
  BaseNodeHeader,
  BaseNodeHeaderTitle,
} from "@/components/base-node";
import { LabeledHandle } from "@/components/labeled-handle";
import {
  Position,
  type NodeProps,
  type Node,
  type HandleType,
  type HandleProps,
} from "@xyflow/react";
import type { Annotation, NodeMetadata } from "../interfaces/NodeMetadata";
import { Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";

interface InputHandleProps {
  title: string;
  type: HandleType;
  id: string;
  position: Position;
  connectionCount?: number;
  annotation?: Annotation;
}
const InputHandle = ({ title, type, id, position }: InputHandleProps) => {
  return (
    <LabeledHandle title={title} type={type} position={position} id={id} />
  );
};

interface OutputHandleProps extends HandleProps {
  title: string;
  type: HandleType;
  id: string;
  position: Position;
}
const OutputHandle = (props: OutputHandleProps) => {
  return <LabeledHandle {...props} />;
};

export type NodeData = {
  label: string;
  metadata: NodeMetadata;
};
export type FunctionNodeType = Node<NodeData>;
export function FunctionNode({ data }: NodeProps<FunctionNodeType>) {
  return (
    <BaseNode>
      <BaseNodeHeader className="border-b rounded-t-md bg-function-node-background">
        <div className="flex items-center justify-between w-full gap-4">
          <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
          <Button variant="outline" size="icon" aria-label="Submit">
            <Pencil />
          </Button>
        </div>
      </BaseNodeHeader>
      <BaseNodeContent className="pl-0 pr-0 pt-3 pb-3">
        <div className="flex flex-row">
          <div className="flex-1">
            {data.metadata.inputs.map((value, index) => (
              <InputHandle
                id={value.label}
                title={value.label}
                type="target"
                position={Position.Left}
                key={index}
                connectionCount={1}
                annotation={value}
              />
            ))}
          </div>
          <div className="flex-1">
            {data.metadata.outputs.map((value, index) => (
              <OutputHandle
                id={value.label}
                title={value.label}
                type="source"
                position={Position.Right}
                key={index}
              />
            ))}
          </div>
        </div>
      </BaseNodeContent>
    </BaseNode>
  );
}
