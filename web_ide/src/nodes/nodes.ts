import { type NodeTypes } from "@xyflow/react";
import { InputNode, type InputNodeType } from "./InputNode";
import { FunctionNode, type FunctionNodeType } from "./FunctionNode";
import { OutputNode, type OutputNodeType } from "./OutputNode";
import { ConstantNode, type ConstantNodeType } from "./ConstantNode";

export const nodeTypes: NodeTypes = {
  FunctionNode: FunctionNode,
  InputNode: InputNode,
  OutputNode: OutputNode,
  ConstantNode: ConstantNode,
};

export type WorkflowNode =
  FunctionNodeType | InputNodeType | OutputNodeType | ConstantNodeType;
