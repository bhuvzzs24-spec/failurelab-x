import type { ExperimentConfig } from "@/types/domain";
import { z } from "zod";
export const faultKinds = [
  "latency",
  "timeout",
  "http_503",
  "reset",
  "unavailable",
  "worker_interrupt",
] as const;
export const configSchema = z
  .object({
    fault: z.object({
      target: z.literal("payment"),
      kind: z.enum(faultKinds),
      delay_seconds: z.number().min(0).max(10),
      duration_seconds: z.number().min(1).max(30),
      phase: z.enum(["before", "after"]),
    }),
    invariant_ids: z
      .array(z.string().min(1))
      .min(1, "Select at least one registered invariant")
      .max(20),
    seed: z.number().int().min(0).max(2147483647),
    max_duration_seconds: z.number().int().min(10).max(90),
    consistency_seconds: z.number().min(0).max(15),
    retry_seconds: z.number().min(0.05).max(2),
    amount: z.number().int().min(1).max(10000),
    quantity: z.number().int().min(1).max(10),
  })
  .superRefine((value, context) => {
    if (value.fault.duration_seconds + value.consistency_seconds + 5 > value.max_duration_seconds)
      context.addIssue({
        code: "custom",
        path: ["max_duration_seconds"],
        message: "Deadline must cover fault TTL + consistency window + 5 seconds cleanup",
      });
  });
export const definitionSchema = z.object({
  name: z.string().trim().min(1).max(120),
  config: configSchema,
});
export type DefinitionValues = z.infer<typeof definitionSchema>;
export function completeConfig(config?: ExperimentConfig): DefinitionValues["config"] {
  return {
    fault: {
      target: "payment",
      kind: config?.fault.kind ?? "latency",
      phase: config?.fault.phase ?? "after",
      delay_seconds: config?.fault.delay_seconds ?? 1.5,
      duration_seconds: config?.fault.duration_seconds ?? 10,
    },
    invariant_ids: config?.invariant_ids ?? [],
    seed: config?.seed ?? 42,
    max_duration_seconds: config?.max_duration_seconds ?? 45,
    consistency_seconds: config?.consistency_seconds ?? 2,
    retry_seconds: config?.retry_seconds ?? 0.2,
    amount: config?.amount ?? 100,
    quantity: config?.quantity ?? 1,
  };
}
