export type NodeType = "function" | "pwd" | "pyiron_workflow_function" | "pyiron_core_node";

export interface NodeResponse {
  author_name: string;
  author_email: string;
  node_type: NodeType;
  python_import: string;
  dependencies: null;
  source_code: string;
  source_code_hash: string;
  docstring: string;
  ai_docstring: string;
  inputs: Annotation[];
  outputs: Annotation[];
}

export interface Annotation {
  has_default_value: boolean;
  label: string;
  datatype: string;
  unit: null | string;
  quantity: null | string;
}