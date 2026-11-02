import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { CausalBoard, type HypothesisView } from "@/components/causal-board";
import {
  MeasuredBaselines,
  SequenceComparison,
  DecisionHistory,
} from "@/components/research-insights";
import { ReplayTimeline } from "@/components/replay-timeline";
import { JsonView } from "@/components/evidence-common";
import type { ResearchJob } from "@/lib/research";
import { artifact } from "./fixtures";
const h = (id: string, status: HypothesisView["status"]): HypothesisView => ({
  id,
  status,
  description: id + " mechanism",
  services: ["payment", "order"],
  assumptions: ["Fresh state"],
  supporting_observations: [],
  contradicting_observations: [],
  intervention: "Remove the recorded action",
  outcomes: [],
});
it("distinguishes intervention verdicts from missing evidence and supports keyboard inspection", async () => {
  render(
    <CausalBoard hypotheses={[h("acknowledgement", "SUPPORTED"), h("retry", "INCONCLUSIVE")]} />,
  );
  const user = userEvent.setup();
  expect(screen.getByRole("tabpanel")).toHaveTextContent("acknowledgement mechanism");
  expect(screen.getByText("No supporting evidence recorded.")).toBeVisible();
  screen.getByRole("tab", { name: /acknowledgement mechanism/ }).focus();
  await user.keyboard("{ArrowDown}");
  expect(screen.getByRole("tab", { name: /retry mechanism/ })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(screen.getByRole("tabpanel")).toHaveTextContent("INCONCLUSIVE");
  expect(screen.queryByText(/confidence:|100%/i)).not.toBeInTheDocument();
});
it("shows adaptive underperformance directly from a recorded completed comparison", () => {
  const measured = {
    id: "measured",
    kind: "BENCHMARK",
    status: "COMPLETED",
    created_at: 1,
    result: { mean_unique_bugs: { random: 4, coverage: 5, adaptive: 3 } },
  } as unknown as ResearchJob;
  render(<MeasuredBaselines jobs={[measured]} />);
  expect(screen.getByText("Adaptive underperformed")).toBeVisible();
  expect(screen.getByText(/2.00 families below/)).toBeVisible();
  expect(screen.getByRole("link", { name: /Full study/ })).toHaveAttribute(
    "href",
    "/benchmarks?job=measured",
  );
});
it("does not fabricate a comparison when no benchmark was completed", () => {
  render(<MeasuredBaselines jobs={[]} />);
  expect(screen.getByText(/No completed equal-budget comparison/)).toBeVisible();
  expect(screen.queryByText("Adaptive underperformed")).not.toBeInTheDocument();
});
it("keeps reduced sequence, confirmations and unproved minimality distinct", () => {
  const scenario = {
    defect: "payment_ack_loss",
    amount: 1,
    quantity: 1,
    concurrency: 1,
    actions: [{ boundary: "charge", kind: "latency", phase: "after", delay_ms: 90, at_ms: 0 }],
  };
  render(
    <SequenceComparison
      report={{
        original: scenario,
        reduced: scenario,
        removed_events: [],
        attempts: [{}],
        reproductions: 0,
        confirmation_trials: 0,
        local_minimality_tested: false,
      }}
    />,
  );
  expect(screen.getByText("Unproved")).toBeVisible();
  expect(screen.getByText("0 / 0")).toBeVisible();
  expect(screen.getByLabelText("Reduced failure sequence")).toHaveTextContent("90ms delay");
});
it("replay filters select actual persisted events and payloads", async () => {
  const user = userEvent.setup();
  render(
    <ReplayTimeline
      artifacts={[
        artifact,
        {
          ...artifact,
          id: "fault",
          kind: "fault_schedule",
          created_at: artifact.created_at + 2,
          payload: { activated_at: 1, marker: "recorded-only" },
        },
      ]}
    />,
  );
  await user.click(screen.getByRole("button", { name: /fault schedule 1/ }));
  expect(screen.getByLabelText("Replay event evidence")).toHaveTextContent("recorded-only");
  expect(screen.getByLabelText("Recorded replay events")).toHaveTextContent("+2.000s");
});
it("JSON highlighting safely escapes untrusted strings", () => {
  render(<JsonView value={{ text: "<script>unsafe()</script>", count: 4 }} />);
  expect(document.querySelector("script")).toBeNull();
  expect(screen.getByLabelText("JSON evidence")).toHaveTextContent("<script>unsafe()</script>");
});
it("search history exposes the actual selected inputs and utility without a causal claim", async () => {
  const user = userEvent.setup();
  render(
    <DecisionHistory
      decisions={[
        {
          id: "d",
          job_id: "j",
          step: 0,
          score: 1.5,
          reward: 0,
          cost_seconds: 0.8,
          context: {},
          scenario: { defect: "payment_ack_loss", actions: [] },
        } as never,
      ]}
    />,
  );
  await user.click(screen.getByText("Selected inputs and planner context"));
  expect(screen.getByLabelText("Selected experiment decision")).toHaveTextContent(
    "payment_ack_loss",
  );
  expect(screen.getByText(/not a probability/)).toBeVisible();
});
