import { expect, test } from "@playwright/test";

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
  await page.getByRole("button", { name: "Confirm sandbox execution" }).click();
  await expect(page.getByRole("status").filter({ hasText: "COMPLETED" })).toBeVisible({
    timeout: 100_000,
  });
  await expect(page.getByLabel("Measured discovery history")).toBeVisible();
  await page.goto("/minimization");
  await expect(page.getByRole("combobox", { name: "Observed failure" })).not.toHaveValue("");
  await page.getByRole("spinbutton", { name: "Trial budget" }).fill("40");
  await page.getByRole("button", { name: "Reduce sequence", exact: true }).click();
  await page.getByRole("button", { name: "Confirm sandbox execution" }).click();
  await expect(page.getByRole("status").filter({ hasText: "COMPLETED" })).toBeVisible({
    timeout: 100_000,
  });
  await expect(page.getByLabel("Reduced failure sequence")).toContainText("payment_ack_loss");
  await page.goto("/ai");
  await page.getByRole("button", { name: "Test hypotheses", exact: true }).click();
  await page.getByRole("button", { name: "Confirm sandbox execution" }).click();
  await expect(page.getByRole("status").filter({ hasText: "COMPLETED" })).toBeVisible({
    timeout: 100_000,
  });
  await expect(page.getByLabel("Competing causal hypotheses")).toBeVisible();
  await expect(page.getByText("SUPPORTED", { exact: true }).first()).toBeVisible();
  await page.goto("/patches");
  await page.getByRole("button", { name: "Prepare candidate", exact: true }).click();
  await page.getByRole("button", { name: "Confirm sandbox execution" }).click();
  await expect(page.getByRole("status").filter({ hasText: "COMPLETED" })).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByLabel("Candidate source diff")).toContainText("POLICIES");
  await page.goto("/verification");
  await page.getByRole("button", { name: "Verify candidate", exact: true }).click();
  await page.getByRole("button", { name: "Confirm sandbox execution" }).click();
  await expect(page.getByRole("status").filter({ hasText: "COMPLETED" })).toBeVisible({
    timeout: 120_000,
  });
  const report = page.getByLabel("Verification outcome");
  await expect(report).toBeVisible();
  await expect(page.getByText(/^[1-9][0-9]* recorded artifacts$/)).toBeVisible();
  await expect(report).toContainText(
    /INFRASTRUCTURE_ERROR|PATCH_PASSES_TESTED_SCENARIOS|PATCH_FAILS_VERIFICATION|INCONCLUSIVE/,
  );
  // The test asserts the evidence report, not that missing Docker constitutes a verified repair.
  await page.screenshot({ path: "test-results/research-verification.png", fullPage: true });
});
