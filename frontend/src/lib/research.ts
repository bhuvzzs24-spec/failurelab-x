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
