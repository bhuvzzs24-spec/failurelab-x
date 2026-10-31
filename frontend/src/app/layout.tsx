import { Providers } from "@/components/providers";
import { Shell } from "@/components/shell";
import "@xyflow/react/dist/style.css";
import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "FailureLab X — Engineering certainty",
  description: "Controlled failure experiments. Executable invariants. Reproducible evidence.",
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <Shell>{children}</Shell>
        </Providers>
      </body>
    </html>
  );
}
