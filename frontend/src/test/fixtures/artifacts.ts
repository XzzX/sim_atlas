import type {
  Annotation,
  WorkflowResponse,
  ExecutionResultMetadata,
  FilterOptions,
  ScoredSearchResponse,
} from "@/types/index";

const floatPort = (label: string): Annotation => ({
  label,
  datatype: "float",
  has_default_value: false,
});

export function makeLinearWorkflow(overrides: Partial<WorkflowResponse> = {}): WorkflowResponse {
  return {
    author_name: "Test Author",
    author_email: "author@example.com",
    creator_name: "Test Creator",
    creator_email: "creator@example.com",
    creation_timestamp: "2026-01-01T00:00:00Z",
    id: "wf-linear-0001",
    name: "dummy_module.flowrep.linear",
    artifact_type: "workflow",
    category: "dummy_module>flowrep",
    keywords: ["flowrep"],
    python_import: "dummy_module.flowrep.linear",
    source_code: "def linear(x, slope, intercept): ...",
    docstring: "y = slope * x + intercept",
    inputs: [floatPort("x"), floatPort("slope"), floatPort("intercept")],
    outputs: [floatPort("result")],
    see_also: [],
    uses: [],
    wf_definition: {
      nodes: [
        { type: "input", node_id: "x", outputs: [floatPort("x")] },
        {
          type: "function",
          node_id: "mul_0",
          atlas_id: null,
          inputs: [floatPort("a"), floatPort("b")],
          outputs: [floatPort("product")],
        },
        {
          type: "function",
          node_id: "add_0",
          atlas_id: null,
          inputs: [floatPort("a"), floatPort("b")],
          outputs: [floatPort("sum")],
        },
        { type: "output", node_id: "result", inputs: [floatPort("result")] },
      ],
      edges: [
        { source_node: "x", source_port: null, target_node: "mul_0", target_port: "a" },
        { source_node: "mul_0", source_port: "product", target_node: "add_0", target_port: "a" },
        { source_node: "add_0", source_port: "sum", target_node: "result", target_port: null },
      ],
    },
    ...overrides,
  };
}

export function makeExecutionResult(
  overrides: Partial<ExecutionResultMetadata> = {},
): ExecutionResultMetadata {
  return {
    id: "run-0001",
    author_name: "Test Author",
    author_email: "author@example.com",
    creator_name: "Test Creator",
    creator_email: "creator@example.com",
    creation_timestamp: "2026-01-02T00:00:00Z",
    artifact_id: "wf-linear-0001",
    inputs: [
      { label: "x", value: -1.3 },
      { label: "slope", value: -5 },
      { label: "intercept", value: 2.1 },
    ],
    outputs: '{"result": 8.6}',
    hash: "hash-run-0001",
    ...overrides,
  };
}

export const linearWorkflow = makeLinearWorkflow();

export const linearExecutions: ExecutionResultMetadata[] = [
  makeExecutionResult(),
  makeExecutionResult({
    id: "run-0002",
    hash: "hash-run-0002",
    inputs: [
      { label: "x", value: 3.1 },
      { label: "slope", value: 2 },
      { label: "intercept", value: 0 },
    ],
    outputs: '{"result": 6.2}',
  }),
  makeExecutionResult({
    id: "run-0003",
    hash: "hash-run-0003",
    inputs: [
      { label: "x", value: 81.0 },
      { label: "slope", value: 9 },
      { label: "intercept", value: -1.1 },
    ],
    outputs: '{"result": 727.9}',
  }),
];

export const filterOptions: FilterOptions = {
  category: { dummy_module: ["flowrep"] },
  artifact_type: ["function", "workflow"],
  author: ["Test Author"],
  keywords: ["flowrep"],
  datatypes: ["float"],
  units: [],
  quantities: [],
};

export const searchResponse: ScoredSearchResponse = {
  results: {
    data: [{ score: 1, node: linearWorkflow }],
    page: 1,
    limit: 10,
    total_items: 1,
    total_pages: 1,
  },
  aggregations: null,
};
