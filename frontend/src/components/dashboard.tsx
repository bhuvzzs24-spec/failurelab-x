"use client";
import { useAccess } from "./access";
import { useOverview, useSummary } from "@/hooks/data";
import { asObject, asText, relativeTime, shortId } from "@/lib/utils";
import type { Artifact } from "@/types/domain";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Box,
  FlaskConical,
  GitBranch,
  ShieldAlert,
  Zap,
} from "lucide-react";
import Link from "next/link";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useProject } from "./providers";
import { SystemGraph } from "./system-graph";
import { EmptyState, ErrorState, Loading, Panel } from "./ui/states";
import { StatusBadge } from "./ui/status";

export function TimelineList({ events, limit = 8 }: { events: Artifact[]; limit?: number }) {
  if (!events.length) return <p className="panel-empty">No recorded execution events.</p>;
  return (
    <ol className="timeline-list">
      {events
        .slice(-limit)
        .reverse()
        .map((event) => (
          <li key={event.id}>
            <span
              className={`timeline-point ${event.kind === "evaluation" ? "point-violet" : ""}`}
            />
            <div>
              <strong>{event.kind.replaceAll("_", " ")}</strong>
              <span>
                {asText(
                  event.payload.status,
                  asText(
                    event.payload.stage,
                    event.payload.activated_at
                      ? "Fault activated"
                      : event.payload.removed_at
                        ? "Fault removed"
                        : "Evidence recorded",
                  ),
                )}
              </span>
            </div>
            <time dateTime={new Date(event.created_at * 1000).toISOString()}>
              {relativeTime(event.created_at)}
            </time>
          </li>
        ))}
    </ol>
  );
}
export function Dashboard() {
  const access = useAccess();
  const { projectId } = useProject();
  const query = useOverview(projectId);
  const overview = query.data;
  const latest = useSummary(overview?.latest_runs[0]?.id ?? "");
  if (query.isPending) return <Loading />;
  if (query.error)
    return (
      <ErrorState
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      />
    );
  if (!overview) return null;
  const metrics = [
    {
      label: "Registered services",
      value: overview.service_count,
      icon: GitBranch,
      detail: "Explicit dependency model",
      tone: "violet",
    },
    {
      label: "Total experiments",
      value: overview.run_count,
      icon: FlaskConical,
      detail: `${overview.experiment_count} reusable definitions`,
      tone: "cyan",
    },
    {
      label: access.recorded_demo ? "Active at capture" : "Active executions",
      value: overview.active_run_count,
      icon: Activity,
      detail: access.recorded_demo
        ? "Historical snapshot; no live jobs"
        : "Queued, running or verifying",
      tone: "emerald",
    },
    {
      label: "Invariant violations",
      value: overview.violation_count,
      icon: ShieldAlert,
      detail: "Authoritative FAIL findings",
      tone: "red",
    },
  ];
  const faults = latest.data?.artifacts.filter((a) => a.kind === "fault_schedule") ?? [];
  return (
    <div className="page-stack command-center">
      <div className="overview-context">
        <span>
          <span className="status-dot" /> Project observatory
        </span>
        <span>
          Persisted observations <span className="context-separator">/</span>{" "}
          {access.recorded_demo ? "Frozen demo dataset" : "Live backend queries"}
        </span>
      </div>
      <div className="metric-grid">
        {metrics.map(({ label, value, icon: Icon, detail, tone }, i) => (
          <div className={`metric-card metric-${tone}`} key={label}>
            <div className="metric-top">
              <span>{label}</span>
              <Icon size={17} />
            </div>
            <div className="metric-value">
              <strong>{value.toLocaleString()}</strong>
              <span className="metric-index">0{i + 1}</span>
            </div>
            <small>{detail}</small>
          </div>
        ))}
      </div>
      <div className="overview-grid">
        <Panel
          title="System topology"
          subtitle="Your registered architecture, mapped to service boundaries"
          className="graph-panel overview-topology"
          action={
            <Link href="/graph" className="text-link">
              Open map <ArrowUpRight size={14} />
            </Link>
          }
        >
          <SystemGraph compact />
        </Panel>
        <Panel
          title="Research pulse"
          subtitle="Discovery, interventions and verification"
          className="research-pulse"
        >
          <div className="pulse-number">
            <Activity size={19} />
            <strong>{overview.active_research_count ?? "—"}</strong>
            <span>{access.recorded_demo ? "active jobs at capture" : "active research jobs"}</span>
          </div>
          <div className="pulse-facts">
            <div>
              <span>Recorded jobs</span>
              <strong>{overview.research_job_count ?? "—"}</strong>
            </div>
            <div>
              <span>Unique violation patterns</span>
              <strong>{overview.research_violation_count ?? "—"}</strong>
            </div>
            <div>
              <span>Execution artifacts</span>
              <strong>{overview.artifact_count}</strong>
            </div>
          </div>
          <p className="pulse-note">
            Research signatures are deduplicated independently from experiment findings.
          </p>
          <Link className="pulse-action" href="/explorer">
            <span>
              <FlaskConical size={16} /> Explore failure boundaries
            </span>
            <ArrowRight size={16} />
          </Link>
          <Link className="pulse-action" href="/benchmarks">
            <span>
              <Activity size={16} /> Compare discovery strategies
            </span>
            <ArrowRight size={16} />
          </Link>
        </Panel>
      </div>
      <div className="dashboard-secondary">
        <Panel
          title="Recent experiments"
          subtitle="From controlled injection to a verifiable outcome"
          action={
            <Link href="/experiments" className="text-link">
              All executions <ArrowUpRight size={14} />
            </Link>
          }
        >
          {overview.latest_runs.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Execution</th>
                    <th>Fault boundary</th>
                    <th>Status</th>
                    <th>Recorded</th>
                    <th>
                      <span className="sr-only">Open</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {overview.latest_runs.slice(0, 5).map((run) => (
                    <tr key={run.id}>
                      <td>
                        <Link className="table-run" href={`/experiments?run=${run.id}`}>
                          <span className="small-icon">
                            <FlaskConical size={15} />
                          </span>
                          <span>
                            <strong>{shortId(run.id)}</strong>
                            <small>Sandbox experiment</small>
                          </span>
                        </Link>
                      </td>
                      <td>
                        <span className="boundary-cell">
                          {asText(asObject(run.config.fault).target)}
                        </span>
                        <small className="cell-subtitle">
                          {asText(asObject(run.config.fault).kind).replaceAll("_", " ")}
                        </small>
                      </td>
                      <td>
                        <StatusBadge small status={run.status} />
                      </td>
                      <td className="muted nowrap">{relativeTime(run.created_at)}</td>
                      <td>
                        <Link
                          href={`/experiments?run=${run.id}`}
                          aria-label={`Open run ${shortId(run.id)}`}
                        >
                          <ArrowUpRight size={16} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No executions yet"
              description="Run a bounded experiment to begin recording evidence."
              href="/experiments"
              action="Open experiment studio"
            />
          )}
        </Panel>
        <Panel
          title="Execution trend"
          subtitle="Recorded run creation · 14 days · UTC"
          action={<span className="subtle-chip">14 days</span>}
        >
          <div className="chart-total">
            <strong>{overview.activity.reduce((n, p) => n + p.runs, 0)}</strong>
            <span>recorded runs in this window</span>
          </div>
          <div
            className="activity-chart"
            role="img"
            aria-label={`Run activity: ${overview.activity.map((p) => `${p.day}: ${p.runs}`).join(", ")}`}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={overview.activity}
                margin={{ left: -24, right: 10, top: 8, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="activity-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#8d9eff" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#8d9eff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#272c39" vertical={false} strokeDasharray="3 5" />
                <XAxis
                  dataKey="day"
                  tickFormatter={(v: string) => v.slice(5)}
                  minTickGap={32}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#a0a9bf", fontSize: 11 }}
                />
                <YAxis
                  allowDecimals={false}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#a0a9bf", fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    background: "#191e2b",
                    border: "1px solid #353d53",
                    borderRadius: 8,
                    color: "#f1f3ff",
                  }}
                />
                <Area
                  dataKey="runs"
                  type="linear"
                  stroke="#9aa9ff"
                  fill="url(#activity-fill)"
                  strokeWidth={2}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-statuses">
            {Object.entries(overview.status_counts).map(([status, count]) => (
              <span key={status}>
                <StatusBadge small status={status} />
                <b>{count}</b>
              </span>
            ))}
          </div>
        </Panel>
      </div>
      <div className="dashboard-tertiary">
        <Panel
          title="Findings that matter"
          subtitle="Business correctness failures, supported by observed state"
          action={
            <Link href="/findings" className="text-link">
              Investigate <ArrowUpRight size={14} />
            </Link>
          }
        >
          {overview.latest_findings.length ? (
            <div className="finding-preview-list">
              {overview.latest_findings.slice(0, 3).map((f) => (
                <Link key={f.id} href={`/findings?run=${f.run_id}&finding=${f.id}`}>
                  <span className="finding-mark">
                    <ShieldAlert size={19} />
                  </span>
                  <div>
                    <strong>{f.summary}</strong>
                    <small>
                      Invariant {shortId(f.invariant_id)} · run {shortId(f.run_id)}
                    </small>
                  </div>
                  <StatusBadge status="FAIL" small />
                  <ArrowRight size={16} />
                </Link>
              ))}
            </div>
          ) : (
            <div className="quiet-state">
              <ShieldAlert size={24} />
              <div>
                <strong>No invariant violations recorded</strong>
                <p>No findings have been observed in this project.</p>
              </div>
            </div>
          )}
          <div className="evidence-footnote">
            <Box size={14} />
            {overview.artifact_count} persisted evidence artifacts
            <Link href="/evidence">
              Browse evidence <ArrowRight size={13} />
            </Link>
          </div>
        </Panel>
        <Panel
          title="Latest execution timeline"
          subtitle={
            overview.latest_runs[0]
              ? `Execution ${shortId(overview.latest_runs[0].id)}`
              : "Waiting for an execution"
          }
        >
          {latest.error ? (
            <p className="inline-error">Timeline could not be loaded.</p>
          ) : latest.data ? (
            <TimelineList events={latest.data.artifacts} limit={5} />
          ) : (
            <p className="panel-empty">Events appear after an experiment starts.</p>
          )}
          {faults.length > 0 && (
            <div className="recorded-fault-strip">
              <Zap size={14} />
              <span>
                {faults.some((a) => !!a.payload.removed_at)
                  ? "Fault removal recorded"
                  : "Fault schedule recorded"}
                <small>Recorded activity; no live fault assertion</small>
              </span>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
