import { test, expect } from "@playwright/test";

test("web IDE loads linear workflow and add-node dialog shows 4 function nodes", async ({
  page,
}) => {
  // Fetch the linear workflow's UUID from the backend search API
  const resp = await page.request.post("/api/v1/search", {
    data: {
      query: "linear",
      filter: { artifact_type: ["workflow"] },
      limit: 20,
    },
  });
  const json = (await resp.json()) as {
    results: { data: Array<{ node: { id: string; name: string } }> };
  };
  const linearId = json.results.data.find(
    (d) => d.node.name === "dummy_module.flowrep.linear",
  )?.node.id;
  expect(linearId).toBeDefined();

  // Navigate to the web IDE with the linear workflow
  await page.goto(`/ide?wf_id=${linearId}`);

  // main.tsx uses top-level await for API calls before mounting React,
  // so allow extra time for the canvas to appear
  await expect(page.locator(".react-flow__node")).toHaveCount(6, {
    timeout: 30_000,
  });

  // 3 input nodes (label = node_id)
  await expect(page.getByText("x", { exact: true })).toBeVisible();
  await expect(page.getByText("slope", { exact: true })).toBeVisible();
  await expect(page.getByText("intercept", { exact: true })).toBeVisible();

  // 2 function nodes — identified by their unique python_import subtitle
  await expect(page.getByText("dummy_module.flowrep.mul")).toBeVisible();
  await expect(page.getByText("dummy_module.flowrep.add")).toBeVisible();

  // 1 output node (label = node_id)
  await expect(page.getByText("result", { exact: true })).toBeVisible();

  // 5 edges verified by their data-id (format: e{source_node}.{source_port}-{target_node}.{target_port})
  await expect(page.locator('[data-id="ex.-mul_0.a"]')).toBeVisible();
  await expect(page.locator('[data-id="eslope.-mul_0.b"]')).toBeVisible();
  await expect(page.locator('[data-id="eintercept.-add_0.b"]')).toBeVisible();
  await expect(page.locator('[data-id="emul_0.product-add_0.a"]')).toBeVisible();
  await expect(page.locator('[data-id="eadd_0.sum-result."]')).toBeVisible();

  // Exporting as flowrep must reproduce dummy_module.flowrep.linear's own recipe
  await page.getByRole("button", { name: "export" }).click();
  await page.locator("#export-format").selectOption("flowrep");
  const recipe = JSON.parse(
    await page.locator("textarea[readonly]").inputValue(),
  ) as {
    type: string;
    inputs: string[];
    outputs: string[];
    nodes: Record<string, { reference: { info: { qualname: string } } }>;
    input_edges: Record<string, string>;
    edges: Record<string, string>;
    output_edges: Record<string, string>;
    reference: unknown;
  };
  expect(recipe.type).toBe("workflow");
  expect(recipe.inputs).toEqual(["x", "slope", "intercept"]);
  expect(recipe.outputs).toEqual(["result"]);
  expect(Object.keys(recipe.nodes)).toEqual(["mul_0", "add_0"]);
  expect(recipe.nodes.mul_0.reference.info.qualname).toBe("mul");
  expect(recipe.input_edges).toEqual({
    "mul_0.a": "x",
    "mul_0.b": "slope",
    "add_0.b": "intercept",
  });
  expect(recipe.edges).toEqual({ "add_0.a": "mul_0.product" });
  expect(recipe.output_edges).toEqual({ result: "add_0.sum" });
  expect(recipe.reference).toBeNull();
  // A graph imported from a real recipe must export without diagnostics
  await expect(page.getByTestId("export-errors")).toHaveCount(0);
  await expect(page.getByTestId("export-warnings")).toHaveCount(0);
  await page.getByRole("button", { name: "Close" }).click();

  // Right-click on a corner of the pane (avoids nodes which are placed in the centre)
  await page.locator(".react-flow__pane").click({ button: "right", position: { x: 10, y: 10 } });

  // Scope all dialog assertions to the dialog overlay to avoid matching canvas nodes
  const dialog = page.locator(".fixed.inset-0");
  await expect(dialog.getByText("Add Node")).toBeVisible();

  // All 4 function artifacts should appear (workflow is excluded by default filter)
  await expect(dialog.getByText("dummy_module.functions.add")).toBeVisible();
  await expect(dialog.getByText("dummy_module.functions.mul")).toBeVisible();
  await expect(dialog.getByText("dummy_module.flowrep.add")).toBeVisible();
  await expect(dialog.getByText("dummy_module.flowrep.mul")).toBeVisible();

  // The linear workflow should not appear
  await expect(dialog.getByText("dummy_module.flowrep.linear")).not.toBeVisible();
});
