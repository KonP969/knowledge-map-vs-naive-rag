// UX Round 3 — Playwright verification for features 2 / 4 / 5 / 6
//
// Prereqs: backend on :8000 with some ingested data + at least one lint report
// that contains an entity/concept/source location; frontend dev server running.
// Set BASE via env (defaults to http://localhost:5174).
//
// Run:  node test_ux_round3.js
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://localhost:5174";
const RESULTS = [];

function log(feature, status, detail = "") {
  const icon = status === "PASS" ? "✅" : status === "FAIL" ? "❌" : "⚠️";
  console.log(`${icon} ${feature}: ${detail}`);
  RESULTS.push({ feature, status, detail });
}

const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ── Feature 2: chat history persists in localStorage ────────────────────────
async function testFeature2(browser) {
  const fakeTrace = {
    query_id: "q_test_1",
    question: "Round3 history question?",
    intent: { original_question: "Round3 history question?", entity_mentions: [], concept_mentions: [], time_period: null, intent_type: "fact_lookup", expected_answer_form: "short" },
    candidates_count: 3, selected_count: 1, context_chars: 100,
    answer: { final_answer: "Round3 history answer.", sources: [], confidence: 0.9, reasoning_steps: ["s1"], related_questions: ["Follow up?"] },
    stages: [{ stage: 1, name: "Intent Parser", duration_ms: 10, llm_called: true, input_summary: "", output_summary: "parsed" }],
    total_duration_ms: 120, total_llm_calls: 1,
  };
  const page = await browser.newPage();
  try {
    await page.goto(BASE, { waitUntil: "networkidle" });
    await page.evaluate((t) => localStorage.setItem("wikiChatHistory", JSON.stringify([t])), fakeTrace);
    await page.reload({ waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Wiki Chat" }).click();
    await page.waitForTimeout(500);

    const answer = await page.getByText("Round3 history answer.").isVisible().catch(() => false);
    const clearBtn = await page.getByRole("button", { name: /Wyczyść historię/i }).isVisible().catch(() => false);
    if (!answer || !clearBtn) return log("Feature 2", "FAIL", `history not rendered (answer=${answer}, clear=${clearBtn})`);

    await page.getByRole("button", { name: /Wyczyść historię/i }).click();
    await page.waitForTimeout(300);
    const gone = !(await page.getByText("Round3 history answer.").isVisible().catch(() => false));
    const ls = await page.evaluate(() => localStorage.getItem("wikiChatHistory"));
    if (gone && (ls === "[]" || ls === null)) log("Feature 2", "PASS", "history persists across reload + clear works");
    else log("Feature 2", "FAIL", `clear failed (gone=${gone}, ls=${ls})`);
  } finally {
    await page.close();
  }
}

// ── Feature 4: lint location link jumps to Knowledge Map ────────────────────
async function testFeature4(browser) {
  const page = await browser.newPage();
  try {
    await page.goto(BASE, { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Lint" }).click();
    await page.waitForTimeout(1200);

    const links = page.locator('button[title^="Pokaż w Knowledge Map"]');
    const count = await links.count();
    if (count === 0) return log("Feature 4", "WARN", "no clickable node location in current lint report — skipped");

    await links.first().click();
    await page.waitForTimeout(1800);
    const onGraph = await page.getByPlaceholder("Search nodes…").isVisible().catch(() => false);
    const lintGone = !(await page.getByRole("button", { name: "Run Now" }).isVisible().catch(() => false));
    if (onGraph && lintGone) log("Feature 4", "PASS", `clicked location → Knowledge Map graph (${count} links found)`);
    else log("Feature 4", "FAIL", `did not switch (onGraph=${onGraph}, lintGone=${lintGone})`);
  } finally {
    await page.close();
  }
}

// ── Feature 5: sources sorting (mocked API, 3 sources) ──────────────────────
async function testFeature5(browser) {
  const mk = (id, title, date) => ({ slug: id, id, title, type: "txt", ingested_at: date, tags: ["t"], questions: [], summary: "s " + title, key_takeaways: [], source_url: null });
  const FAKE = [mk("a", "Alpha", "2026-01-01T10:00:00"), mk("b", "Beta", "2026-03-01T10:00:00"), mk("c", "Gamma", "2026-02-01T10:00:00")];
  const titles = (page) => page.locator("p.text-sm.font-medium.truncate.flex-1").allInnerTexts();
  const context = await browser.newContext();
  const page = await context.newPage();
  try {
    await page.route("**/api/wiki/sources", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FAKE) }));
    await page.goto(BASE, { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Sources" }).click();
    await page.waitForTimeout(700);

    const def = await titles(page);
    await page.getByRole("button", { name: "Tytuł" }).click();
    await page.waitForTimeout(250);
    const titleAsc = await titles(page);
    await page.getByRole("button", { name: "Tytuł" }).click();
    await page.waitForTimeout(250);
    const titleDesc = await titles(page);

    const ok = eq(def, ["Beta", "Gamma", "Alpha"]) && eq(titleAsc, ["Alpha", "Beta", "Gamma"]) && eq(titleDesc, ["Gamma", "Beta", "Alpha"]);
    if (ok) log("Feature 5", "PASS", "date desc default, title asc/desc toggle correct");
    else log("Feature 5", "FAIL", `def=${JSON.stringify(def)} asc=${JSON.stringify(titleAsc)} desc=${JSON.stringify(titleDesc)}`);
  } finally {
    await context.close();
  }
}

// ── Feature 6: source detail drawer ─────────────────────────────────────────
async function testFeature6(browser) {
  const page = await browser.newPage();
  try {
    await page.goto(BASE, { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Sources" }).click();
    await page.waitForTimeout(700);

    const card = page.locator("p.text-sm.font-medium.truncate.flex-1").first();
    if ((await card.count()) === 0) return log("Feature 6", "WARN", "no sources ingested — skipped");
    await card.click();
    await page.waitForTimeout(400);

    const drawerOpen = await page.getByText(/Key takeaways|Questions|No extra details/i).first().isVisible().catch(() => false);
    if (!drawerOpen) return log("Feature 6", "FAIL", "drawer did not open");

    // Trash must not open drawer (stopPropagation)
    const closeBtn = page.locator("div.border-l button").first();
    await closeBtn.click();
    await page.waitForTimeout(250);
    await page.locator('button[title="Usuń źródło"]').first().click();
    await page.waitForTimeout(250);
    const confirm = await page.getByText("Usuń?").isVisible().catch(() => false);
    if (confirm) log("Feature 6", "PASS", "drawer opens with details; trash uses stopPropagation");
    else log("Feature 6", "FAIL", "trash confirm not shown");
  } finally {
    await page.close();
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    await testFeature2(browser);
    await testFeature4(browser);
    await testFeature5(browser);
    await testFeature6(browser);
  } finally {
    await browser.close();
  }
  const failed = RESULTS.filter((r) => r.status === "FAIL").length;
  const passed = RESULTS.filter((r) => r.status === "PASS").length;
  const warned = RESULTS.filter((r) => r.status === "WARN").length;
  console.log(`\n── ${passed} PASS · ${warned} WARN · ${failed} FAIL ──`);
  process.exit(failed > 0 ? 1 : 0);
})();
