"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Check,
  FileSearch,
  GitCompareArrows,
  HelpCircle,
  ShieldCheck,
  X,
} from "lucide-react";
import type { Trial } from "@/lib/research";
import { request } from "@/lib/api";
import { asObject, asText, shortId } from "@/lib/utils";
import { JsonView, StateComparison } from "./evidence-common";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { ErrorState, FactLabel, Loading } from "./ui/states";
import { StatusBadge } from "./ui/status";
// Research result payload is open JSON in OpenAPI. Values are validated by ResultView
// against the backend Hypothesis contract before this component receives them.
export type HypothesisView = {
  id: string;
  description: string;
  status: "UNTESTED" | "SUPPORTED" | "REFUTED" | "INCONCLUSIVE";
  services: string[];
  assumptions: string[];
  supporting_observations: string[];
  contradicting_observations: string[];
  intervention: string;
  outcomes: Record<string, unknown>[];
};
const uuid = /^[a-f0-9-]{36}$/i;
export function TrialInspection({ id, onClose }: { id: string; onClose: () => void }) {
  const query = useQuery({
    queryKey: ["inspect-research-trial", id],
    queryFn: () => request<Trial>(`api/v1/research/trials/${id}`),
    enabled: !!id,
    retry: false,
  });
  const snapshots = query.data?.evidence.snapshots;
  const last = Array.isArray(snapshots) ? asObject(snapshots.at(-1)) : {};
  return (
    <Dialog
      open={!!id}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="trial-inspection">
        <DialogTitle>Trial evidence · {shortId(id)}</DialogTitle>
        <DialogDescription>
          Authoritative observations retrieved from the recorded intervention trial.
        </DialogDescription>
        {query.isPending ? (
          <Loading label="Loading trial evidence" />
        ) : query.error ? (
          <ErrorState
            error={query.error}
            retry={() => {
              void query.refetch();
            }}
          />
        ) : (
          query.data && (
            <>
              <div className="trial-inspection-summary">
                <StatusBadge status={query.data.classification} />
                <span>{query.data.scenario.defect.replaceAll("_", " ")}</span>
                <code>{query.data.cost_seconds.toFixed(3)}s measured</code>
              </div>
              <FactLabel kind="observed" />
              <StateComparison observed={last.state} />
              <details>
                <summary>Scenario, snapshots and fault receipts</summary>
                <JsonView value={query.data} label="Intervention trial record" />
              </details>
            </>
          )
        )}
      </DialogContent>
    </Dialog>
  );
}
export function CausalBoard({
  hypotheses,
  interpretation,
}: {
  hypotheses: HypothesisView[];
  interpretation?: string;
}) {
  const [chosen, setChosen] = useState(hypotheses[0]?.id ?? "");
  const [trial, setTrial] = useState("");
  const selected = hypotheses.find((h) => h.id === chosen) ?? hypotheses[0];
  if (!selected)
    return <p className="panel-empty">No hypotheses were recorded by this investigation.</p>;
  const references = (items: string[], type: "support" | "contradict") =>
    !items.length ? (
      <p className="missing-observation">
        No {type === "support" ? "supporting" : "contradicting"} evidence recorded.
      </p>
    ) : (
      <ul className="causal-reference-list">
        {items.map((value, i) => (
          <li key={`${value}-${i}`}>
            {uuid.test(value) ? (
              <Button variant="ghost" size="sm" onClick={() => setTrial(value)}>
                <FileSearch size={14} />
                Trial {shortId(value)}
                <ArrowUpRight size={12} />
              </Button>
            ) : (
              <span>{value}</span>
            )}
          </li>
        ))}
      </ul>
    );
  return (
    <div className="causal-workbench">
      <div className="causal-summary">
        <span>
          <ShieldCheck size={16} /> Experimental adjudication
        </span>
        <span>
          <strong>{hypotheses.filter((h) => h.status === "SUPPORTED").length}</strong> supported{" "}
          <i /> <strong>{hypotheses.filter((h) => h.status === "REFUTED").length}</strong> refuted{" "}
          <i />{" "}
          <strong>
            {hypotheses.filter((h) => !["SUPPORTED", "REFUTED"].includes(h.status)).length}
          </strong>{" "}
          unresolved
        </span>
      </div>
      <div className="causal-board">
        <div
          className="causal-mechanisms"
          role="tablist"
          aria-label="Competing explanations"
          aria-orientation="vertical"
        >
          {hypotheses.map((h, i) => (
            <button
              key={h.id}
              role="tab"
              id={`hypothesis-${h.id}`}
              aria-controls="hypothesis-detail"
              aria-selected={selected.id === h.id}
              tabIndex={selected.id === h.id ? 0 : -1}
              onClick={() => setChosen(h.id)}
              onKeyDown={(event) => {
                if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
                event.preventDefault();
                const index =
                  event.key === "Home"
                    ? 0
                    : event.key === "End"
                      ? hypotheses.length - 1
                      : (i + (event.key === "ArrowDown" ? 1 : -1) + hypotheses.length) %
                        hypotheses.length;
                setChosen(hypotheses[index].id);
                const tabs =
                  event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>(
                    '[role="tab"]',
                  );
                tabs?.item(index)?.focus();
              }}
            >
              <span className={`mechanism-icon mechanism-${h.status.toLowerCase()}`}>
                {h.status === "SUPPORTED" ? (
                  <Check size={15} />
                ) : h.status === "REFUTED" ? (
                  <X size={15} />
                ) : (
                  <HelpCircle size={15} />
                )}
              </span>
              <span>
                <strong>{h.description}</strong>
                <small>{[...new Set(h.services)].join(" / ")}</small>
              </span>
              <span className="mechanism-state">{h.status}</span>
            </button>
          ))}
        </div>
        <div
          role="tabpanel"
          id="hypothesis-detail"
          aria-labelledby={`hypothesis-${selected.id}`}
          tabIndex={0}
          className="causal-detail"
        >
          <span className="eyebrow">TESTED MECHANISM / {selected.id}</span>
          <h3>{selected.description}</h3>
          <div className="causal-verdict">
            <StatusBadge status={selected.status} />
            <span>Experimental status · no calibrated probability</span>
          </div>
          <p className="causal-intervention">
            <GitCompareArrows size={17} />
            {selected.intervention}
          </p>
          <div className="causal-evidence-grid">
            <div>
              <h4>
                <Check size={14} />
                Supporting evidence
              </h4>
              {references(selected.supporting_observations, "support")}
            </div>
            <div>
              <h4>
                <X size={14} />
                Contradicting evidence
              </h4>
              {references(selected.contradicting_observations, "contradict")}
            </div>
          </div>
          {selected.outcomes.length > 0 && (
            <div className="table-wrap">
              <table>
                <caption>Matched introduced and removed interventions</caption>
                <thead>
                  <tr>
                    <th>Pair</th>
                    <th>Mechanism introduced</th>
                    <th>Mechanism removed</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.outcomes.map((outcome, i) => (
                    <tr key={i}>
                      <td>{String(i + 1).padStart(2, "0")}</td>
                      <td>
                        <strong>{asText(outcome.introduced)}</strong>
                        {typeof outcome.introduced_trial_id === "string" &&
                          uuid.test(outcome.introduced_trial_id) && (
                            <button
                              className="trial-reference"
                              onClick={() => setTrial(String(outcome.introduced_trial_id))}
                            >
                              Inspect {shortId(outcome.introduced_trial_id)}{" "}
                              <ArrowUpRight size={11} />
                            </button>
                          )}
                      </td>
                      <td>
                        <strong>{asText(outcome.removed)}</strong>
                        {typeof outcome.removed_trial_id === "string" &&
                          uuid.test(outcome.removed_trial_id) && (
                            <button
                              className="trial-reference"
                              onClick={() => setTrial(String(outcome.removed_trial_id))}
                            >
                              Inspect {shortId(outcome.removed_trial_id)} <ArrowUpRight size={11} />
                            </button>
                          )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <details className="causal-assumptions">
            <summary>Experimental assumptions</summary>
            <ul>
              {selected.assumptions.map((value) => (
                <li key={value}>{value}</li>
              ))}
            </ul>
          </details>
        </div>
      </div>
      <p className="causal-boundary">
        {interpretation ??
          "A supported paired effect does not establish a unique source-level root cause. Missing evidence remains unresolved."}
      </p>
      {trial && <TrialInspection id={trial} onClose={() => setTrial("")} />}
    </div>
  );
}
