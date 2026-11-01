"use client";
import { api, ApiError } from "@/lib/api";
import type { Project } from "@/types/domain";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState } from "react";
import { Toaster } from "sonner";
import { AccessProvider } from "./access";

type ProjectContextValue = {
  projects: Project[];
  projectId: string;
  setProjectId: (id: string) => void;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
};
const ProjectContext = createContext<ProjectContextValue | null>(null);
function Projects({ children }: { children: React.ReactNode }) {
  const query = useQuery({ queryKey: ["projects"], queryFn: ({ signal }) => api.projects(signal) });
  const [selected, setSelected] = useState(() =>
    typeof window !== "undefined" ? (window.localStorage.getItem("failurelab.project") ?? "") : "",
  );
  const projects = query.data ?? [];
  const projectId = projects.some((project) => project.id === selected)
    ? selected
    : (projects[0]?.id ?? "");
  function setProjectId(id: string) {
    setSelected(id);
    window.localStorage.setItem("failurelab.project", id);
  }
  return (
    <ProjectContext.Provider
      value={{
        projects,
        projectId,
        setProjectId,
        loading: query.isPending,
        error: query.error,
        refetch: () => {
          void query.refetch();
        },
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}
export function useProject() {
  const context = useContext(ProjectContext);
  if (!context) throw new Error("Project provider is missing");
  return context;
}
export function Providers({
  children,
  readOnly = false,
}: {
  children: React.ReactNode;
  readOnly?: boolean;
}) {
  useEffect(() => {
    document.documentElement.dataset.contrast =
      localStorage.getItem("failurelab.contrast") ?? "standard";
  }, []);
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 15_000,
            retry: (count, error) =>
              !(error instanceof ApiError && error.status < 500) && count < 1,
            refetchOnWindowFocus: true,
          },
          mutations: { retry: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <AccessProvider readOnly={readOnly}>
        <Projects>{children}</Projects>
      </AccessProvider>
      <Toaster theme="dark" richColors position="bottom-right" />
    </QueryClientProvider>
  );
}
