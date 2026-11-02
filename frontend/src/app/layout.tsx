import { Providers } from "@/components/providers";
import { Shell } from "@/components/shell";
import "@xyflow/react/dist/style.css";
import type { Metadata } from "next";
import "./globals.css";
import "./premium.css";
export const metadata: Metadata = {
  title: "FailureLab X — Engineering certainty",
  description: "Controlled failure experiments. Executable invariants. Reproducible evidence.",
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers readOnly={process.env.ACCESS_MODE === "read_only"}>
          <Shell>{children}</Shell>
        </Providers>
      </body>
    </html>
  );
}
