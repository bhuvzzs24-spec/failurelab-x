/** Server-only, network-free read model. Never imports an execution adapter. */
import { readFile, stat } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { z } from "zod";

export const demoEnvironment = (env: Record<string, string | undefined>) =>
  env.DATA_MODE === "recorded_demo" || env.DEPLOYMENT_ENV === "frontend_demo";

export function validateDemoEnvironment(env: Record<string, string | undefined>) {
  if (
    env.DATA_MODE !== "recorded_demo" ||
    env.DEPLOYMENT_ENV !== "frontend_demo" ||
    env.ACCESS_MODE !== "read_only"
  )
    throw new Error("The recorded demo requires its complete read-only environment profile");
  if (env.VERCEL === "1" && env.VERCEL_ENV !== "preview")
    throw new Error("This demo profile is permitted only in Vercel Preview");
  for (const [name, value] of Object.entries(env))
    if (
      value &&
      (/^(?:BACKEND_URL|HOSTED_BACKEND_ORIGIN|API_TOKEN|CONTROL_TOKEN|VERCEL_TOKEN|GH_TOKEN|GITHUB_TOKEN|AUTH_.*_TOKEN|DATABASE_URL|REDIS_URL|REPAIR_AGENT_.*|OLLAMA_.*)$/.test(
        name,
      ) ||
        /^NEXT_PUBLIC_.*(?:TOKEN|SECRET|PASSWORD|KEY)/i.test(name))
    )
      throw new Error(
        "Execution connections and credentials must be absent from the frontend demo",
      );
}

export const datasetSchema = z.object({
  format: z.literal("failurelab-frontend-demo-v1"),
  captured_at: z.number().finite().positive(),
  source_revision: z.string().regex(/^[a-f0-9]{40}$/),
  source_snapshot_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  notice: z.string().min(20),
  resources: z.record(z.string(), z.unknown()),
});
export type DemoDataset = z.infer<typeof datasetSchema>;
export type LoadedDemo = { data: DemoDataset; sha256: string };
let cached: Promise<LoadedDemo> | undefined;
export async function loadRecordedDemo(): Promise<LoadedDemo> {
  if (!cached)
    cached = (async () => {
      const file = resolve(process.cwd(), "demo-data/recorded.json");
      if ((await stat(file)).size > 16 * 1024 * 1024)
        throw new Error("Demo dataset exceeds its bound");
      const bytes = await readFile(file);
      const digest = createHash("sha256").update(bytes).digest("hex");
      const expected = (await readFile(file + ".sha256", "utf8")).trim();
      if (expected !== digest) throw new Error("Demo dataset integrity mismatch");
      const data = datasetSchema.parse(JSON.parse(bytes.toString("utf8")));
      // Active historical rows must never be interpreted as live work in this release.
      for (const [path, value] of Object.entries(data.resources)) {
        if (!/^api\/v1\/[A-Za-z0-9_/-]+$/.test(path))
          throw new Error("Invalid recorded resource path");
        if (/\/(?:runs|jobs)$/.test(path)) {
          const page = value as { items?: { status: string }[] };
          if (page.items?.some((row) => !["COMPLETED", "FAILED", "CANCELLED"].includes(row.status)))
            throw new Error("A frontend demo cannot contain active execution records");
        }
      }
      return { data, sha256: digest };
    })().catch((error) => {
      cached = undefined;
      throw error;
    });
  return cached;
}
const response = (body: unknown, status = 200) =>
  Response.json(body, {
    status,
    headers: {
      "Cache-Control": "private, no-store",
      "X-FailureLab-Data-Source": "recorded_demo",
      "X-Robots-Tag": "noindex, nofollow, noarchive",
    },
  });
const failure = (status: number, message: string) =>
  response({ error: { code: String(status), message } }, status);
const object = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};

