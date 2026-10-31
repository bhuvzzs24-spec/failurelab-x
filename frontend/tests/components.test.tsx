import { Dashboard } from "@/components/dashboard";
import { EvidenceExplorer } from "@/components/evidence-explorer";
import { ExperimentStudio } from "@/components/experiment-studio";
import { FutureWorkspace } from "@/components/future-workspaces";
import { Investigator } from "@/components/investigator";
import { RunMonitor } from "@/components/run-monitor";
import { graphLayout } from "@/components/system-graph";
import { StatusBadge } from "@/components/ui/status";
import * as data from "@/hooks/data";
import { api } from "@/lib/api";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import {
  artifact,
  experiment,
  finding,
  graph,
  invariant,
  overview,
  run,
  summary,
} from "./fixtures";
const navigation = vi.hoisted(() => ({ push: vi.fn(), params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: navigation.push }),
  useSearchParams: () => navigation.params,
  usePathname: () => "/evidence",
}));
vi.mock("@/components/providers", () => ({
  useProject: () => ({
    projectId: "project-test",
    projects: [{ id: "project-test", name: "Test sandbox" }],
    setProjectId: vi.fn(),
    loading: false,
    error: null,
  }),
}));
vi.mock("@/hooks/data", () => ({
  useGraph: vi.fn(),
  useOverview: vi.fn(),
  useSummary: vi.fn(),
  useExperiments: vi.fn(),
  useInvariants: vi.fn(),
  useRuns: vi.fn(),
  useFindings: vi.fn(),
}));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      start: vi.fn(),
      cancel: vi.fn(),
      createExperiment: vi.fn(),
      capabilities: vi.fn().mockResolvedValue({ causal_analysis: false }),
    },
  };
});
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  AreaChart: () => <div />,
  Area: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));
