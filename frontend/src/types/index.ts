export enum NodeType {
  FUNCTION = "function",
  PYTHON_WORKFLOW_DEFINITION = "python_workflow_definition",
  PYIRON_WORKFLOW_FUNCTION = "pyiron_workflow_function",
  PYIRON_CORE_NODE = "pyiron_core_node",
}

export interface Annotation {
  has_default_value?: boolean; // default False in Pydantic
  label?: string | null;
  datatype?: string | null;
  unit?: string | null;
  quantity?: string | null;
}

export interface NodeRequest {
  author_name: string;
  author_email: string;

  name: string;
  node_type: NodeType;
  category: string;

  keywords: string[];

  homepage_url: string;
  documentation_url: string;
  source_url: string;

  python_import: string;
  dependencies?: string[] | null;

  source_code: string;
  source_code_hash: string;

  docstring: string;
  inputs: Annotation[];
  outputs: Annotation[];
}

export interface NodeResponse {
  author_name: string;
  author_email: string;

  creator_name: string;
  creator_email: string;
  creation_timestamp: string;

  name: string;
  node_type: NodeType;
  category: string;

  keywords: string[];

  homepage_url: string;
  documentation_url: string;
  source_url: string;

  python_import: string;
  dependencies?: string[] | null;

  source_code: string;
  source_code_hash: string;

  docstring: string;
  ai_docstring: string;

  inputs: Annotation[];
  outputs: Annotation[];
}

export interface NodeIndex {
  module: string;
  qualname: string;
  source_code_hash: string;
}

export interface ScoredSearchResponse {
  score: number;
  node: NodeResponse;
}

export interface NodeMetadata extends NodeResponse {
  embedding?: number[] | null;
}

export interface Filter {
  category: string;
  type: string[];
  author: string[];
  keywords: string[];
  datatypes: string[];
  units: string[];
  quantities: string[];
}

export interface FilterOptions {
  category: Record<string, string[]>; // dict[str, set[str]] -> Record<string, string[]>
  type: NodeType[]; // set[NodeType] -> NodeType[]
  author: string[]; // set[str] -> string[]
  keywords: string[];
  datatypes: string[];
  units: string[];
  quantities: string[];
}
