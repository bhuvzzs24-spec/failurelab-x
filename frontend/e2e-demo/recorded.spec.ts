import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const pages = [
  "/",
  "/graph",
  "/experiments",
  "/findings",
  "/evidence",
  "/replay",
  "/explorer",
  "/ai",
  "/minimization",
  "/patches",
  "/verification",
  "/benchmarks",
  "/settings",
];
test("all recorded pages are honest, accessible and network-isolated; real evidence remains inspectable", async ({
  page,
  baseURL,
}) => {
  await mkdir("test-results/demo/screenshots", { recursive: true });
  const external: string[] = [],
    errors: string[] = [],
    failed: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).origin !== new URL(baseURL!).origin) external.push(request.url());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    if (response.status() >= 400) failed.push(response.url() + " " + response.status());
  });
  const health = await page.request.get("/api/health");
  expect(await health.json()).toEqual({ status: "recorded_demo_ready", live_backend: false });
  const session = await page.request.get("/api/backend/api/v1/session");
  expect(await session.json()).toMatchObject({
    role: "viewer",
    data_source: "recorded_demo",
    can_execute: false,
    can_manage: false,
    live_backend: false,
  });
  const project = (await (await page.request.get("/api/backend/api/v1/projects")).json()).items[0];
  expect(project.name).toBe("FailureLab demo");
  const overview = await (
    await page.request.get(`/api/backend/api/v1/projects/${project.id}/overview`)
  ).json();
  const jobs = (
    await (
      await page.request.get(`/api/backend/api/v1/research/projects/${project.id}/jobs?limit=100`)
    ).json()
  ).items.sort(
    (a: { created_at: number }, b: { created_at: number }) => b.created_at - a.created_at,
  );
  const kind: Record<string, string> = {
    "/explorer": "SEARCH",
    "/ai": "INVESTIGATE",
    "/minimization": "MINIMIZE",
    "/patches": "REPAIR",
    "/verification": "VERIFY",
    "/benchmarks": "BENCHMARK",
  };
  await page.setViewportSize({ width: 1512, height: 1050 });
  for (const path of pages) {
    const selected = jobs.find(
      (job: { kind: string; status: string }) =>
        job.kind === kind[path] && job.status === "COMPLETED",
    );
    const run = overview.latest_runs[0];
    const query = selected
      ? `?job=${selected.id}`
      : ["/findings", "/evidence", "/replay", "/experiments"].includes(path) && run
        ? `?run=${run.id}`
        : "";
    await page.goto(path + query);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator(".demo-banner")).toContainText("No live backend");
    await page.waitForFunction(() => !document.querySelector('main [aria-busy="true"]'));
    await expect(page.locator('main [role="alert"]')).toHaveCount(0);
    await expect(page.getByText("Backend ready", { exact: true })).toHaveCount(0);
    await expect(
      page.getByRole("button", {
        name: /^(Review & run|Start discovery|Reduce sequence|Test hypotheses|Prepare candidate|Verify candidate|Create project|Register service|New|Cancel job)$/,
      }),
    ).toHaveCount(0);
    if (path === "/graph") await expect(page.locator(".service-node>strong")).toHaveCount(4);
    if (path === "/experiments")
      await expect(page.getByLabel("Recorded experiment configuration")).toBeVisible();
    if (path === "/settings")
      await expect(page.getByText("Live execution", { exact: true })).toBeVisible();
    await page.screenshot({
      path: `test-results/demo/screenshots/${path.slice(1) || "dashboard"}.png`,
      fullPage: true,
    });
    const axe = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      axe.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })),
      path,
    ).toEqual([]);
  }
  await page.goto(
    `/verification?job=${jobs.find((j: { kind: string; status: string }) => j.kind === "VERIFY" && j.status === "COMPLETED").id}`,
  );
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export record", exact: true }).click();
  expect((await download).suggestedFilename()).toContain("failurelab-evidence-");
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/", "/ai", "/evidence", "/settings"]) {
    await page.goto(path);
    await expect(page.locator(".demo-banner")).toBeVisible();
    await page.waitForFunction(() => !document.querySelector('main [aria-busy="true"]'));
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      path,
    ).toBe(true);
    await page.screenshot({
      path: `test-results/demo/screenshots/mobile-${path.slice(1) || "dashboard"}.png`,
      fullPage: true,
    });
  }
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
  expect(failed).toEqual([]);
  const denied = await page.request.post("/api/backend/api/v1/projects", {
    data: { name: "must-not-create" },
  });
  expect(denied.status()).toBe(403);
  const missing = await page.request.get("/api/backend/api/v1/runs/not-recorded/summary");
  expect(missing.status()).toBe(404);
  expect(await missing.text()).toContain("not included");
});

test("missing recorded evidence yields an honest unavailable state on every page", async ({
  page,
}) => {
  const origin = process.env.DEMO_MISSING_URL;
  test.skip(!origin, "Missing-evidence instance was not supplied");
  for (const path of pages) {
    await page.goto(origin + path);
    await expect(
      page.getByRole("heading", { name: "Recorded evidence is unavailable", exact: true }),
    ).toBeVisible();
    await expect(page.locator(".demo-banner")).toContainText("No live backend");
    await expect(page.getByText("Backend ready", { exact: true })).toHaveCount(0);
  }
  await page.screenshot({
    path: "test-results/demo/screenshots/missing-evidence.png",
    fullPage: true,
  });
  expect((await page.request.get(origin + "/api/health")).status()).toBe(503);
  expect(
    (await page.request.post(origin + "/api/backend/api/v1/projects", { data: {} })).status(),
  ).toBe(403);
});
