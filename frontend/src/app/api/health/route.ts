import { bridge } from "@/lib/bridge";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 15;
export async function GET(request: Request) {
  const result = await bridge(request, ["ready"]);
  const recorded = result.headers.get("X-FailureLab-Data-Source") === "recorded_demo";
  return Response.json(
    {
      status: result.ok ? (recorded ? "recorded_demo_ready" : "ready") : "unavailable",
      ...(recorded ? { live_backend: false } : { backend_status: result.status }),
    },
    { status: result.ok ? 200 : 503, headers: { "Cache-Control": "no-store" } },
  );
}
