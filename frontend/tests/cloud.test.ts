import { expect, it, vi } from "vitest";
import { cloudConfiguration } from "@/lib/cloud-config";
import { bridge } from "@/lib/bridge";
const valid = {
  ACCESS_MODE: "read_only",
  DEPLOYMENT_ENV: "cloud",
  PUBLIC_FRONTEND_ORIGIN: "https://lab.example",
  BACKEND_URL: "https://records.example",
  HOSTED_BACKEND_ORIGIN: "https://records.example",
  API_TOKEN: "unit-viewer-".padEnd(40, "x"),
};
it("requires explicit matching HTTPS origins and server-only viewer configuration", () => {
  expect(cloudConfiguration(valid)).toEqual({
    frontend: "https://lab.example",
    backend: "https://records.example",
    access: "read_only",
  });
  for (const change of [
    { API_TOKEN: "" },
    { ACCESS_MODE: "local" },
    { BACKEND_URL: "http://localhost:8000" },
    { HOSTED_BACKEND_ORIGIN: "https://other.example" },
    { PUBLIC_FRONTEND_ORIGIN: "https://replace.invalid" },
    { NEXT_PUBLIC_API_TOKEN: "not-permitted" },
  ])
    expect(() => cloudConfiguration({ ...valid, ...change })).toThrow();
});
it("never falls back to localhost for a public backend request", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const result = await bridge(new Request("https://lab.example/api/backend/ready"), ["ready"], {
    ...valid,
    BACKEND_URL: undefined,
  });
  expect(result.status).toBe(503);
  expect(fetcher).not.toHaveBeenCalled();
});
it("enforces cloud safeguards even when the platform uses an internal localhost URL", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const result = await bridge(
    new Request("http://localhost/ready", { headers: { Host: "lab.example" } }),
    ["ready"],
    {
      ...valid,
      VERCEL: "1",
      BACKEND_URL: "http://api:8000",
      HOSTED_BACKEND_ORIGIN: "http://api:8000",
    },
  );
  expect(result.status).toBe(503);
  expect(fetcher).not.toHaveBeenCalled();
});
it("allows read-only cloud data and blocks execution before contacting the backend", async () => {
  const fetcher = vi.fn().mockResolvedValue(Response.json({ status: "ready" }));
  vi.stubGlobal("fetch", fetcher);
  expect((await bridge(new Request("https://lab.example/test"), ["ready"], valid)).status).toBe(
    200,
  );
  expect(fetcher.mock.calls[0][0].origin).toBe("https://records.example");
  fetcher.mockClear();
  expect(
    (
      await bridge(
        new Request("https://lab.example/test", {
          method: "POST",
          headers: { Origin: "https://lab.example", "Content-Type": "application/json" },
          body: "{}",
        }),
        ["api", "v1", "projects"],
        valid,
      )
    ).status,
  ).toBe(403);
  expect(fetcher).not.toHaveBeenCalled();
});
