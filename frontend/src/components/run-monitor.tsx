"use client";
import { useSummary } from "@/hooks/data";
import { api } from "@/lib/api";
import { asObject, asText, dateTime, isActive, shortId } from "@/lib/utils";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Check,
  Circle,
  ExternalLink,
  LoaderCircle,
  ShieldAlert,
  Square,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { TimelineList } from "./dashboard";
import { Button } from "./ui/button";
import { Confirm } from "./ui/confirm";
import { ErrorState, Loading, Panel } from "./ui/states";
import { StatusBadge } from "./ui/status";
const stages = ["CREATED", "QUEUED", "RUNNING", "VERIFYING"];
export function RunMonitor({ runId }: { runId: string }) {
  const query = useSummary(runId);
  const [confirm, setConfirm] = useState(false);
  const client = useQueryClient();
  const cancel = useMutation({
    mutationFn: () => api.cancel(runId),
    onSuccess: () => {
      toast.success("Cancellation requested; waiting for cleanup");
      void client.invalidateQueries({ queryKey: ["summary", runId] });
    },
    onError: (error) => toast.error(error.message),
  });
  if (query.isPending) return <Loading label="Loading execution" />;
  if (query.error)
    return (
      <ErrorState
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      />
    );
  const { run, findings, artifacts } = query.data;
  const current = stages.indexOf(run.status);
  const terminal = !isActive(run.status);
  const evaluations = asObject(run.result.evaluations);
  return (
    <Panel
      title={`Execution ${shortId(run.id)}`}
      subtitle={`Created ${dateTime(run.created_at)} · deadline ${dateTime(run.deadline)}`}
      action={<StatusBadge status={run.status} />}
    >
      <ol className="run-stages" aria-label="Execution lifecycle">
        {stages.map((stage, index) => (
          <li
            key={stage}
            className={
              run.status === stage
                ? "stage-current"
                : terminal || index < current
                  ? "stage-past"
                  : ""
            }
          >
            {index < current || run.status === "COMPLETED" ? (
              <Check size={14} />
            ) : run.status === stage ? (
              <LoaderCircle size={14} className="spin" />
            ) : (
              <Circle size={12} />
            )}
            <span>{stage}</span>
          </li>
        ))}
      </ol>
      <div className="run-control-bar">
        <code className="break-all">{run.id}</code>
        {isActive(run.status) && (
          <Button
            variant="destructive"
            size="sm"
            disabled={!!run.cancel_requested || cancel.isPending}
            control="execute"
            onClick={() => setConfirm(true)}
          >
            <Square size={12} />
            {run.cancel_requested ? "Cancellation requested" : "Cancel run"}
          </Button>
        )}
      </div>
      {asText(run.result.reason, "") && (
        <div className="notice notice-warning" role="status">
          {asText(run.result.reason)}
          {run.result.detail ? ` · ${asText(run.result.detail)}` : ""}
        </div>
      )}
      {run.status === "COMPLETED" && (
        <p className="microcopy">
          Execution completed. Invariant outcomes below determine whether the target behaved
          correctly.
        </p>
      )}
      {!!Object.keys(evaluations).length && (
        <div className="evaluation-strip">
          {Object.entries(evaluations).map(([id, value]) => (
            <div key={id}>
              <span>Invariant {shortId(id)}</span>
              <StatusBadge status={asText(asObject(value).status, "INCONCLUSIVE")} small />
            </div>
          ))}
        </div>
      )}
      {findings.map((finding) => (
        <Link
          className="run-finding"
          key={finding.id}
          href={`/findings?run=${run.id}&finding=${finding.id}`}
        >
          <ShieldAlert size={19} />
          <div>
            <strong>{finding.summary}</strong>
            <span>Open invariant evidence</span>
          </div>
          <ArrowUpRight size={17} />
        </Link>
      ))}
      <TimelineList events={artifacts} limit={6} />
      <div className="panel-bottom-actions">
        <Button asChild variant="secondary" size="sm">
          <Link href={`/evidence?run=${run.id}`}>
            Inspect {artifacts.length} artifacts
            <ArrowUpRight size={13} />
          </Link>
        </Button>
        <Button asChild variant="ghost" size="sm">
          <Link href={`/replay?run=${run.id}`}>
            Reproduction record
            <ExternalLink size={12} />
          </Link>
        </Button>
      </div>
      <Confirm
        open={confirm}
        onOpenChange={setConfirm}
        title="Cancel this experiment?"
        description="The worker will stop orchestration and remove injected faults. Business effects that have already committed are not rolled back."
        action="Request cancellation"
        pending={cancel.isPending}
        onConfirm={() => cancel.mutate()}
      />
    </Panel>
  );
}
