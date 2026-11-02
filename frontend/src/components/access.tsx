"use client";
import { createContext, useContext } from "react";
import { useQuery } from "@tanstack/react-query";
import { request } from "@/lib/api";
type Access = {
  data_source?: string;
  role: string;
  read_only: boolean;
  can_execute: boolean;
  can_manage: boolean;
  unavailable?: boolean;
  recorded_demo?: boolean;
  captured_at?: number;
  source_revision?: string;
};
// Standalone reusable components retain local behavior. Root always supplies an
// explicit provider, which disables mutations until the authenticated query loads.
const AccessContext = createContext<Access>({
  role: "local",
  read_only: false,
  can_execute: true,
  can_manage: true,
});
export function useAccess() {
  return useContext(AccessContext);
}
export function AccessProvider({
  children,
  readOnly = false,
  recordedDemo = false,
}: {
  children: React.ReactNode;
  readOnly?: boolean;
  recordedDemo?: boolean;
}) {
  const query = useQuery({
    queryKey: ["access-session"],
    queryFn: () => request<Access>("api/v1/session"),
    refetchInterval: recordedDemo ? false : 15000,
    retry: false,
  });
  const data = query.data;
  const value = {
    role: query.isError ? "unavailable" : (data?.role ?? "unavailable"),
    recorded_demo: recordedDemo || data?.data_source === "recorded_demo",
    captured_at: data?.captured_at,
    source_revision: data?.source_revision,
    read_only: recordedDemo || readOnly || !!data?.read_only,
    can_execute: !recordedDemo && !readOnly && !query.isError && !!data?.can_execute,
    can_manage: !recordedDemo && !readOnly && !query.isError && !!data?.can_manage,
    unavailable: !!query.error,
  };
  return <AccessContext.Provider value={value}>{children}</AccessContext.Provider>;
}
export function AccessNotice() {
  const access = useAccess();
  if (access.recorded_demo)
    return (
      <div className="access-banner demo-banner" role="status">
        <strong>Recorded evidence demo</strong>
        <span>
          {access.captured_at
            ? `Captured ${new Date(access.captured_at * 1000).toLocaleString()}. `
            : ""}
          Historical synthetic sandbox results only. No live backend, current service health, fault
          injection, replay or patch execution is available.
        </span>
      </div>
    );
  if (access.unavailable)
    return (
      <div className="access-banner" role="alert">
        Access permissions could not be verified. Control actions are disabled.
      </div>
    );
  if (access.read_only)
    return (
      <div className="access-banner" role="status">
        Read-only demonstration · experiments, registration and patch execution are disabled.
      </div>
    );
  return null;
}
