import { cn } from "@/lib/utils";
export function StatusBadge({ status, small = false }: { status: string; small?: boolean }) {
  const tone = [
    "COMPLETED",
    "PASS",
    "NO_VIOLATION",
    "SUPPORTED",
    "PATCH_PASSES_TESTED_SCENARIOS",
  ].includes(status)
    ? "success"
    : ["FAIL", "FAILED", "APPLICATION_VIOLATION", "REFUTED", "PATCH_FAILS_VERIFICATION"].includes(
          status,
        )
      ? "critical"
      : ["RUNNING", "VERIFYING"].includes(status)
        ? "active"
        : ["INCONCLUSIVE", "CANCELLED", "INFRASTRUCTURE_ERROR", "INJECTION_NOT_OBSERVED"].includes(
              status,
            )
          ? "warning"
          : "neutral";
  return (
    <span className={cn("status-badge", `status-${tone}`, small && "status-small")}>
      <span className="status-dot" />
      {status}
    </span>
  );
}
