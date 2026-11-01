import { bridge } from "@/lib/bridge";
export const dynamic = "force-dynamic";
export async function GET(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return bridge(request, (await context.params).path);
}
export const POST = GET;

export const maxDuration = 15;
