"use client";
import { useSummary } from "@/hooks/data";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/utils";
import type { Section } from "@/types/domain";
import type {
  Hypothesis,
  MinimizationResult,
  SequenceEvent,
  VerificationComparison,
} from "@/types/future";
import { useQuery } from "@tanstack/react-query";
import {
  CheckCheck,
  GitPullRequest,
  LockKeyhole,
  Scissors,
  Sparkles,
  Workflow,
} from "lucide-react";
import { JsonView, RunPicker, useRunLocation } from "./evidence-common";
import { SystemGraph } from "./system-graph";
import { Button } from "./ui/button";
import { ErrorState, FactLabel, Panel } from "./ui/states";
export function HypothesisList({ hypotheses }: { hypotheses: Hypothesis[] | null }) {
  return hypotheses ? (
    <div>
      {hypotheses.map((hypothesis) => (
        <div className="hypothesis-card" key={hypothesis.id}>
          <h3>{hypothesis.statement}</h3>
          <p>{hypothesis.uncertainty}</p>
          <span>
            Confidence:{" "}
            {hypothesis.confidence === null
              ? "Unknown"
              : `${Math.round(hypothesis.confidence * 100)}%`}
          </span>
          <JsonView value={hypothesis.evidence} />
        </div>
      ))}
    </div>
  ) : (
    <div className="future-slot">
      <span className="eyebrow">HYPOTHESES</span>
      <h3>Nothing inferred. Nothing invented.</h3>
      <p>
        Candidate causes, uncertainty and supporting or contradicting evidence will appear when the
        causal engine is connected.
      </p>
    </div>
  );
}
export function SequenceComparison({
  original,
  result,
}: {
  original: SequenceEvent[];
  result: MinimizationResult | null;
}) {
  const render = (events: SequenceEvent[]) => (
    <ol className="sequence-events">
      {events.map((event) => (
        <li key={event.id}>
          <span className="timeline-point" />
          <div>
            <strong>{event.operation}</strong>
            <small>{dateTime(event.timestamp)}</small>
          </div>
          <code>{event.id.slice(0, 8)}</code>
        </li>
      ))}
    </ol>
  );
  return (
    <div className="two-columns">
      <Panel
        title="Original recorded sequence"
        subtitle={`${original.length} events loaded from the selected run`}
      >
        {original.length ? (
          render(original)
        ) : (
          <p className="panel-empty">Select a run with persisted timeline events.</p>
        )}
      </Panel>
      <Panel
        title="Reduced failure sequence"
        subtitle={result ? "Result supplied by the minimization engine" : "Engine unavailable"}
      >
        {result ? (
          render(result.reduced)
        ) : (
          <div className="future-slot">
            <Scissors size={24} />
            <h3>No minimization result</h3>
            <p>
              Removed events, replay attempts and reproduction rates are unavailable. No placeholder
              statistics are shown.
            </p>
          </div>
        )}
      </Panel>
    </div>
  );
}
export function VerificationTable({ comparison }: { comparison: VerificationComparison | null }) {
  return comparison ? (
    <table>
      <thead>
        <tr>
          <th>Condition</th>
          <th>Original</th>
          <th>Candidate</th>
        </tr>
      </thead>
      <tbody>
        {comparison.conditions.map((condition) => (
          <tr key={condition.name}>
            <td>{condition.name}</td>
            <td>{condition.original}</td>
            <td>{condition.candidate}</td>
          </tr>
        ))}
      </tbody>
    </table>
  ) : (
    <div className="verification-empty-grid">
      {["Source revision", "Candidate patch", "Failure retest", "Regression outcomes"].map(
        (label) => (
          <div key={label}>
            <span className="eyebrow">{label}</span>
            <strong>Not available</strong>
            <small>Requires a recorded verification result</small>
          </div>
        ),
      )}
    </div>
  );
}
export function FutureWorkspace({
  section,
}: {
  section: Extract<Section, "ai" | "minimization" | "verification">;
}) {
  const capabilities = useQuery({ queryKey: ["capabilities"], queryFn: api.capabilities });
  const { runId, setRun } = useRunLocation();
  const summary = useSummary(runId);
  const config =
    section === "ai"
      ? {
          icon: Sparkles,
          title: "From evidence to understanding.",
          description:
            "A dedicated workspace for causal hypotheses, counterevidence, and controlled interventions. The Phase 3 intelligence engine is not available yet.",
          labels: ["Evidence-backed hypotheses", "Causal interventions", "Explicit uncertainty"],
        }
      : section === "minimization"
        ? {
            icon: Scissors,
            title: "Find the smallest sequence that matters.",
            description:
              "Inspect the original recorded sequence today. Automated reduction and repeated reproduction belong to Phase 3 and are unavailable.",
            labels: ["Original sequence", "Reduced sequence", "Reproduction evidence"],
          }
        : {
            icon: GitPullRequest,
            title: "A fix is a claim. Verification is evidence.",
            description:
              "A prepared comparison workspace for source revisions, candidate patches, invariant retests, and regression evidence. The repair and verification engine is unavailable.",
            labels: ["Source comparison", "Fault retesting", "Regression evidence"],
          };
  const Icon = config.icon;
  const original: SequenceEvent[] =
    summary.data?.artifacts.map((artifact) => ({
      id: artifact.id,
      timestamp: artifact.created_at,
      operation: artifact.kind,
      artifactIds: [artifact.id],
    })) ?? [];
  return (
    <div className="page-stack">
      <section className="future-hero">
        <span className="future-phase">
          <LockKeyhole size={12} />
          PHASE 3 · NOT AVAILABLE
        </span>
        <div className="intelligence-emblem">
          <Icon size={38} />
        </div>
        <h2>{config.title}</h2>
        <p>{config.description}</p>
        <div className="future-capabilities">
          {config.labels.map((label) => (
            <span key={label}>
              <CheckCheck size={14} />
              {label}
            </span>
          ))}
        </div>
        <Button disabled variant="secondary">
          <LockKeyhole size={14} />
          Engine not connected
        </Button>
      </section>
      {capabilities.error && (
        <ErrorState
          error={capabilities.error}
          retry={() => {
            void capabilities.refetch();
          }}
        />
      )}
      {section === "ai" ? (
        <>
          <div className="two-columns">
            <Panel
              title="Hypothesis workspace"
              subtitle="Typed contracts ready for future analysis"
            >
              <HypothesisList hypotheses={null} />
            </Panel>
            <Panel title="Interventions & outcomes" subtitle="No analysis has been executed">
              <div className="future-slot">
                <Workflow size={26} />
                <h3>Awaiting controlled investigation</h3>
                <p>
                  Proposed interventions, their real experiment outcomes, and uncertainty will be
                  presented here. No generated root-cause claim is treated as fact.
                </p>
              </div>
            </Panel>
          </div>
          <Panel
            title="Dependency context"
            subtitle="Registered topology, not an inferred causal graph"
          >
            <SystemGraph compact />
          </Panel>
        </>
      ) : (
        <>
          <RunPicker runId={runId} onChange={setRun} />
          {summary.error && (
            <ErrorState
              error={summary.error}
              retry={() => {
                void summary.refetch();
              }}
            />
          )}
          {section === "minimization" ? (
            <SequenceComparison original={original} result={null} />
          ) : (
            <Panel
              title="Verification comparison"
              subtitle="Typed source/candidate/outcome contract prepared"
            >
              <VerificationTable comparison={null} />
              {summary.data && (
                <>
                  <FactLabel kind="observed" />
                  <h3>Original execution record</h3>
                  <JsonView
                    value={{
                      run_id: summary.data.run.id,
                      result: summary.data.run.result,
                      versions: summary.data.artifacts.find(
                        (artifact) => artifact.kind === "manifest",
                      )?.payload.versions,
                    }}
                  />
                </>
              )}
            </Panel>
          )}
        </>
      )}
    </div>
  );
}
