"use client";
import type { Section } from "@/types/domain";
import { ArrowUpRight, Play, Plus } from "lucide-react";
import Link from "next/link";
import { Dashboard } from "./dashboard";
import { EvidenceExplorer } from "./evidence-explorer";
import { ExperimentStudio } from "./experiment-studio";
import { FutureWorkspace } from "./future-workspaces";
import { Investigator } from "./investigator";
import { useProject } from "./providers";
import { Replay } from "./replay";
import { Settings } from "./settings";
import { SystemGraph } from "./system-graph";
import { Button } from "./ui/button";
import { ErrorState, Loading, NoProject, Panel } from "./ui/states";
const titles: Record<Section, { eyebrow: string; title: string; description: string }> = {
  home: {
    eyebrow: "YOUR SYSTEM, UNDER A MICROSCOPE",
    title: "Command center",
    description: "Explore the boundaries. Surface the failures. Trust the evidence.",
  },
  graph: {
    eyebrow: "DEPENDENCY INTELLIGENCE",
    title: "System graph",
    description: "An explicit model of your services and the boundaries between them.",
  },
  experiments: {
    eyebrow: "CONTROLLED CHAOS. MEASURABLE OUTCOMES.",
    title: "Experiment studio",
    description: "Turn a failure scenario into a bounded, verifiable experiment.",
  },
  findings: {
    eyebrow: "EVIDENCE-DRIVEN INVESTIGATION",
    title: "Failure investigator",
    description: "See what happened, what was expected, and what remains unknown.",
  },
  evidence: {
    eyebrow: "THE RECORD OF WHAT ACTUALLY HAPPENED",
    title: "Evidence explorer",
    description: "Search state snapshots, evaluations, fault schedules, and execution artifacts.",
  },
  replay: {
    eyebrow: "REPRODUCIBILITY, WITH HONEST LIMITS",
    title: "Failure replay",
    description: "Inspect original inputs and recorded instructions before repeating a scenario.",
  },
  ai: {
    eyebrow: "PHASE 3 WORKSPACE",
    title: "AI investigator",
    description: "A prepared workspace for causal reasoning grounded in execution evidence.",
  },
  minimization: {
    eyebrow: "PHASE 3 WORKSPACE",
    title: "Minimal failure sequence",
    description: "Compare recorded events with future verified reduction results.",
  },
  verification: {
    eyebrow: "PHASE 3 WORKSPACE",
    title: "Fix verification lab",
    description: "Prepare to test a repair against the failure it claims to resolve.",
  },
  settings: {
    eyebrow: "WORKSPACE CONFIGURATION",
    title: "Settings & projects",
    description: "Manage explicit registrations and inspect the connected execution environment.",
  },
};
export function Workspace({ section }: { section: Section }) {
  const { projectId, loading, error, refetch } = useProject();
  const title = titles[section];
  let content: React.ReactNode;
  if (loading) content = <Loading />;
  else if (error && section !== "settings") content = <ErrorState error={error} retry={refetch} />;
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
        content = <FutureWorkspace section={section} />;
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
                  Run experiment
                </Link>
              </Button>
            </>
          )}
          {section === "graph" && (
            <Button asChild variant="secondary">
              <Link href="/settings">
                <Plus size={14} />
                Register services
              </Link>
            </Button>
          )}
        </div>
      </div>
      {content}
    </>
  );
}
