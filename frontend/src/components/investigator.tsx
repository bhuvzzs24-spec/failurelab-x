"use client";
import { useFindings, useInvariants, useSummary } from "@/hooks/data";
import { asObject, asText, dateTime, shortId } from "@/lib/utils";
import type { Finding, Summary } from "@/types/domain";
import { ArrowUpRight, ChevronRight, GitBranch, Search, ShieldAlert, Terminal } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { TimelineList } from "./dashboard";
import { JsonView, StateComparison } from "./evidence-common";
import { useProject } from "./providers";
import { Button } from "./ui/button";
import { EmptyState, ErrorState, FactLabel, Loading, Panel } from "./ui/states";
import { StatusBadge } from "./ui/status";

function Detail({ summary, finding }: { summary: Summary; finding: Finding }) {
  const { projectId } = useProject();
  const invariants = useInvariants(projectId);
  const evidence = finding.evidence;
  const snapshots = summary.artifacts.filter((artifact) => artifact.kind === "snapshot");
  const workflows = summary.artifacts.filter((artifact) => artifact.kind === "workflow");
  const manifest = summary.artifacts.find((artifact) => artifact.kind === "manifest");
  const name =
    invariants.data?.find((rule) => rule.id === finding.invariant_id)?.name ??
    `Invariant ${shortId(finding.invariant_id)}`;
  return (
    <div className="page-stack">
      <Panel
        title={name}
        subtitle={`Finding ${finding.id}`}
        action={<StatusBadge status={asText(evidence.status, "FAIL")} />}
      >
        <div className="investigation-banner">
          <span className="finding-mark">
            <ShieldAlert size={25} />
          </span>
          <div>
            <span className="eyebrow">CROSS-SERVICE CORRECTNESS</span>
            <h2>{finding.summary}</h2>
            <p>
              Persisted deterministic rule outcome, supported by authoritative state observations.
            </p>
          </div>
        </div>
        <FactLabel kind="observed" />
        <StateComparison observed={evidence.observed} />
        <div className="split-evidence">
          <div>
            <h3>Expected constraint</h3>
            <JsonView value={evidence.expected} label="Expected invariant constraint" />
          </div>
          <div>
            <h3>Observed state</h3>
            <JsonView value={evidence.observed} label="Observed authoritative state" />
          </div>
        </div>
        <div className="evaluation-provenance">
          <span>
            Evaluated{" "}
            {typeof evidence.evaluated_at === "number"
              ? dateTime(evidence.evaluated_at)
              : "timestamp not recorded"}
          </span>
          <span>
            {Array.isArray(evidence.evidence_refs) ? evidence.evidence_refs.length : 0} supporting
            references
          </span>
        </div>
      </Panel>
      <div className="two-columns">
        <Panel
          title="Execution timeline"
          subtitle={`Run ${shortId(summary.run.id)} · ${summary.run.status}`}
          action={
            <Button asChild variant="ghost" size="sm">
              <Link href={`/evidence?run=${summary.run.id}`}>
                All events
                <ArrowUpRight size={12} />
              </Link>
            </Button>
          }
        >
          <TimelineList events={summary.artifacts} limit={20} />
        </Panel>
        <div className="page-stack">
          <Panel title="Fault configuration" subtitle="Recorded experiment scope">
            <FactLabel kind="observed" />
            <JsonView value={summary.run.config} label="Recorded experiment configuration" />
          </Panel>
          <Panel
            title="Investigation boundary"
            subtitle="What the evidence does and does not establish"
          >
            <FactLabel kind="inferred" />
            <p className="body-copy">
              The configured fault and the failed invariant occurred within this recorded
              experiment. Causal attribution requires controlled interventions; this interface makes
              no confirmed root-cause claim.
            </p>
            <FactLabel kind="missing" />
            <p className="body-copy">
              Raw logs and complete distributed spans are not stored by the Phase 1 API. Only
              recorded trace identifiers and log source references are available.
            </p>
          </Panel>
        </div>
      </div>
      <Panel
        title="Trace correlation & log references"
        subtitle="References recorded by the engine; not fabricated trace spans"
      >
        <div className="trace-grid">
          {workflows.map((artifact) => (
            <div className="trace-record" key={artifact.id}>
              <Terminal size={16} />
              <div>
                <strong>Checkout {asText(asObject(artifact.payload.input).key)}</strong>
                <JsonView
                  value={{
                    trace: artifact.payload.trace_reference,
                    outcome: artifact.payload.outcome,
                  }}
                  label="Trace correlation"
                />
              </div>
            </div>
          ))}
        </div>
        {manifest ? (
          <JsonView value={manifest.payload.log_reference} label="Recorded log reference" />
        ) : (
          <p className="panel-empty">No log reference recorded.</p>
        )}
      </Panel>
      <Panel title="Supporting evidence" subtitle={`${snapshots.length} state snapshots recorded`}>
        <div className="reference-list">
          {summary.artifacts
            .filter(
              (artifact) =>
                Array.isArray(evidence.evidence_refs) &&
                evidence.evidence_refs.includes(artifact.id),
            )
            .map((artifact) => (
              <Link
                key={artifact.id}
                href={`/evidence?run=${summary.run.id}&artifact=${artifact.id}`}
              >
                <span className="small-icon">
                  <GitBranch size={14} />
                </span>
                <div>
                  <strong>
                    {artifact.kind} · {asText(artifact.payload.stage, "observation")}
                  </strong>
                  <small>{artifact.id}</small>
                </div>
                <ArrowUpRight size={14} />
              </Link>
            ))}
        </div>
        <div className="panel-bottom-actions">
          <Button asChild variant="secondary">
            <Link href={`/replay?run=${summary.run.id}`}>
              Reproduction metadata
              <ArrowUpRight size={13} />
            </Link>
          </Button>
        </div>
      </Panel>
    </div>
  );
}
export function Investigator() {
  const { projectId } = useProject();
  const params = useSearchParams();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const findings = useFindings(projectId, offset);
  const runId = params.get("run") ?? "";
  const requested = params.get("finding");
  const summary = useSummary(runId);
  const finding =
    summary.data?.findings.find((item) => item.id === requested) ?? summary.data?.findings[0];
  return (
    <div className="investigator-layout">
      <Panel
        title="Recorded findings"
        subtitle="Authoritative FAIL outcomes"
        className="finding-list-panel"
      >
        <label className="search-field">
          <Search size={14} />
          <input
            aria-label="Filter findings on this page"
            value={search}
            placeholder="Filter this page…"
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        {findings.isPending ? (
          <p className="panel-empty">Loading findings…</p>
        ) : findings.error ? (
          <ErrorState
            error={findings.error}
            retry={() => {
              void findings.refetch();
            }}
          />
        ) : !findings.data.items.length ? (
          <EmptyState
            title="No findings yet"
            description="A finding appears only after a genuine invariant violation."
            href="/experiments"
            action="Run an experiment"
          />
        ) : (
          <div className="finding-selection-list">
            {findings.data.items
              .filter((item) =>
                `${item.summary} ${item.id} ${item.run_id}`
                  .toLowerCase()
                  .includes(search.toLowerCase()),
              )
              .map((item) => (
                <button
                  key={item.id}
                  className={finding?.id === item.id ? "finding-selected" : ""}
                  onClick={() => router.push(`/findings?run=${item.run_id}&finding=${item.id}`)}
                >
                  <span className="finding-mark">
                    <ShieldAlert size={16} />
                  </span>
                  <div>
                    <strong>{item.summary}</strong>
                    <small>Run {shortId(item.run_id)}</small>
                    <span className="mono">{shortId(item.invariant_id)}</span>
                  </div>
                  <ChevronRight size={14} />
                </button>
              ))}
          </div>
        )}
        <div className="pagination">
          <Button
            variant="ghost"
            size="sm"
            disabled={!offset}
            onClick={() => setOffset(offset - 25)}
          >
            Previous
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={!findings.data || offset + 25 >= findings.data.total}
            onClick={() => setOffset(offset + 25)}
          >
            Next
          </Button>
        </div>
      </Panel>
      <div>
        {!runId ? (
          <EmptyState
            title="Follow the evidence"
            description="Select a persisted finding to inspect its exact rule, authoritative state, timeline, and reproduction record."
          />
        ) : summary.isPending ? (
          <Loading label="Loading finding evidence" />
        ) : summary.error ? (
          <ErrorState
            error={summary.error}
            retry={() => {
              void summary.refetch();
            }}
          />
        ) : finding ? (
          <Detail summary={summary.data} finding={finding} />
        ) : (
          <EmptyState
            title="No violation recorded in this run"
            description="The run may be active, healthy, failed to execute, or inconclusive. Inspect its real outcomes in the studio."
            href={`/experiments?run=${runId}`}
            action="Open execution"
          />
        )}
      </div>
    </div>
  );
}
