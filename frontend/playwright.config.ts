import { defineConfig, devices } from "@playwright/test";

// Runs the smoke suite against a live backend + frontend. The backend is pointed
// at the bundled demo corpus so the tests don't depend on your own wiki_data.
// Already-running dev servers are reused.
export default defineConfig({
  testDir: "./e2e",
  // The @screenshots suite runs a paid query and writes files — opt in with
  // RUN_SCREENSHOTS=1. Everything else is the free smoke suite.
  grepInvert: process.env.RUN_SCREENSHOTS ? undefined : /@screenshots/,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "python -m uvicorn main:app --port 8000",
      cwd: "../backend",
      env: { WIKI_DATA_DIR: "wiki_data/.example" },
      url: "http://localhost:8000/health",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
