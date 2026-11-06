"use client";
import { useCallback, useEffect, useState } from "react";
import { api, post } from "@/lib/api";
import type { ModuleInfo } from "@/lib/modules";
import { Chip, Header, Notice, Panel } from "@/components/ui";
import { QuestionRunner, type Question } from "./QuestionRunner";

type Status = { completed_today: number; streak: number; best_streak: number; kinds: string[] };

export function DailyModule({ module }: { module: ModuleInfo }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [started, setStarted] = useState(false);
  const [error, setError] = useState("");
  const refresh = useCallback(() => api<Status>("/daily/status").then(setStatus).catch((e) => setError(e.message)), []);
  useEffect(() => { void refresh(); }, [refresh]);
  // Every call returns a brand-new question, and the server picks a different TYPE from your last few.
  const load = useCallback(() => post<Question>("/daily/question", {}), []);

  return (
    <div className="space-y-6">
      <Header module={module} />
      {error && <Notice tone="red">{error}</Notice>}
      <Panel>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-6">
            <div><p className="text-xs uppercase tracking-wide text-ink-500">Streak</p><p className="text-2xl font-semibold">🔥 {status?.streak ?? 0} <span className="text-sm font-normal text-ink-500">day{status?.streak === 1 ? "" : "s"}</span></p></div>
            <div><p className="text-xs uppercase tracking-wide text-ink-500">Best streak</p><p className="text-2xl font-semibold">{status?.best_streak ?? 0}</p></div>
            <div><p className="text-xs uppercase tracking-wide text-ink-500">Done today</p><p className="text-2xl font-semibold">{status?.completed_today ?? 0}</p></div>
          </div>
          {!started && <button className="btn-primary" onClick={() => setStarted(true)}>{status?.completed_today ? "Do another challenge" : "Start today's challenge"}</button>}
        </div>
        {status && <div className="mt-4 flex flex-wrap items-center gap-1.5 text-xs text-ink-500">Challenge types you will see: {status.kinds.map((k) => <Chip key={k}>{k}</Chip>)}</div>}
      </Panel>
      {started && <QuestionRunner load={load} nextLabel="Next challenge" onAnswered={() => void refresh()} placeholder="Type your answer here. For code or SQL questions you can write the code directly." />}
    </div>
  );
}
