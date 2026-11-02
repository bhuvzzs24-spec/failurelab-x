import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e-demo",
  workers: 1,
  fullyParallel: false,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  outputDir: "test-results/demo",
  reporter: [["list"]],
  use: {
    baseURL: process.env.DEMO_BASE_URL ?? "http://127.0.0.1:3004",
    reducedMotion: "reduce",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "recorded-chrome",
      use: { ...devices["Desktop Chrome"], channel: process.env.PLAYWRIGHT_CHANNEL ?? "chrome" },
    },
  ],
});
