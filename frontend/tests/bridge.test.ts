// Node web APIs are used here; the bridge never receives browser credentials.
import { bridge } from "@/lib/bridge";
import { redact } from "@/lib/redact";
import { expect, it, vi } from "vitest";
const env = { API_TOKEN: "unit-test-only", BACKEND_URL: "http://api:8000" };
it("keeps credentials server-side and redacts evidence", async () => {
  const fetcher = vi.fn().mockResolvedValue(
    Response.json({
      id: "run",
      payload: { api_key: "private", path: "/Users/operator/private/file.log", status: "FAIL" },
    }),
  );
  vi.stubGlobal("fetch", fetcher);
  const result = await bridge(
    new Request("http://localhost:3000/api/backend/api/v1/runs/run"),
    ["api", "v1", "runs", "run"],
    env,
  );
  expect(fetcher.mock.calls[0][1].headers.Authorization).toBe("Bearer unit-test-only");
  expect(await result.json()).toEqual({
    id: "run",
    payload: { api_key: "[redacted]", path: "[redacted local path]", status: "FAIL" },
  });
});
it("blocks cross-origin mutations before contacting the backend", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const result = await bridge(
    new Request("http://localhost:3000/api/backend/api/v1/projects", {
      method: "POST",
      headers: { Origin: "https://outside.example", "Content-Type": "application/json" },
      body: "{}",
    }),
    ["api", "v1", "projects"],
    env,
  );
  expect(result.status).toBe(403);
  expect(fetcher).not.toHaveBeenCalled();
});
it("blocks arbitrary origins, path traversal and unsupported operations", async () => {
  expect(
    (
      await bridge(new Request("http://localhost/health"), ["health"], {
        ...env,
        BACKEND_URL: "http://169.254.169.254",
      })
    ).status,
  ).toBe(503);
  expect(
    (await bridge(new Request("http://localhost/test"), ["api", "..", "health"], env)).status,
  ).toBe(404);
  expect((await bridge(new Request("http://localhost/test"), ["shell"], env)).status).toBe(404);
});
it("rejects oversized mutation bodies and missing server configuration", async () => {
  const request = new Request("http://localhost:3000/test", {
    method: "POST",
    headers: { Origin: "http://localhost:3000", "Content-Type": "application/json" },
    body: "x".repeat(65537),
  });
  expect((await bridge(request, ["api", "v1", "projects"], env)).status).toBe(413);
  expect((await bridge(new Request("http://localhost/health"), ["health"], {})).status).toBe(503);
});
it("returns a useful connection error without leaking internal details", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new Error("password in private upstream error")),
  );
  const response = await bridge(new Request("http://localhost/health"), ["health"], env);
  expect(response.status).toBe(502);
  expect(JSON.stringify(await response.json())).not.toContain("password");
});
it("redacts nested credentials while preserving ordinary HTTP operation paths", () => {
  expect(
    redact({
      password: "x",
      nested: {
        authorization: "x",
        operation: "/charge",
        url: "postgresql://user:" + "unit-test-only" + "@database/db",
      },
    }),
  ).toEqual({
    password: "[redacted]",
    nested: {
      authorization: "[redacted]",
      operation: "/charge",
      url: "postgresql://[redacted]@database/db",
    },
  });
});

it("compares mutation origin with the validated browser Host instead of Next's internal URL", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(Response.json({ id: "created" }, { status: 202 })),
  );
  const request = new Request("http://localhost:3000/internal", {
    method: "POST",
    headers: {
      Host: "127.0.0.1:3000",
      Origin: "http://127.0.0.1:3000",
      "Content-Type": "application/json",
    },
    body: "{}",
  });
  expect((await bridge(request, ["api", "v1", "projects"], env)).status).toBe(202);
});
it("blocks DNS-rebinding hosts even when Origin matches", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const request = new Request("http://localhost:3000/internal", {
    method: "POST",
    headers: {
      Host: "outside.example",
      Origin: "http://outside.example",
      "Content-Type": "application/json",
    },
    body: "{}",
  });
  expect((await bridge(request, ["api", "v1", "projects"], env)).status).toBe(403);
  expect(fetcher).not.toHaveBeenCalled();
});

it("allows only an explicitly configured public read-only origin and HTTPS backend", async () => {
  const fetcher = vi.fn().mockResolvedValue(Response.json({ items: [] }));
  vi.stubGlobal("fetch", fetcher);
  const hosted = {
    API_TOKEN: "viewer-unit-token".padEnd(40, "x"),
    ACCESS_MODE: "read_only",
    PUBLIC_FRONTEND_ORIGIN: "https://lab.example",
    BACKEND_URL: "https://records.example",
    HOSTED_BACKEND_ORIGIN: "https://records.example",
  };
  const read = new Request("https://lab.example/api/backend/api/v1/projects");
  expect((await bridge(read, ["api", "v1", "projects"], hosted)).status).toBe(200);
  expect(fetcher.mock.calls[0][0].origin).toBe("https://records.example");
  fetcher.mockClear();
  const write = new Request("https://lab.example/api/backend/api/v1/projects", {
    method: "POST",
    headers: { origin: "https://lab.example", "content-type": "application/json" },
    body: "{}",
  });
  expect((await bridge(write, ["api", "v1", "projects"], hosted)).status).toBe(403);
  expect(fetcher).not.toHaveBeenCalled();
  expect((await bridge(new Request("https://evil.example/test"), ["health"], hosted)).status).toBe(
    403,
  );
  expect(
    (
      await bridge(read, ["api", "v1", "projects"], {
        ...hosted,
        HOSTED_BACKEND_ORIGIN: "https://other.example",
      })
    ).status,
  ).toBe(503);
});
it("retains safe rate-limit metadata without forwarding arbitrary headers", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json(
          { error: { message: "limited" } },
          { status: 429, headers: { "Retry-After": "60", "Set-Cookie": "secret=value" } },
        ),
      ),
  );
  const response = await bridge(
    new Request("http://localhost/test"),
    ["api", "v1", "projects"],
    env,
  );
  expect(response.status).toBe(429);
  expect(response.headers.get("retry-after")).toBe("60");
  expect(response.headers.get("set-cookie")).toBeNull();
});
