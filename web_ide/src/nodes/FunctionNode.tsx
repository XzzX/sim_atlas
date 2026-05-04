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
import type { Annotation, NodeResponse } from "../interfaces/BackendSchema";
import { useHighlight } from "@/highlight/useHighlight";
import { type CompatibilityResult } from "@/highlight/typeCompatibility";

const ringClass: Record<CompatibilityResult, string> = {
  match: "ring-2 ring-green-400",
  "unit-mismatch": "ring-2 ring-amber-400",
  "type-mismatch": "ring-2 ring-red-400",
  unknown: "",
};

interface InputHandleProps {
  title: string;
  type: HandleType;
  id: string;
  position: Position;
  connectionCount?: number;
  annotation?: Annotation;
  handleClassName?: string;
}
const InputHandle = ({ title, type, id, position, handleClassName }: InputHandleProps) => {
  return (
    <LabeledHandle title={title} type={type} position={position} id={id} handleClassName={handleClassName} />
  );
};

interface OutputHandleProps extends HandleProps {
  title: string;
  type: HandleType;
  id: string;
  position: Position;
  handleClassName?: string;
}
const OutputHandle = (props: OutputHandleProps) => {
  return <LabeledHandle {...props} />;
};

// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
export type NodeData = {
  label: string;
  metadata: NodeResponse;
};
export type FunctionNodeType = Node<NodeData>;
export function FunctionNode({ id, data }: NodeProps<FunctionNodeType>) {
  const { highlightState, interaction } = useHighlight();
  const isDragging = interaction.mode === "dragging";

  return (
    <BaseNode>
      <BaseNodeHeader className="border-b rounded-t-md bg-function-node-background">
        <div className="flex items-center justify-between w-full gap-4">
          <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
        </div>
      </BaseNodeHeader>
      <BaseNodeContent className="pl-0 pr-0 pt-3 pb-3">
        <div className="flex flex-row">
          <div className="flex-1">
            {data.metadata.inputs.map((value, index) => (
              <InputHandle
                id={value.label ?? index.toString()}
                title={value.label ?? index.toString()}
                type="target"
                position={Position.Left}
                key={index}
                connectionCount={1}
                annotation={value}
                handleClassName={isDragging
                  ? ringClass[highlightState.handleCompatibility.get(`${id}::${value.label ?? index.toString()}`) ?? "unknown"]
                  : undefined}
              />
            ))}
          </div>
          <div className="flex-1">
            {data.metadata.outputs.map((value, index) => (
              <OutputHandle
                id={value.label ?? index.toString()}
                title={value.label ?? index.toString()}
                type="source"
                position={Position.Right}
                key={index}
                handleClassName={isDragging
                  ? ringClass[highlightState.handleCompatibility.get(`${id}::${value.label ?? index.toString()}`) ?? "unknown"]
                  : undefined}
              />
            ))}
          </div>
        </div>
      </BaseNodeContent>
    </BaseNode>
  );
}
