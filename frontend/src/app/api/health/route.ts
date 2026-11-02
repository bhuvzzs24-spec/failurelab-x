import { bridge } from "@/lib/bridge";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 15;
export async function GET(request: Request) {
  const result = await bridge(request, ["ready"]);
  return Response.json(
    { status: result.ok ? "ready" : "unavailable", backend_status: result.status },
    { status: result.ok ? 200 : 503, headers: { "Cache-Control": "no-store" } },
  );
}
