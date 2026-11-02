import { expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { recordedResponse, validateDemoEnvironment, type LoadedDemo } from "@/lib/recorded-demo";
import { AccessProvider, AccessNotice } from "@/components/access";
import { Button } from "@/components/ui/button";

const env = {
  DATA_MODE: "recorded_demo",
  ACCESS_MODE: "read_only",
  DEPLOYMENT_ENV: "frontend_demo",
  VERCEL: "1",
  VERCEL_ENV: "preview",
};
const fixture: LoadedDemo = {
  sha256: "b".repeat(64),
  data: {
    format: "failurelab-frontend-demo-v1",
    captured_at: 100,
    source_revision: "a".repeat(40),
    source_snapshot_sha256: "c".repeat(64),
    notice: "Unit fixture only; never a measured experiment",
    resources: {
      "api/v1/projects": { items: [{ id: "fixture-project", name: "Unit fixture" }] },
      "api/v1/projects/fixture-project/runs": {
        items: [
          { id: "fixture-run", status: "COMPLETED" },
          { id: "fixture-failed", status: "FAILED" },
        ],
      },
      "api/v1/research/projects/fixture-project/jobs": {
        items: [{ id: "fixture-job", status: "COMPLETED" }],
      },
      "api/v1/research/projects/fixture-project/trials": {
        items: [{ id: "fixture-trial", job_id: "fixture-job" }],
      },
    },
  },
};
it("requires a backend-free Preview-only configuration", () => {
  expect(() => validateDemoEnvironment(env)).not.toThrow();
  for (const change of [
    { VERCEL_ENV: "production" },
    { ACCESS_MODE: "local" },
    { BACKEND_URL: "https://unused.example" },
    { API_TOKEN: "not-allowed" },
    { DATABASE_URL: "not-allowed" },
    { NEXT_PUBLIC_API_TOKEN: "not-allowed" },
  ])
    expect(() => validateDemoEnvironment({ ...env, ...change })).toThrow();
});
it("serves only frozen viewer access and never advertises a healthy live backend", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const session = await recordedResponse(
    new Request("https://preview.example/test"),
    ["api", "v1", "session"],
    fixture,
  ).json();
  expect(session).toMatchObject({
    role: "viewer",
    can_execute: false,
    can_manage: false,
    read_only: true,
    data_source: "recorded_demo",
    live_backend: false,
    captured_at: 100,
  });
  const health = await recordedResponse(
    new Request("https://preview.example/test"),
    ["ready"],
    fixture,
  ).json();
  expect(health.status).toBe("recorded_demo");
  expect(fetcher).not.toHaveBeenCalled();
});
it("paginates and filters captured collections and resolves original IDs", async () => {
  const response = recordedResponse(
    new Request("https://preview.example/test?status=FAILED&limit=1&offset=0"),
    ["api", "v1", "projects", "fixture-project", "runs"],
    fixture,
  );
  expect(await response.json()).toMatchObject({
    total: 1,
    items: [{ id: "fixture-failed", status: "FAILED" }],
  });
  expect(
    await recordedResponse(
      new Request("https://preview.example/test"),
      ["api", "v1", "runs", "fixture-run"],
      fixture,
    ).json(),
  ).toMatchObject({ id: "fixture-run" });
  expect(
    await recordedResponse(
      new Request("https://preview.example/test"),
      ["api", "v1", "research", "jobs", "fixture-job", "trials"],
      fixture,
    ).json(),
  ).toMatchObject({ total: 1 });
});
it("rejects mutations, unsupported paths and malformed pagination without network access", () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  for (const method of ["POST", "PUT", "PATCH", "DELETE"])
    expect(
      recordedResponse(
        new Request("https://preview.example/test", { method }),
        ["api", "v1", "projects"],
        fixture,
      ).status,
    ).toBe(403);
  expect(
    recordedResponse(new Request("https://preview.example/test"), ["..", "health"], fixture).status,
  ).toBe(404);
  expect(
    recordedResponse(
      new Request("https://preview.example/test?limit=101"),
      ["api", "v1", "projects"],
      fixture,
    ).status,
  ).toBe(422);
  expect(
    recordedResponse(
      new Request("https://preview.example/test?url=https://outside.example"),
      ["api", "v1", "projects"],
      fixture,
    ).status,
  ).toBe(400);
  expect(
    recordedResponse(
      new Request("https://preview.example/test"),
      ["api", "v1", "runs", "missing"],
      fixture,
    ).status,
  ).toBe(404);
  expect(fetcher).not.toHaveBeenCalled();
});
it("hides privileged controls even before the viewer session loads", () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise(() => {})),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AccessProvider recordedDemo>
        <AccessNotice />
        <Button control="execute">Start discovery</Button>
        <Button control="manage">Create project</Button>
        <Button>Inspect evidence</Button>
      </AccessProvider>
    </QueryClientProvider>,
  );
  expect(screen.queryByRole("button", { name: "Start discovery" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Create project" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Inspect evidence" })).toBeEnabled();
  expect(screen.getByRole("status")).toHaveTextContent("Historical synthetic sandbox results only");
});
