import { AlertCircle, ArrowUpRight, Database, SearchX } from "lucide-react";
import Link from "next/link";
import { Button } from "./button";
export function Loading({ label = "Loading backend data" }: { label?: string }) {
  return (
    <div aria-live="polite" aria-busy="true" className="loading-state">
      <span className="sr-only">{label}</span>
      <div className="skeleton skeleton-title" />
      <div className="skeleton-grid">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton skeleton-card" />
        ))}
      </div>
      <div className="skeleton skeleton-panel" />
    </div>
  );
}
export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  return (
    <div className="state-panel error-panel" role="alert">
      <AlertCircle />
      <h2>Backend data is unavailable</h2>
      <p>{error instanceof Error ? error.message : "The request could not be completed."}</p>
      <p className="muted">No cached or example results are presented as live data.</p>
      {retry && (
        <Button variant="secondary" onClick={retry}>
          Retry connection
        </Button>
      )}
    </div>
  );
}
export function EmptyState({
  title,
  description,
  href,
  action,
}: {
  title: string;
  description: string;
  href?: string;
  action?: string;
}) {
  return (
    <div className="state-panel">
      <SearchX size={28} />
      <h2>{title}</h2>
      <p>{description}</p>
      {href && (
        <Button asChild variant="secondary">
          <Link href={href}>
            {action ?? "Open settings"}
            <ArrowUpRight size={14} />
          </Link>
        </Button>
      )}
    </div>
  );
}
export function NoProject() {
  return (
    <EmptyState
      title="Your first system starts here"
      description="Create a project and register the managed demo services, or run the documented seed command. Every view is powered by your backend."
      href="/settings"
      action="Create a project"
    />
  );
}
export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function FactLabel({ kind }: { kind: "observed" | "inferred" | "missing" }) {
  return (
    <span className={`fact-label ${kind}`}>
      <Database size={11} />
      {kind === "observed"
        ? "Observed fact"
        : kind === "inferred"
          ? "Inferred explanation"
          : "Missing evidence"}
    </span>
  );
}
