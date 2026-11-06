"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, post } from "@/lib/api";
import { announceReward, type Reward } from "@/lib/rewards";
import type { ModuleInfo } from "@/lib/modules";
import { Bar, Chip, Header, List, Notice, Panel, Ring, Spinner } from "@/components/ui";

type Row = { id: number; filename: string; score: number; ai_percent: number; created_at: string };
type SkillRow = { skill: string; status: "match" | "partial" | "missing"; evidence: string };
type Result = {
  score: number; verdict: string; how_calculated: string; summary: string; required_skills: SkillRow[]; preferred_skills: SkillRow[];
  experience_fit: { required?: string; candidate?: string; fit?: string }; education_fit: string; score_breakdown: Record<string, number>;
  keywords_found: string[]; keywords_missing: string[]; strengths: string[]; gaps: string[]; resume_improvements: { section: string; suggestion: string }[];
  interview_focus: string[]; source: string; resume: { id: number; filename: string; score: number };
};
const tone = { match: "green", partial: "amber", missing: "red" } as const;

export function JobMatchModule({ module }: { module: ModuleInfo }) {
  const [resumes, setResumes] = useState<Row[] | null>(null);
  const [resumeId, setResumeId] = useState<number | "">("");
  const [title, setTitle] = useState("");
  const [jd, setJd] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [res, setRes] = useState<Result | null>(null);

  useEffect(() => { api<Row[]>("/resume").then((r) => { setResumes(r); if (r[0]) setResumeId(r[0].id); }).catch((e) => { setResumes([]); setError(e.message); }); }, []);

  const run = async () => {
    setBusy(true); setError("");
    try {
      const r = await post<{ result: Result; reward: Reward }>("/job-match", { job_description: jd, job_title: title, resume_id: resumeId || null });
      setRes(r.result); announceReward(r.reward);
      setTimeout(() => document.getElementById("match-result")?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (e) { setError(e instanceof Error ? e.message : "Match failed"); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-8">
      <Header module={module} />
      {resumes && resumes.length === 0 ? (
        <Panel><Notice tone="amber">Job match compares the job description with your analyzed resume. <Link href="/resume" className="font-medium underline">Analyze your resume first</Link>, then come back.</Notice></Panel>
      ) : (
        <Panel>
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label className="label" htmlFor="jm-resume">Resume to use</label>
              <select id="jm-resume" className="input" value={resumeId} onChange={(e) => setResumeId(Number(e.target.value))}>
                {(resumes ?? []).map((r) => <option key={r.id} value={r.id}>{r.filename} · {r.score}% · {new Date(r.created_at).toLocaleDateString()}</option>)}
              </select><p className="hint">Uses the analysis of this resume: its skills, projects, experience and full text.</p></div>
            <div><label className="label" htmlFor="jm-title">Job title (optional)</label><input id="jm-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Backend Developer Intern" /></div>
          </div>
          <label className="label mt-4" htmlFor="jm-jd">Job description</label>
          <textarea id="jm-jd" rows={10} className="input" value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the full job description: responsibilities, required skills, preferred skills…" />
          {error && <div className="mt-4"><Notice tone="red">{error}</Notice></div>}
          <div className="mt-4 flex items-center gap-3"><button className="btn-primary" disabled={busy || jd.trim().length < 40 || !resumeId} onClick={run}>{busy ? "Matching…" : "Match resume to this job"}</button>{busy && <Spinner label="Comparing your resume with the job…" />}</div>
        </Panel>
      )}

      {res && (
        <div id="match-result" className="space-y-6">
          <Panel>
            <div className="flex flex-wrap items-center gap-8">
              <Ring value={res.score} label="Match" size={128} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2"><h2 className="text-xl font-semibold">{res.verdict}</h2>{res.source === "offline" && <Chip tone="amber">Offline estimate</Chip>}</div>
                <p className="mt-2 text-sm text-ink-700">{res.summary}</p>
                <p className="mt-2 text-xs text-ink-500">Resume used: {res.resume.filename}. How this was calculated: {res.how_calculated}.</p>
              </div>
            </div>
            {Object.keys(res.score_breakdown).length > 0 && <div className="mt-6 grid gap-4 sm:grid-cols-2">{Object.entries(res.score_breakdown).map(([k, v]) => <Bar key={k} label={k[0].toUpperCase() + k.slice(1)} value={v} />)}</div>}
          </Panel>

          <Panel>
            <h2 className="font-medium">Skills the job asks for</h2>
            <SkillTable title="Required" rows={res.required_skills} />
            {res.preferred_skills.length > 0 && <SkillTable title="Preferred" rows={res.preferred_skills} />}
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div><p className="mb-2 text-sm font-medium">Keywords found in your resume</p><div className="flex flex-wrap gap-1.5">{res.keywords_found.length ? res.keywords_found.map((k) => <Chip key={k} tone="green">{k}</Chip>) : <span className="text-sm text-ink-500">None</span>}</div></div>
              <div><p className="mb-2 text-sm font-medium">Keywords missing</p><div className="flex flex-wrap gap-1.5">{res.keywords_missing.length ? res.keywords_missing.map((k) => <Chip key={k} tone="red">{k}</Chip>) : <span className="text-sm text-ink-500">None</span>}</div></div>
            </div>
            {(res.experience_fit?.fit || res.education_fit) && (
              <div className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
                {res.experience_fit?.fit && <div className="rounded-md bg-slate-50 p-3"><p className="font-medium">Experience: {res.experience_fit.fit}</p><p className="mt-1 text-ink-700">Job wants: {res.experience_fit.required || "—"}<br />You have: {res.experience_fit.candidate || "—"}</p></div>}
                {res.education_fit && <div className="rounded-md bg-slate-50 p-3"><p className="font-medium">Education</p><p className="mt-1 text-ink-700">{res.education_fit}</p></div>}
              </div>
            )}
          </Panel>

          <Panel>
            <div className="grid gap-6 md:grid-cols-2">
              <div><p className="mb-2 font-medium">Where you fit</p>{res.strengths.length ? <List tone="good" items={res.strengths} /> : <p className="text-sm text-ink-500">No clear strengths found for this job.</p>}</div>
              <div><p className="mb-2 font-medium">Gaps to close</p>{res.gaps.length ? <List tone="bad" items={res.gaps} /> : <p className="text-sm text-ink-500">No major gaps.</p>}</div>
            </div>
            {res.resume_improvements.length > 0 && <div className="mt-6"><p className="mb-2 font-medium">Tailor your resume for this job</p><ul className="space-y-2">{res.resume_improvements.map((x, i) => <li key={i} className="rounded-md border border-slate-200 p-3 text-sm"><Chip tone="blue">{x.section}</Chip> <span className="ml-1">{x.suggestion}</span></li>)}</ul></div>}
            {res.interview_focus.length > 0 && <div className="mt-6"><p className="mb-2 font-medium">Expect interview questions on</p><List items={res.interview_focus} /></div>}
          </Panel>
        </div>
      )}
    </div>
  );
}

function SkillTable({ title, rows }: { title: string; rows: SkillRow[] }) {
  if (!rows.length) return null;
  return (
    <div className="mt-4"><p className="mb-2 text-sm font-medium text-ink-500">{title}</p>
      <ul className="divide-y divide-slate-200 rounded-md border border-slate-200">
        {rows.map((r, i) => (
          <li key={i} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm">
            <span className="font-medium">{r.skill}</span>
            <span className="flex items-center gap-3">{r.evidence && <span className="max-w-md text-xs text-ink-500">{r.evidence}</span>}<Chip tone={tone[r.status]}>{r.status === "match" ? "Matched" : r.status === "partial" ? "Partial" : "Missing"}</Chip></span>
          </li>
        ))}
      </ul>
    </div>
  );
}
