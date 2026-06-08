import { test, expect } from "@playwright/test";

test("frontend shows all uploaded functions", async ({ page }) => {
  await page.goto("/");

  // Wait for the search results to load — expects both uploaded functions
  await expect(page.getByText("2 results total")).toBeVisible();

  // Verify both uploaded functions appear as node card titles
  const cardTitles = page.locator('[data-slot="card-title"]');
  await expect(cardTitles.filter({ hasText: "add" })).toBeVisible();
  await expect(cardTitles.filter({ hasText: "multiply" })).toBeVisible();
});
