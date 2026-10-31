"use client";
import { useSummary } from "@/hooks/data";
import { dateTime, shortId } from "@/lib/utils";
import { Download, FileJson, Search } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { ArtifactView, downloadJson, RunPicker, useRunLocation } from "./evidence-common";
import { Button } from "./ui/button";
import { EmptyState, ErrorState, Loading, Panel } from "./ui/states";
export function EvidenceExplorer() {
  const { runId, setRun } = useRunLocation();
  const params = useSearchParams();
  const query = useSummary(runId);
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("");
  const [findingId, setFindingId] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const summary = query.data;
  const finding = summary?.findings.find((finding) => finding.id === findingId);
  const refs = Array.isArray(finding?.evidence.evidence_refs)
    ? finding.evidence.evidence_refs
    : null;
  const artifacts = (summary?.artifacts ?? []).filter(
    (artifact) =>
      (!kind || artifact.kind === kind) &&
      (!refs || refs.includes(artifact.id)) &&
      `${artifact.kind} ${artifact.id} ${JSON.stringify(artifact.payload)}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const selected =
    artifacts.find((artifact) => artifact.id === (selectedId || params.get("artifact"))) ??
    artifacts[0];
  return (
    <div className="page-stack">
      <RunPicker
        runId={runId}
        onChange={(id) => {
          setRun(id);
          setSelectedId("");
          setFindingId("");
        }}
      />
      {!runId ? (
        <EmptyState
          title="Evidence, with provenance"
          description="Select an execution to inspect the artifacts actually stored by the engine. No local filesystem browsing is exposed."
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
          <div className="evidence-toolbar">
            <label className="search-field">
              <Search size={15} />
              <input
                aria-label="Search recorded evidence"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search payloads, kinds, or artifact IDs…"
              />
            </label>
            <select
              aria-label="Filter artifact kind"
              value={kind}
              onChange={(event) => {
                setKind(event.target.value);
                setSelectedId("");
              }}
            >
              <option value="">All artifact kinds</option>
              {Array.from(new Set(summary?.artifacts.map((artifact) => artifact.kind))).map(
                (value) => (
                  <option key={value}>{value}</option>
                ),
              )}
            </select>
            <select
              aria-label="Filter evidence by finding"
              value={findingId}
              onChange={(event) => {
                setFindingId(event.target.value);
                setSelectedId("");
              }}
            >
              <option value="">All findings & artifacts</option>
              {summary?.findings.map((finding) => (
                <option key={finding.id} value={finding.id}>
                  Finding {shortId(finding.id)}
                </option>
              ))}
            </select>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => downloadJson(summary, `failurelab-run-${runId}.json`)}
            >
              <Download size={14} />
              Export record
            </Button>
          </div>
          <div className="evidence-layout">
            <Panel
              title="Execution artifacts"
              subtitle={`${artifacts.length} matching · ${summary?.artifacts.length ?? 0} recorded`}
              className="artifact-list-panel"
            >
              <div className="artifact-list">
                {artifacts.map((artifact) => (
                  <button
                    key={artifact.id}
                    className={selected?.id === artifact.id ? "artifact-selected" : ""}
                    onClick={() => setSelectedId(artifact.id)}
                  >
                    <FileJson size={17} />
                    <span>
                      <strong>{artifact.kind.replaceAll("_", " ")}</strong>
                      <small>{dateTime(artifact.created_at)}</small>
                      <code>{shortId(artifact.id)}</code>
                    </span>
                    <span className="artifact-extension">JSON</span>
                  </button>
                ))}
                {!artifacts.length && (
                  <p className="panel-empty">No artifacts match the filters.</p>
                )}
              </div>
            </Panel>
            <Panel title="Evidence inspector" subtitle="Read-only, escaped JSON representation">
              {selected ? (
                <ArtifactView artifact={selected} />
              ) : (
                <EmptyState
                  title="No selected artifact"
                  description="Choose an artifact or adjust the filters."
                />
              )}
            </Panel>
          </div>
          {kind === "logs" && (
            <p className="microcopy">
              Raw logs are not available inline. The manifest contains recorded log source
              references.
            </p>
          )}
        </>
      )}
    </div>
  );
}
