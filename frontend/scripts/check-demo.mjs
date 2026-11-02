/** Prebuild guard for the approved preview profile. No authentication or network. */
import process from "node:process";
import console from "node:console";
import { readFileSync, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
const env = process.env;
if (
  env.DATA_MODE !== "recorded_demo" ||
  env.DEPLOYMENT_ENV !== "frontend_demo" ||
  env.ACCESS_MODE !== "read_only"
)
  throw new Error("Use the complete frontend-only demo environment");
if (env.VERCEL === "1" && env.VERCEL_ENV !== "preview")
  throw new Error("Only a Preview deployment is permitted");
for (const [name, value] of Object.entries(env))
  if (
    value &&
    (/^(?:BACKEND_URL|HOSTED_BACKEND_ORIGIN|API_TOKEN|CONTROL_TOKEN|VERCEL_TOKEN|GH_TOKEN|GITHUB_TOKEN|AUTH_.*_TOKEN|DATABASE_URL|REDIS_URL|REPAIR_AGENT_.*|OLLAMA_.*)$/.test(
      name,
    ) ||
      /^NEXT_PUBLIC_.*(?:TOKEN|SECRET|PASSWORD|KEY)/i.test(name))
  )
    throw new Error("Remove execution connections and credentials from the demo environment");
const file = resolve("demo-data/recorded.json");
if (statSync(file).size > 16 * 1024 * 1024) throw new Error("Dataset exceeds 16 MiB");
const bytes = readFileSync(file),
  hash = createHash("sha256").update(bytes).digest("hex");
if (readFileSync(file + ".sha256", "utf8").trim() !== hash)
  throw new Error("Recorded evidence failed integrity verification");
const data = JSON.parse(bytes);
if (data.format !== "failurelab-frontend-demo-v1" || !data.resources || !data.captured_at)
  throw new Error("A reviewed recorded dataset is required");
if (/https?:\/\/(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?/i.test(bytes.toString()))
  throw new Error("Internal network addresses remain in recorded evidence");
console.log(
  "Frontend-only demo prebuild passed. No backend connection, credentials or deployment attempted. Dataset SHA256: " +
    hash,
);
