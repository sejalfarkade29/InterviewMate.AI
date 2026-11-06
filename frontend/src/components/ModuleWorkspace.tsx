"use client";

import { useState } from "react";
import type { ModuleInfo } from "@/lib/modules";
import { Tabs } from "@/components/ui";
import { CodingModule } from "./modules/CodingModule";
import { DailyModule } from "./modules/DailyModule";
import { GroupDiscussionModule } from "./modules/GroupDiscussionModule";
import { AnalyticsModule, HistoryModule, RewardsModule, RoadmapModule } from "./modules/InsightModules";
import { JobMatchModule } from "./modules/JobMatchModule";
import { PracticeModule } from "./modules/PracticeModule";
import { ResumeModule } from "./modules/ResumeModule";
import { SimulationModule } from "./modules/SimulationModule";
import { VoiceModule } from "./modules/VoiceModule";

/** HR round: written questions (real, most-asked HR questions) and a live voice mode, side by side. */
function HrModule({ module }: { module: ModuleInfo }) {
  const [tab, setTab] = useState<"text" | "voice">("text");
  return (
    <div className="space-y-6">
      <Tabs value={tab} onChange={setTab} items={[{ id: "text", label: "Written questions" }, { id: "voice", label: "Voice interview" }]} />
      {tab === "text" ? <PracticeModule module={module} kind="hr" /> : <VoiceModule module={module} mode="hr" />}
    </div>
  );
}

export function ModuleWorkspace({ module }: { module: ModuleInfo }) {
  switch (module.slug) {
    case "resume": return <ResumeModule module={module} />;
    case "job-match": return <JobMatchModule module={module} />;
    case "roadmap": return <RoadmapModule module={module} />;
    case "daily": return <DailyModule module={module} />;
    case "simulation": return <SimulationModule module={module} />;
    case "aptitude": return <PracticeModule module={module} kind="aptitude" />;
    case "technical": return <PracticeModule module={module} kind="technical" />;
    case "dsa": return <PracticeModule module={module} kind="dsa" />;
    case "coding": return <CodingModule module={module} />;
    case "voice": return <VoiceModule module={module} mode="voice" />;
    case "hr": return <HrModule module={module} />;
    case "project": return <PracticeModule module={module} kind="project" />;
    case "group-discussion": return <GroupDiscussionModule module={module} />;
    case "rewards": return <RewardsModule module={module} />;
    case "analytics": return <AnalyticsModule module={module} />;
    case "history": return <HistoryModule module={module} />;
    default: return null;
  }
}
