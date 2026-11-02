import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHash } from "node:crypto";
let folder: string;
const env = {
  DATA_MODE: "recorded_demo",
  ACCESS_MODE: "read_only",
  DEPLOYMENT_ENV: "frontend_demo",
};
beforeEach(async () => {
  vi.resetModules();
  folder = await mkdtemp(join(tmpdir(), "failurelab-demo-test-"));
  vi.spyOn(process, "cwd").mockReturnValue(folder);
});
afterEach(async () => {
  await rm(folder, { recursive: true, force: true });
});
async function write(status = "COMPLETED", checksum = true) {
  await mkdir(join(folder, "demo-data"));
  const data = JSON.stringify({
    format: "failurelab-frontend-demo-v1",
    captured_at: 100,
    source_revision: "a".repeat(40),
    source_snapshot_sha256: "b".repeat(64),
    notice: "Unit fixture; not an experiment result",
    resources: { "api/v1/projects/fixture/runs": { items: [{ status }] } },
  });
  await writeFile(join(folder, "demo-data/recorded.json"), data);
  await writeFile(
    join(folder, "demo-data/recorded.json.sha256"),
    checksum ? createHash("sha256").update(data).digest("hex") : "tampered",
  );
}
it("serves a bounded integrity-checked file and calls no external API", async () => {
  await write();
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const { bridge } = await import("@/lib/bridge");
  const result = await bridge(new Request("https://preview.example/ready"), ["ready"], env);
  expect(result.status).toBe(200);
  expect((await result.json()).live_backend).toBe(false);
  expect(fetcher).not.toHaveBeenCalled();
});
it("fails honestly when evidence is absent and refuses writes before reading it", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const { bridge } = await import("@/lib/bridge");
  expect(
    (await bridge(new Request("https://preview.example/test"), ["api", "v1", "projects"], env))
      .status,
  ).toBe(503);
  expect(
    (
      await bridge(
        new Request("https://preview.example/test", { method: "POST" }),
        ["api", "v1", "projects"],
        env,
      )
    ).status,
  ).toBe(403);
  expect(fetcher).not.toHaveBeenCalled();
});
it("rejects modified evidence", async () => {
  await write("COMPLETED", false);
  const { loadRecordedDemo } = await import("@/lib/recorded-demo");
  await expect(loadRecordedDemo()).rejects.toThrow("integrity");
});
it("rejects captured active jobs instead of portraying them as live work", async () => {
  await write("RUNNING");
  const { loadRecordedDemo } = await import("@/lib/recorded-demo");
  await expect(loadRecordedDemo()).rejects.toThrow("active execution");
});
