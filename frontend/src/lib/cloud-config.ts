/** Public hosting is intentionally read-only. Values here are server configuration. */
export function cloudConfiguration(env: Record<string, string | undefined>) {
  const origin = (name: string) => {
    const value = env[name];
    if (!value) throw new Error(`${name} is required for cloud deployment`);
    const url = new URL(value);
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.pathname !== "/" ||
      url.search ||
      url.hash ||
      ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname) ||
      url.hostname.endsWith(".invalid")
    )
      throw new Error(`${name} must be an explicit public HTTPS origin`);
    return url.origin;
  };
  if (env.ACCESS_MODE !== "read_only")
    throw new Error("Public hosting requires ACCESS_MODE=read_only");
  if (!env.API_TOKEN || env.API_TOKEN.length < 32)
    throw new Error("A strong server-only viewer credential is required");
  const frontend = origin("PUBLIC_FRONTEND_ORIGIN");
  const backend = origin("BACKEND_URL");
  if (origin("HOSTED_BACKEND_ORIGIN") !== backend)
    throw new Error("Backend origin allowlist must exactly match BACKEND_URL");
  if (
    Object.keys(env).some(
      (key) => /^NEXT_PUBLIC_.*(?:TOKEN|SECRET|PASSWORD|KEY)/i.test(key) && !!env[key],
    )
  )
    throw new Error("Credentials must not use NEXT_PUBLIC_ variables");
  return { frontend, backend, access: "read_only" as const };
}
