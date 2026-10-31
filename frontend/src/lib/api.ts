import type {
  Capabilities,
  Experiment,
  Finding,
  Graph,
  Overview,
  Page,
  Project,
  Run,
  Schema,
  Summary,
} from "@/types/domain";
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, {
    cache: "no-store",
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const data = await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(response.status, data?.error?.message ?? "The backend request failed");
  return data as T;
}
export async function allPages<T>(path: string, signal?: AbortSignal): Promise<T[]> {
  const items: T[] = [];
  let offset = 0;
  for (let page = 0; page < 1000; page++) {
    const result = await request<Page<T>>(
      `${path}${path.includes("?") ? "&" : "?"}offset=${offset}&limit=100`,
      { signal },
    );
    items.push(...result.items);
    offset += result.items.length;
    if (offset >= result.total) return items;
    if (!result.items.length) throw new Error("The backend returned an incomplete collection");
  }
  throw new Error("Collection is too large to load; narrow the query");
}
const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });
export const api = {
  projects: (signal?: AbortSignal) => allPages<Project>("api/v1/projects", signal),
  graph: (id: string, signal?: AbortSignal) =>
    request<Graph>(`api/v1/projects/${id}/graph`, { signal }),
  experiments: (id: string, signal?: AbortSignal) =>
    allPages<Experiment>(`api/v1/projects/${id}/experiments`, signal),
  invariants: (id: string, signal?: AbortSignal) =>
    allPages<Schema["InvariantOut"]>(`api/v1/projects/${id}/invariants`, signal),
  overview: (id: string, signal?: AbortSignal) =>
    request<Overview>(`api/v1/projects/${id}/overview`, { signal }),
  runs: (id: string, offset = 0, status = "", signal?: AbortSignal) =>
    request<Page<Run>>(
      `api/v1/projects/${id}/runs?offset=${offset}&limit=25${status ? `&status=${encodeURIComponent(status)}` : ""}`,
      { signal },
    ),
  findings: (id: string, offset = 0, signal?: AbortSignal) =>
    request<Page<Finding>>(`api/v1/projects/${id}/findings?offset=${offset}&limit=25`, { signal }),
  summary: (id: string, signal?: AbortSignal) =>
    request<Summary>(`api/v1/runs/${id}/summary`, { signal }),
  capabilities: () => request<Capabilities>("api/v1/capabilities"),
  createProject: (body: Schema["ProjectCreate"]) => post<Project>("api/v1/projects", body),
  createService: (id: string, body: Schema["ServiceCreate"]) =>
    post<Schema["ServiceOut"]>(`api/v1/projects/${id}/services`, body),
  createExperiment: (id: string, body: Schema["ExperimentCreate"]) =>
    post<Experiment>(`api/v1/projects/${id}/experiments`, body),
  start: (id: string, key: string) =>
    post<Run>(`api/v1/experiments/${id}/runs`, { idempotency_key: key }),
  cancel: (id: string) => post<Run>(`api/v1/runs/${id}/cancel`, {}),
};
export const registration = {
  dependency: (projectId: string, body: Schema["DependencyCreate"]) =>
    post<Schema["DependencyOut"]>(`api/v1/projects/${projectId}/dependencies`, body),
  invariant: (projectId: string, body: Schema["InvariantCreate"]) =>
    post<Schema["InvariantOut"]>(`api/v1/projects/${projectId}/invariants`, body),
};
