import { allPages, api } from "@/lib/api";
import { expect, it, vi } from "vitest";
it("rejects structured API failures instead of fabricating success", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(Response.json({ error: { message: "Unauthorized" } }, { status: 401 })),
  );
  await expect(api.start("experiment", "key")).rejects.toMatchObject({
    status: 401,
    message: "Unauthorized",
  });
});
it("loads every collection page without silently truncating totals", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(Response.json({ items: [1, 2], total: 3 }))
    .mockResolvedValueOnce(Response.json({ items: [3], total: 3 }));
  vi.stubGlobal("fetch", fetcher);
  expect(await allPages<number>("api/v1/projects")).toEqual([1, 2, 3]);
  expect(fetcher.mock.calls[1][0]).toContain("offset=2");
});
it("rejects incomplete backend pagination", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ items: [], total: 1 })));
  await expect(allPages("api/v1/projects")).rejects.toThrow("incomplete collection");
});
it("sends real run and cancellation mutations to existing endpoints", async () => {
  const fetcher = vi.fn().mockImplementation(() => Promise.resolve(Response.json({ id: "run" })));
  vi.stubGlobal("fetch", fetcher);
  await api.start("exp", "one");
  await api.cancel("run");
  expect(fetcher.mock.calls[0][0]).toBe("/api/backend/api/v1/experiments/exp/runs");
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ idempotency_key: "one" });
  expect(fetcher.mock.calls[1][0]).toBe("/api/backend/api/v1/runs/run/cancel");
});
