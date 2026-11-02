import { demoEnvironment, recordedBridge } from "./recorded-demo";
import { cloudConfiguration } from "./cloud-config";
import { redact } from "@/lib/redact";

const id = "[a-zA-Z0-9_-]+";
const allowed: { pattern: RegExp; methods: string[] }[] = [
  { pattern: /^api\/v1\/research\/capabilities$/, methods: ["GET"] },
  { pattern: new RegExp(`^api/v1/research/projects/${id}/jobs$`), methods: ["GET", "POST"] },
  {
    pattern: new RegExp(`^api/v1/research/projects/${id}/(trials|findings|candidates)$`),
    methods: ["GET"],
  },
  {
    pattern: new RegExp(`^api/v1/research/jobs/${id}(/(decisions|artifacts|trials))?$`),
    methods: ["GET"],
  },
  { pattern: new RegExp(`^api/v1/research/jobs/${id}/cancel$`), methods: ["POST"] },
  { pattern: new RegExp(`^api/v1/research/(trials|candidates)/${id}$`), methods: ["GET"] },
  { pattern: /^(health|ready)$/, methods: ["GET"] },
  { pattern: /^api\/v1\/session$/, methods: ["GET"] },
  { pattern: /^api\/v1\/capabilities$/, methods: ["GET"] },
  { pattern: /^api\/v1\/projects$/, methods: ["GET", "POST"] },
  { pattern: new RegExp(`^api/v1/projects/${id}$`), methods: ["GET"] },
  {
    pattern: new RegExp(`^api/v1/projects/${id}/(services|invariants|experiments)$`),
    methods: ["GET", "POST"],
  },
  { pattern: new RegExp(`^api/v1/projects/${id}/dependencies$`), methods: ["POST"] },
  {
    pattern: new RegExp(`^api/v1/projects/${id}/(graph|overview|runs|findings)$`),
    methods: ["GET"],
  },
  { pattern: new RegExp(`^api/v1/experiments/${id}$`), methods: ["GET"] },
  { pattern: new RegExp(`^api/v1/experiments/${id}/runs$`), methods: ["GET", "POST"] },
  {
    pattern: new RegExp(`^api/v1/runs/${id}(/(summary|timeline|artifacts|findings))?$`),
    methods: ["GET"],
  },
  { pattern: new RegExp(`^api/v1/runs/${id}/cancel$`), methods: ["POST"] },
  { pattern: new RegExp(`^api/v1/artifacts/${id}$`), methods: ["GET"] },
];
const error = (status: number, message: string) =>
  Response.json(
    { error: { code: String(status), message } },
    { status, headers: { "Cache-Control": "no-store" } },
  );

export async function bridge(
  request: Request,
  segments: string[],
  env: Record<string, string | undefined> = process.env,
): Promise<Response> {
  if (demoEnvironment(env)) return recordedBridge(request, segments, env);
  const path = segments.join("/");
  if (
    !segments.every((segment) => /^[A-Za-z0-9_-]+$/.test(segment)) ||
    !allowed.some((entry) => entry.pattern.test(path) && entry.methods.includes(request.method))
  )
    return error(404, "Unsupported backend operation");
  const incoming = new URL(request.url);
  // Next may construct request.url with an internal hostname. Compare against
  // the validated original Host header, never an untrusted forwarded host.
  let browserOrigin: URL;
  try {
    browserOrigin = new URL(
      incoming.protocol + "//" + (request.headers.get("host") ?? incoming.host),
    );
  } catch {
    return error(400, "Invalid request host");
  }
  const readOnly = env.ACCESS_MODE === "read_only";
  const local = ["127.0.0.1", "localhost", "[::1]"].includes(browserOrigin.hostname);
  const cloud = env.DEPLOYMENT_ENV === "cloud" || env.VERCEL === "1" || !local;
  if (cloud) {
    try {
      const configured = new URL(env.PUBLIC_FRONTEND_ORIGIN ?? "");
      if (
        !readOnly ||
        configured.protocol !== "https:" ||
        configured.username ||
        configured.password ||
        configured.pathname !== "/" ||
        configured.search ||
        configured.hash ||
        configured.host !== browserOrigin.host
      )
        throw new Error();
    } catch {
      return error(403, "Only the configured read-only public frontend host is allowed");
    }
    try {
      cloudConfiguration(env);
    } catch {
      return error(503, "Cloud API connection is not safely configured");
    }
  }
  if (readOnly && request.method !== "GET")
    return error(403, "Read-only demonstration: mutations are disabled");
  if (request.method !== "GET" && request.headers.get("origin") !== browserOrigin.origin)
    return error(403, "Same-origin request required");
  const token = env.API_TOKEN;
  if (!token) return error(503, "Server API connection is not configured");
  let upstream: URL;
  try {
    upstream = new URL(env.BACKEND_URL ?? "");
    const localUpstream =
      !cloud &&
      upstream.protocol === "http:" &&
      ["127.0.0.1", "localhost", "[::1]", "api"].includes(upstream.hostname);
    const hostedUpstream =
      readOnly && upstream.protocol === "https:" && env.HOSTED_BACKEND_ORIGIN === upstream.origin;
    if (
      (!localUpstream && !hostedUpstream) ||
      upstream.username ||
      upstream.password ||
      upstream.search ||
      upstream.hash ||
      !["", "/"].includes(upstream.pathname)
    )
      throw new Error();
  } catch {
    return error(503, "Server backend origin is not authorized");
  }
  upstream.pathname = `/${path}`;
  for (const [key, value] of incoming.searchParams) {
    if (!["offset", "limit", "status", "kind"].includes(key))
      return error(400, "Unsupported query parameter");
    upstream.searchParams.append(key, value);
  }
  let body: string | undefined;
  if (request.method !== "GET") {
    if (!request.headers.get("content-type")?.startsWith("application/json"))
      return error(415, "JSON body required");
    const reader = request.body?.getReader();
    let length = 0;
    const chunks: Uint8Array[] = [];
    if (reader)
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        length += value.length;
        if (length > 65536) {
          await reader.cancel();
          return error(413, "Request exceeds 64 KiB");
        }
        chunks.push(value);
      }
    body = Buffer.concat(chunks).toString("utf8");
  }
  try {
    const response = await fetch(upstream, {
      method: request.method,
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(10_000),
    });
    const reader = response.body?.getReader();
    const chunks: Uint8Array[] = [];
    let length = 0;
    if (reader)
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        length += value.length;
        if (length > 8 * 1024 * 1024) {
          await reader.cancel();
          return error(502, "Backend response exceeds the safe display limit");
        }
        chunks.push(value);
      }
    let payload: unknown;
    try {
      payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    } catch {
      return error(502, "Backend returned an invalid JSON response");
    }
    if (response.status >= 500)
      return error(
        response.status,
        path === "ready" ? "Backend dependencies are not ready" : "Backend request failed",
      );
    const headers: Record<string, string> = { "Cache-Control": "no-store" };
    const retry = response.headers.get("retry-after");
    const requestId = response.headers.get("x-request-id");
    if (retry && /^\d{1,6}$/.test(retry)) headers["Retry-After"] = retry;
    if (requestId && /^[a-f0-9-]{36}$/.test(requestId)) headers["X-Request-ID"] = requestId;
    return Response.json(redact(payload), {
      status: response.status,
      headers,
    });
  } catch {
    return error(
      502,
      "Cannot reach the configured backend. Check API readiness and server configuration.",
    );
  }
}
