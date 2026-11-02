"use client";
import { useAccess } from "./access";
import { useProject } from "./providers";
import { useGraph, useInvariants } from "@/hooks/data";
import { Panel, ErrorState, Loading } from "./ui/states";
import { JsonView } from "./evidence-common";

export function RecordedDemoSettings() {
  const access = useAccess();
  const { projects, projectId } = useProject();
  const graph = useGraph(projectId),
    invariants = useInvariants(projectId);
  if (graph.isPending || invariants.isPending) return <Loading />;
  if (graph.error || invariants.error)
    return (
      <ErrorState
        error={graph.error ?? invariants.error}
        retry={() => {
          void graph.refetch();
          void invariants.refetch();
        }}
      />
    );
  return (
    <div className="page-stack">
      <Panel
        title="Frontend-only recorded demonstration"
        subtitle="No external API, database, broker or experiment worker is connected"
      >
        <dl className="detail-list">
          <dt>Access</dt>
          <dd>Viewer · immutable recorded evidence</dd>
          <dt>Live execution</dt>
          <dd>Unavailable</dd>
          <dt>Captured</dt>
          <dd>
            {access.captured_at
              ? new Date(access.captured_at * 1000).toLocaleString()
              : "Not available"}
          </dd>
          <dt>Recorded engine source</dt>
          <dd>{access.source_revision ?? "Not available"}</dd>
          <dt>Projects</dt>
          <dd>{projects.map((project) => project.name).join(", ")}</dd>
          <dt>Registered services at capture</dt>
          <dd>{graph.data?.nodes.length ?? 0}</dd>
          <dt>Invariants at capture</dt>
          <dd>{invariants.data?.length ?? 0}</dd>
        </dl>
        <p className="microcopy">
          Project administration, target registration, credentials, fault injection and patch
          execution are not exposed. Provider authentication protects the approved preview; this
          viewer is not an operator login.
        </p>
      </Panel>
      <Panel
        title="Recorded service registrations"
        subtitle="Dependency metadata is historical; health and traffic are not inferred"
      >
        <JsonView value={graph.data} />
      </Panel>
      <Panel
        title="Recorded invariants"
        subtitle="Deterministic constraints used by the original executions"
      >
        <JsonView value={invariants.data} />
      </Panel>
    </div>
  );
}
