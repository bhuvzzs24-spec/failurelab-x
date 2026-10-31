import { cn } from "@/lib/utils";
export function StatusBadge({ status, small = false }: { status: string; small?: boolean }) {
  const tone = ["COMPLETED", "PASS"].includes(status)
    ? "success"
    : ["FAIL", "FAILED"].includes(status)
      ? "critical"
      : ["RUNNING", "VERIFYING"].includes(status)
        ? "active"
        : ["INCONCLUSIVE", "CANCELLED"].includes(status)
          ? "warning"
          : "neutral";
  return (
    <span className={cn("status-badge", `status-${tone}`, small && "status-small")}>
      <span className="status-dot" />
      {status}
    </span>
  );
}
