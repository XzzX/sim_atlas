import { test, expect } from "@playwright/test";

test("web IDE loads linear workflow and add-node dialog shows 4 function nodes", async ({
  page,
}) => {
  // Fetch the linear workflow's UUID from the backend search API
  const resp = await page.request.post("/api/v1/search", {
    data: { artifact_type: ["workflow"] },
    params: { query: "linear", limit: 20 },
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

  // Verify the complete workflow: 6 nodes total
  await expect(page.locator(".react-flow__node")).toHaveCount(6);

  // 3 input nodes (label = node_id)
  await expect(page.getByText("x", { exact: true })).toBeVisible();
  await expect(page.getByText("slope", { exact: true })).toBeVisible();
  await expect(page.getByText("intercept", { exact: true })).toBeVisible();

  // 2 function nodes — identified by their unique python_import subtitle
  await expect(page.getByText("dummy_module.flowrep.mul")).toBeVisible();
  await expect(page.getByText("dummy_module.flowrep.add")).toBeVisible();

  // 1 output node (label = node_id)
  await expect(page.getByText("result", { exact: true })).toBeVisible();

  // Right-click on the empty canvas pane to open the add-node dialog
  await page.locator(".react-flow__pane").click({ button: "right" });

  // Verify the dialog is open
  await expect(page.getByText("Add Node")).toBeVisible();

  // All 4 function artifacts should appear (workflow is excluded by default filter)
  await expect(page.getByText("dummy_module.functions.add")).toBeVisible();
  await expect(page.getByText("dummy_module.functions.mul")).toBeVisible();
  await expect(page.getByText("dummy_module.flowrep.add")).toBeVisible();
  await expect(page.getByText("dummy_module.flowrep.mul")).toBeVisible();

  // The linear workflow should not appear
  await expect(
    page.getByText("dummy_module.flowrep.linear"),
  ).not.toBeVisible();
});
