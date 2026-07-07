import { test, expect } from "@playwright/test";

test("frontend shows all uploaded functions", async ({ page }) => {
  await page.goto("/");

  // Wait for the search results to load — expects all uploaded nodes
  await expect(page.getByText("5 results")).toBeVisible();

  // Verify both uploaded functions appear in the results table
  await expect(page.getByTitle("dummy_module.functions.add")).toBeVisible();
  await expect(page.getByTitle("dummy_module.functions.mul")).toBeVisible();
});

test("frontend shows the 3 execution results for the linear workflow", async ({ page }) => {
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

  // Land directly on the node detail page's "Executions" tab
  await page.goto(`/node/${linearId}?tab=executions`);

  // run_1/run_2/run_3 in the dummy module should show up as 3 execution results
  await expect(page.getByText("of 3 executions")).toBeVisible();
  await expect(page.locator(".cursor-pointer.rounded-xl.border")).toHaveCount(3);
});
