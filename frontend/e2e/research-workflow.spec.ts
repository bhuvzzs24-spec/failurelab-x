import { expect, test, type Page } from "@playwright/test";

async function confirmNewExecution(page: Page) {
  const response = page.waitForResponse((r) =>
    r.request().method() === "POST" && /\/research\/projects\/[^/]+\/jobs$/.test(r.url())
  );
  await page.getByRole("button", { name: "Confirm sandbox execution" }).click();
  const created = await response;
  expect(created.status()).toBe(202);
  const row = await created.json();
  await expect(page.getByRole("combobox", { name: "Research job", exact: true })).toHaveValue(row.id);
  await expect(page.getByRole("status").filter({ hasText: "COMPLETED" })).toBeVisible({ timeout: 120_000 });
}

test("real research discovery → reduction → causal evidence → candidate → independent verification availability", async ({
  page,
}) => {
  test.setTimeout(300_000);
  await page.goto("/explorer");
  await page
    .getByRole("combobox", { name: "Project", exact: true })
    .selectOption({ label: "FailureLab demo" });
  await page.getByRole("combobox", { name: "Benchmark defect" }).selectOption("payment_ack_loss");
  await page.getByRole("spinbutton", { name: "Trial budget" }).fill("12");
  await page.getByRole("button", { name: "Start discovery", exact: true }).click();
  await confirmNewExecution(page);
  await expect(page.getByLabel("Measured discovery history")).toBeVisible();
  await page.goto("/minimization");
  await expect(page.getByRole("combobox", { name: "Observed failure" })).not.toHaveValue("");
  await page.getByRole("spinbutton", { name: "Trial budget" }).fill("40");
  await page.getByRole("button", { name: "Reduce sequence", exact: true }).click();
  await confirmNewExecution(page);
  await expect(page.getByLabel("Reduced failure sequence")).toContainText("payment_ack_loss");
  await page.goto("/ai");
  await page.getByRole("button", { name: "Test hypotheses", exact: true }).click();
  await confirmNewExecution(page);
  await expect(page.getByLabel("Competing causal hypotheses")).toBeVisible();
  await expect(page.getByText("SUPPORTED", { exact: true }).first()).toBeVisible();
  await page.goto("/patches");
  await page.getByRole("button", { name: "Prepare candidate", exact: true }).click();
  await confirmNewExecution(page);
  await expect(page.getByLabel("Candidate source diff")).toContainText("POLICIES");
  await page.goto("/verification");
  await page.getByRole("button", { name: "Verify candidate", exact: true }).click();
  await confirmNewExecution(page);
  const report = page.getByLabel("Verification outcome");
  await expect(report).toBeVisible();
  await expect(page.getByText(/^[1-9][0-9]* recorded artifacts$/)).toBeVisible();
  await expect(report).toContainText(
    /INFRASTRUCTURE_ERROR|PATCH_PASSES_TESTED_SCENARIOS|PATCH_FAILS_VERIFICATION|INCONCLUSIVE/,
  );
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export record", exact: true }).click();
  const download = await downloaded;
  const fs = await import("node:fs/promises");
  const bundle = JSON.parse(await fs.readFile((await download.path())!, "utf8"));
  expect(bundle.format).toBe("failurelab-evidence-v1");
  expect(bundle.artifacts.length).toBeGreaterThan(0);
  expect(bundle.source_trial.classification).toBe("APPLICATION_VIOLATION");
  expect(bundle.candidate.patch).toContain("POLICIES");
  // The test asserts the evidence report, not that missing Docker constitutes a verified repair.
  await page.screenshot({ path: "test-results/research-verification.png", fullPage: true });
});

test("read-only preview permits inspection and blocks all control mutations", async ({ page }) => {
  const origin = process.env.READONLY_BASE_URL;
  test.skip(!origin, "Read-only preview origin was not supplied");
  await page.goto(origin + "/experiments");
  await expect(page.getByText(/Read-only demonstration/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Review & run", exact: true })).toBeDisabled();
  const response = await page.request.post(origin + "/api/backend/api/v1/projects", {
    headers: { Origin: origin! },
    data: { name: "must-not-be-created" },
  });
  expect(response.status()).toBe(403);
  await page.goto(origin + "/graph");
  await expect(page.getByTestId("service-graph")).toBeVisible();
  await page.screenshot({ path: "test-results/read-only-preview.png", fullPage: true });
});
