import { notFound } from "next/navigation";
import { MODULES } from "@/lib/modules";
import { ModuleWorkspace } from "@/components/ModuleWorkspace";

export function generateStaticParams() {
  return MODULES.map((m) => ({ module: m.slug }));
}

export default function ModulePage({ params }: { params: { module: string } }) {
  const m = MODULES.find((x) => x.slug === params.module);
  if (!m) notFound();
  return <ModuleWorkspace module={m} />;
}
