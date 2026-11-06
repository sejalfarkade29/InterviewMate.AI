"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, post } from "@/lib/api";
import type { ModuleInfo } from "@/lib/modules";
import { Header, Notice } from "@/components/ui";
import { QuestionRunner, type Question } from "./QuestionRunner";

type Topics = { aptitude: string[]; technical: string[]; dsa: string[]; daily: string[] };
export type PracticeKind = "aptitude" | "technical" | "dsa" | "hr" | "project";

const COPY: Record<PracticeKind, { placeholder: string; note?: string }> = {
  aptitude: { placeholder: "" },
  technical: { placeholder: "Explain the concept in your own words, then give a short example or a trade-off." },
  dsa: { placeholder: "Describe your approach step by step, then state the time and space complexity. Mention edge cases." },
  hr: { placeholder: "Use the STAR method: the Situation, your Task, the Action you took, and the Result. Be specific.", note: "Questions here are drawn mostly from the real questions most often asked in HR rounds." },
  project: { placeholder: "Answer as you would in the interview: what you built, the decision you made, why, and the result.", note: "Questions are generated from the projects in your analyzed resume." },
};

export function PracticeModule({ module, kind }: { module: ModuleInfo; kind: PracticeKind }) {
  const [topics, setTopics] = useState<Topics | null>(null);
  const [topic, setTopic] = useState("");
  useEffect(() => { if (kind === "aptitude" || kind === "technical" || kind === "dsa") api<Topics>("/practice/topics").then(setTopics).catch(() => undefined); }, [kind]);
  const list = topics && (kind === "aptitude" || kind === "technical" || kind === "dsa") ? topics[kind] : [];
  const load = useCallback(() => post<Question>("/practice/question", { module: kind, topic }), [kind, topic]);
  const copy = COPY[kind];

  return (
    <div className="space-y-6">
      <Header module={module} />
      {copy.note && <Notice>{copy.note} {kind === "project" && <Link href="/resume" className="font-medium underline">Analyze a resume</Link>}</Notice>}
      <QuestionRunner load={load} reloadKey={`${kind}:${topic}`} placeholder={copy.placeholder}
        extraTop={list.length > 0 ? (
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm font-medium" htmlFor="topic">Topic</label>
            <select id="topic" className="input max-w-xs" value={topic} onChange={(e) => setTopic(e.target.value)}>
              <option value="">Any topic (mixed)</option>{list.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <span className="text-xs text-ink-500">Difficulty adapts to your recent scores.</span>
          </div>
        ) : null} />
    </div>
  );
}
