import { type NodeTypes } from "@xyflow/react";
import { InputNode, type InputNodeType } from "./InputNode";
import { FunctionNode, type FunctionNodeType } from "./FunctionNode";
import { OutputNode, type OutputNodeType } from "./OutputNode";
import {
  ConditionalExpressionNode,
  type ConditionalExpressionNodeType,
} from "./ConditionalExpressionNode";

export const nodeTypes: NodeTypes = {
  FunctionNode: FunctionNode,
  InputNode: InputNode,
  OutputNode: OutputNode,
  ConditionalExpressionNode: ConditionalExpressionNode,
};

export type WorkflowNode =
  | FunctionNodeType
  | InputNodeType
  | ConditionalExpressionNodeType
  | OutputNodeType;
