import { Loading } from "@/components/ui/states";
import { Workspace } from "@/components/workspace";
import type { Section } from "@/types/domain";
import { notFound } from "next/navigation";
import { Suspense } from "react";
const sections: Section[] = [
  "home",
  "graph",
  "experiments",
  "findings",
  "evidence",
  "replay",
  "ai",
  "minimization",
  "verification",
  "settings",
];
export default async function Page({ params }: { params: Promise<{ workspace?: string[] }> }) {
  const path = (await params).workspace ?? [];
  const section = (path[0] ?? "home") as Section;
  if (path.length > 1 || !sections.includes(section)) notFound();
  return (
    <Suspense fallback={<Loading />}>
      <Workspace section={section} />
    </Suspense>
  );
}
