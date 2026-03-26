import React, { useState } from "react";
import { Position, type NodeProps, type Node } from "@xyflow/react";
import {
  BaseNode,
  BaseNodeContent,
  BaseNodeHeader,
  BaseNodeHeaderTitle,
} from "@/components/base-node";
import { LabeledHandle } from "@/components/labeled-handle";

export type ConditionalExpressionDataElement = {
  label: string;
};
export type ConditionalExpressionNodeType =
  Node<ConditionalExpressionDataElement>;

export function ConditionalExpressionNode({
  data,
}: NodeProps<ConditionalExpressionNodeType>) {
  return (
    <BaseNode>
      <BaseNodeHeader className="border-b rounded-t-md bg-input-node-background">
        <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
      </BaseNodeHeader>
      <BaseNodeContent className="pl-0 pr-0 pt-3 pb-3">
        <div className="flex flex-row">
          <div className="flex-1">
            <LabeledHandle
              title="if"
              type="target"
              position={Position.Left}
              id="if"
            />
            <LabeledHandle
              title="then"
              type="target"
              position={Position.Left}
              id="then"
            />
            <LabeledHandle
              title="else"
              type="target"
              position={Position.Left}
              id="else"
            />
          </div>
          <div className="flex-1">
            <LabeledHandle
              title="result"
              type="source"
              position={Position.Right}
              id="result"
            />
          </div>
        </div>
      </BaseNodeContent>
    </BaseNode>
  );
}
