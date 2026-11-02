import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test("redesigned product uses actual records across desktop/mobile and passes accessibility checks", async ({
  page,
}) => {
  test.setTimeout(240_000);
  await mkdir("test-results/product", { recursive: true });
  await page.setViewportSize({ width: 1512, height: 1050 });
  const projects = await page.request.get("/api/backend/api/v1/projects?limit=100");
  expect(projects.ok()).toBe(true);
  const project = (await projects.json()).items.find(
    (p: { name: string }) => p.name === "FailureLab demo",
  );
  expect(project).toBeTruthy();
  const overview = await page.request.get(`/api/backend/api/v1/projects/${project.id}/overview`);
  expect(overview.ok()).toBe(true);
  const data = await overview.json();
  const run = data.latest_runs[0];
  const finding = data.latest_findings[0];
  const jobsResponse = await page.request.get(
    `/api/backend/api/v1/research/projects/${project.id}/jobs?limit=100`,
  );
  expect(jobsResponse.ok()).toBe(true);
  const jobs = (await jobsResponse.json()).items.sort(
    (a: { created_at: number }, b: { created_at: number }) => b.created_at - a.created_at,
  );
  const job = (kind: string) =>
    jobs.find((j: { kind: string; status: string }) => j.kind === kind && j.status === "COMPLETED");
  const routes: [string, string][] = [
    ["/", "command-center"],
    ["/graph", "system-graph"],
    ["/experiments", "experiment-studio"],
    [
      finding ? `/findings?run=${finding.run_id}&finding=${finding.id}` : "/findings",
      "failure-investigator",
    ],
    [run ? `/evidence?run=${run.id}` : "/evidence", "evidence-explorer"],
    [run ? `/replay?run=${run.id}` : "/replay", "failure-replay"],
    ...(["SEARCH", "MINIMIZE", "INVESTIGATE", "REPAIR", "VERIFY", "BENCHMARK"] as const).map(
      (kind): [string, string] => {
        const paths = {
          SEARCH: "explorer",
          MINIMIZE: "minimization",
          INVESTIGATE: "ai",
          REPAIR: "patches",
          VERIFY: "verification",
          BENCHMARK: "benchmarks",
        };
        return [`/${paths[kind]}${job(kind) ? "?job=" + job(kind).id : ""}`, paths[kind]];
      },
    ),
    ["/settings", "settings"],
  ];
  for (const [url, name] of routes) {
    await page.goto(url);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByText("Backend ready", { exact: true })).toBeVisible();
    await expect(page.locator('main[aria-busy="true"]')).toHaveCount(0);
    await page.waitForFunction(() => !document.querySelector('main [aria-busy="true"]'));
    if (name === "system-graph") await expect(page.getByTestId("service-graph")).toBeVisible();
    if (name === "ai" && job("INVESTIGATE"))
      await expect(page.getByRole("tablist", { name: "Competing explanations" })).toBeVisible();
    if (name === "experiment-studio")
      await expect(page.getByLabel("Experiment setup steps")).toBeVisible();
    await page.screenshot({ path: `test-results/product/${name}.png`, fullPage: true });
    const axe = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      axe.violations,
      `${name}: ${JSON.stringify(axe.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })))}`,
    ).toEqual([]);
  }
  await page.goto("/experiments");
  for (let i = 0; i < 3; i++)
    await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel("Experiment scope review")).toBeVisible();
  await page.screenshot({ path: "test-results/product/experiment-review.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  for (const [url, name] of [
    ["/", "mobile-command-center"],
    [`/ai${job("INVESTIGATE") ? "?job=" + job("INVESTIGATE").id : ""}`, "mobile-investigator"],
    [run ? `/evidence?run=${run.id}` : "/evidence", "mobile-evidence"],
  ] as const) {
    await page.goto(url);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForFunction(() => !document.querySelector('main [aria-busy="true"]'));
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      name,
    ).toBe(true);
    await page.screenshot({ path: `test-results/product/${name}.png`, fullPage: true });
  }
});
