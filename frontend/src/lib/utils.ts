import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));
export const shortId = (id: string) => id.slice(0, 8);
export const dateTime = (epoch: number) => new Date(epoch * 1000).toLocaleString();
export const relativeTime = (epoch: number) => {
  const minutes = Math.max(0, Math.round((Date.now() / 1000 - epoch) / 60));
  return minutes < 1
    ? "just now"
    : minutes < 60
      ? `${minutes}m ago`
      : minutes < 1440
        ? `${Math.floor(minutes / 60)}h ago`
        : `${Math.floor(minutes / 1440)}d ago`;
};
export const isActive = (status: string) =>
  ["CREATED", "QUEUED", "RUNNING", "VERIFYING"].includes(status);
export const asObject = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
export const asText = (value: unknown, fallback = "Not recorded") =>
  typeof value === "string"
    ? value
    : typeof value === "number" && Number.isFinite(value)
      ? String(value)
      : fallback;
