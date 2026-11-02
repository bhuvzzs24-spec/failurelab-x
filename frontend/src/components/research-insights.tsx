"use client";
import { useState } from "react";
import { ArrowRight, ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import Link from "next/link";
import type { ResearchJob } from "@/lib/research";
import { asObject, asText } from "@/lib/utils";
import { JsonView } from "./evidence-common";
import { Panel } from "./ui/states";
export function MeasuredBaselines({ jobs }: { jobs: ResearchJob[] }) {
  const job = jobs
    .filter(
      (j) =>
        j.kind === "BENCHMARK" &&
        j.status === "COMPLETED" &&
        typeof asObject(j.result.mean_unique_bugs).adaptive === "number",
    )
    .sort((a, b) => b.created_at - a.created_at)[0];
  if (!job)
    return (
      <Panel
        title="Compare before you conclude"
        subtitle="Adaptive search is a strategy, not a performance guarantee"
      >
        <p className="body-copy">
          No completed equal-budget comparison is available for this project.
        </p>
        <Link href="/benchmarks" className="insight-footer">
          Open benchmark workspace <ArrowRight size={14} />
        </Link>
      </Panel>
    );
  const means = asObject(job.result.mean_unique_bugs);
  const entries = ["random", "coverage", "adaptive"].map((strategy) => ({
    strategy,
    value: means[strategy],
  }));
  if (entries.some((row) => typeof row.value !== "number" || !Number.isFinite(row.value)))
    return null;
  const random = Number(means.random),
    coverage = Number(means.coverage),
    adaptive = Number(means.adaptive);
  const delta = adaptive - Math.max(random, coverage);
  const maximum = Math.max(1, random, coverage, adaptive);
  return (
    <Panel
      title="Measured baseline comparison"
      subtitle="Latest completed study · mean distinct seeded defect families"
      action={
        <Link className="text-link" href={`/benchmarks?job=${job.id}`}>
          Full study <ArrowUpRight size={13} />
        </Link>
      }
    >
      <div className="baseline-insight">
        <div className="baseline-bars">
          {entries.map((row) => (
            <div key={row.strategy}>
              <span>{row.strategy}</span>
              <span className="baseline-track">
                <span
                  style={{ width: `${(100 * Number(row.value)) / maximum}%` }}
                  data-strategy={row.strategy}
                />
              </span>
              <strong>{Number(row.value).toFixed(2)}</strong>
            </div>
          ))}
        </div>
        <div className={`baseline-verdict ${delta < 0 ? "below" : "neutral"}`}>
          {delta < 0 ? (
            <ArrowDownRight size={25} />
          ) : delta > 0 ? (
            <ArrowUpRight size={25} />
          ) : (
            <Minus size={25} />
          )}
          <div>
            <strong>
              {delta < 0
                ? "Adaptive underperformed"
                : delta > 0
                  ? "Higher observed coverage"
                  : "No coverage improvement"}
            </strong>
            <p>
              {Math.abs(delta).toFixed(2)} families{" "}
              {delta < 0 ? "below" : delta > 0 ? "above" : "from"} the best baseline in this finite
              study.
            </p>
            <small>Equal budgets · recorded seed set · synthetic defects</small>
          </div>
        </div>
      </div>
      <p className="microcopy">
        An observed difference does not establish statistical superiority or performance on unseen
        applications.
      </p>
    </Panel>
  );
}
export function SequenceComparison({ report }: { report: Record<string, unknown> }) {
  const original = asObject(report.original),
    reduced = asObject(report.reduced);
  const sequence = (scenario: Record<string, unknown>, label: string) => (
    <div className="sequence-column" aria-label={label}>
      <div className="sequence-heading">
        <h3>{label.startsWith("Original") ? "Original sequence" : "Reduced sequence"}</h3>
        <span className="subtle-chip">
          {Array.isArray(scenario.actions) ? scenario.actions.length : 0} faults
        </span>
      </div>
      <p className="sequence-family">{asText(scenario.defect)}</p>
      <ol className="sequence-events">
        {(Array.isArray(scenario.actions) ? scenario.actions : []).map((raw, i) => {
          const action = asObject(raw);
          return (
            <li key={i}>
              <span className="sequence-index">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <strong>
                  {asText(action.boundary)} <span>/ {asText(action.kind)}</span>
                </strong>
                <p>
                  {asText(action.phase)} execution · {asText(action.at_ms)}ms activation
                  {action.kind === "latency" ? ` · ${asText(action.delay_ms)}ms delay` : ""}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
      <div className="sequence-inputs">
        <span>
          Amount <strong>{asText(scenario.amount)}</strong>
        </span>
        <span>
          Quantity <strong>{asText(scenario.quantity)}</strong>
        </span>
        <span>
          Concurrency <strong>{asText(scenario.concurrency)}</strong>
        </span>
      </div>
      <details>
        <summary>Recorded scenario JSON</summary>
        <JsonView value={scenario} label={`${label} JSON`} />
      </details>
    </div>
  );
  const removed = Array.isArray(report.removed_events) ? report.removed_events.length : 0;
  const attempts = Array.isArray(report.attempts) ? report.attempts.length : 0;
  return (
    <div className="sequence-workbench">
      <div className="reduction-readout">
        <div>
          <strong>{removed}</strong>
          <span>removed fault events</span>
        </div>
        <div>
          <strong>{attempts}</strong>
          <span>recorded replay attempts</span>
        </div>
        <div>
          <strong>
            {asText(report.reproductions)} / {asText(report.confirmation_trials)}
          </strong>
          <span>final confirmations</span>
        </div>
        <div>
          <strong>{report.local_minimality_tested === true ? "Tested" : "Unproved"}</strong>
          <span>finite local minimality</span>
        </div>
      </div>
      <div className="research-comparison">
        {sequence(original, "Original failure sequence")}
        {sequence(reduced, "Reduced failure sequence")}
      </div>
      <p className="microcopy">
        Only repeated exact-signature reproductions justify an accepted reduction. A budget-limited
        result does not establish global minimality.
      </p>
    </div>
  );
}

export function DecisionHistory({
  decisions,
}: {
  decisions: import("@/types/domain").Schema["DecisionOut"][];
}) {
  const [chosen, setChosen] = useState("");
  const rows = [...decisions].sort((a, b) => a.step - b.step);
  const selected = rows.find((row) => row.id === chosen) ?? rows[0];
  if (!selected) return null;
  return (
    <div className="decision-workbench">
      <div className="decision-list table-scroll">
        <table>
          <caption>Actual selected experiments</caption>
          <thead>
            <tr>
              <th>Step</th>
              <th>Selected scenario</th>
              <th>Observed reward</th>
              <th>Trial cost</th>
              <th>Inspect</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className={selected.id === row.id ? "decision-selected" : ""}>
                <td>{row.step + 1}</td>
                <td>
                  <strong>{row.scenario.defect.replaceAll("_", " ")}</strong>
                  <small className="cell-subtitle">
                    {(row.scenario.actions ?? [])
                      .map((a) => `${a.boundary} / ${a.kind}`)
                      .join(" + ") || "No injected fault"}
                  </small>
                </td>
                <td>{row.reward > 0 ? "Novelty rewarded" : "No novelty reward"}</td>
                <td>{row.cost_seconds.toFixed(3)}s</td>
                <td>
                  <button
                    className="trial-reference"
                    aria-label={`Inspect decision ${row.step + 1}`}
                    aria-pressed={selected.id === row.id}
                    onClick={() => setChosen(row.id)}
                  >
                    Context <ArrowUpRight size={12} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="decision-context">
        <span className="eyebrow">DECISION {selected.step + 1}</span>
        <h3>{selected.scenario.defect.replaceAll("_", " ")}</h3>
        <p>
          Acquisition utility <strong>{selected.score.toFixed(3)}</strong> · a selection heuristic,
          not a probability.
        </p>
        <details>
          <summary>Selected inputs and planner context</summary>
          <JsonView
            value={{
              scenario: selected.scenario,
              context: selected.context,
              reward: selected.reward,
              measured_cost_seconds: selected.cost_seconds,
            }}
            label="Selected experiment decision"
          />
        </details>
      </div>
    </div>
  );
}
