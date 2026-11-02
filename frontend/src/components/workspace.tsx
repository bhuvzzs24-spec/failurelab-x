"use client";
import { useAccess } from "./access";
import type { Section } from "@/types/domain";
import { ArrowUpRight, Play, Plus } from "lucide-react";
import Link from "next/link";
import { Dashboard } from "./dashboard";
import { EvidenceExplorer } from "./evidence-explorer";
import { ExperimentStudio } from "./experiment-studio";
import { ResearchWorkspace } from "./research-workspace";
import { Investigator } from "./investigator";
import { useProject } from "./providers";
import { Replay } from "./replay";
import { Settings } from "./settings";
import { SystemGraph } from "./system-graph";
import { Button } from "./ui/button";
import { ErrorState, Loading, NoProject, Panel } from "./ui/states";
const titles: Record<Section, { eyebrow: string; title: string; description: string }> = {
  explorer: {
    eyebrow: "ADAPTIVE DISCOVERY",
    title: "Experiment explorer",
    description: "Allocate a bounded budget across faults, timing and service boundaries.",
  },
  patches: {
    eyebrow: "ISOLATED REPAIR",
    title: "Patch review",
    description: "Inspect proposed source changes and independent verification evidence.",
  },
  benchmarks: {
    eyebrow: "MEASURE, DO NOT ASSUME",
    title: "Benchmark dashboard",
    description: "Compare discovery strategies under equal budgets and repeated seeds.",
  },
  home: {
    eyebrow: "SYSTEM RELIABILITY / OVERVIEW",
    title: "Command center",
    description: "A complete view of your architecture, experiments and correctness evidence.",
  },
  graph: {
    eyebrow: "DEPENDENCY INTELLIGENCE",
    title: "System graph",
    description: "An explicit model of your services and the boundaries between them.",
  },
  experiments: {
    eyebrow: "EXPERIMENT WORKBENCH",
    title: "Experiment studio",
    description: "Turn a failure scenario into a bounded, verifiable experiment.",
  },
  findings: {
    eyebrow: "EVIDENCE-DRIVEN INVESTIGATION",
    title: "Failure investigator",
    description: "See what happened, what was expected, and what remains unknown.",
  },
  evidence: {
    eyebrow: "OBSERVATIONS / PROVENANCE",
    title: "Evidence explorer",
    description: "Search state snapshots, evaluations, fault schedules, and execution artifacts.",
  },
  replay: {
    eyebrow: "REPRODUCTION WORKSPACE",
    title: "Failure replay",
    description: "Inspect original inputs and recorded instructions before repeating a scenario.",
  },
  ai: {
    eyebrow: "CAUSAL INVESTIGATION",
    title: "AI investigator",
    description: "Test competing hypotheses with paired controlled interventions.",
  },
  minimization: {
    eyebrow: "COUNTEREXAMPLE REDUCTION",
    title: "Minimal failure sequence",
    description: "Reduce observed failures through repeated, signature-preserving trials.",
  },
  verification: {
    eyebrow: "INDEPENDENT VERIFICATION",
    title: "Fix verification lab",
    description: "Compare original and candidate versions in the restricted verification sandbox.",
  },
  settings: {
    eyebrow: "WORKSPACE CONFIGURATION",
    title: "Settings & projects",
    description: "Manage explicit registrations and inspect the connected execution environment.",
  },
};
export function Workspace({ section }: { section: Section }) {
  const access = useAccess();
  const { projectId, loading, error, refetch } = useProject();
  const title = titles[section];
  let content: React.ReactNode;
  if (loading) content = <Loading />;
  else if (error && (section !== "settings" || access.recorded_demo))
    content = <ErrorState error={error} retry={refetch} />;
  else if (!projectId && section !== "settings") content = <NoProject />;
  else
    switch (section) {
      case "home":
        content = <Dashboard />;
        break;
      case "graph":
        content = (
          <Panel
            title="Registered service topology"
            subtitle="Directional dependencies from the backend graph API"
          >
            <SystemGraph />
          </Panel>
        );
        break;
      case "experiments":
        content = <ExperimentStudio key={projectId} />;
        break;
      case "findings":
        content = <Investigator key={projectId} />;
        break;
      case "evidence":
        content = <EvidenceExplorer key={projectId} />;
        break;
      case "replay":
        content = <Replay key={projectId} />;
        break;
      case "settings":
        content = <Settings />;
        break;
      default:
        content = <ResearchWorkspace key={`${projectId}-${section}`} section={section} />;
    }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{title.eyebrow}</span>
          <h1>
            {title.title}
            <span className="heading-dot">.</span>
          </h1>
          <p>{title.description}</p>
        </div>
        <div className="page-heading-actions">
          {section === "home" && (
            <>
              <Button asChild variant="secondary">
                <Link href="/graph">
                  View system
                  <ArrowUpRight size={14} />
                </Link>
              </Button>
              <Button asChild>
                <Link href="/experiments">
                  <Play size={14} />
                  {access.recorded_demo ? "Inspect experiments" : "Run experiment"}
                </Link>
              </Button>
            </>
          )}
          {section === "graph" && (
            <Button asChild variant="secondary">
              <Link href="/settings">
                <Plus size={14} />
                {access.recorded_demo ? "Inspect registrations" : "Register services"}
              </Link>
            </Button>
          )}
        </div>
      </div>
      {["explorer", "minimization", "ai", "patches", "verification", "benchmarks"].includes(
        section,
      ) && (
        <nav className="research-route-tabs" aria-label="Research workflow">
          {[
            ["explorer", "01", "Discover"],
            ["minimization", "02", "Reduce"],
            ["ai", "03", "Investigate"],
            ["patches", "04", "Prepare fix"],
            ["verification", "05", "Verify"],
            ["benchmarks", "06", "Benchmark"],
          ].map(([path, number, label]) => (
            <Link key={path} href={`/${path}`} aria-current={section === path ? "page" : undefined}>
              <span>{number}</span>
              {label}
            </Link>
          ))}
        </nav>
      )}
      {content}
    </>
  );
}
