import { test, expect } from "@playwright/test";

test("frontend shows all uploaded functions", async ({ page }) => {
  await page.goto("/");

  // Wait for the search results to load — expects all uploaded nodes
  await expect(page.getByText("5 results")).toBeVisible();

  // Verify both uploaded functions appear in the results table
  await expect(page.getByTitle("dummy_module.functions.add")).toBeVisible();
  await expect(page.getByTitle("dummy_module.functions.mul")).toBeVisible();
});
