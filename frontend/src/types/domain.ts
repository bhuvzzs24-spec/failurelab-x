import type { components } from "./api.generated";
export type Schema = components["schemas"];
export type Project = Schema["ProjectOut"];
export type Service = Schema["ServiceOut"];
export type Graph = Schema["Graph"];
export type Experiment = Schema["ExperimentOut"];
export type ExperimentConfig = Schema["ExperimentConfig"];
export type Run = Schema["RunOut"];
export type Finding = Schema["FindingOut"];
export type Artifact = Schema["ArtifactOut"];
export type Summary = Schema["RunSummary"];
export type Overview = Schema["ProjectOverview"];
export type Capabilities = Schema["Capabilities"];
export type Page<T> = { items: T[]; offset: number; limit: number; total: number };
export type Status = Run["status"];
export type Section =
  | "home"
  | "graph"
  | "experiments"
  | "findings"
  | "evidence"
  | "replay"
  | "ai"
  | "minimization"
  | "verification"
  | "settings";
