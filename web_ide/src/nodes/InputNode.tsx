import React, { useState } from "react";
import { Position, type NodeProps, type Node } from "@xyflow/react";
import {
  BaseNode,
  BaseNodeContent,
  BaseNodeHeader,
  BaseNodeHeaderTitle,
} from "@/components/base-node";
import { BaseHandle } from "@/components/base-handle";

// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
export type InputDataElement = {
  label: string;
  value: string;
};
export type InputNodeType = Node<InputDataElement>;

export function InputNode({ data }: NodeProps<InputNodeType>) {
  const [value, setValue] = useState(data.value);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setValue(newValue);
  };

  return (
    <BaseNode>
      <BaseNodeHeader className="border-b rounded-t-md bg-input-node-background">
        <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
      </BaseNodeHeader>
      <BaseNodeContent className="p-3">
        <input
          type="text"
          value={value}
          onChange={handleChange}
          placeholder="Enter value..."
          className="nodrag w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />
        <BaseHandle type="source" position={Position.Right} />
      </BaseNodeContent>
    </BaseNode>
  );
}
