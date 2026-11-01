import { AccessProvider, AccessNotice } from "@/components/access";
import { Button } from "@/components/ui/button";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
function mount(readOnly = false) {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <AccessProvider readOnly={readOnly}>
        <AccessNotice />
        <Button control="execute">Execute</Button>
        <Button control="manage">Register</Button>
        <Button>Inspect evidence</Button>
      </AccessProvider>
    </QueryClientProvider>,
  );
}
it("disables controls for a viewer while preserving inspection", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json({ role: "viewer", read_only: true, can_execute: false, can_manage: false }),
      ),
  );
  mount();
  expect(await screen.findByText(/Read-only demonstration/)).toBeVisible();
  expect(screen.getByText("Execute")).toBeDisabled();
  expect(screen.getByText("Register")).toBeDisabled();
  expect(screen.getByText("Inspect evidence")).toBeEnabled();
});
it("uses the server permission boundary for operators", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json({ role: "operator", read_only: false, can_execute: true, can_manage: false }),
      ),
  );
  mount();
  expect(screen.getByText("Execute")).toBeDisabled();
  await import("@testing-library/react").then(({ waitFor }) =>
    waitFor(() => expect(screen.getByText("Execute")).toBeEnabled()),
  );
  expect(screen.getByText("Register")).toBeDisabled();
});
it("fails closed when permissions cannot be loaded", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  mount();
  expect(await screen.findByRole("alert")).toHaveTextContent("Control actions are disabled");
  expect(screen.getByText("Execute")).toBeDisabled();
});
it("enforces read-only deployment even if backend credentials are mistakenly overprivileged", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json({ role: "admin", read_only: false, can_execute: true, can_manage: true }),
      ),
  );
  mount(true);
  expect(await screen.findByText(/Read-only demonstration/)).toBeVisible();
  expect(screen.getByText("Execute")).toBeDisabled();
});

it("disables stale cached permissions after a refresh failure", async () => {
  const { waitFor, act } = await import("@testing-library/react");
  const fetcher = vi
    .fn()
    .mockResolvedValue(
      Response.json({ role: "admin", read_only: false, can_execute: true, can_manage: true }),
    );
  vi.stubGlobal("fetch", fetcher);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AccessProvider>
        <AccessNotice />
        <Button control="execute">Execute cached</Button>
      </AccessProvider>
    </QueryClientProvider>,
  );
  await waitFor(() => expect(screen.getByText("Execute cached")).toBeEnabled());
  fetcher.mockRejectedValue(new Error("offline"));
  await act(async () => {
    await client.refetchQueries({ queryKey: ["access-session"] });
  });
  await waitFor(() => expect(screen.getByText("Execute cached")).toBeDisabled());
  expect(screen.getByRole("alert")).toHaveTextContent("Control actions are disabled");
});
