// Test UX Round 2 — weryfikacja 7 poprawek
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE = "http://localhost:5174";
const R = [];

function log(label, status, detail = "") {
  const icon = status === "PASS" ? "✅" : status === "FAIL" ? "❌" : "⚠️";
  const msg = `${icon} ${label}: ${detail}`;
  console.log(msg);
  R.push({ label, status, detail });
}

async function ingestTestFile(page) {
  const filePath = path.join(__dirname, "_test_content_r2.txt");
  fs.writeFileSync(filePath, `# Knowledge Management System\n\nThe KMS uses structured wiki storage.\nEntities and concepts are extracted by LLM.\nClaims link entities to sources.\n`.trim());
  await page.locator("nav button").filter({ hasText: "Sources" }).click();
  await page.waitForTimeout(300);
  await page.locator('input[type="file"]').setInputFiles(filePath);
  await page.locator("text=Ingested").waitFor({ timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(800);
  try { fs.unlinkSync(filePath); } catch (_) {}
}

async function main() {
  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const page = await browser.newPage();
  await page.goto(BASE, { waitUntil: "networkidle" });

  // ── Ingest test content ──────────────────────────────────────────────────
  console.log("\n── Ingest test content…");
  await ingestTestFile(page);
  const ingestOk = await page.locator("text=Ingested").count() > 0;
  log("Ingest", ingestOk ? "PASS" : "WARN", ingestOk ? "OK" : "Brak tekstu Ingested");

  // ── A: Metryki — pytanie i sprawdzenie naliczenia ────────────────────────
  console.log("\n── A: Metrics — zadaję pytanie w Wiki Chat…");
  await page.locator("nav button").filter({ hasText: "Wiki Chat" }).click();
  await page.waitForTimeout(300);
  const input = page.locator('input[placeholder*="wiki"]');
  await input.fill("What is the Knowledge Management System?");
  await page.keyboard.press("Enter");
  await page.locator("text=Confidence:").waitFor({ timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(500);

  await page.locator("nav button").filter({ hasText: "Metrics" }).click();
  await page.waitForTimeout(600);
  const noDataMsg = await page.locator("text=Brak danych sesji").count();
  const metricsTable = await page.locator("table tbody tr").count();

  if (metricsTable > 0) {
    log("A — Metryki naliczone", "PASS", `${metricsTable} wiersz(y) w tabeli`);
  } else if (noDataMsg > 0) {
    log("A — Metryki naliczone", "FAIL", "Nadal 'Brak danych sesji' po zadaniu pytania");
  } else {
    log("A — Metryki naliczone", "WARN", "Brak tabeli i brak komunikatu — niejasny stan");
  }

  // ── C+D: Wiki Chat — source cards + Pipeline Trace ──────────────────────
  console.log("\n── C+D: Wiki Chat — karty źródeł + Pipeline Trace…");
  await page.locator("nav button").filter({ hasText: "Wiki Chat" }).click();
  await page.waitForTimeout(300);

  // D: placeholder stages should show names (not "waiting")
  const waitingCount = await page.locator("text=waiting").count();
  const stageNameInPlaceholder = await page.locator("text=Intent Parser").count();
  if (stageNameInPlaceholder > 0) {
    log("D — Pipeline Trace placeholder", "PASS", "Widoczne nazwy stagów (Intent Parser)");
  } else if (waitingCount > 0) {
    log("D — Pipeline Trace placeholder", "FAIL", `${waitingCount}x "waiting…" zamiast nazw stagów`);
  } else {
    log("D — Pipeline Trace placeholder", "WARN", "Brak ani 'waiting' ani 'Intent Parser'");
  }

  // D: subtitle "Jak system przetwarza"
  const subtitle = await page.locator("text=Jak system przetwarza").count();
  log("D — Pipeline Trace podtytuł", subtitle > 0 ? "PASS" : "FAIL",
    subtitle > 0 ? "Widoczny podtytuł" : "Brak podtytułu 'Jak system przetwarza'");

  // Wait for answer (already asked above, but if we navigated away, ask again)
  const answerAlready = await page.locator(".whitespace-pre-wrap").count();
  if (answerAlready === 0) {
    await input.fill("What is the Knowledge Management System?");
    await page.keyboard.press("Enter");
    await page.locator("text=Confidence:").waitFor({ timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(500);
  }

  // C: no raw claim IDs in Sources section
  const rawClaimIds = await page.locator("text=/\\[claim:cl_/").count();
  if (rawClaimIds === 0) {
    log("C — Brak raw claim IDs", "PASS", "Nie widać [claim:cl_xxx]");
  } else {
    log("C — Brak raw claim IDs", "FAIL", `${rawClaimIds}x [claim:cl_] widoczne`);
  }

  // C: source summary visible (line-clamp-2 paragraph)
  const sourceCards = await page.locator("div.border.border-border.rounded-md.px-3.py-2").count();
  log("C — Karty źródeł", sourceCards > 0 ? "PASS" : "WARN",
    `${sourceCards} kart źródeł z nowym designem`);

  // ── E: Knowledge Map — filter bug ────────────────────────────────────────
  console.log("\n── E: Knowledge Map — filter reset bug…");
  await page.locator("nav button").filter({ hasText: "Knowledge Map" }).click();
  await page.waitForTimeout(2000);

  const nodeCountBefore = await page.locator(".react-flow__node").count();
  if (nodeCountBefore === 0) {
    log("E — Knowledge Map data", "WARN", "Brak węzłów — nie można przetestować filtrów");
  } else {
    // Use filter bar container to scope buttons — avoids matching nav "Sources" button
    const filterBar = page.locator("div.border-b.border-border").filter({ has: page.locator("button", { hasText: "Entities" }) }).first();
    const filterEntities = filterBar.locator("button", { hasText: "Entities" });
    const filterConcepts = filterBar.locator("button", { hasText: "Concepts" });
    const filterSources = filterBar.locator("button", { hasText: "Sources" });

    // Uncheck all 3 filter buttons
    for (const btn of [filterEntities, filterConcepts, filterSources]) {
      await btn.click().catch(() => {});
      await page.waitForTimeout(100);
    }
    await page.waitForTimeout(500);

    // Check that filter bar is still visible (not stuck on blank screen)
    const filtersStillVisible = await filterBar.locator("button", { hasText: "Entities" }).count();
    const resetBtn = await page.locator("text=Włącz wszystkie filtry").count();

    if (filtersStillVisible > 0 && resetBtn > 0) {
      log("E — Filter reset button", "PASS", "Przycisk 'Włącz wszystkie filtry' widoczny");
    } else if (filtersStillVisible > 0) {
      log("E — Filter reset button", "WARN", "Filtry widoczne ale brak przycisku reset");
    } else {
      log("E — Filter reset button", "FAIL", "Filtry zniknęły — bug nadal obecny");
    }

    // Click reset button and verify nodes come back
    if (resetBtn > 0) {
      await page.locator("text=Włącz wszystkie filtry").click();
      await page.waitForTimeout(500);
      const nodeCountAfter = await page.locator(".react-flow__node").count();
      log("E — Po reset filtrów", nodeCountAfter > 0 ? "PASS" : "FAIL",
        `${nodeCountAfter} węzłów po włączeniu filtrów`);
    }
  }

  // ── F: Knowledge Map — legenda ────────────────────────────────────────────
  console.log("\n── F: Knowledge Map — legenda…");
  const conceptLegend = await page.locator("text=Concept").count();
  const sourceLegend = await page.locator("text=Source").count();
  if (conceptLegend > 0 && sourceLegend > 0) {
    log("F — Legenda kolorów", "PASS", "Widoczna 'Concept' i 'Source' w legendzie");
  } else {
    log("F — Legenda kolorów", "FAIL", `Concept: ${conceptLegend}, Source: ${sourceLegend}`);
  }

  // ── G: Lint — baner + czytelne typy ──────────────────────────────────────
  console.log("\n── G: Lint — baner i czytelność…");
  await page.locator("nav button").filter({ hasText: "Lint" }).click();
  await page.waitForTimeout(300);

  const lintBanner = await page.locator("text=Co to jest Lint?").count();
  log("G — Lint baner", lintBanner > 0 ? "PASS" : "FAIL",
    lintBanner > 0 ? "Baner widoczny" : "Brak banera 'Co to jest Lint?'");

  // Run lint and check readability
  await page.locator("button").filter({ hasText: "Run Now" }).click();
  await page.locator("text=Run Now").waitFor({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1000);

  const rawTypeVisible = await page.locator("text=empty_description").count();
  const plTypeVisible = await page.locator("text=Brak opisu").count();

  if (plTypeVisible > 0 && rawTypeVisible === 0) {
    log("G — Czytelne typy błędów", "PASS", "Widoczne PL nazwy, brak raw kodu");
  } else if (rawTypeVisible > 0) {
    log("G — Czytelne typy błędów", "FAIL", `Nadal widoczne raw: empty_description (${rawTypeVisible}x)`);
  } else {
    log("G — Czytelne typy błędów", "WARN", "Brak żadnych issues po Lint run");
  }

  // ── SUMMARY ──────────────────────────────────────────────────────────────
  console.log("\n═══════════════════════════════════════════");
  console.log("  WYNIKI — UX Round 2");
  console.log("═══════════════════════════════════════════");
  R.forEach((r) => {
    const icon = r.status === "PASS" ? "✅" : r.status === "FAIL" ? "❌" : "⚠️";
    console.log(`${icon} ${r.label}: ${r.detail}`);
  });
  const pass = R.filter((r) => r.status === "PASS").length;
  const fail = R.filter((r) => r.status === "FAIL").length;
  const warn = R.filter((r) => r.status === "WARN").length;
  console.log(`\nRazem: ${pass} PASS, ${warn} WARN, ${fail} FAIL`);
  console.log("═══════════════════════════════════════════\n");

  await browser.close();
}

main().catch((e) => { console.error("Fatal:", e); process.exit(1); });
