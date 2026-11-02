import type { NextConfig } from "next";
const config: NextConfig = {
  output: "standalone",
  outputFileTracingIncludes: {
    "/api/backend/[...path]": ["./demo-data/recorded.json", "./demo-data/recorded.json.sha256"],
    "/api/health": ["./demo-data/recorded.json", "./demo-data/recorded.json.sha256"],
  },
  agentRules: false,
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          ...(process.env.DATA_MODE === "recorded_demo"
            ? [{ key: "X-Robots-Tag", value: "noindex, nofollow, noarchive" }]
            : []),
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Content-Security-Policy",
            value: "frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
          },
        ],
      },
    ];
  },
};
export default config;
