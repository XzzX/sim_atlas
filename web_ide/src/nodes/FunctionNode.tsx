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
  unknown: "ring-2 ring-green-400",
};

const bgClass: Record<CompatibilityResult, string> = {
  match: "bg-green-400/20",
  "unit-mismatch": "bg-amber-400/20",
  "type-mismatch": "bg-red-400/20",
  unknown: "bg-green-400/20",
};

interface InputHandleProps {
  title: string;
  type: HandleType;
  id: string;
  position: Position;
  connectionCount?: number;
  annotation?: Annotation;
  handleClassName?: string;
  className?: string;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}
const InputHandle = ({
  title,
  type,
  id,
  position,
  handleClassName,
  className,
  onMouseEnter,
  onMouseLeave,
}: InputHandleProps) => {
  return (
    <LabeledHandle
      title={title}
      type={type}
      position={position}
      id={id}
      handleClassName={handleClassName}
      className={className}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    />
  );
};

interface OutputHandleProps extends HandleProps {
  title: string;
  type: HandleType;
  id: string;
  position: Position;
  handleClassName?: string;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
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
  const { highlightState, interaction, setInteraction } = useHighlight();
  const isDragging = interaction.mode === "dragging";
  const fromHandleType = isDragging ? interaction.fromHandleType : null;
  const isInputRelevant = fromHandleType === "source";
  const isOutputRelevant = fromHandleType === "target";

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
                key={index}
                id={value.label ?? index.toString()}
                title={value.label ?? index.toString()}
                type="target"
                position={Position.Left}
                connectionCount={1}
                annotation={value}
                handleClassName={
                  isDragging && isInputRelevant
                    ? ringClass[
                        highlightState.handleCompatibility.get(
                          `${id}::${value.label ?? index.toString()}`,
                        ) ?? "unknown"
                      ]
                    : undefined
                }
                className={
                  isDragging && isInputRelevant
                    ? bgClass[
                        highlightState.handleCompatibility.get(
                          `${id}::${value.label ?? index.toString()}`,
                        ) ?? "unknown"
                      ]
                    : undefined
                }
                onMouseEnter={() =>
                  setInteraction({
                    mode: "handle-hover",
                    nodeId: id,
                    handleId: value.label ?? index.toString(),
                  })
                }
                onMouseLeave={() => setInteraction({ mode: "idle" })}
              />
            ))}
          </div>
          <div className="flex-1">
            {data.metadata.outputs.map((value, index) => (
              <OutputHandle
                key={index}
                id={value.label ?? index.toString()}
                title={value.label ?? index.toString()}
                type="source"
                position={Position.Right}
                handleClassName={
                  isDragging && isOutputRelevant
                    ? ringClass[
                        highlightState.handleCompatibility.get(
                          `${id}::${value.label ?? index.toString()}`,
                        ) ?? "unknown"
                      ]
                    : undefined
                }
                className={
                  isDragging && isOutputRelevant
                    ? bgClass[
                        highlightState.handleCompatibility.get(
                          `${id}::${value.label ?? index.toString()}`,
                        ) ?? "unknown"
                      ]
                    : undefined
                }
                onMouseEnter={() =>
                  setInteraction({
                    mode: "handle-hover",
                    nodeId: id,
                    handleId: value.label ?? index.toString(),
                  })
                }
                onMouseLeave={() => setInteraction({ mode: "idle" })}
              />
            ))}
          </div>
        </div>
      </BaseNodeContent>
    </BaseNode>
  );
}
