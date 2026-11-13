import React from "react";
import {
  Position,
  useReactFlow,
  type NodeProps,
  type Node,
} from "@xyflow/react";
import {
  BaseNode,
  BaseNodeContent,
  BaseNodeHeader,
  BaseNodeHeaderTitle,
} from "@/components/base-node";
import { LabeledHandle } from "@/components/labeled-handle";
import { constantType, parseConstant } from "./constantValue";

// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
export type ConstantDataElement = {
  label: string;
  /** JSON text; see `constantValue.ts`. */
  value: string;
};
export type ConstantNodeType = Node<ConstantDataElement>;

/** A literal value inside the workflow (flowrep's `ConstantRecipe`). */
export function ConstantNode({ id, data }: NodeProps<ConstantNodeType>) {
  const { updateNodeData } = useReactFlow();
  const parsed = parseConstant(data.value);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateNodeData(id, { value: e.target.value });
  };

  return (
    <BaseNode>
      <BaseNodeHeader className="border-b rounded-t-md bg-constant-node-background">
        <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
      </BaseNodeHeader>
      <BaseNodeContent className="p-3">
        <input
          type="text"
          value={data.value}
          onChange={handleChange}
          placeholder='JSON, e.g. "x", 1, true, [1, 2]'
          aria-invalid={!parsed.ok}
          className="nodrag w-full px-3 py-2 font-mono border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 aria-invalid:border-red-500"
        />
        <div
          className={`text-xs ${parsed.ok ? "text-gray-500" : "text-red-600"}`}
        >
          {parsed.ok ? constantType(parsed.value) : "invalid JSON"}
        </div>
      </BaseNodeContent>
      <LabeledHandle
        title="constant"
        type="source"
        position={Position.Right}
        id="constant"
        className="pb-3"
      />
    </BaseNode>
  );
}
