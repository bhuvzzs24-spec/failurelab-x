"use client";
import { createContext, useContext } from "react";
import { useQuery } from "@tanstack/react-query";
import { request } from "@/lib/api";
type Access = {
  role: string;
  read_only: boolean;
  can_execute: boolean;
  can_manage: boolean;
  unavailable?: boolean;
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
}: {
  children: React.ReactNode;
  readOnly?: boolean;
}) {
  const query = useQuery({
    queryKey: ["access-session"],
    queryFn: () => request<Access>("api/v1/session"),
    refetchInterval: 15000,
    retry: false,
  });
  const data = query.data;
  const value = {
    role: query.isError ? "unavailable" : (data?.role ?? "unavailable"),
    read_only: readOnly || !!data?.read_only,
    can_execute: !readOnly && !query.isError && !!data?.can_execute,
    can_manage: !readOnly && !query.isError && !!data?.can_manage,
    unavailable: !!query.error,
  };
  return <AccessContext.Provider value={value}>{children}</AccessContext.Provider>;
}
export function AccessNotice() {
  const access = useAccess();
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
