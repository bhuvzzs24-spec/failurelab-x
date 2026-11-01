import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("real registered demo → graph → controlled experiment → finding → evidence", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Command center.", exact: true })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Project", exact: true })).toContainText(
    "FailureLab demo",
  );
  await page
    .getByRole("combobox", { name: "Project", exact: true })
    .selectOption({ label: "FailureLab demo" });
  await expect(page.getByText("Backend ready", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "System graph", exact: true }).click();
  await expect(page.getByTestId("service-graph")).toBeVisible();
  for (const name of ["gateway", "order", "payment", "inventory"])
    await expect(page.locator(".service-node>strong").filter({ hasText: name })).toBeVisible();
  await page.locator(".react-flow__node").filter({ hasText: "payment" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "payment service", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Close dialog", exact: true }).click();
  await page.getByRole("link", { name: "Experiment studio", exact: true }).click();
  await page.getByRole("button", { name: "Review & run", exact: true }).click();
  await expect(page.getByRole("alertdialog")).toContainText("Target: payment");
  await page.getByRole("button", { name: "Start sandbox experiment", exact: true }).click();
  await expect(page).toHaveURL(/\/experiments\?run=/);
  await expect(page.locator(".studio-monitor .status-badge").first()).toHaveText(/COMPLETED/, {
    timeout: 100_000,
  });
  const finding = page.locator(".run-finding").first();
  await expect(finding).toContainText("Cross-service correctness invariant violated");
  await finding.click();
  await expect(
    page.getByRole("heading", { name: "Charged payment implies finalized order", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Observed fact", { exact: true }).first()).toBeVisible();
  await expect(page.locator(".state-service").filter({ hasText: "payment" })).toContainText(
    "charged",
  );
  await expect(page.locator(".state-service").filter({ hasText: "order" })).toContainText(
    "pending",
  );
  await page.getByRole("link", { name: "All events", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Evidence explorer.", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".artifact-list>button")).not.toHaveCount(0);
  await page
    .getByRole("combobox", { name: "Filter artifact kind", exact: true })
    .selectOption("snapshot");
  await expect(page.getByLabel("Artifact payload")).toContainText('"state"');
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download JSON", exact: true }).click();
  expect((await download).suggestedFilename()).toMatch(/^failurelab-artifact-.*\.json$/);
  await page.goto("/");
  await expect(
    page.locator(".metric-card").filter({ hasText: "Invariant violations" }),
  ).not.toContainText("No data");
  await expect(page.locator(".finding-preview-list")).toContainText(
    "Cross-service correctness invariant violated",
  );
  await page.screenshot({ path: "test-results/command-center.png", fullPage: true });
});

test("responsive navigation, command palette and accessible research states", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open navigation", exact: true }).click();
  await page.getByRole("link", { name: /AI investigator/ }).click();
  await expect(page.getByRole("heading", { name: "AI investigator.", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Test hypotheses", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.getByRole("button", { name: "Open command palette", exact: true }).click();
  await page.getByRole("textbox", { name: "Search pages", exact: true }).fill("Evidence");
  await page.getByRole("button", { name: "Evidence explorer", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Evidence explorer.", exact: true }),
  ).toBeVisible();
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
});

test("all thirteen workspaces render their real or accurately unavailable state", async ({
  page,
}) => {
  for (const [path, title] of [
    ["/", "Command center."],
    ["/graph", "System graph."],
    ["/experiments", "Experiment studio."],
    ["/findings", "Failure investigator."],
    ["/evidence", "Evidence explorer."],
    ["/replay", "Failure replay."],
    ["/ai", "AI investigator."],
    ["/minimization", "Minimal failure sequence."],
    ["/verification", "Fix verification lab."],
    ["/explorer", "Experiment explorer."],
    ["/patches", "Patch review."],
    ["/benchmarks", "Benchmark dashboard."],
    ["/settings", "Settings & projects."],
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
    await expect(
      page.getByRole("alert").filter({ hasText: "Backend data is unavailable" }),
    ).toHaveCount(0);
  }
});
