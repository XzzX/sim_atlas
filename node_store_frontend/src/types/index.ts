export enum NodeType {
  Function = "function",
  PythonWorkflowDefinition = "python_workflow_definition",
  PyironWorkflowFunction = "pyiron_workflow_function",
  PyironCoreNode = "pyiron_core_node",
}

export interface Annotation {
  has_default_value?: boolean; // default: false
  label?: string | null;
  datatype?: string | null;
  unit?: string | null;
  quantity?: string | null;
}

export interface NodeRequest {
  author_name: string;
  author_email: string;

  node_type: NodeType;
  category: string;

  python_import: string;
  dependencies?: string[] | null;

  keywords: string[];

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

  node_type: NodeType;
  category: string;

  python_import: string;
  dependencies?: string[] | null;

  keywords: string[];

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

export interface ArgumentFilter {
  datatype?: string | null;
  unit?: string | null;
  quantity?: string | null;
}

export interface NodeFilter {
  input?: ArgumentFilter; // default: {}
  output?: ArgumentFilter; // default: {}
}

export interface NodeMetadata extends NodeResponse {
  embedding?: number[] | null;
}

export interface Filter {
  category?: string | null;
  type?: NodeType[] | null;
  author?: string[] | null;
  keywords?: string[] | null;
}

export interface SearchFilters extends Filter {
  inputDatatype?: string[] | null;
  outputDatatype?: string[] | null;
}

/**
 * JSON-safe API shape:
 * Python sets are serialized as arrays in JSON.
 */
export interface FilterOptions {
  category: Record<string, string[]>;
  type: NodeType[];
  author: string[];
  keywords: string[];
}
