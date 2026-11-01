import { allPages, request } from "./api";
import type { Schema } from "@/types/domain";
export type ResearchJob = Schema["ResearchJobOut"];
export type Trial = Schema["TrialOut"];
export type Candidate = Schema["CandidateOut"];
export type ResearchCreate = Schema["ResearchCreate"];
export const research = {
  capabilities: () => request<Record<string, unknown>>("api/v1/research/capabilities"),
  jobs: (project: string) => allPages<ResearchJob>(`api/v1/research/projects/${project}/jobs`),
  trials: (project: string) => allPages<Trial>(`api/v1/research/projects/${project}/trials`),
  findings: (project: string) =>
    allPages<Schema["ResearchFindingOut"]>(`api/v1/research/projects/${project}/findings`),
  candidates: (project: string) =>
    allPages<Candidate>(`api/v1/research/projects/${project}/candidates`),
  decisions: (job: string) =>
    allPages<Schema["DecisionOut"]>(`api/v1/research/jobs/${job}/decisions`),
  artifacts: (job: string) =>
    allPages<Schema["ResearchArtifactOut"]>(`api/v1/research/jobs/${job}/artifacts`),
  create: (project: string, body: ResearchCreate) =>
    request<ResearchJob>(`api/v1/research/projects/${project}/jobs`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  cancel: (job: string) =>
    request<ResearchJob>(`api/v1/research/jobs/${job}/cancel`, { method: "POST", body: "{}" }),
};

export async function evidenceBundle(jobId: string) {
  const job = await request<ResearchJob>(`api/v1/research/jobs/${jobId}`);
  const [trials, decisions, artifacts] = await Promise.all([
    allPages<Trial>(`api/v1/research/jobs/${jobId}/trials`),
    research.decisions(jobId),
    research.artifacts(jobId),
  ]);
  const candidateId =
    job.input.candidate_id ??
    (typeof job.result.candidate_id === "string" ? job.result.candidate_id : null);
  const candidate = candidateId
    ? await request<Candidate>(`api/v1/research/candidates/${candidateId}`)
    : null;
  const sourceId = candidate?.source_trial_id ?? job.input.source_trial_id;
  const sourceTrial = sourceId ? await request<Trial>(`api/v1/research/trials/${sourceId}`) : null;
  const bundle = {
    format: "failurelab-evidence-v1",
    redacted: true,
    job,
    trials,
    decisions,
    artifacts,
    candidate,
    source_trial: sourceTrial,
    complete: job.status === "COMPLETED",
    limitations: [
      "Bridge redacts secrets and local paths; artifact hashes identify original backend payloads.",
      "A completed job may contain an infrastructure error or failed invariant; inspect outcomes.",
    ],
  };
  if (new TextEncoder().encode(JSON.stringify(bundle)).length > 32 * 1024 * 1024)
    throw new Error(
      "Evidence exceeds the 32 MiB browser export limit. Retrieve paginated records through the authenticated API.",
    );
  return bundle;
}
