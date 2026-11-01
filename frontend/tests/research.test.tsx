import { ResearchWorkspace, PatchDiff } from "@/components/research-workspace";
import { research } from "@/lib/research";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
vi.mock("@/components/providers", () => ({ useProject: () => ({ projectId: "project-test" }) }));
vi.mock("@/lib/research", () => ({
  research: {
    jobs: vi.fn(),
    trials: vi.fn(),
    candidates: vi.fn(),
    capabilities: vi.fn(),
    decisions: vi.fn(),
    artifacts: vi.fn(),
    create: vi.fn(),
    cancel: vi.fn(),
  },
}));
vi.mock("recharts", () => ({
  ResponsiveContainer: () => null,
  CartesianGrid: () => null,
  LineChart: () => null,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  BarChart: () => null,
  Bar: () => null,
  Legend: () => null,
}));
vi.mock("@xyflow/react", () => ({
  ReactFlow: () => <div>Hypothesis graph</div>,
  Background: () => null,
  Controls: () => null,
}));
const job = {
  id: "job-1",
  project_id: "project-test",
  kind: "SEARCH",
  status: "CREATED",
  created_at: 1,
  updated_at: 1,
  deadline: 9999999999,
  input: {
    kind: "SEARCH",
    idempotency_key: "test",
    search: { budget: 2, strategy: "adaptive", seed: 42, defects: ["payment_ack_loss"] },
    budget: 20,
    repeats: 2,
    seeds: [17, 42, 93],
  },
  result: {},
  error: null,
  cancel_requested: false,
} as const;
function mount(
  section:
    "explorer" | "ai" | "minimization" | "patches" | "verification" | "benchmarks" = "explorer",
) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      <ResearchWorkspace section={section} />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(research.jobs).mockResolvedValue([]);
  vi.mocked(research.trials).mockResolvedValue([]);
  vi.mocked(research.candidates).mockResolvedValue([]);
  vi.mocked(research.capabilities).mockResolvedValue({ repair_agent_configured: false });
  vi.mocked(research.decisions).mockResolvedValue([]);
  vi.mocked(research.artifacts).mockResolvedValue([]);
});
it("loads real job queries and an honest empty state", async () => {
  mount();
  expect(await screen.findByText(/No search job exists/)).toBeVisible();
  expect(research.jobs).toHaveBeenCalledWith("project-test");
});
it("renders API errors without inventing results", async () => {
  vi.mocked(research.jobs).mockRejectedValue(new Error("Research unavailable"));
  mount();
  expect(await screen.findByText("Research unavailable")).toBeVisible();
});
it("submits a validated bounded job after sandbox confirmation", async () => {
  vi.mocked(research.create).mockResolvedValue(job as never);
  const user = userEvent.setup();
  mount();
  await user.click(await screen.findByRole("button", { name: "Start discovery" }));
  expect(research.create).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Confirm sandbox execution" }));
  await waitFor(() =>
    expect(research.create).toHaveBeenCalledWith(
      "project-test",
      expect.objectContaining({
        kind: "SEARCH",
        budget: 12,
        search: expect.objectContaining({ strategy: "adaptive", budget: 12 }),
      }),
    ),
  );
});
it("rejects out-of-range budgets", async () => {
  const user = userEvent.setup();
  mount();
  const input = await screen.findByRole("spinbutton", { name: "Trial budget" });
  await user.clear(input);
  await user.type(input, "99");
  await user.click(screen.getByRole("button", { name: "Start discovery" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Budget must be 2–60");
  expect(research.create).not.toHaveBeenCalled();
});
it("requires a measured violation for minimization", async () => {
  const user = userEvent.setup();
  mount("minimization");
  await user.click(await screen.findByRole("button", { name: "Reduce sequence" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Discover an original invariant violation");
});
it("cancels an active persisted job", async () => {
  vi.mocked(research.jobs).mockResolvedValue([job as never]);
  vi.mocked(research.cancel).mockResolvedValue({ ...job, status: "CANCELLED" } as never);
  const user = userEvent.setup();
  mount();
  await user.click(await screen.findByRole("button", { name: "Cancel job" }));
  await waitFor(() => expect(research.cancel).toHaveBeenCalledWith("job-1", expect.anything()));
});
it("labels unavailable isolated verification accurately", async () => {
  mount("verification");
  expect(await screen.findByText(/Docker verification agent is not configured/)).toBeVisible();
});
it("renders patch source as escaped text", () => {
  render(<PatchDiff patch={"+<script>alert(1)</script>\n-old"} />);
  expect(screen.getByLabelText("Candidate source diff")).toHaveTextContent(
    "<script>alert(1)</script>",
  );
  expect(document.querySelector("script")).toBeNull();
});
it("shows an actual verification infrastructure error report", async () => {
  vi.mocked(research.jobs).mockResolvedValue([
    {
      ...job,
      kind: "VERIFY",
      status: "COMPLETED",
      result: { outcome: "INFRASTRUCTURE_ERROR", reason: "Docker unavailable" },
    } as never,
  ]);
  mount("verification");
  expect(await screen.findByLabelText("Verification outcome")).toHaveTextContent(
    "INFRASTRUCTURE_ERROR",
  );
});
