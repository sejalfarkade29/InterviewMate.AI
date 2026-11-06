"use client";
import type { ReactNode } from "react";
import type { ModuleInfo } from "@/lib/modules";

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-lg border border-slate-200 bg-white p-5 ${className}`}>{children}</section>;
}
export function Header({ module, eyebrow, right }: { module: ModuleInfo; eyebrow?: string; right?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-sm text-ink-500">{eyebrow || module.group}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">{module.title}</h1>
        <p className="mt-2 max-w-2xl text-ink-700">{module.summary}</p>
      </div>
      {right}
    </div>
  );
}
export function Notice({ children, tone = "blue" }: { children: ReactNode; tone?: "blue" | "green" | "amber" | "red" }) {
  const c = { green: "border-green-200 bg-green-50 text-green-800", amber: "border-amber-200 bg-amber-50 text-amber-900", red: "border-red-200 bg-red-50 text-red-700", blue: "border-brand-100 bg-brand-50 text-brand-700" }[tone];
  return <div role={tone === "red" ? "alert" : undefined} className={`rounded-md border px-3 py-2 text-sm ${c}`}>{children}</div>;
}
export function Spinner({ label = "Working…" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-ink-500" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />{label}
    </span>
  );
}
export function List({ items, tone }: { items: ReactNode[]; tone?: "good" | "bad" }) {
  if (!items.length) return null;
  const dot = tone === "good" ? "text-green-600" : tone === "bad" ? "text-amber-600" : "text-slate-400";
  return (
    <ul className="space-y-1.5 text-sm text-ink-700">
      {items.map((it, i) => <li key={i} className="flex gap-2"><span className={`mt-0.5 ${dot}`} aria-hidden>{tone === "good" ? "✓" : tone === "bad" ? "→" : "•"}</span><span>{it}</span></li>)}
    </ul>
  );
}
export function Chip({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "green" | "amber" | "red" | "blue" }) {
  const c = { slate: "bg-slate-100 text-ink-700", green: "bg-green-100 text-green-800", amber: "bg-amber-100 text-amber-900", red: "bg-red-100 text-red-800", blue: "bg-brand-100 text-brand-700" }[tone];
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${c}`}>{children}</span>;
}
export const scoreTone = (n: number) => (n >= 75 ? "green" : n >= 50 ? "amber" : "red") as "green" | "amber" | "red";
const BAR = { green: "bg-green-500", amber: "bg-amber-500", red: "bg-red-500" };

export function Bar({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm"><span className="text-ink-700">{label}</span><span className="tabular-nums text-ink-500">{Math.round(value)}%</span></div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={Math.round(value)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
        <div className={`h-full rounded-full ${BAR[scoreTone(value)]}`} style={{ width: `${Math.max(2, Math.min(100, value))}%` }} />
      </div>
      {hint && <p className="mt-1 text-xs text-ink-500">{hint}</p>}
    </div>
  );
}
const RING = { green: "#16a34a", amber: "#d97706", red: "#dc2626" };
/** Circular gauge. Set `invert` when a LOW number is good (for example the AI-written share of a resume). */
export function Ring({ value, label, size = 110, invert = false }: { value: number; label?: string; size?: number; invert?: boolean }) {
  const v = Math.max(0, Math.min(100, Math.round(value)));
  const r = size / 2 - 9, c = 2 * Math.PI * r;
  const color = RING[scoreTone(invert ? 100 - v : v)];
  return (
    <div className="flex flex-col items-center" role="img" aria-label={`${label ?? "Score"}: ${v} percent`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth="9" />
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - v / 100)} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-2xl font-semibold tabular-nums">{v}<span className="text-sm text-ink-500">%</span></div>
      </div>
      {label && <p className="mt-1 text-center text-xs font-medium uppercase tracking-wide text-ink-500">{label}</p>}
    </div>
  );
}
export function Score({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{Math.round(value)}<span className="text-base text-ink-500">/100</span></p>
    </div>
  );
}
export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { id: T; label: string }[] }) {
  return (
    <div className="inline-flex rounded-md border border-slate-300 p-0.5" role="tablist">
      {items.map((it) => (
        <button key={it.id} role="tab" aria-selected={value === it.id} type="button" onClick={() => onChange(it.id)}
          className={`rounded px-3 py-1.5 text-sm font-medium ${value === it.id ? "bg-brand-600 text-white" : "text-ink-700 hover:bg-slate-100"}`}>{it.label}</button>
      ))}
    </div>
  );
}

/** What a scored answer looks like. Used by every practice round. */
export type Evaluation = {
  score: number; verdict: string; summary: string; strengths: string[]; improvements: string[]; ideal_answer: string;
  rubric: Record<string, number>; extras: Record<string, any>; source: string; correct?: boolean; correct_index?: number;
};
export function EvaluationCard({ result }: { result: Evaluation }) {
  const star = result.extras?.star as Record<string, number> | undefined;
  const filler = result.extras?.filler_or_vague_phrases as string[] | undefined;
  return (
    <div className="space-y-5" aria-live="polite">
      <div className="flex flex-wrap items-center gap-5">
        <Ring value={result.score} label="Score" size={96} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2"><h3 className="text-lg font-semibold">{result.verdict || "Result"}</h3>{result.source === "offline" && <Chip tone="amber">Offline estimate</Chip>}</div>
          <p className="mt-1 text-sm text-ink-700">{result.summary}</p>
        </div>
      </div>
      {Object.keys(result.rubric || {}).length > 0 && <div className="grid gap-3 sm:grid-cols-3">{Object.entries(result.rubric).map(([k, v]) => <Bar key={k} label={k[0].toUpperCase() + k.slice(1)} value={v} />)}</div>}
      {star && <div><p className="mb-2 text-sm font-medium">STAR structure</p><div className="grid gap-3 sm:grid-cols-4">{Object.entries(star).map(([k, v]) => <Bar key={k} label={k[0].toUpperCase() + k.slice(1)} value={Number(v)} />)}</div></div>}
      {result.extras?.time_complexity && <div className="flex flex-wrap gap-2 text-sm"><Chip tone="blue">Time: {String(result.extras.time_complexity)}</Chip><Chip tone="blue">Space: {String(result.extras.space_complexity)}</Chip></div>}
      <div className="grid gap-5 sm:grid-cols-2">
        {result.strengths?.length > 0 && <div><p className="mb-2 text-sm font-medium">What went well</p><List tone="good" items={result.strengths} /></div>}
        {result.improvements?.length > 0 && <div><p className="mb-2 text-sm font-medium">How to improve</p><List tone="bad" items={result.improvements} /></div>}
      </div>
      {filler && filler.length > 0 && <p className="text-sm text-ink-500">Vague or filler phrases: {filler.join(", ")}</p>}
      {result.ideal_answer && <div className="rounded-md bg-slate-50 p-4"><p className="mb-1 text-sm font-medium">{result.correct !== undefined ? "Explanation" : "A strong answer"}</p><p className="whitespace-pre-wrap text-sm text-ink-700">{result.ideal_answer}</p></div>}
    </div>
  );
}
export function fmtTime(sec: number) { return `${Math.floor(sec / 60)}:${String(Math.floor(sec % 60)).padStart(2, "0")}`; }
