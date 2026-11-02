"use client";
import { ReplayTimeline } from "./replay-timeline";
import { useSummary } from "@/hooks/data";
import { asText } from "@/lib/utils";
import { AlertTriangle, LockKeyhole, Play } from "lucide-react";
import Link from "next/link";
import { JsonView, RunPicker, useRunLocation } from "./evidence-common";
import { Button } from "./ui/button";
import { EmptyState, ErrorState, FactLabel, Loading, Panel } from "./ui/states";
export function Replay() {
  const { runId, setRun } = useRunLocation();
  const query = useSummary(runId);
  const summary = query.data;
  const manifest = summary?.artifacts.find((artifact) => artifact.kind === "manifest");
  const instructions = manifest?.payload.reproduction;
  return (
    <div className="page-stack">
      <RunPicker runId={runId} onChange={setRun} />
      {!runId ? (
        <EmptyState
          title="A scenario you can inspect and reproduce"
          description="Select a recorded execution to inspect the original inputs, versions, fault schedule, and reproduction instructions."
        />
      ) : query.isPending ? (
        <Loading />
      ) : query.error ? (
        <ErrorState
          error={query.error}
          retry={() => {
            void query.refetch();
          }}
        />
      ) : (
        <>
          <div className="notice notice-warning">
            <AlertTriangle size={18} />
            <div>
              <strong>Scenario reproducibility is not exact deterministic replay</strong>
              <span>
                The execution engine stores reproduction metadata. It has no automatic replay
                endpoint. Timing, image drift, and scheduling can differ.
              </span>
            </div>
          </div>
          <Panel
            title="Recorded failure sequence"
            subtitle="Inspect the actual order of faults, workflows and authoritative observations"
          >
            <ReplayTimeline artifacts={summary?.artifacts ?? []} />
          </Panel>
          <div className="two-columns">
            <Panel title="Original experiment configuration" subtitle="Immutable run snapshot">
              <FactLabel kind="observed" />
              <JsonView value={summary?.run.config} />
            </Panel>
            <Panel
              title="Recorded service versions"
              subtitle="Operator-supplied identifiers; not verified image digests"
            >
              {manifest ? (
                <JsonView
                  value={{
                    versions: manifest.payload.versions,
                    image_identifiers: manifest.payload.image_identifiers,
                    engine_version: manifest.payload.engine_version,
                    python: manifest.payload.python,
                  }}
                />
              ) : (
                <EmptyState
                  title="Version manifest not recorded"
                  description="This execution has no manifest artifact."
                />
              )}
            </Panel>
          </div>
          <Panel title="Reproduction instructions" subtitle="Recorded by the execution engine">
            {Array.isArray(instructions) ? (
              <ol className="reproduction-steps">
                {instructions.map((value, index) => (
                  <li key={index}>
                    <span>{index + 1}</span>
                    <p>{asText(value)}</p>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="panel-empty">No reproduction instructions were recorded.</p>
            )}
            <div className="replay-actions">
              <Button disabled variant="secondary">
                <LockKeyhole size={14} />
                Automatic replay unavailable
              </Button>
              <Button asChild>
                <Link href={`/experiments?experiment=${summary?.run.experiment_id}`}>
                  <Play size={14} />
                  Configure a new scenario run
                </Link>
              </Button>
            </div>
            <p className="microcopy">
              A new scenario run creates new workflow keys and resets the sandbox. It is not
              presented as replay of the original execution.
            </p>
          </Panel>
          <div className="two-columns">
            <Panel title="Fault schedule" subtitle="Actual recorded activation and removal events">
              <JsonView
                value={summary?.artifacts
                  .filter((artifact) => artifact.kind === "fault_schedule")
                  .map((artifact) => ({ created_at: artifact.created_at, ...artifact.payload }))}
              />
            </Panel>
            <Panel
              title="Workflow inputs & outcomes"
              subtitle="Original idempotency keys and observed API results"
            >
              <JsonView
                value={summary?.artifacts
                  .filter((artifact) => artifact.kind === "workflow")
                  .map((artifact) => artifact.payload)}
              />
            </Panel>
          </div>
          <Panel title="Remaining nondeterminism" subtitle="Explicit replay limitations">
            <JsonView
              value={manifest?.payload.nondeterminism ?? ["No nondeterminism metadata recorded"]}
            />
          </Panel>
        </>
      )}
    </div>
  );
}
