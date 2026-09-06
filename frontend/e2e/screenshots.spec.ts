import { test, expect } from "@playwright/test";
import { existsSync } from "fs";

// Regenerates the images in ../docs/screenshots used by the root README.
// Runs a real retrieval query, so it needs the backend to have an OpenAI key.
//   npx playwright test screenshots --grep @screenshots
test.describe("@screenshots", () => {
  test.skip(!existsSync("../backend/.env"), "backend/.env with OPENAI_API_KEY required");

  const dir = "../docs/screenshots";

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("tourSeen", "1"));
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test("wiki chat trace", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Wiki Chat", exact: true }).click();
    await page.getByPlaceholder("Ask a question about your wiki…")
      .fill("What problem with large language models does retrieval-augmented generation address?");
    await page.keyboard.press("Enter");
    await expect(page.getByText("Follow-ups")).toBeVisible({ timeout: 60_000 });
    await page.waitForTimeout(3500); // let the chain finish its staged reveal
    await page.screenshot({ path: `${dir}/wiki-chat.png` });
  });

  test("knowledge map", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Knowledge Map", exact: true }).click();
    await expect(page.locator(".react-flow__node").first()).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `${dir}/knowledge-map.png` });
  });

  test("tutorial", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Tutorial", exact: true }).click();
    await expect(page.getByRole("heading", { name: "What is Knowledge-Map RAG?" })).toBeVisible();
    await page.screenshot({ path: `${dir}/tutorial.png` });
  });

  test("sources", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Sources", exact: true }).click();
    await expect(page.getByText("Retrieval-augmented generation", { exact: true })).toBeVisible();
    await page.screenshot({ path: `${dir}/sources.png` });
  });

  test("ingest pipeline", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Ingest", exact: true }).click();
    await expect(page.getByRole("heading", { name: "5-Stage Pipeline" })).toBeVisible();
    await page.screenshot({ path: `${dir}/ingest.png` });
  });
});
