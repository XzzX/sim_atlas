export enum NodeType {
  FUNCTION = "function",
  PYTHON_WORKFLOW_DEFINITION = "python_workflow_definition",
  PYIRON_WORKFLOW_FUNCTION = "pyiron_workflow_function",
  PYIRON_CORE_NODE = "pyiron_core_node",
}

export interface Annotation {
  has_default_value: boolean;
  label: string | null;
  datatype: string | null;
  unit: string | null;
  quantity: string | null;
}

export interface NodeMetadata {
  author_name: string;
  author_email: string;
  creator_name: string;
  creator_email: string;
  creation_timestamp: string;
  node_type: NodeType;
  python_import: string;
  keywords: string[] | null;
  dependencies: string[] | null;
  source_code: string;
  source_code_hash: string;
  docstring: string;
  ai_docstring: string;
  inputs: Annotation[];
  outputs: Annotation[];
  embedding?: number[] | null;
}

export interface ScoredSearchResponse {
  score: number;
  node: NodeMetadata;
}

export interface FilterOptions {
  category?: string;
  type?: NodeType[];
  author?: string[];
  keywords?: string[];
  inputDatatype?: string[];
  outputDatatype?: string[];
}
