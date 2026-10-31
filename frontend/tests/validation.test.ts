import { completeConfig, configSchema, definitionSchema, faultKinds } from "@/lib/validation";
import { describe, expect, it } from "vitest";
import spec from "../../docs/openapi.json";
const valid = () => ({ ...completeConfig(), invariant_ids: ["registered-rule"] });
describe("backend-aligned experiment validation", () => {
  it("accepts each supported fault and rejects arbitrary targets", () => {
    for (const kind of faultKinds)
      expect(
        configSchema.safeParse({ ...valid(), fault: { ...valid().fault, kind } }).success,
      ).toBe(true);
    expect(
      configSchema.safeParse({
        ...valid(),
        fault: { ...valid().fault, target: "https://example.com" },
      }).success,
    ).toBe(false);
  });
  it("matches the exported backend fault enum and limits", () => {
    expect([...faultKinds]).toEqual(spec.components.schemas.Fault.properties.kind.enum);
    expect(spec.components.schemas.Fault.properties.duration_seconds.maximum).toBe(30);
    expect(spec.components.schemas.ExperimentConfig.properties.max_duration_seconds.maximum).toBe(
      90,
    );
  });
  it.each([0, 31, NaN])("rejects an invalid TTL %s", (duration_seconds) =>
    expect(
      configSchema.safeParse({ ...valid(), fault: { ...valid().fault, duration_seconds } }).success,
    ).toBe(false),
  );
  it("enforces the consistency/cleanup deadline budget", () => {
    const result = configSchema.safeParse({ ...valid(), max_duration_seconds: 10 });
    expect(result.success).toBe(false);
    if (!result.success) expect(result.error.issues[0].path).toContain("max_duration_seconds");
  });
  it("requires a registered invariant and valid workflow quantities", () => {
    expect(configSchema.safeParse({ ...valid(), invariant_ids: [] }).success).toBe(false);
    expect(configSchema.safeParse({ ...valid(), quantity: 1.5 }).success).toBe(false);
    expect(definitionSchema.safeParse({ name: "", config: valid() }).success).toBe(false);
  });
});