function mount(element: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      {element}
    </QueryClientProvider>,
  );
}
function loaded<T>(value: T) {
  return { data: value, isPending: false, error: null, refetch: vi.fn() } as never;
}
beforeEach(() => {
  navigation.params = new URLSearchParams();
  vi.clearAllMocks();
  vi.mocked(data.useGraph).mockReturnValue(loaded(graph));
  vi.mocked(data.useOverview).mockReturnValue(loaded(overview));
  vi.mocked(data.useSummary).mockReturnValue(loaded(summary));
  vi.mocked(data.useExperiments).mockReturnValue(loaded([experiment]));
  vi.mocked(data.useInvariants).mockReturnValue(loaded([invariant]));
  vi.mocked(data.useRuns).mockReturnValue(loaded({ items: [run], offset: 0, limit: 25, total: 1 }));
  vi.mocked(data.useFindings).mockReturnValue(
    loaded({ items: [finding], offset: 0, limit: 25, total: 1 }),
  );
});
it("shows a genuine loading state instead of zero metrics", () => {
  vi.mocked(data.useOverview).mockReturnValue({ isPending: true } as never);
  mount(<Dashboard />);
  expect(screen.getByText("Loading backend data")).toBeInTheDocument();
  expect(screen.queryByText("Registered services")).not.toBeInTheDocument();
});
it("shows errors without fabricated dashboard metrics", () => {
  vi.mocked(data.useOverview).mockReturnValue({
    isPending: false,
    error: new Error("Connection refused"),
    refetch: vi.fn(),
  } as never);
  mount(<Dashboard />);
  expect(screen.getByRole("alert")).toHaveTextContent("Connection refused");
});
it("computes dashboard presentation from backend aggregates", () => {
  mount(<Dashboard />);
  expect(screen.getByText("Registered services").closest(".metric-card")).toHaveTextContent("4");
  expect(screen.getByText("Total experiments").closest(".metric-card")).toHaveTextContent("7");
  expect(screen.getByText("Invariant violations").closest(".metric-card")).toHaveTextContent("3");
});
it("lays out only registered graph nodes and directional edges", () => {
  const result = graphLayout(graph, "payment");
  expect(result.nodes).toHaveLength(4);
  expect(result.edges).toHaveLength(3);
  expect(
    result.nodes.every(
      (node) => Number.isFinite(node.position.x) && Number.isFinite(node.position.y),
    ),
  ).toBe(true);
  expect(result.nodes.find((node) => node.data.service.name === "payment")?.data.focused).toBe(
    true,
  );
  expect(result.edges[0].source).toBe("service-gateway");
});
it("validates invalid fault parameters before opening confirmation", async () => {
  const user = userEvent.setup();
  mount(<ExperimentStudio />);
  const ttl = screen.getByLabelText(/Fault lease TTL/);
  await user.clear(ttl);
  await user.type(ttl, "31");
  await user.click(screen.getByRole("button", { name: "Review & run" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  expect(api.start).not.toHaveBeenCalled();
});
it("requires confirmation and submits a real API mutation with an idempotency key", async () => {
  vi.mocked(api.start).mockResolvedValue({ ...run, status: "CREATED" });
  const user = userEvent.setup();
  mount(<ExperimentStudio />);
  await user.click(screen.getByRole("button", { name: "Review & run" }));
  expect(await screen.findByRole("alertdialog")).toHaveTextContent("Target: payment");
  expect(api.start).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Start sandbox experiment" }));
  await waitFor(() =>
    expect(api.start).toHaveBeenCalledWith(experiment.id, expect.stringMatching(/^ui_/)),
  );
  await waitFor(() => expect(navigation.push).toHaveBeenCalledWith("/experiments?run=run-test"));
});
it.each(["CREATED", "QUEUED", "RUNNING", "VERIFYING", "COMPLETED", "FAILED", "CANCELLED"])(
  "renders the backend status %s exactly",
  (status) => {
    mount(<StatusBadge status={status} />);
    expect(screen.getByText(status)).toBeVisible();
  },
);
it("cancels an active run only after confirmation", async () => {
  vi.mocked(data.useSummary).mockReturnValue(
    loaded({ ...summary, run: { ...run, status: "RUNNING" } }),
  );
  vi.mocked(api.cancel).mockResolvedValue({ ...run, cancel_requested: 1 });
  const user = userEvent.setup();
  mount(<RunMonitor runId={run.id} />);
  await user.click(screen.getByRole("button", { name: "Cancel run" }));
  expect(api.cancel).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Request cancellation" }));
  await waitFor(() => expect(api.cancel).toHaveBeenCalledWith(run.id));
});
it("does not offer cancellation for a terminal run", () => {
  mount(<RunMonitor runId={run.id} />);
  expect(screen.queryByRole("button", { name: "Cancel run" })).not.toBeInTheDocument();
});
it("shows observed finding state, expected rule and missing telemetry accurately", () => {
  navigation.params = new URLSearchParams("run=run-test&finding=finding-test");
  mount(<Investigator />);
  expect(screen.getByRole("heading", { name: "Paid implies finalized" })).toBeInTheDocument();
  expect(screen.getByLabelText("Observed authoritative state")).toHaveTextContent('"charged"');
  expect(screen.getByText("Missing evidence")).toBeInTheDocument();
  expect(screen.getByText(/Causal attribution requires/)).toBeInTheDocument();
});
it("filters evidence and safely renders untrusted text", async () => {
  navigation.params = new URLSearchParams("run=run-test");
  vi.mocked(data.useSummary).mockReturnValue(
    loaded({
      ...summary,
      artifacts: [{ ...artifact, payload: { text: "<img src=x onerror=alert(1)>" } }],
    }),
  );
  const user = userEvent.setup();
  mount(<EvidenceExplorer />);
  expect(screen.getByLabelText("Artifact payload")).toHaveTextContent(
    "<img src=x onerror=alert(1)>",
  );
  expect(document.querySelector("img")).toBeNull();
  await user.type(screen.getByRole("textbox", { name: "Search recorded evidence" }), "not-a-match");
  expect(screen.getByText("No artifacts match the filters.")).toBeInTheDocument();
});
it("marks the future intelligence engine unavailable without fake hypotheses", () => {
  mount(<FutureWorkspace section="ai" />);
  expect(screen.getByRole("button", { name: "Engine not connected" })).toBeDisabled();
  expect(screen.getByText("Nothing inferred. Nothing invented.")).toBeVisible();
});

it("persists a changed configuration as a new definition before starting it", async () => {
  const custom = {
    ...experiment,
    id: "experiment-custom",
    config: { ...experiment.config, fault: { ...experiment.config.fault, delay_seconds: 1.8 } },
  };
  vi.mocked(api.createExperiment).mockResolvedValue(custom);
  vi.mocked(api.start).mockResolvedValue({ ...run, experiment_id: custom.id, status: "CREATED" });
  const user = userEvent.setup();
  mount(<ExperimentStudio />);
  const delay = screen.getByLabelText(/HTTP delay \(seconds\)/);
  await user.clear(delay);
  await user.type(delay, "1.8");
  await user.click(screen.getByRole("button", { name: "Review & run" }));
  await user.click(screen.getByRole("button", { name: "Start sandbox experiment" }));
  await waitFor(() =>
    expect(api.createExperiment).toHaveBeenCalledWith(
      "project-test",
      expect.objectContaining({
        config: expect.objectContaining({ fault: expect.objectContaining({ delay_seconds: 1.8 }) }),
      }),
    ),
  );
  await waitFor(() =>
    expect(api.start).toHaveBeenCalledWith(custom.id, expect.stringMatching(/^ui_/)),
  );
});
it("keeps a visible error when experiment submission fails", async () => {
  vi.mocked(api.start).mockRejectedValue(new Error("Backend rejected this run"));
  const user = userEvent.setup();
  mount(<ExperimentStudio />);
  await user.click(screen.getByRole("button", { name: "Review & run" }));
  await user.click(screen.getByRole("button", { name: "Start sandbox experiment" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Backend rejected this run");
});
