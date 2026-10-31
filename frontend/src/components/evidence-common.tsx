"use client";
import { useRuns } from "@/hooks/data";
import { asObject, asText, dateTime, shortId } from "@/lib/utils";
import type { Artifact } from "@/types/domain";
import { Download } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useProject } from "./providers";
import { Button } from "./ui/button";
export function JsonView({ value, label = "JSON evidence" }: { value: unknown; label?: string }) {
  return (
    <pre className="json-view" tabIndex={0} aria-label={label}>
      <code>{JSON.stringify(value, null, 2) ?? "No value recorded"}</code>
    </pre>
  );
}
export function downloadJson(value: unknown, filename: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = filename.replace(/[^a-zA-Z0-9._-]/g, "_");
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function ArtifactView({ artifact }: { artifact: Artifact }) {
  return (
    <div className="artifact-detail">
      <div className="artifact-detail-heading">
        <div>
          <span className="eyebrow">{artifact.kind.replaceAll("_", " ")}</span>
          <h3>{shortId(artifact.id)}</h3>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => downloadJson(artifact, `failurelab-artifact-${artifact.id}.json`)}
        >
          <Download size={13} />
          Download JSON
        </Button>
      </div>
      <dl className="detail-list compact">
        <div>
          <dt>Recorded</dt>
          <dd>{dateTime(artifact.created_at)}</dd>
        </div>
        <div>
          <dt>Artifact ID</dt>
          <dd className="mono break-all">{artifact.id}</dd>
        </div>
        <div>
          <dt>Original SHA-256</dt>
          <dd className="mono break-all">{artifact.sha256}</dd>
        </div>
      </dl>
      <p className="microcopy">
        Secret values and local paths are redacted before display and download. The hash identifies
        the original backend payload, not this redacted representation.
      </p>
      <JsonView value={artifact.payload} label="Artifact payload" />
    </div>
  );
}
export function RunPicker({ runId, onChange }: { runId: string; onChange: (id: string) => void }) {
  const { projectId } = useProject();
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState("");
  const query = useRuns(projectId, offset, status);
  return (
    <div className="run-picker">
      <label>
        <span>Execution record</span>
        <select
          aria-label="Select execution record"
          value={runId}
          onChange={(event) => onChange(event.target.value)}
        >
          {!runId && <option value="">Select a recorded run</option>}
          {runId && !query.data?.items.some((run) => run.id === runId) && (
            <option value={runId}>{shortId(runId)} · linked execution</option>
          )}
          {query.data?.items.map((run) => (
            <option value={run.id} key={run.id}>
              {shortId(run.id)} · {run.status} · {dateTime(run.created_at)}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Status filter</span>
        <select
          aria-label="Filter available runs"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setOffset(0);
          }}
        >
          <option value="">All statuses</option>
          {["CREATED", "QUEUED", "RUNNING", "VERIFYING", "COMPLETED", "FAILED", "CANCELLED"].map(
            (status) => (
              <option key={status}>{status}</option>
            ),
          )}
        </select>
      </label>
      <div className="picker-pagination">
        <Button
          variant="ghost"
          size="sm"
          disabled={!offset}
          onClick={() => setOffset(Math.max(0, offset - 25))}
        >
          Previous
        </Button>
        <Button
          variant="ghost"
          size="sm"
          disabled={!query.data || offset + 25 >= query.data.total}
          onClick={() => setOffset(offset + 25)}
        >
          Next
        </Button>
      </div>
      {query.error && (
        <p role="alert" className="inline-error">
          {query.error.message}
        </p>
      )}
    </div>
  );
}
export function useRunLocation() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  return {
    runId: params.get("run") ?? "",
    findingId: params.get("finding") ?? "",
    setRun: (id: string) => router.push(`${pathname}?run=${encodeURIComponent(id)}`),
  };
}
export function StateComparison({ observed }: { observed: unknown }) {
  const state = asObject(observed);
  return (
    <div className="state-comparison">
      {Object.entries(state).map(([service, value]) => {
        const item = asObject(value);
        return (
          <div className="state-service" key={service}>
            <span className="eyebrow">{service}</span>
            <strong
              className={
                item.status === "pending"
                  ? "text-amber"
                  : item.status === "charged"
                    ? "text-cyan"
                    : ""
              }
            >
              {asText(item.status)}
            </strong>
            <dl>
              <div>
                <dt>Amount</dt>
                <dd>{typeof item.amount === "number" ? item.amount : "Not observed"}</dd>
              </div>
              <div>
                <dt>Quantity</dt>
                <dd>{typeof item.quantity === "number" ? item.quantity : "Not observed"}</dd>
              </div>
            </dl>
          </div>
        );
      })}
    </div>
  );
}
