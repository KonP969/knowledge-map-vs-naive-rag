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
  // The label reads "0 nodes · 0 edges" until the graph has loaded — wait for a real count.
  const label = page.getByText(/\d+ nodes · \d+ edges/);
  await expect(label).toHaveText(/[1-9]\d* nodes/, { timeout: 15_000 });
  const nodes = Number((await label.textContent())?.match(/(\d+) nodes/)?.[1] ?? 0);
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
  // Diacritics catch most leftovers; the word list catches the ones without any
  // (e.g. "Tak" / "Nie" on confirm buttons). Tooltips, placeholders and aria-labels
  // aren't in innerText, so they're checked separately.
  const diacritics = /[ąćęłńśźżĄĆĘŁŃŚŹŻ]/;
  const words = /\b(Tak|Nie|Kliknij|Otwórz|Wgraj|Zadaj|Wszystkie|Zaznacz|Odznacz|Importuj|Sortuj|Zamknij|Naprawiam|Przewodnik|Wyczyść|Naprawić|folderu|źródł\w*|pytani\w*|węzeł|encj\w*)\b/;
  for (const p of panels) {
    await goToPanel(page, p);
    await page.waitForTimeout(300);
    const main = page.locator("main");
    const text = (await main.innerText()).replace(/\s+/g, " ");
    const attrs = await main.evaluate((el) =>
      Array.from(el.querySelectorAll("[title],[placeholder],[aria-label]"))
        .flatMap((n) => ["title", "placeholder", "aria-label"].map((a) => n.getAttribute(a) ?? ""))
        .join(" | "),
    );
    for (const [what, s] of [["text", text], ["attributes", attrs]] as const) {
      expect(s, `Polish ${what} in ${p}`).not.toMatch(diacritics);
      expect(s, `Polish ${what} in ${p}`).not.toMatch(words);
    }
  }
});
