import { test, expect, type Page } from "@playwright/test";

// Console/page errors that aren't the app's fault.
const IGNORE = [/favicon/i, /Download the React DevTools/i, /ResizeObserver loop/i];

function watchErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" && !IGNORE.some((r) => r.test(m.text()))) errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(String(e)));
  return errors;
}

async function goToPanel(page: Page, name: string) {
  await page.getByRole("button", { name, exact: true }).click();
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("tourSeen", "1"); // don't auto-run the onboarding tour in tests
  });
});

test("every panel renders without console errors", async ({ page }) => {
  const errors = watchErrors(page);
  await page.goto("/");

  await expect(page.getByText("Karpathy Method")).toBeVisible();

  await goToPanel(page, "Ingest");
  await expect(page.getByRole("heading", { name: "5-Stage Pipeline" })).toBeVisible();

  await goToPanel(page, "Sources");
  await expect(page.getByText("Retrieval-augmented generation", { exact: true })).toBeVisible();

  await goToPanel(page, "Wiki Chat");
  await expect(page.getByPlaceholder("Ask a question about your wiki…")).toBeVisible();
  await expect(page.getByText("Pipeline", { exact: true })).toBeVisible();

  await goToPanel(page, "Knowledge Map");
  await expect(page.locator(".react-flow__node").first()).toBeVisible({ timeout: 15_000 });

  await goToPanel(page, "Lint");
  await expect(page.getByText("What is Lint?")).toBeVisible();

  await goToPanel(page, "Metrics");
  await goToPanel(page, "Tutorial");
  await expect(page.getByRole("heading", { name: "What is Knowledge-Map RAG?" })).toBeVisible();

  expect(errors, `console errors:\n${errors.join("\n")}`).toEqual([]);
});

test("the demo corpus loaded into the graph", async ({ page }) => {
  await page.goto("/");
  await goToPanel(page, "Knowledge Map");
  await expect(page.getByText(/\d+ nodes · \d+ edges/)).toBeVisible({ timeout: 15_000 });
  const label = await page.getByText(/\d+ nodes · \d+ edges/).textContent();
  const nodes = Number(label?.match(/(\d+) nodes/)?.[1] ?? 0);
  expect(nodes).toBeGreaterThan(10);
});

test("the onboarding tour runs on a first visit", async ({ browser }) => {
  const ctx = await browser.newContext(); // fresh storage — tour not yet seen
  const page = await ctx.newPage();
  await page.goto("/");
  await expect(page.getByText("Knowledge-Map RAG", { exact: true })).toBeVisible({ timeout: 5_000 });
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText("1 · Add knowledge")).toBeVisible();
  await ctx.close();
});

test("the app has no Polish UI strings left", async ({ page }) => {
  await page.goto("/");
  const panels = ["Ingest", "Sources", "Wiki Chat", "Knowledge Map", "Lint", "Metrics", "Tutorial"];
  const polish = /\b(Kliknij|Otwórz|Wgraj|Zadaj|źródł\w*|pytani\w*|węzeł|encj\w*|Przewodnik|Krok po kroku|Wyczyść|Naprawić)\b/;
  for (const p of panels) {
    await goToPanel(page, p);
    await page.waitForTimeout(300);
    const body = (await page.locator("main").innerText()).replace(/\s+/g, " ");
    expect(body, `Polish text in ${p}`).not.toMatch(polish);
  }
});
