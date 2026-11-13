// Constant nodes (#233) through the import and both export formats.
import { describe, expect, it } from "vitest";
import type { Edge } from "@xyflow/react";
import { NodeResponseSchema, type WfDefinition } from "sim-atlas-api-schema";
import workflowNode from "sim-atlas-api-schema/fixtures/workflow-node-response.json";
import { convertWfDefinition } from "./importWorkflow";
import { toFlowrepRecipe } from "./exportFlowrep";
import { toWorkflowDefinition } from "./exportWorkflow";
import type { WorkflowNode } from "./nodes/nodes";

const at = { x: 0, y: 0 };

function constant(id: string, value: string): WorkflowNode {
  return { id, type: "ConstantNode", position: at, data: { label: id, value } };
}

function output(id: string): WorkflowNode {
  return { id, type: "OutputNode", position: at, data: { label: id } };
}

function edge(
  source: string,
  sourceHandle: string,
  target: string,
  targetHandle: string,
): Edge {
  return {
    id: `${source}-${target}`,
    source,
    sourceHandle,
    target,
    targetHandle,
  };
}

describe("catalog import", () => {
  it("turns a WfConstantNode into a ConstantNode holding its JSON text", async () => {
    const wfDef: WfDefinition = {
      nodes: [
        {
          type: "constant",
          node_id: "constant_0",
          value: "x",
          outputs: [{ label: "constant", has_default_value: false }],
        },
        {
          type: "output",
          node_id: "out",
          inputs: [{ label: "out", has_default_value: false }],
        },
      ],
      edges: [
        {
          source_node: "constant_0",
          source_port: "constant",
          target_node: "out",
          target_port: null,
        },
      ],
    };

    const { nodes, edges } = await convertWfDefinition(wfDef);

    expect(nodes.find((n) => n.id === "constant_0")).toMatchObject({
      type: "ConstantNode",
      data: { label: "constant_0", value: '"x"' },
    });
    expect(edges).toMatchObject([
      { source: "constant_0", sourceHandle: "constant", target: "out" },
    ]);
  });
});

describe("flowrep export", () => {
  it("emits a ConstantRecipe and keeps the value's JSON type", () => {
    const { recipe, errors } = toFlowrepRecipe(
      [constant("1", '"1"'), constant("2", "1"), output("a"), output("b")],
      [
        edge("1", "constant", "a", "input"),
        edge("2", "constant", "b", "input"),
      ],
    );

    expect(errors).toEqual([]);
    expect(recipe.nodes).toEqual({
      constant_0: {
        type: "constant",
        inputs: [],
        outputs: ["constant"],
        description: null,
        constant: "1",
      },
      constant_1: {
        type: "constant",
        inputs: [],
        outputs: ["constant"],
        description: null,
        constant: 1,
      },
    });
    expect(recipe.output_edges).toEqual({
      a: "constant_0.constant",
      b: "constant_1.constant",
    });
  });

  it("wires a constant into a function input as a node-to-node edge", () => {
    const linear: WorkflowNode = {
      id: "f",
      type: "FunctionNode",
      position: at,
      data: {
        label: "linear",
        metadata: NodeResponseSchema.parse(workflowNode),
      },
    };

    const { recipe } = toFlowrepRecipe(
      [constant("c", "[1, 2]"), linear],
      [edge("c", "constant", "f", "x")],
    );

    expect(recipe.edges).toEqual({ "linear_0.x": "constant_0.constant" });
    expect(recipe.input_edges).toEqual({});
  });

  it("reports a value that is not JSON", () => {
    const { errors } = toFlowrepRecipe([constant("1", "not json")], []);

    expect(errors).toEqual(['Constant "1" is not valid JSON: not json']);
  });
});

describe("python_workflow_definition export", () => {
  it("exports a constant as an input node carrying its value", () => {
    const { workflow, errors } = toWorkflowDefinition(
      [constant("c", '{"a": [1, null]}'), output("o")],
      [edge("c", "constant", "o", "input")],
    );

    expect(errors).toEqual([]);
    expect(workflow.nodes[0]).toEqual({
      id: "c",
      type: "input",
      name: "c",
      default: { a: [1, null] },
    });
    expect(workflow.edges).toEqual([
      { source: "c", source_handle: null, target: "o", target_handle: "input" },
    ]);
  });

  it("reports a constant without a valid JSON value", () => {
    const { errors } = toWorkflowDefinition(
      [constant("empty", ""), constant("bad", "not json")],
      [],
    );

    expect(errors).toEqual([
      'Constant "empty" has no value.',
      'Constant "bad" is not valid JSON: not json',
    ]);
  });

  it("renames a constant whose name an input already uses", () => {
    const input: WorkflowNode = {
      id: "i",
      type: "InputNode",
      position: at,
      data: { label: "x", value: "" },
    };

    const { workflow, warnings } = toWorkflowDefinition(
      [input, { ...constant("c", "1"), data: { label: "x", value: "1" } }],
      [],
    );

    expect(workflow.nodes.map((n) => n.type === "input" && n.name)).toEqual([
      "x",
      "x_1",
    ]);
    expect(warnings).toEqual(['Constant "x" was exported as the input "x_1".']);
  });
});
