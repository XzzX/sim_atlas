import { type NodeTypes } from "@xyflow/react";
import { InputNode, type InputNodeType } from "./InputNode";
import { FunctionNode, type FunctionNodeType } from "./FunctionNode";
import { OutputNode, type OutputNodeType } from "./OutputNode";

export const nodeTypes: NodeTypes = {
  FunctionNode: FunctionNode,
  InputNode: InputNode,
  OutputNode: OutputNode,
};

export type WorkflowNode = FunctionNodeType | InputNodeType | OutputNodeType;
