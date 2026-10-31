"use client";
import { request } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  Box,
  ChevronLeft,
  Command,
  FlaskConical,
  GitBranch,
  Layers3,
  Menu,
  PanelLeftClose,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  SquareTerminal,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useProject } from "./providers";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
export const navigation = [
  { href: "/", label: "Command center", icon: Layers3, group: "WORKSPACE" },
  { href: "/graph", label: "System graph", icon: GitBranch },
  { href: "/experiments", label: "Experiment studio", icon: FlaskConical },
  { href: "/findings", label: "Failure investigator", icon: Search },
  { href: "/evidence", label: "Evidence explorer", icon: Box },
  { href: "/replay", label: "Failure replay", icon: Workflow },
  { href: "/ai", label: "AI investigator", icon: Sparkles, group: "INTELLIGENCE", future: true },
  { href: "/minimization", label: "Minimal sequence", icon: Activity, future: true },
  { href: "/verification", label: "Fix verification lab", icon: ShieldCheck, future: true },
  { href: "/settings", label: "Settings", icon: Settings2, group: "CONFIGURATION" },
];
export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [command, setCommand] = useState(false);
  const [search, setSearch] = useState("");
  const { projects, projectId, setProjectId, loading } = useProject();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => request<{ status: string; version: string }>("health"),
    refetchInterval: 15_000,
    retry: false,
  });
  const ready = useQuery({
    queryKey: ["readiness"],
    queryFn: () => request<{ status: string }>("ready"),
    refetchInterval: 15_000,
    retry: false,
  });
  useEffect(() => {
    const handle = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobile(false);
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        setCommand((value) => !value);
      }
    };
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, []);
  const current = navigation.find((entry) => entry.href === path);
  return (
    <div className={cn("app-shell", collapsed && "sidebar-collapsed", mobile && "mobile-open")}>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      {mobile && (
        <button
          className="mobile-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobile(false)}
        />
      )}
      <aside className="sidebar" aria-label="Primary navigation">
        <Link href="/" className="brand">
          <span className="brand-symbol">
            <FlaskConical size={20} />
          </span>
          <span className="brand-wordmark">
            FailureLab <b>X</b>
          </span>
        </Link>
        <button
          className="workspace-switch"
          onClick={() => {
            router.push("/settings");
            setMobile(false);
          }}
        >
          <span className="workspace-avatar">FL</span>
          <span className="workspace-name">
            Engineering workspace<small>Local sandbox</small>
          </span>
          <ChevronLeft className="workspace-chevron" size={14} />
        </button>
        <nav>
          {navigation.map(({ href, label, icon: Icon, group, future }) => (
            <div key={href}>
              {group && <span className="nav-group">{group}</span>}
              <Link
                href={href}
                title={collapsed ? label : undefined}
                aria-current={path === href ? "page" : undefined}
                className={cn("nav-item", path === href && "selected")}
                onClick={() => setMobile(false)}
              >
                <Icon size={17} />
                <span>{label}</span>
                {future && <span className="phase-tag">P3</span>}
              </Link>
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sandbox-note">
            <span className="status-dot" />
            <span>
              Sandbox isolation<small>Managed demo targets only</small>
            </span>
          </div>
          <a
            className="nav-item"
            href="https://github.com/bhuvzzs24-spec/failurelab-x"
            target="_blank"
            rel="noreferrer"
          >
            <BookOpen size={16} />
            <span>Documentation</span>
            <ArrowUpRight size={13} />
          </a>
          <button
            className="collapse-control"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => setCollapsed(!collapsed)}
          >
            <PanelLeftClose size={17} />
            <span>Collapse sidebar</span>
          </button>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="topbar">
          <div className="topbar-left">
            <Button
              variant="ghost"
              size="icon"
              className="mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobile(true)}
            >
              <Menu size={19} />
            </Button>
            <span className="breadcrumb">
              Workspace <span>/</span> <strong>{current?.label ?? "FailureLab X"}</strong>
            </span>
          </div>
          <div className="topbar-actions">
            <label className="project-select">
              <GitBranch size={14} />
              <span className="sr-only">Project</span>
              <select
                aria-label="Project"
                value={projectId}
                disabled={loading || !projects.length}
                onChange={(event) => {
                  setProjectId(event.target.value);
                  router.push(path);
                }}
              >
                {!projects.length && (
                  <option value="">{loading ? "Loading projects…" : "No projects"}</option>
                )}
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>
            <span
              className={cn(
                "connection-indicator",
                health.isError ? "offline" : ready.data ? "ready" : "pending",
              )}
              title={
                ready.isError ? "API reachable; database or broker not ready" : "Backend connection"
              }
            >
              <span className="status-dot" />
              {health.isPending
                ? "Connecting"
                : health.isError
                  ? "API offline"
                  : ready.data
                    ? "Backend ready"
                    : "API connected"}
            </span>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Open command palette"
              onClick={() => setCommand(true)}
            >
              <Command size={16} />
            </Button>
            <span className="operator-avatar" title="Local operator">
              OP
            </span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
        <footer className="app-footer">
          <span>
            <SquareTerminal size={12} /> FAILURELAB X{" "}
            <span className="footer-version">PHASE 2</span>
          </span>
          <span>
            Evidence over assumptions <span className="footer-separator">·</span> Local execution
            only
          </span>
        </footer>
      </div>
      <Dialog open={command} onOpenChange={setCommand}>
        <DialogContent className="command-dialog">
          <DialogTitle>Navigate workspace</DialogTitle>
          <DialogDescription>Search pages. Press Escape to close.</DialogDescription>
          <label className="search-field">
            <Search size={17} />
            <input
              autoFocus
              aria-label="Search pages"
              placeholder="Where would you like to go?"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <kbd>⌘ K</kbd>
          </label>
          <div className="command-results">
            {navigation
              .filter((item) => item.label.toLowerCase().includes(search.toLowerCase()))
              .map((item) => (
                <button
                  key={item.href}
                  onClick={() => {
                    router.push(item.href);
                    setCommand(false);
                  }}
                >
                  <item.icon size={16} />
                  <span>{item.label}</span>
                  <ArrowUpRight size={14} />
                </button>
              ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