/** Existing GET contracts, backed only by recorded responses. Missing evidence stays missing. */
export function recordedResponse(request: Request, segments: string[], loaded: LoadedDemo) {
  if (request.method !== "GET")
    return failure(403, "Recorded demonstration: all mutations and execution are unavailable");
  if (!segments.every((part) => /^[A-Za-z0-9_-]+$/.test(part)))
    return failure(404, "Unsupported recorded resource");
  const path = segments.join("/");
  const { data, sha256 } = loaded;
  const provenance = {
    data_source: "recorded_demo",
    captured_at: data.captured_at,
    source_revision: data.source_revision,
    dataset_sha256: sha256,
    live_backend: false,
  };
  if (path === "api/v1/session")
    return response({
      role: "viewer",
      read_only: true,
      can_execute: false,
      can_manage: false,
      ...provenance,
    });
  if (path === "health" || path === "ready")
    return response({ status: "recorded_demo", version: data.source_revision, ...provenance });
  if (path === "api/v1/capabilities")
    return response({
      sandbox_id: "recorded-demo-no-executor",
      engine_version: data.source_revision,
      allowed_services: [],
      fault_targets: [],
      fault_kinds: [],
      max_fault_seconds: 0,
      max_run_seconds: 0,
      automatic_replay: false,
      causal_analysis: false,
      minimization: false,
      repair_verification: false,
      logs_inline: false,
      ...provenance,
    });
  if (path === "api/v1/research/capabilities")
    return response({
      sandbox: "recorded-demo-no-executor",
      defects: [],
      strategies: [],
      candidate_execution: "unavailable",
      repair_agent_configured: false,
      llm_enabled: false,
      max_job_seconds: 0,
      max_actions: 0,
      arbitrary_repository_repair: false,
      ...provenance,
    });
  const url = new URL(request.url);
  for (const key of url.searchParams.keys())
    if (!["offset", "limit", "status", "kind"].includes(key))
      return failure(400, "Unsupported recorded query parameter");
  let value: unknown = data.resources[path];
  if (value === undefined) {
    // Resolve individual records from the complete captured collections.
    const match =
      /^(api\/v1\/(?:research\/)?(?:projects|services|invariants|experiments|runs|findings|trials|candidates|jobs|artifacts))\/([A-Za-z0-9_-]+)$/.exec(
        path,
      );
    if (match)
      for (const [key, collection] of Object.entries(data.resources)) {
        if (key.endsWith("/" + match[1].split("/").at(-1))) {
          const found = (object(collection).items as Record<string, unknown>[] | undefined)?.find(
            (row) => row.id === match[2],
          );
          if (found) {
            value = found;
            break;
          }
        }
        if (path.startsWith("api/v1/artifacts/") && key.endsWith("/summary")) {
          const found = (
            object(collection).artifacts as Record<string, unknown>[] | undefined
          )?.find((row) => row.id === match[2]);
          if (found) {
            value = found;
            break;
          }
        }
      }
    const jobTrials = /^api\/v1\/research\/jobs\/([A-Za-z0-9_-]+)\/trials$/.exec(path);
    if (
      jobTrials &&
      Object.entries(data.resources).some(
        ([key, value]) =>
          key.startsWith("api/v1/research/projects/") &&
          key.endsWith("/jobs") &&
          (object(value).items as { id: string }[] | undefined)?.some(
            (job) => job.id === jobTrials[1],
          ),
      )
    )
      for (const [key, collection] of Object.entries(data.resources)) {
        if (key.startsWith("api/v1/research/projects/") && key.endsWith("/trials")) {
          const items = object(collection).items;
          if (Array.isArray(items))
            value = { items: items.filter((row) => row.job_id === jobTrials[1]) };
        }
      }
    const run = /^api\/v1\/runs\/([A-Za-z0-9_-]+)\/(artifacts|timeline|findings)$/.exec(path);
    if (run) {
      const summary = object(data.resources[`api/v1/runs/${run[1]}/summary`]);
      const rows = summary[run[2] === "findings" ? "findings" : "artifacts"];
      if (Array.isArray(rows)) value = run[2] === "timeline" ? { events: rows } : { items: rows };
    }
  }
  if (value === undefined)
    return failure(
      404,
      "This resource was not included in the recorded demo. No live backend is connected.",
    );
  const rows = object(value).items;
  if (Array.isArray(rows)) {
    const offset = url.searchParams.get("offset") ?? "0",
      limit = url.searchParams.get("limit") ?? "50";
    if (
      !/^\d+$/.test(offset) ||
      !/^\d+$/.test(limit) ||
      !Number.isSafeInteger(Number(offset)) ||
      Number(limit) < 1 ||
      Number(limit) > 100
    )
      return failure(422, "Pagination requires offset >= 0 and limit 1..100");
    const filtered = rows.filter((row: Record<string, unknown>) =>
      ["status", "kind"].every(
        (key) => !url.searchParams.has(key) || row[key] === url.searchParams.get(key),
      ),
    );
    return response({
      items: filtered.slice(Number(offset), Number(offset) + Number(limit)),
      offset: Number(offset),
      limit: Number(limit),
      total: filtered.length,
    });
  }
  return response(value);
}

export async function recordedBridge(
  request: Request,
  segments: string[],
  env: Record<string, string | undefined>,
) {
  // Refuse mutations even when configuration or the dataset is missing.
  if (request.method !== "GET")
    return failure(403, "Recorded demonstration: all mutations and execution are unavailable");
  try {
    validateDemoEnvironment(env);
  } catch {
    return failure(
      503,
      "The frontend-only demo is not safely configured; no backend connection was attempted",
    );
  }
  try {
    return recordedResponse(request, segments, await loadRecordedDemo());
  } catch {
    return failure(
      503,
      "Reviewed recorded evidence is unavailable or failed integrity checks. No live backend is connected.",
    );
  }
}
