"use client";
import { api } from "@/lib/api";
import { isActive } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
export const useGraph = (id: string) =>
  useQuery({
    queryKey: ["graph", id],
    queryFn: ({ signal }) => api.graph(id, signal),
    enabled: !!id,
  });
export const useOverview = (id: string) =>
  useQuery({
    queryKey: ["overview", id],
    queryFn: ({ signal }) => api.overview(id, signal),
    enabled: !!id,
    refetchInterval: 4000,
  });
export const useExperiments = (id: string) =>
  useQuery({
    queryKey: ["experiments", id],
    queryFn: ({ signal }) => api.experiments(id, signal),
    enabled: !!id,
  });
export const useInvariants = (id: string) =>
  useQuery({
    queryKey: ["invariants", id],
    queryFn: ({ signal }) => api.invariants(id, signal),
    enabled: !!id,
  });
export const useSummary = (id: string) =>
  useQuery({
    queryKey: ["summary", id],
    queryFn: ({ signal }) => api.summary(id, signal),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data && !isActive(query.state.data.run.status) ? false : 1500,
  });
export const useRuns = (id: string, offset = 0, status = "") =>
  useQuery({
    queryKey: ["runs", id, offset, status],
    queryFn: ({ signal }) => api.runs(id, offset, status, signal),
    enabled: !!id,
    refetchInterval: 3000,
  });
export const useFindings = (id: string, offset = 0) =>
  useQuery({
    queryKey: ["findings", id, offset],
    queryFn: ({ signal }) => api.findings(id, offset, signal),
    enabled: !!id,
    refetchInterval: 5000,
  });
