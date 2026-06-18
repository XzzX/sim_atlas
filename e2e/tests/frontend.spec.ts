import { test, expect } from "@playwright/test";

test("frontend shows all uploaded functions", async ({ page }) => {
  await page.goto("/");

  // Wait for the search results to load — expects all uploaded nodes
  await expect(page.getByText("5 results total")).toBeVisible();

  // Verify both uploaded functions appear as node card titles
  const cardTitles = page.locator('[data-slot="card-title"]');
  await expect(cardTitles.filter({ hasText: "dummy_module.functions.add" })).toBeVisible();
  await expect(cardTitles.filter({ hasText: "dummy_module.functions.mul" })).toBeVisible();
});
