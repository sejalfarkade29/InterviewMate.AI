"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, del, put, post } from "@/lib/api";
import type { Badge } from "@/lib/rewards";
import type { ModuleInfo } from "@/lib/modules";
import { MODULES } from "@/lib/modules";
import { Bar, Chip, Header, List, Notice, Panel, Ring, Score, Spinner, scoreTone } from "@/components/ui";

const label = (slug: string) => MODULES.find((m) => m.slug === slug)?.title ?? ({ "hr-voice": "HR voice interview" } as Record<string, string>)[slug] ?? slug;
const route = (slug: string) => (slug === "hr-voice" ? "/hr" : `/${slug}`);

// ------------------------------------------------------------------ rewards
export type Rewards = {
  xp: number; level: number; title: string; progress: number; xp_into_level: number; xp_for_next: number; streak: number; best_streak: number;
  badges: Badge[]; timeline: { level: number; title: string; reached_at: string | null; xp: number }[]; weekly_xp: { date: string; xp: number }[];
  recent: { id: number; title: string; module: string; xp: number; score: number; created_at: string }[]; total_activities: number;
};
export function RewardsModule({ module }: { module: ModuleInfo }) {
  const [d, setD] = useState<Rewards | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<Rewards>("/rewards").then(setD).catch((e) => setError(e.message)); }, []);
  if (error) return <div className="space-y-6"><Header module={module} /><Notice tone="red">{error}</Notice></div>;
  if (!d) return <div className="space-y-6"><Header module={module} /><Spinner label="Loading your rewards…" /></div>;
  const max = Math.max(1, ...d.weekly_xp.map((w) => w.xp));
  return (
    <div className="space-y-6">
      <Header module={module} />
      <Panel>
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex h-24 w-24 shrink-0 flex-col items-center justify-center rounded-full bg-brand-600 text-white"><span className="text-xs uppercase tracking-wide opacity-80">Level</span><span className="text-3xl font-semibold leading-none">{d.level}</span></div>
          <div className="min-w-[220px] flex-1">
            <p className="text-lg font-semibold">{d.title}</p>
            <p className="text-sm text-ink-500">{d.xp} XP total · {d.xp_into_level} / {d.xp_for_next} XP to level {d.level + 1}</p>
            <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={d.progress} aria-valuemin={0} aria-valuemax={100} aria-label="Progress to next level"><div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.max(3, d.progress)}%` }} /></div>
          </div>
          <div className="flex gap-6"><div><p className="text-xs uppercase tracking-wide text-ink-500">Streak</p><p className="text-2xl font-semibold">🔥 {d.streak}</p></div><div><p className="text-xs uppercase tracking-wide text-ink-500">Best</p><p className="text-2xl font-semibold">{d.best_streak}</p></div><div><p className="text-xs uppercase tracking-wide text-ink-500">Activities</p><p className="text-2xl font-semibold">{d.total_activities}</p></div></div>
        </div>
      </Panel>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel><h2 className="font-medium">XP this week</h2>
          <div className="mt-4 flex h-36 items-end gap-2">{d.weekly_xp.map((w) => (
            <div key={w.date} className="flex flex-1 flex-col items-center gap-1"><span className="text-xs tabular-nums text-ink-500">{w.xp || ""}</span><div className="w-full rounded-t bg-brand-600/80" style={{ height: `${Math.max(w.xp ? 6 : 2, (w.xp / max) * 100)}%`, opacity: w.xp ? 1 : 0.2 }} title={`${w.date}: ${w.xp} XP`} /><span className="text-xs text-ink-500">{new Date(w.date + "T00:00").toLocaleDateString(undefined, { weekday: "short" })}</span></div>
          ))}</div></Panel>
        <Panel><h2 className="font-medium">Your level-ups</h2>
          <ol className="mt-3 space-y-2">{[...d.timeline].reverse().map((t) => <li key={t.level} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm"><span><strong>Level {t.level}</strong> · {t.title}</span><span className="text-xs text-ink-500">{t.reached_at ? new Date(t.reached_at).toLocaleDateString() : "Start"}</span></li>)}</ol></Panel>
      </div>
      <Panel><h2 className="font-medium">Badges · {d.badges.filter((b) => b.earned).length} of {d.badges.length}</h2>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{d.badges.map((b) => (
          <li key={b.id} className={`rounded-lg border p-3 ${b.earned ? "border-amber-300 bg-amber-50" : "border-slate-200"}`}>
            <div className="flex items-center gap-2"><span aria-hidden className={b.earned ? "" : "grayscale"}>🏅</span><p className="text-sm font-medium">{b.name}</p></div>
            <p className="mt-1 text-xs text-ink-500">{b.description}</p>
            {!b.earned && <div className="mt-2"><div className="h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full bg-brand-600" style={{ width: `${(b.progress / b.target) * 100}%` }} /></div><p className="mt-1 text-xs text-ink-500">{b.progress} / {b.target}</p></div>}
          </li>))}</ul></Panel>
      {d.recent.length > 0 && <Panel><h2 className="font-medium">Recent XP</h2><ul className="mt-3 divide-y divide-slate-200 text-sm">{d.recent.map((r) => <li key={r.id} className="flex justify-between gap-3 py-2"><span>{r.title}</span><span className="shrink-0 font-medium text-brand-700">+{r.xp} XP</span></li>)}</ul></Panel>}
    </div>
  );
}

// ------------------------------------------------------------------ history
type HRow = { id: number; module: string; kind: string; topic: string; title: string; score: number; xp: number; created_at: string; question: string; summary: string };
type HFull = HRow & { answer: string; feedback: Record<string, any>; meta: Record<string, any> };
export function HistoryModule({ module }: { module: ModuleInfo }) {
  const [items, setItems] = useState<HRow[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [mod, setMod] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [open, setOpen] = useState<HFull | null>(null);
  const PAGE = 20;
  const load = useCallback(async (offset: number, replace: boolean) => {
    setBusy(true); setError("");
    try {
      const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
      if (q.trim()) params.set("q", q.trim()); if (mod) params.set("module", mod);
      const r = await api<{ total: number; items: HRow[] }>(`/history?${params}`);
      setTotal(r.total); setItems((cur) => (replace ? r.items : [...cur, ...r.items]));
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load history"); } finally { setBusy(false); }
  }, [q, mod]);
  useEffect(() => { const t = setTimeout(() => void load(0, true), 250); return () => clearTimeout(t); }, [load]);
  const view = async (id: number) => { if (open?.id === id) return setOpen(null); try { setOpen(await api<HFull>(`/history/${id}`)); } catch (e) { setError(e instanceof Error ? e.message : "Could not open"); } };
  const remove = async (id: number) => { await del(`/history/${id}`).catch(() => undefined); setItems((c) => c.filter((x) => x.id !== id)); setTotal((t) => t - 1); if (open?.id === id) setOpen(null); };
  const clear = async () => { if (!confirm("Delete your entire history? XP and level are kept, but the saved questions and answers are removed.")) return; await del("/history"); setItems([]); setTotal(0); setOpen(null); };
  const mods = ["", "aptitude", "technical", "dsa", "coding", "hr", "project", "daily", "voice", "hr-voice", "group-discussion", "simulation", "resume", "job-match"];
  return (
    <div className="space-y-6">
      <Header module={module} />
      <Panel>
        <div className="flex flex-wrap items-center gap-3">
          <input className="input max-w-sm" placeholder="Search questions and answers" aria-label="Search history" value={q} onChange={(e) => setQ(e.target.value)} />
          <select className="input max-w-[220px]" aria-label="Filter by module" value={mod} onChange={(e) => setMod(e.target.value)}>{mods.map((m) => <option key={m} value={m}>{m ? label(m) : "All activities"}</option>)}</select>
          <span className="text-sm text-ink-500">{total} saved</span>
          {total > 0 && <button className="btn-secondary ml-auto" onClick={clear}>Clear history</button>}
        </div>
      </Panel>
      {error && <Notice tone="red">{error}</Notice>}
      <Panel className="!p-0">
        {items.length === 0 && !busy ? <p className="p-6 text-sm text-ink-500">Nothing saved yet. Every question you answer, code you submit and interview you finish is saved here automatically.</p> : (
          <ul className="divide-y divide-slate-200">
            {items.map((h) => (
              <li key={h.id} className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <button className="min-w-0 flex-1 text-left" onClick={() => view(h.id)} aria-expanded={open?.id === h.id}>
                    <p className="font-medium">{h.title}</p>
                    <p className="mt-0.5 line-clamp-2 text-sm text-ink-700">{h.question}</p>
                    <p className="mt-1 text-xs text-ink-500">{new Date(h.created_at).toLocaleString()} · {label(h.module)}{h.topic ? ` · ${h.topic}` : ""}</p>
                  </button>
                  <div className="flex items-center gap-3"><Chip tone={scoreTone(h.score)}>{h.score}%</Chip><span className="text-xs text-ink-500">+{h.xp} XP</span><button className="text-sm text-red-700 hover:underline" onClick={() => remove(h.id)}>Delete</button></div>
                </div>
                {open?.id === h.id && (
                  <div className="mt-4 space-y-4 rounded-md bg-slate-50 p-4 text-sm">
                    <div><p className="font-medium">Question</p><p className="mt-1 whitespace-pre-wrap text-ink-700">{open.question}</p></div>
                    {open.answer && <div><p className="font-medium">Your answer</p><pre className="mt-1 whitespace-pre-wrap font-sans text-ink-700">{open.answer}</pre></div>}
                    {open.feedback?.summary && <div><p className="font-medium">Feedback</p><p className="mt-1 text-ink-700">{open.feedback.summary}</p></div>}
                    <div className="grid gap-4 sm:grid-cols-2">{open.feedback?.strengths?.length > 0 && <div><p className="mb-1 font-medium">What went well</p><List tone="good" items={open.feedback.strengths} /></div>}{(open.feedback?.improvements?.length > 0) && <div><p className="mb-1 font-medium">To improve</p><List tone="bad" items={open.feedback.improvements} /></div>}</div>
                    {open.feedback?.ideal_answer && <div><p className="font-medium">A strong answer</p><p className="mt-1 whitespace-pre-wrap text-ink-700">{open.feedback.ideal_answer}</p></div>}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {busy && <div className="p-4"><Spinner label="Loading…" /></div>}
        {!busy && items.length < total && <div className="border-t border-slate-200 p-4 text-center"><button className="btn-secondary" onClick={() => void load(items.length, false)}>Load more</button></div>}
      </Panel>
    </div>
  );
}

// ------------------------------------------------------------------ analytics
type Analytics = { total: number; average: number; by_module: { module: string; count: number; avg: number; best: number }[]; trend: { date: string; avg: number; count: number }[]; weakest: { module: string; topic: string; count: number; avg: number }[]; strongest: { module: string; topic: string; count: number; avg: number }[] };
export function AnalyticsModule({ module }: { module: ModuleInfo }) {
  const [a, setA] = useState<Analytics | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<Analytics>("/analytics").then(setA).catch((e) => setError(e.message)); }, []);
  if (error) return <div className="space-y-6"><Header module={module} /><Notice tone="red">{error}</Notice></div>;
  if (!a) return <div className="space-y-6"><Header module={module} /><Spinner /></div>;
  if (!a.total) return <div className="space-y-6"><Header module={module} /><Panel><p className="text-sm text-ink-500">Complete a practice round to build your performance view.</p></Panel></div>;
  return (
    <div className="space-y-6">
      <Header module={module} />
      <div className="grid gap-4 sm:grid-cols-3"><Score value={a.average} label="Average score" /><Score value={Math.max(...a.by_module.map((m) => m.best))} label="Best score" /><Score value={a.total} label="Activities" /></div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel><h2 className="font-medium">By round</h2><div className="mt-4 space-y-4">{a.by_module.map((m) => <Bar key={m.module} label={`${label(m.module)} (${m.count})`} value={m.avg} />)}</div></Panel>
        <Panel><h2 className="font-medium">Trend (daily average)</h2>
          <div className="mt-4 flex h-40 items-end gap-1.5">{a.trend.map((t) => <div key={t.date} className="flex flex-1 flex-col items-center justify-end gap-1" title={`${t.date}: ${t.avg}% over ${t.count}`}><div className="w-full rounded-t bg-brand-600/80" style={{ height: `${Math.max(4, t.avg)}%` }} /><span className="text-[10px] text-ink-500">{t.date.slice(5)}</span></div>)}</div></Panel>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel><h2 className="font-medium">Weakest topics</h2>{a.weakest.length ? <ul className="mt-3 space-y-2 text-sm">{a.weakest.map((t, i) => <li key={i} className="flex justify-between"><span>{t.topic} <span className="text-ink-500">· {label(t.module)}</span></span><Chip tone={scoreTone(t.avg)}>{t.avg}%</Chip></li>)}</ul> : <p className="mt-3 text-sm text-ink-500">Not enough topic data yet.</p>}</Panel>
        <Panel><h2 className="font-medium">Strongest topics</h2>{a.strongest.length ? <ul className="mt-3 space-y-2 text-sm">{a.strongest.map((t, i) => <li key={i} className="flex justify-between"><span>{t.topic} <span className="text-ink-500">· {label(t.module)}</span></span><Chip tone={scoreTone(t.avg)}>{t.avg}%</Chip></li>)}</ul> : <p className="mt-3 text-sm text-ink-500">Not enough topic data yet.</p>}</Panel>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ roadmap
type Plan = { summary: string; source: string; weeks: { title: string; focus: string; tasks: { id: string; title: string; module: string; done: boolean }[] }[] };
export function RoadmapModule({ module }: { module: ModuleInfo }) {
  const [plan, setPlan] = useState<Plan | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { api<{ roadmap: Plan | null }>("/roadmap").then((r) => setPlan(r.roadmap)).catch((e) => { setPlan(null); setError(e.message); }); }, []);
  const generate = async () => { setBusy(true); setError(""); try { setPlan((await post<{ roadmap: Plan }>("/roadmap/generate")).roadmap); } catch (e) { setError(e instanceof Error ? e.message : "Failed"); } finally { setBusy(false); } };
  const toggle = async (id: string, done: boolean) => { try { setPlan((await put<{ roadmap: Plan }>("/roadmap/task", { id, done })).roadmap); } catch (e) { setError(e instanceof Error ? e.message : "Failed"); } };
  const all = plan?.weeks.flatMap((w) => w.tasks) ?? [];
  const done = all.filter((t) => t.done).length;
  return (
    <div className="space-y-6">
      <Header module={module} />
      {error && <Notice tone="red">{error}</Notice>}
      <div className="flex flex-wrap items-center gap-3"><button className="btn-primary" disabled={busy} onClick={generate}>{plan ? "Regenerate from my latest results" : "Create my roadmap"}</button>{busy && <Spinner label="Building your plan…" />}</div>
      {plan && (<>
        <Panel><p className="text-sm text-ink-700">{plan.summary}</p><div className="mt-4"><Bar label={`Progress: ${done} of ${all.length} tasks`} value={all.length ? (done / all.length) * 100 : 0} /></div></Panel>
        <div className="grid gap-4 md:grid-cols-2">{plan.weeks.map((w) => (
          <Panel key={w.title}><h2 className="font-medium">{w.title}</h2>{w.focus && <p className="text-sm text-ink-500">Focus: {w.focus}</p>}
            <ul className="mt-3 space-y-2">{w.tasks.map((t) => (
              <li key={t.id} className="flex items-start gap-3 rounded-md border border-slate-200 p-2.5 text-sm">
                <input type="checkbox" className="mt-0.5" checked={t.done} onChange={(e) => toggle(t.id, e.target.checked)} aria-label={t.title} />
                <div className="min-w-0 flex-1"><p className={t.done ? "text-ink-500 line-through" : ""}>{t.title}</p><Link href={route(t.module)} className="text-xs text-brand-700 hover:underline">Open {label(t.module)} →</Link></div>
              </li>))}</ul></Panel>))}</div>
      </>)}
    </div>
  );
}
