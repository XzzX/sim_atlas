// The generated schemas (sim-atlas-api-schema, ADR-0027) against what the backend
// really sends and accepts.
import { describe, expect, it } from "vitest";
import { NodeRequestSchema, NodeResponseSchema } from "sim-atlas-api-schema";
import workflowNode from "sim-atlas-api-schema/fixtures/workflow-node-response.json";

describe("generated API schema", () => {
  it("parses a real workflow response with uses, used_by, connections and wf_definition", () => {
    const node = NodeResponseSchema.parse(workflowNode);

    expect(node.uses.map((r) => r.label)).toEqual(["mul", "add"]);
    expect(node.used_by?.map((r) => r.label)).toEqual(["dummy_module.flowrep.twice"]);
    expect(node.used_by?.[0].artifact_type).toBe("workflow");
    expect(node.outputs[0].connections?.map((r) => r.label)).toEqual([
      "dummy_module.flowrep.add",
    ]);
    expect(node.wf_definition.nodes.map((n) => n.type)).toEqual([
      "input",
      "input",
      "constant",
      "function",
      "function",
      "output",
    ]);
    expect(node.wf_definition.nodes.find((n) => n.type === "constant")).toMatchObject({
      node_id: "constant_0",
      value: 1,
    });
  });

  it("rejects a server-owned field in a node request", () => {
    const request = {
      artifact_type: "function",
      name: "f",
      category: "c",
      keywords: [],
      source_code: "def f(): ...",
      inputs: [],
      outputs: [],
    };

    expect(NodeRequestSchema.safeParse(request).success).toBe(true);
    expect(
      NodeRequestSchema.safeParse({ ...request, creator_name: "someone" }).success,
    ).toBe(false);
  });
});
